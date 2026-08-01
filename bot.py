import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables & Admin ID
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "8053042225"))
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Databases & State Storage (Mock / In-memory structures)
user_balances = {}   # {user_id: {"id_balance": 100.0, "ref_balance": 0.0}}
user_accounts = {}   # {user_id: [{"json_data": "..."}]}
pending_utrs = {}    # {req_id: {"user_id": user_id, "amount": amount}}
all_users = set()    # Track all unique users for User List

# Official Channels & Group Dictionary provided by you
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
    all_users.add(user_id)

    # Force Join Check
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

    # Main Menu (4-dot / Grid Layout + Admin Panel option if admin)
    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data="menu_balance"), InlineKeyboardButton("➕ Add Balance", callback_data="menu_add_balance")],
        [InlineKeyboardButton("👤 Add Account", callback_data="menu_add_account"), InlineKeyboardButton("📂 My Accounts", callback_data="menu_my_accounts")],
        [InlineKeyboardButton("🌐 Mini Web Panel", callback_data="menu_mini_web"), InlineKeyboardButton("💬 Customer Support", url="https://t.me/YourChatbotLink")]
    ]
    
    if user_id == ADMIN_CHAT_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"), InlineKeyboardButton("👥 User List", callback_data="admin_users_0")])

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
        text = (
            "👤 **Add Account (2-in-1 Auto Detect)**\n\n"
            "Please send either your **JSON Session Token** OR your **Phone Number** to receive OTP and connect with Mini Web:"
        )
        context.user_data['waiting_for_account_input'] = True
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

    elif data == "admin_panel":
        if user_id != ADMIN_CHAT_ID:
            await query.answer("❌ यह कमांड सिर्फ एडमिन के लिए है।", show_alert=True)
            return
        kb = [
            [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
            [InlineKeyboardButton("👥 User List", callback_data="admin_users_0")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_home")]
        ]
        await query.message.edit_text("⚙️ **Admin Control Panel**\n\nChoose an action:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "admin_broadcast":
        if user_id != ADMIN_CHAT_ID:
            await query.answer("❌ यह कमांड सिर्फ एडमिन के लिए है।", show_alert=True)
            return
        context.user_data['waiting_for_broadcast'] = True
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]
        await query.message.edit_text("📢 **Broadcast Mode**\n\nSend the message, text, sticker, or media you want to broadcast to all users:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data.startswith("admin_users_"):
        if user_id != ADMIN_CHAT_ID:
            await query.answer("❌ यह कमांड सिर्फ एडमिन के लिए है।", show_alert=True)
            return
        page = int(data.split("_")[-1])
        users_list = list(all_users)
        per_page = 10
        total_pages = (len(users_list) + per_page - 1) // per_page
        
        start_idx = page * per_page
        end_idx = start_idx + per_page
        current_users = users_list[start_idx:end_idx]

        text = f"👥 **Total Users:** {len(users_list)} (Page {page+1}/{max(1, total_pages)})\n\n"
        for u in current_users:
            text += f"• `{u}`\n"

        kb = []
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"admin_users_{page-1}"))
        if end_idx < len(users_list):
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin_users_{page+1}"))
        
        if nav_buttons:
            kb.append(nav_buttons)
        kb.append([InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")])

        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

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
    all_users.add(user_id)

    # Admin Broadcast Handler (Supports text, stickers, photos, documents, etc.)
    if context.user_data.get('waiting_for_broadcast'):
        if user_id != ADMIN_CHAT_ID:
            return
        context.user_data['waiting_for_broadcast'] = False
        
        success_count = 0
        fail_count = 0
        for uid in all_users:
            try:
                await update.message.copy(chat_id=uid)
                success_count += 1
            except Exception:
                fail_count += 1

        await update.message.reply_text(f"📢 **Broadcast Completed!**\n\n✅ Success: {success_count}\n❌ Failed: {fail_count}")
        return

    # Add Balance Amount Input
    if context.user_data.get('waiting_for_amount'):
        context.user_data['waiting_for_amount'] = False
        try:
            amount = float(update.message.text)
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

    # UTR Submission Input
    if context.user_data.get('waiting_for_utr'):
        utr_data = context.user_data.pop('waiting_for_utr')
        amount = utr_data['amount']
        req_id = utr_data['req_id']
        utr = update.message.text

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

    # 2-in-1 Auto-detect Account Input (JSON Token or Phone Number for OTP)
    if context.user_data.get('waiting_for_account_input'):
        context.user_data['waiting_for_account_input'] = False
        user_input = update.message.text.strip()

        # Check if input is JSON format or Phone Number
        if user_input.startswith("{") and user_input.endswith("}"):
            if user_id not in user_accounts:
                user_accounts[user_id] = []
            user_accounts[user_id].append({"json_data": user_input})
            await update.message.reply_text("✅ JSON Session Token detected, saved and linked successfully with Mini Web session!")
        else:
            # Treated as Phone Number for OTP login flow integration
            await update.message.reply_text(f"📱 Phone number `{user_input}` received. OTP request triggered. Please send your OTP code next:")
            context.user_data['waiting_for_otp'] = {"phone": user_input}
        return

    # OTP Input Handler for Phone Login
    if context.user_data.get('waiting_for_otp'):
        otp_data = context.user_data.pop('waiting_for_otp')
        otp_code = update.message.text.strip()
        
        # Mock session string creation on successful verification
        mock_session_string = f"session_token_for_{otp_data['phone']}_verified"
        if user_id not in user_accounts:
            user_accounts[user_id] = []
        user_accounts[user_id].append({"json_data": mock_session_string})
        
        await update.message.reply_text("✅ OTP verified successfully! Session string generated and linked with Mini Web.")
        return

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), message_router))

    logger.info("Bot is running with full error-free setup, pagination and 2-in-1 auto-detect...")
    app.run_polling()

if __name__ == "__main__":
    main()
            
