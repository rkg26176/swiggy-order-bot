import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "8053042225"))
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# In-Memory/Mock Databases (Railway/Firebase integration ready structure)
user_balances = {}  # {user_id: {"id_balance": 0.0, "ref_balance": 0.0}}
user_accounts = {}  # {user_id: [ {"account_name": "...", "json_data": "..."}, ... ]}
pending_utrs = {}   # {utr_id: {"user_id": user_id, "amount": amount}}

# Mandatory Channels for Force Join
FORCED_CHANNELS = ["@your_channel_username"]  # Replace/Add your channels here

async def check_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    for channel in FORCED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception as e:
            logger.error(f"Error checking channel {channel}: {e}")
            return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Force Join Check
    is_joined = await check_force_join(update, context)
    if not is_joined:
        keyboard = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FORCED_CHANNELS[0].replace('@', '')}")],
                    [InlineKeyboardButton("🔄 Check Join", callback_data="check_join")]]
        await update.message.reply_text("❌ Please join our channels first to use this bot!", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Initialize User Balance if not exists
    if user_id not in user_balances:
        user_balances[user_id] = {"id_balance": 100.0, "ref_balance": 0.0} # Starting mock balance for testing

    # Main Menu with 4-dot/grid layout buttons
    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data="menu_balance"), InlineKeyboardButton("➕ Add Balance", callback_data="menu_add_balance")],
        [InlineKeyboardButton("👤 Add Account", callback_data="menu_add_account"), InlineKeyboardButton("📂 My Accounts", callback_data="menu_my_accounts")],
        [InlineKeyboardButton("🌐 Mini Web Panel", callback_data="menu_mini_web"), InlineKeyboardButton("💬 Customer Support", url="https://t.me/YourSupportUsername")]
    ]
    
    text = (
        "🤖 **Welcome to the Automation Bot**\n\n"
        f"💳 **ID Balance:** ₹{user_balances[user_id]['id_balance']}\n"
        f"👥 **Referral Balance:** ₹{user_balances[user_id]['ref_balance']}\n\n"
        "Choose an option below:"
    )
    
    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "check_join":
        if await check_force_join(update, context):
            await query.message.delete()
            await start(update, context)
        else:
            await query.answer("❌ You haven't joined all channels yet!", show_alert=True)

    elif data == "menu_balance":
        bal = user_balances.get(user_id, {"id_balance": 0, "ref_balance": 0})
        text = f"💰 **Your Wallet Status**\n\nID Balance: ₹{bal['id_balance']}\nReferral Balance: ₹{bal['ref_balance']}"
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "menu_add_balance":
        text = "➕ **Add Balance System**\n\nPlease send the amount you want to add (e.g., type `500`):"
        context.user_data['waiting_for_amount'] = True
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "menu_add_account":
        text = "👤 **Add Account**\n\nPlease send your account JSON data to login and link with Mini Web session:"
        context.user_data['waiting_for_json'] = True
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "menu_my_accounts":
        accounts = user_accounts.get(user_id, [])
        if not accounts:
            text = "📂 You have no logged-in accounts currently."
        else:
            text = "📂 **Your Logged-in Accounts:**\nSelect an account to manage:"
        
        kb = []
        for idx, acc in enumerate(accounts):
            kb.append([InlineKeyboardButton(f"Account {idx+1}", callback_data=f"manage_acc_{idx}")])
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="back_home")])
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "menu_mini_web":
        # Mini Web link simulation with force join verification context inside bot view
        kb = [
            [InlineKeyboardButton("🚀 Open Mini Web", url="https://your-mini-web-url.com")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_home")]
        ]
        await query.message.edit_text("🌐 **Mini Web Dashboard**\n\nClick below to open the real-time panel securely inside the bot ecosystem:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "back_home":
        await start(update, context)

    elif data.startswith("manage_acc_"):
        acc_idx = int(data.split("_")[-1])
        kb = [
            [InlineKeyboardButton("📤 Export Auth JSON", callback_data=f"export_acc_{acc_idx}")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_my_accounts")]
        ]
        await query.message.edit_text(f"⚙️ **Manage Account #{acc_idx+1}**\nChoose an action:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data.startswith("export_acc_"):
        acc_idx = int(data.split("_")[-1])
        accounts = user_accounts.get(user_id, [])
        if accounts and len(accounts) > acc_idx:
            removed_acc = accounts.pop(acc_idx)
            text = f"✅ **Account Exported & Removed Successfully!**\n\n`{removed_acc['json_data']}`"
        else:
            text = "❌ Account not found."
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="menu_my_accounts")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data.startswith("approve_"):
        req_id = data.split("_")[1]
        if req_id in pending_utrs:
            req_data = pending_utrs[req_id]
            target_user = req_data["user_id"]
            amount = req_data["amount"]
            
            if target_user in user_balances:
                user_balances[target_user]["id_balance"] += amount
            
            await query.message.edit_text(f"✅ Approved! ₹{amount} added to User ID: {target_user}")
            try:
                await context.bot.send_message(chat_id=target_user, text=f"🎉 Your payment of ₹{amount} has been Approved and added to your balance!")
            except Exception:
                pass
            del pending_utrs[req_id]

    elif data.startswith("reject_"):
        req_id = data.split("_")[1]
        if req_id in pending_utrs:
            req_data = pending_utrs[req_id]
            target_user = req_data["user_id"]
            await query.message.edit_text(f"❌ Rejected payment request for User ID: {target_user}")
            try:
                await context.bot.send_message(chat_id=target_user, text="❌ Your payment request was rejected by admin.")
            except Exception:
                pass
            del pending_utrs[req_id]

async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if context.user_data.get('waiting_for_amount'):
        context.user_data['waiting_for_amount'] = False
        try:
            amount = float(text)
            req_id = str(user_id) + "_" + str(int(os.urandom(2).hex(), 16))
            pending_utrs[req_id] = {"user_id": user_id, "amount": amount}

            # Generate Mock QR and ask for UTR
            await update.message.reply_text(
                f"🧾 **QR Generated for Amount: ₹{amount}**\n\n"
                "Please scan the QR code, pay the amount, and send your **UTR / Transaction ID** here:"
            )
            context.user_data['waiting_for_utr'] = {"amount": amount, "req_id": req_id}
        except ValueError:
            await update.message.reply_text("❌ Invalid amount format. Please type numbers only.")
        return

    if context.user_data.get('waiting_for_utr'):
        utr_data = context.user_data.pop('waiting_for_utr')
        amount = utr_data['amount']
        req_id = utr_data['req_id']
        utr = text

        # Send to Admin for Approval/Rejection with inline web-like buttons
        admin_keyboard = [
            [InlineKeyboardButton("✅ Accept", callback_data=f"approve_{req_id}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_{req_id}")]
        ]
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"🔔 **New UTR Payment Verification**\n\nUser ID: `{user_id}`\nAmount: ₹{amount}\nUTR: `{utr}`",
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ UTR submitted successfully! Waiting for admin approval.")
        return

    if context.user_data.get('waiting_for_json'):
        context.user_data['waiting_for_json'] = False
        if user_id not in user_accounts:
            user_accounts[user_id] = []
        user_accounts[user_id].append({"json_data": text})
        await update.message.reply_text("✅ Account JSON saved and linked successfully with Mini Web session!")
        return

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_router))

    logger.info("Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
