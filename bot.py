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

# Databases & State Storage
user_balances = {}  # {user_id: {"id_balance": 100.0, "ref_balance": 0.0}}
user_accounts = {}  # {user_id: [{"json_data": "..."}]}
pending_utrs = {}   # {req_id: {"user_id": user_id, "amount": amount}}

# Channels and Group Chat dictionary with chat IDs and invite links
CHANNELS = {
    "-1003332858806": {
        "name": "📢 GBX LOOT",
        "url": "https://t.me/+6ByfGDRBKgsxMjZl",
    },
    "-1003630519339": {
        "name": "📢 GBX EARN",
        "url": "https://t.me/+OWrCoeF-JutmNjg1",
    },
    "-1003197501531": {
        "name": "📢 GBX ZONE",
        "url": "https://t.me/+f2mWfDs6EUIxYTBl",
    },
    "-1003862251237": {
        "name": "💬 Join Group Chat (GC)",
        "url": "https://t.me/+O_-kEF2f5f1kMjdl",
    },
}

async def check_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    for chat_id in CHANNELS.keys():
        try:
            member = await context.bot.get_chat_member(chat_id=int(chat_id), user_id=user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception as e:
            logger.error(f"Error checking chat {chat_id}: {e}")
            return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Check Force Join for all channels and group chat
    if not await check_force_join(update, context):
        keyboard = []
        for chat_id, info in CHANNELS.items():
            keyboard.append([InlineKeyboardButton(info["name"], url=info["url"])])
        keyboard.append([InlineKeyboardButton("🔄 Check Join Status", callback_data="check_join")])
        
        text = "❌ **Access Denied!**\nYou must join all the channels and group chat below to use this bot:"
        if update.callback_query:
            await update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    # Initialize Balance
    if user_id not in user_balances:
        user_balances[user_id] = {"id_balance": 100.0, "ref_balance": 0.0}

    # Main Menu (4-dot / Grid Layout)
    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data="menu_balance"), InlineKeyboardButton("➕ Add Balance", callback_data="menu_add_balance")],
        [InlineKeyboardButton("👤 Add Account", callback_data="menu_add_account"), InlineKeyboardButton("📂 My Accounts", callback_data="menu_my_accounts")],
        [InlineKeyboardButton("🌐 Mini Web Panel", callback_data="menu_mini_web"), InlineKeyboardButton("💬 Customer Support", url="https://t.me/YourChatbotLink")]
    ]

    text = (
        "🤖 **Main Dashboard**\n\n"
        f"💳 **ID Balance:** ₹{user_balances[user_id]['id_balance']}\n"
        f"👥 **Referral Balance:** ₹{user_balances[user_id]['ref_balance']}\n\n"
        "Select an option below:"
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
            await start(update, context)
        else:
            await query.answer("❌ You haven't joined all required chats yet!", show_alert=True)

    elif data == "menu_balance":
        bal = user_balances.get(user_id, {"id_balance": 0, "ref_balance": 0})
        text = f"💰 **Wallet Overview**\n\nID Balance: ₹{bal['id_balance']}\nReferral Balance: ₹{bal['ref_balance']}"
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "menu_add_balance":
        text = "➕ **Add Balance**\n\nSend the exact amount you want to add (e.g., `500`):"
        context.user_data['waiting_for_amount'] = True
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "menu_add_account":
        text = "👤 **Add Account**\n\nPlease send your account JSON data to connect with the Mini Web session:"
        context.user_data['waiting_for_json'] = True
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "menu_my_accounts":
        accounts = user_accounts.get(user_id, [])
        if not accounts:
            text = "📂 No active accounts found. Please add an account first."
            kb = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        else:
            text = "📂 **Your Logged-in Accounts:**\nSelect an account to manage:"
            kb = []
            for idx, acc in enumerate(accounts):
                kb.append([InlineKeyboardButton(f"Account {idx+1}", callback_data=f"manage_acc_{idx}")])
            kb.append([InlineKeyboardButton("🔙 Back", callback_data="back_home")])
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "menu_mini_web":
        kb = [
            [InlineKeyboardButton("🚀 Launch Mini Web", url="https://your-mini-web-app.com")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_home")]
        ]
        await query.message.edit_text("🌐 **Mini Web Dashboard**\n\nReal-time monitoring panel connected with your bot accounts:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

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
            removed = accounts.pop(acc_idx)
            text = f"✅ **Account Exported Successfully! Session Removed.**\n\n`{removed['json_data']}`"
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
                await context.bot.send_message(chat_id=target_user, text=f"🎉 Your payment of ₹{amount} has been approved by admin!")
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

            await update.message.reply_text(
                f"🧾 **QR Code Generated for ₹{amount}**\n\n"
                "Scan and pay, then send your **UTR / Transaction ID** here:"
            )
            context.user_data['waiting_for_utr'] = {"amount": amount, "req_id": req_id}
        except ValueError:
            await update.message.reply_text("❌ Please enter valid numbers only.")
        return

    if context.user_data.get('waiting_for_utr'):
        utr_data = context.user_data.pop('waiting_for_utr')
        amount = utr_data['amount']
        req_id = utr_data['req_id']
        utr = text

        admin_keyboard = [
            [InlineKeyboardButton("✅ Accept", callback_data=f"approve_{req_id}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_{req_id}")]
        ]
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"🔔 **New UTR Verification Request**\n\nUser ID: `{user_id}`\nAmount: ₹{amount}\nUTR: `{utr}`",
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ UTR sent to admin for verification!")
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

    logger.info("Bot is running with exact channels and group configuration...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
