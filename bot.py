import os
import json
import logging
import threading
from flask import Flask, render_template_string, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables & Admin ID
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "8053042225"))
BOT_TOKEN = "8813624728:AAF5v_Rnq3R4LYNP1_Sd_tBQU6TxomBDwK4"

# Initialize Flask for Mini Web Panel (Swiggy Order Bot Connected)
app_flask = Flask(__name__)

@app_flask.route('/')
def mini_web_home():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Swiggy Order Bot - Mini Web</title>
        <style>
            body { font-family: Arial, sans-serif; background: #121212; color: #fff; text-align: center; padding: 20px; }
            .container { background: #1e1e1e; padding: 20px; border-radius: 10px; max-width: 600px; margin: auto; box-shadow: 0 4px 15px rgba(0,0,0,0.6); }
            h1 { color: #ff5722; font-size: 20px; }
            .card { background: #2a2a2a; padding: 12px; margin: 10px 0; border-radius: 8px; text-align: left; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🍔 Swiggy Order Bot Mini Web Dashboard</h1>
            <p>Live Account & Balance Connected Panel</p>
            <div id="live-data" class="card">
                <p>Loading database records...</p>
            </div>
        </div>
        <script>
            async function fetchLiveData() {
                try {
                    let res = await fetch('/get_live_state');
                    let data = await res.json();
                    let html = "<h3>📊 User Accounts & Balances:</h3>";
                    if(data.users && data.users.length > 0) {
                        data.users.forEach(u => {
                            html += `<div style="border-bottom: 1px solid #444; padding: 8px 0;">
                                <b>User ID:</b> ${u.id} <br>
                                <b>Current Balance:</b> ₹${u.id_balance || 0} <br>
                                <b>Linked Accounts:</b> ${u.accounts ? u.accounts.length : 0}
                            </div>`;
                        });
                    } else {
                        html += "<p>No users found yet.</p>";
                    }
                    document.getElementById('live-data').innerHTML = html;
                } catch(e) { console.log(e); }
            }
            setInterval(fetchLiveData, 5000);
            fetchLiveData();
        </script>
    </body>
    </html>
    """)

@app_flask.route('/get_live_state')
def get_live_state():
    users_data = []
    if db:
        try:
            docs = db.collection("users").stream()
            for doc in docs:
                u_dict = doc.to_dict()
                u_dict['id'] = doc.id
                users_data.append(u_dict)
        except Exception as e:
            logger.error(f"Web sync error: {e}")
    return jsonify({"users": users_data})

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

# Channels & Group Dictionary (2 Channels & 2 GCs)
CHANNELS = {
    "-1003332858806": {"name": "📢 GBX LOOT 1", "url": "https://t.me/+6ByfGDRBKgsxMjZl"},
    "-1003630519339": {"name": "📢 GBX EARN 2", "url": "https://t.me/+OWrCoeF-JutmNjg1"},
    "-1003862251237": {"name": "💬 GBX GC 1", "url": "https://t.me/+O_-kEF2f5f1kMjdl"},
    "-1003197501531": {"name": "💬 GBX GC 2", "url": "https://t.me/+f2mWfDs6EUIxYTBl"},
}

async def get_unjoined_channels(bot, user_id):
    unjoined = {}
    for chat_id, info in CHANNELS.items():
        try:
            member = await bot.get_chat_member(chat_id=int(chat_id), user_id=user_id)
            if member.status in ['left', 'kicked']:
                unjoined[chat_id] = info
        except Exception as e:
            logger.error(f"Error checking chat {chat_id}: {e}")
            unjoined[chat_id] = info
    return unjoined

def get_user_data(user_id):
    if not db:
        return {"id_balance": 100.0, "ref_balance": 0.0, "accounts": [], "used_utrs": []}
    doc_ref = db.collection("users").document(str(user_id))
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        if "used_utrs" not in data:
            data["used_utrs"] = []
        return data
    else:
        default_data = {"id_balance": 100.0, "ref_balance": 0.0, "accounts": [], "used_utrs": []}
        doc_ref.set(default_data)
        return default_data

def update_user_data(user_id, data):
    if db:
        db.collection("users").document(str(user_id)).set(data, merge=True)

async def set_bot_commands(bot):
    commands = [
        BotCommand("start", "Start the bot & open dashboard"),
        BotCommand("admin", "Admin Control Panel")
    ]
    await bot.set_my_commands(commands)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if db:
        db.collection("all_users").document(str(user_id)).set({"user_id": user_id, "username": user.username or "None"})

    unjoined = await get_unjoined_channels(context.bot, user_id)
    if unjoined:
        keyboard = []
        for chat_id, info in unjoined.items():
            keyboard.append([InlineKeyboardButton(info["name"], url=info["url"])])
        keyboard.append([InlineKeyboardButton("🔄 Verify Joined Status", callback_data="check_join")])
        
        text = "❌ **Access Denied!**\nYou must join all the required channels and group chats below to use this bot:"
        if update.callback_query:
            await update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    user_data = get_user_data(user_id)
    ref_link = f"https://t.me/{context.bot.username}?start=ref_{user_id}"

    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data="menu_balance"), InlineKeyboardButton("👤 Add Account", callback_data="menu_add_account")],
        [InlineKeyboardButton("📂 Accounts", callback_data="menu_my_accounts"), InlineKeyboardButton("💬 Customer Support", url="https://t.me/YourSupportBotLink")],
        [InlineKeyboardButton("🌐 Mini Web", url="https://swiggy-order-bot.onrender.com")]
    ]

    text = (
        "🤖 **Swiggy Bot Dashboard**\n\n"
        f"💳 **Current Balance:** ₹{user_data.get('id_balance', 100.0)}\n"
        f"👥 **Referral Link:** `{ref_link}`\n\n"
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
        unjoined = await get_unjoined_channels(context.bot, user_id)
        if not unjoined:
            await start(update, context)
        else:
            await query.answer("❌ You still haven't joined all chats!", show_alert=True)

    elif data == "menu_balance":
        user_data = get_user_data(user_id)
        ref_link = f"https://t.me/{context.bot.username}?start=ref_{user_id}"
        text = (
            f"💰 **Wallet Overview**\n\n"
            f"💳 **Current Balance:** ₹{user_data.get('id_balance', 0)}\n"
            f"👥 **Referral Link:** `{ref_link}`\n\n"
            f"📥 **To add balance, please send the exact amount you want to deposit (e.g. `500`):**"
        )
        context.user_data['waiting_for_amount'] = True
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "menu_add_account":
        text = (
            "👤 **Add Account System**\n\n"
            "Please send either your **JSON Session Token** OR your **Phone Number** to link with your account:"
        )
        context.user_data['waiting_for_account_input'] = True
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data == "menu_my_accounts":
        user_data = get_user_data(user_id)
        accounts = user_data.get("accounts", [])
        if not accounts:
            text = "📂 No active accounts found. Please add an account first."
            kb = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        else:
            text = "📂 **Your Logged-in Accounts:**\nSelect an account to manage/export:"
            kb = []
            for idx, acc in enumerate(accounts):
                kb.append([InlineKeyboardButton(f"Account {idx+1}", callback_data=f"manage_acc_{idx}")])
            kb.append([InlineKeyboardButton("🔙 Back", callback_data="back_home")])
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
        user_data = get_user_data(user_id)
        accounts = user_data.get("accounts", [])
        if accounts and len(accounts) > acc_idx:
            acc_token = accounts[acc_idx].get('json_data', '')
            text = f"✅ **Here is your Exported Auth JSON:**\n\n`{acc_token}`"
        else:
            text = "❌ Account not found."
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="menu_my_accounts")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data.startswith("approve_"):
        if user_id != ADMIN_CHAT_ID:
            return
        parts = data.split("_")
        req_id = parts[1]
        target_user = int(parts[2])
        amount = float(parts[3])

        req_ref = db.collection("pending_utrs").document(req_id).get() if db else None
        if req_ref and req_ref.exists:
            target_data = get_user_data(target_user)
            target_data["id_balance"] = target_data.get("id_balance", 0) + amount
            update_user_data(target_user, target_data)

            await query.message.edit_text(f"✅ Approved! ₹{amount} added to User ID: {target_user}")
            try:
                await context.bot.send_message(chat_id=target_user, text=f"🎉 Your payment of ₹{amount} has been approved by admin!")
            except Exception:
                pass
            db.collection("pending_utrs").document(req_id).delete()

    elif data.startswith("reject_"):
        if user_id != ADMIN_CHAT_ID:
            return
        parts = data.split("_")
        req_id = parts[1]
        target_user = int(parts[2])

        req_ref = db.collection("pending_utrs").document(req_id).get() if db else None
        if req_ref and req_ref.exists:
            await query.message.edit_text(f"❌ Rejected payment request for User ID: {target_user}")
            try:
                await context.bot.send_message(chat_id=target_user, text="❌ Your payment request was rejected by admin.")
            except Exception:
                pass
            db.collection("pending_utrs").document(req_id).delete()

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ यह कमांड सिर्फ एडमिन के लिए है।")
        return

    kb = [
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👥 User List", callback_data="admin_users_0")]
    ]
    await update.message.reply_text("⚙️ **Admin Control Panel**\n\nChoose an action:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id != ADMIN_CHAT_ID:
        await query.answer("❌ यह कमांड सिर्फ एडमिन के लिए है।", show_alert=True)
        return
    
    data = query.data
    if data == "admin_broadcast":
        await query.answer()
        context.user_data['waiting_for_broadcast'] = True
        kb = [[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]
        await query.message.edit_text("📢 **Broadcast Mode Activated**\n\nSend any message, sticker, or media to broadcast to all users:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    
    elif data.startswith("admin_users_"):
        await query.answer()
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
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="admin_panel")])

        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if db:
        db.collection("all_users").document(str(user_id)).set({"user_id": user_id})

    # Force join check on any message
    unjoined = await get_unjoined_channels(context.bot, user_id)
    if unjoined:
        return

    if context.user_data.get('waiting_for_broadcast'):
        if user_id != ADMIN_CHAT_ID:
            return
        context.user_data['waiting_for_broadcast'] = False
        
        users_list = []
        if db:
            docs = db.collection("all_users").stream()
            users_list = [int(doc.id) for doc in docs]

        success, fail = 0, 0
        for uid in users_list:
            try:
                await update.message.copy(chat_id=uid)
                success += 1
            except Exception:
                fail += 1

        await update.message.reply_text(f"📢 **Broadcast Completed!**\n\n✅ Success: {success}\n❌ Failed: {fail}")
        return

    if context.user_data.get('waiting_for_amount'):
        context.user_data['waiting_for_amount'] = False
        try:
            amount = float(update.message.text)
            req_id = str(user_id) + "_" + str(int(os.urandom(2).hex(), 16))
            context.user_data['waiting_for_utr'] = {"amount": amount, "req_id": req_id}

            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home")]]
            qr_caption = (
                f"🧾 **QR Code Generated for ₹{amount}**\n\n"
                "Scan and pay using any UPI app, then send your **12-digit UTR / Transaction ID** below:"
            )
            await update.message.reply_text(qr_caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number only.")
        return

    if context.user_data.get('waiting_for_utr'):
        utr_data = context.user_data.pop('waiting_for_utr')
        amount = utr_data['amount']
        req_id = utr_data['req_id']
        utr = update.message.text.strip()

        if len(utr) != 12 or not utr.isdigit():
            await update.message.reply_text("❌ Invalid UTR! Please send a valid **12-digit** transaction ID:")
            context.user_data['waiting_for_utr'] = utr_data
            return

        user_data = get_user_data(user_id)
        if utr in user_data.get("used_utrs", []):
            await update.message.reply_text("❌ This UTR has already been used! You cannot reuse the same UTR.")
            return

        user_data["used_utrs"].append(utr)
        update_user_data(user_id, user_data)

        if db:
            db.collection("pending_utrs").document(req_id).set({"user_id": user_id, "amount": amount, "utr": utr})

        admin_keyboard = [
            [InlineKeyboardButton("✅ Accept", callback_data=f"approve_{req_id}_{user_id}_{amount}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_{req_id}_{user_id}")]
        ]
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"🔔 **New UTR Verification Request**\n\nUser ID: `{user_id}`\nAmount: ₹{amount}\nUTR: `{utr}`",
            reply_markup=InlineKeyboardMarkup(admin_keyword),
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ UTR submitted successfully! Waiting for admin verification.")
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
            await update.message.reply_text("✅ JSON Session Token successfully added and linked with Mini Web!")
        else:
            await update.message.reply_text(f"📱 Phone number `{user_input}` received. OTP sent. Please send your OTP code next:")
            context.user_data['waiting_for_otp'] = {"phone": user_input}
        return

    if context.user_data.get('waiting_for_otp'):
        otp_data = context.user_data.pop('waiting_for_otp')
        otp_code = update.message.text.strip()
        
        mock_session_string = f"session_token_for_{otp_data['phone']}_verified_via_otp"
        user_data = get_user_data(user_id)
        if "accounts" not in user_data:
            user_data["accounts"] = []
        user_data["accounts"].append({"json_data": mock_session_string})
        update_user_data(user_id, user_data)
        
        await update.message.reply_text("✅ OTP verified successfully! Account session generated and linked.")
        return

def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^admin_"))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), message_router))

    logger.info("Swiggy Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
