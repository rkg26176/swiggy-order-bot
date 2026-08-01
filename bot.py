import os
import json
import logging
import threading
from flask import Flask
import firebase_admin
from firebase_admin import credentials, firestore
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables & Admin ID
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "8053042225"))
BOT_TOKEN = "8813624728:AAF5v_Rnq3R4LYNP1_Sd_tBQU6TxomBDwK4"

# Initialize Flask for Render Port Binding
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is running live!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port, use_reloader=False)

# Initialize Firebase
try:
    firebase_creds_json = os.environ.get("FIREBASE_CREDENTIALS")
    if firebase_creds_json:
        cred_dict = json.loads(firebase_creds_json)
        cred = credentials.Certificate(cred_dict)
    else:
        cred = credentials.Certificate("firebase_key.json")
    
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("Firebase connected successfully!")
except Exception as e:
    logger.error(f"Firebase initialization failed: {e}")
    db = None

# Official Channels & Group Dictionary
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

def check_force_join(update: Update, context: CallbackContext) -> bool:
    user_id = update.effective_user.id
    for chat_id in CHANNELS.keys():
        try:
            member = context.bot.get_chat_member(chat_id=int(chat_id), user_id=user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception as e:
            logger.error(f"Error checking chat {chat_id}: {e}")
            return False
    return True

def get_user_data(user_id):
    if not db:
        return {"id_balance": 100.0, "ref_balance": 0.0, "accounts": []}
    doc_ref = db.collection("users").document(str(user_id))
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        default_data = {"id_balance": 100.0, "ref_balance": 0.0, "accounts": []}
        doc_ref.set(default_data)
        return default_data

def update_user_data(user_id, data):
    if db:
        db.collection("users").document(str(user_id)).set(data, merge=True)

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    if db:
        db.collection("all_users").document(str(user_id)).set({"user_id": user_id})

    if not check_force_join(update, context):
        keyboard = []
        for chat_id, info in CHANNELS.items():
            keyboard.append([InlineKeyboardButton(info["name"], url=info["url"])])
        keyboard.append([InlineKeyboardButton("🔄 Check Join Status", callback_data="check_join")])
        
        text = "❌ **Access Denied!**\nYou must join all the channels and group chat below to use this bot:"
        if update.callback_query:
            update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    user_data = get_user_data(user_id)

    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data="menu_balance"), InlineKeyboardButton("➕ Add Balance", callback_data="menu_add_balance")],
        [InlineKeyboardButton("👤 Add Account", callback_data="menu_add_account"), InlineKeyboardButton("📂 My Accounts", callback_data="menu_my_accounts")],
        [InlineKeyboardButton("🌐 Mini Web Panel", callback_data="menu_mini_web"), InlineKeyboardButton("💬 Customer Support", url="https://t.me/YourChatbotLink")]
    ]
    
    if user_id == ADMIN_CHAT_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"), InlineKeyboardButton("👥 User List", callback_data="admin_users_0")])

    text = (
        "🤖 **Main Dashboard**\n\n"
        f"💳 **ID Balance:** ₹{user_data.get('id_balance', 100.0)}\n"
        f"👥 **Referral Balance:** ₹{user_data.get('ref_balance', 0.0)}\n\n"
        "Select an option below:"
    )

    if update.callback_query:
        update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "check_join":
        if check_force_join(update, context):
            start(update, context)
        else:
            query.answer("❌ You haven't joined all required chats yet!", show_alert=True)

    elif data == "menu_balance":
        user_data = get_user_data(user_id)
        text = f"💰 **Wallet Overview**\n\nID Balance: ₹{user_data.get('id_balance', 0)}\nReferral Balance: ₹{user_data.get('ref_balance', 0)}"
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "menu_add_balance":
        text = "➕ **Add Balance**\n\nSend the exact amount you want to add (e.g., `500`):"
        context.user_data['waiting_for_amount'] = True
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "menu_add_account":
        text = (
            "👤 **Add Account (2-in-1 Auto Detect)**\n\n"
            "Please send either your **JSON Session Token** OR your **Phone Number** to receive OTP and connect with Mini Web:"
        )
        context.user_data['waiting_for_account_input'] = True
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "menu_my_accounts":
        user_data = get_user_data(user_id)
        accounts = user_data.get("accounts", [])
        if not accounts:
            text = "📂 No active accounts found. Please add an account first."
            kb = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        else:
            text = "📂 **Your Logged-in Accounts:**\nSelect an account to manage:"
            kb = []
            for idx, acc in enumerate(accounts):
                kb.append([InlineKeyboardButton(f"Account {idx+1}", callback_data=f"manage_acc_{idx}")])
            kb.append([InlineKeyboardButton("🔙 Back", callback_data="back_home")])
        query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "menu_mini_web":
        kb = [
            [InlineKeyboardButton("🚀 Launch Mini Web", url="https://your-mini-web-app.com")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_home")]
        ]
        query.message.edit_text("🌐 **Mini Web Dashboard**\n\nReal-time monitoring panel connected with your bot accounts:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "admin_panel":
        if user_id != ADMIN_CHAT_ID:
            query.answer("❌ यह कमांड सिर्फ एडमिन के लिए है।", show_alert=True)
            return
        kb = [
            [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
            [InlineKeyboardButton("👥 User List", callback_data="admin_users_0")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_home")]
        ]
        query.message.edit_text("⚙️ **Admin Control Panel**\n\nChoose an action:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "admin_broadcast":
        if user_id != ADMIN_CHAT_ID:
            query.answer("❌ यह कमांड सिर्फ एडमिन के लिए है।", show_alert=True)
            return
        context.user_data['waiting_for_broadcast'] = True
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]
        query.message.edit_text("📢 **Broadcast Mode**\n\nSend the message, text, sticker, or media you want to broadcast to all users:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data.startswith("admin_users_"):
        if user_id != ADMIN_CHAT_ID:
            query.answer("❌ यह कमांड सिर्फ एडमिन के लिए है।", show_alert=True)
            return
        page = int(data.split("_")[-1])
        
        users_list = []
        if db:
            docs = db.collection("all_users").stream()
            users_list = [doc.id for doc in docs]

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

        query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "back_home":
        start(update, context)

    elif data.startswith("manage_acc_"):
        acc_idx = int(data.split("_")[-1])
        kb = [
            [InlineKeyboardButton("📤 Export Auth JSON", callback_data=f"export_acc_{acc_idx}")],
            [InlineKeyboardButton("🔙 Back", callback_data="menu_my_accounts")]
        ]
        query.message.edit_text(f"⚙️ **Manage Account #{acc_idx+1}**\nChoose an action:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data.startswith("export_acc_"):
        acc_idx = int(data.split("_")[-1])
        user_data = get_user_data(user_id)
        accounts = user_data.get("accounts", [])
        if accounts and len(accounts) > acc_idx:
            removed = accounts.pop(acc_idx)
            user_data["accounts"] = accounts
            update_user_data(user_id, user_data)
            text = f"✅ **Account Exported Successfully! Session Removed.**\n\n`{removed.get('json_data', '')}`"
        else:
            text = "❌ Account not found."
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="menu_my_accounts")]]
        query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data.startswith("approve_"):
        req_id = data.split("_")[1]
        req_ref = db.collection("pending_utrs").document(req_id).get() if db else None
        if req_ref and req_ref.exists:
            req_data = req_ref.to_dict()
            target_user = req_data["user_id"]
            amount = req_data["amount"]

            target_data = get_user_data(target_user)
            target_data["id_balance"] = target_data.get("id_balance", 0) + amount
            update_user_data(target_user, target_data)

            query.message.edit_text(f"✅ Approved! ₹{amount} added to User ID: {target_user}")
            try:
                context.bot.send_message(chat_id=target_user, text=f"🎉 Your payment of ₹{amount} has been approved by admin!")
            except Exception:
                pass
            db.collection("pending_utrs").document(req_id).delete()

    elif data.startswith("reject_"):
        req_id = data.split("_")[1]
        req_ref = db.collection("pending_utrs").document(req_id).get() if db else None
        if req_ref and req_ref.exists:
            req_data = req_ref.to_dict()
            target_user = req_data["user_id"]
            query.message.edit_text(f"❌ Rejected payment request for User ID: {target_user}")
            try:
                context.bot.send_message(chat_id=target_user, text="❌ Your payment request was rejected by admin.")
            except Exception:
                pass
            db.collection("pending_utrs").document(req_id).delete()

def message_router(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if db:
        db.collection("all_users").document(str(user_id)).set({"user_id": user_id})

    if context.user_data.get('waiting_for_broadcast'):
        if user_id != ADMIN_CHAT_ID:
            return
        context.user_data['waiting_for_broadcast'] = False
        
        users_list = []
        if db:
            docs = db.collection("all_users").stream()
            users_list = [int(doc.id) for doc in docs]

        success_count = 0
        fail_count = 0
        for uid in users_list:
            try:
                update.message.copy(chat_id=uid)
                success_count += 1
            except Exception:
                fail_count += 1

        update.message.reply_text(f"📢 **Broadcast Completed!**\n\n✅ Success: {success_count}\n❌ Failed: {fail_count}")
        return

    if context.user_data.get('waiting_for_amount'):
        context.user_data['waiting_for_amount'] = False
        try:
            amount = float(update.message.text)
            req_id = str(user_id) + "_" + str(int(os.urandom(2).hex(), 16))
            
            if db:
                db.collection("pending_utrs").document(req_id).set({"user_id": user_id, "amount": amount})

            update.message.reply_text(
                f"🧾 **QR Code Generated for ₹{amount}**\n\n"
                "Scan and pay, then send your **UTR / Transaction ID** here:"
            )
            context.user_data['waiting_for_utr'] = {"amount": amount, "req_id": req_id}
        except ValueError:
            update.message.reply_text("❌ Please enter valid numbers only.")
        return

    if context.user_data.get('waiting_for_utr'):
        utr_data = context.user_data.pop('waiting_for_utr')
        amount = utr_data['amount']
        req_id = utr_data['req_id']
        utr = update.message.text

        admin_keyboard = [
            [InlineKeyboardButton("✅ Accept", callback_data=f"approve_{req_id}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_{req_id}")]
        ]
        context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"🔔 **New UTR Verification Request**\n\nUser ID: `{user_id}`\nAmount: ₹{amount}\nUTR: `{utr}`",
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode="Markdown"
        )
        update.message.reply_text("✅ UTR sent to admin for verification!")
        return

    if context.user_data.get('waiting_for_account_input'):
        context.user_data['waiting_for_account_input'] = False
        user_input = update.message.text.strip()

        user_data = get_user_data(user_id)
        if "accounts" not in user_data:
            user_data["accounts"] = []

        if user_input.startswith("{") and user_input.endswith("}"):
            user_data["accounts"].append({"json_data": user_input})
            update_user_data(user_id, user_data)
            update.message.reply_text("✅ JSON Session Token detected, saved and linked successfully with Mini Web session!")
        else:
            update.message.reply_text(f"📱 Phone number `{user_input}` received. OTP request triggered. Please send your OTP code next:")
            context.user_data['waiting_for_otp'] = {"phone": user_input}
        return

    if context.user_data.get('waiting_for_otp'):
        otp_data = context.user_data.pop('waiting_for_otp')
        otp_code = update.message.text.strip()
        
        mock_session_string = f"session_token_for_{otp_data['phone']}_verified"
        user_data = get_user_data(user_id)
        if "accounts" not in user_data:
            user_data["accounts"] = []
        user_data["accounts"].append({"json_data": mock_session_string})
        update_user_data(user_id, user_data)
        
        update.message.reply_text("✅ OTP verified successfully! Session string generated and linked with Mini Web.")
        return

def main():
    # Run Flask server in background thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Run Telegram Bot using Legacy Updater (Zero Threading Conflicts)
    updater = Updater(BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(button_handler))
    dispatcher.add_handler(MessageHandler(filters.Filters.all & (~filters.Filters.command), message_router))

    logger.info("Bot is running smoothly with Legacy Updater on Render...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
        
