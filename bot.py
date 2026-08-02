import os
import json
import logging
import asyncio
import threading
from flask import Flask, request, render_template_string, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Update
from aiogram.filters import Command

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables & Admin ID
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "8053042225"))
BOT_TOKEN = "8813624728:AAF5v_Rnq3R4LYNP1_Sd_tBQU6TxomBDwK4"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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

# Webhook route for Telegram
@app_flask.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
def webhook_handler():
    if request.headers.get('content-type') == 'application/json':
        json_data = request.get_json()
        update = Update.model_validate(json_data, context={"bot": bot})
        asyncio.run_coroutine_threadsafe(dp.feed_update(bot, update), loop)
        return '', 200
    return 'Invalid request', 403

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

async def get_unjoined_channels(user_id):
    unjoined = {}
    for chat_id, info in CHANNELS.items():
        try:
            member = await bot.get_chat_member(chat_id=int(chat_id), user_id=user_id)
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

@dp.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id
    if db:
        db.collection("all_users").document(str(user_id)).set({"user_id": user_id, "username": message.from_user.username or "None"})

    unjoined = await get_unjoined_channels(user_id)
    if unjoined:
        keyboard = []
        for chat_id, info in unjoined.items():
            keyboard.append([InlineKeyboardButton(text=info["name"], url=info["url"])])
        keyboard.append([InlineKeyboardButton(text="🔄 Verify Joined Status", callback_data="check_join")])
        
        await message.answer(
            "❌ **Access Denied!**\nYou must join all the required channels and group chats below to use this bot:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="Markdown"
        )
        return

    user_data = get_user_data(user_id)
    ref_link = f"https://t.me/{(await bot.me()).username}?start=ref_{user_id}"

    keyboard = [
        [InlineKeyboardButton(text="💰 Balance", callback_data="menu_balance"), InlineKeyboardButton(text="👤 Add Account", callback_data="menu_add_account")],
        [InlineKeyboardButton(text="📂 Accounts", callback_data="menu_my_accounts"), InlineKeyboardButton(text="💬 Support", url="https://t.me/YourSupportBotLink")],
        [InlineKeyboardButton(text="🌐 Mini Web", url="https://swiggy-order-bot.onrender.com")]
    ]

    text = (
        "🤖 **Swiggy Bot Dashboard**\n\n"
        f"💳 **Current Balance:** ₹{user_data.get('id_balance', 100.0)}\n"
        f"👥 **Referral Link:** `{ref_link}`\n\n"
        "Select an option below:"
    )
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")

@dp.callback_query(F.data == "check_join")
async def check_join_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    unjoined = await get_unjoined_channels(user_id)
    if not unjoined:
        await callback.message.delete()
        await start_command(callback.message)
    else:
        await callback.answer("❌ You still haven't joined all chats!", show_alert=True)

@dp.callback_query(F.data == "menu_balance")
async def menu_balance_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    ref_link = f"https://t.me/{(await bot.me()).username}?start=ref_{user_id}"
    text = (
        f"💰 **Wallet Overview**\n\n"
        f"💳 **Current Balance:** ₹{user_data.get('id_balance', 0)}\n"
        f"👥 **Referral Link:** `{ref_link}`\n\n"
        f"📥 **To add balance, please send the exact amount you want to deposit (e.g. `500`):**"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="back_home")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "menu_add_account")
async def menu_add_account_callback(callback: CallbackQuery):
    text = (
        "👤 **Add Account System**\n\n"
        "Please send either your **JSON Session Token** OR your **Phone Number** to link with your account:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="back_home")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "menu_my_accounts")
async def menu_my_accounts_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    accounts = user_data.get("accounts", [])
    if not accounts:
        text = "📂 No active accounts found. Please add an account first."
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="back_home")]])
    else:
        text = "📂 **Your Logged-in Accounts:**\nSelect an account to manage/export:"
        kb_list = []
        for idx, acc in enumerate(accounts):
            kb_list.append([InlineKeyboardButton(text=f"Account {idx+1}", callback_data=f"manage_acc_{idx}")])
        kb_list.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_home")])
        kb = InlineKeyboardMarkup(inline_keyboard=kb_list)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "back_home")
async def back_home_callback(callback: CallbackQuery):
    await callback.message.delete()
    await start_command(callback.message)

@dp.message(Command("admin"))
async def admin_command(message: Message):
    if message.from_user.id != ADMIN_CHAT_ID:
        await message.answer("❌ यह कमांड सिर्फ एडमिन के लिए है।")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Broadcast Message", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="👥 User List", callback_data="admin_users_0")]
    ])
    await message.answer("⚙️ **Admin Control Panel**", reply_markup=kb, parse_mode="Markdown")

loop = None

async def setup_webhook():
    webhook_url = f"https://swiggy-order-bot.onrender.com/webhook/{BOT_TOKEN}"
    await bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")

def run_flask():
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Set webhook on startup
    loop.run_until_complete(setup_webhook())
    
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port, use_reloader=False)

if __name__ == "__main__":
    run_flask()
