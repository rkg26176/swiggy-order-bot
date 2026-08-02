import os
import json
import logging
import threading
from flask import Flask, render_template_string, jsonify, request
import firebase_admin
from firebase_admin import credentials, firestore
import telebot
from telebot import types

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables & Admin ID
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "8053042225"))
BOT_TOKEN = "8813624728:AAF5v_Rnq3R4LYNP1_Sd_tBQU6TxomBDwK4"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# Initialize Flask for Webhook & Mini Web Dashboard
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

# Telegram Webhook Route
@app_flask.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Forbidden', 403

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

# Channels & Group Dictionary
CHANNELS = {
    "-1003332858806": {"name": "📢 GBX LOOT 1", "url": "https://t.me/+6ByfGDRBKgsxMjZl"},
    "-1003630519339": {"name": "📢 GBX EARN 2", "url": "https://t.me/+OWrCoeF-JutmNjg1"},
    "-1003862251237": {"name": "💬 GBX GC 1", "url": "https://t.me/+O_-kEF2f5f1kMjdl"},
    "-1003197501531": {"name": "💬 GBX GC 2", "url": "https://t.me/+f2mWfDs6EUIxYTBl"},
}

def get_unjoined_channels(user_id):
    unjoined = {}
    for chat_id, info in CHANNELS.items():
        try:
            member = bot.get_chat_member(chat_id=int(chat_id), user_id=user_id)
            if member.status in ['left', 'kicked']:
                unjoined[chat_id] = info
        except Exception:
            pass
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

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    if db:
        db.collection("all_users").document(str(user_id)).set({"user_id": user_id, "username": message.from_user.username or "None"})

    unjoined = get_unjoined_channels(user_id)
    if unjoined:
        keyboard = types.InlineKeyboardMarkup()
        for chat_id, info in unjoined.items():
            keyboard.add(types.InlineKeyboardButton(text=info["name"], url=info["url"]))
        keyboard.add(types.InlineKeyboardButton(text="🔄 Verify Joined Status", callback_data="check_join"))
        
        bot.send_message(
            user_id,
            "❌ **Access Denied!**\nYou must join all the required channels and group chats below to use this bot:",
            reply_markup=keyboard
        )
        return

    user_data = get_user_data(user_id)
    ref_link = f"https://t.me/{bot.get_me().username}?start=ref_{user_id}"

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(text="💰 Balance", callback_data="menu_balance"),
        types.InlineKeyboardButton(text="👤 Add Account", callback_data="menu_add_account"),
        types.InlineKeyboardButton(text="📂 Accounts", callback_data="menu_my_accounts"),
        types.InlineKeyboardButton(text="💬 Support", url="https://t.me/YourSupportBotLink"),
        types.InlineKeyboardButton(text="🌐 Mini Web", url="https://swiggy-order-bot.onrender.com")
    )

    text = (
        "🤖 **Swiggy Bot Dashboard**\n\n"
        f"💳 **Current Balance:** ₹{user_data.get('id_balance', 100.0)}\n"
        f"👥 **Referral Link:** `{ref_link}`\n\n"
        "Select an option below:"
    )
    bot.send_message(user_id, text, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    data = call.data

    if data == "check_join":
        unjoined = get_unjoined_channels(user_id)
        if not unjoined:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            start_command(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ You still haven't joined all chats!", show_alert=True)

    elif data == "menu_balance":
        user_data = get_user_data(user_id)
        ref_link = f"https://t.me/{bot.get_me().username}?start=ref_{user_id}"
        text = (
            f"💰 **Wallet Overview**\n\n"
            f"💳 **Current Balance:** ₹{user_data.get('id_balance', 0)}\n"
            f"👥 **Referral Link:** `{ref_link}`\n\n"
            f"📥 **To add balance, please send the exact amount you want to deposit (e.g. `500`):**"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_home"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif data == "menu_add_account":
        text = (
            "👤 **Add Account System**\n\n"
            "Please send either your **JSON Session Token** OR your **Phone Number** to link with your account:"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_home"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif data == "menu_my_accounts":
        user_data = get_user_data(user_id)
        accounts = user_data.get("accounts", [])
        kb = types.InlineKeyboardMarkup()
        if not accounts:
            text = "📂 No active accounts found. Please add an account first."
        else:
            text = "📂 **Your Logged-in Accounts:**\nSelect an account to manage/export:"
            for idx, acc in enumerate(accounts):
                kb.add(types.InlineKeyboardButton(text=f"Account {idx+1}", callback_data=f"manage_acc_{idx}"))
        kb.add(types.InlineKeyboardButton(text="🔙 Back", callback_data="back_home"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif data == "back_home":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start_command(call.message)

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.from_user.id != ADMIN_CHAT_ID:
        bot.reply_to(message, "❌ यह कमांड सिर्फ एडमिन के लिए है।")
        return
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(text="📢 Broadcast Message", callback_data="admin_broadcast"),
        types.InlineKeyboardButton(text="👥 User List", callback_data="admin_users_0")
    )
    bot.send_message(message.chat.id, "⚙️ **Admin Control Panel**", reply_markup=kb)

if __name__ == "__main__":
    # Set Webhook automatically on startup
    RENDER_URL = "https://swiggy-order-bot.onrender.com"
    bot.remove_webhook()
    bot.set_webhook(url=f"{RENDER_URL}/webhook/{BOT_TOKEN}")
    logger.info("Webhook set successfully!")

    # Run Flask App
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)
        
