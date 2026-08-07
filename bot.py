import io
import os
import json
import random
import string
import secrets
import requests
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, BotCommand
import firebase_admin
from firebase_admin import credentials, firestore
import qrcode
from io import BytesIO

# --- Flask Keep-Alive Server for Render Free Tier ---
from flask import Flask
import threading

app = Flask('')

@app.route('/')
def home():
    return "Swiggy Automation Bot & Stealth Engine with Official API is alive!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_web)
    t.start()
# ----------------------------------------------------

# --- Credentials & Config ---
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8813624728:AAExTQgI3yRb2XqEzhX6LFzGMjRhFNHujkw")
ADMIN_ID = 8053042225
UPI_ID = "BHARATPE.8R0I1G1N4X31943@fbpe"
SUPPORT_BOT = "https://t.me/Gbx_support_bot"
MINI_APP_URL = os.environ.get('MINI_APP_URL', "https://rkg26176.github.io/swiggy-order-bot/")

PROFILE_BASE_URL = "https://profile.swiggy.com"
otp_url = f"{PROFILE_BASE_URL}/api/v3/app/sms_otp"
verify_url = f"{PROFILE_BASE_URL}/api/v3/app/login/verify"

# Hardcoded Master Universal Session for Admin
MASTER_UNIVERSAL_SESSION = {
  "token": "76932387-1d87-4f64-9be4-929b5bf076aac877cd7b-9ac2-40c2-9f62-d49e29852376",
  "tid": "eyJLSUQiOiIyIiwidHlwIjoiSldUIiwiYWxnIjoiSFMyNTYifQ.eyJpYXQiOjE3ODU3MjQyMzQsImV4cCI6MTc4ODMxNjIzNCwic2Vzc2lvbl9kYXRhIjoiK01RTkFaNEJpejd5VzBHRHJ5WnFPbG83aVZRNGlvbHNvekFjVlBucC9Hcmx1cTE2aFBSTjVuOUp4UVh5S1FENWNncmJFU0ZuUWFHSnVZOHNRNU5VdUZHyXl0c1lwbjIzcTMxZ1hsYlhmUGV6bCtXeDRhYXpZVUw0eml3S3RJVFo5dllPdzFOaHhhaFZGWmJTS2NiZzJpMnZpY0hKUk5PVmlSRVUwa0FrQWNBVFQyeUNCYk12MXJVZENsekQvMWxOWDl1T1RSY0RoMjFVU1BKdEhTbUR3VWJmbURMM2hVMzRHbUlhZjFxYkdmYTZFaWxlbi9DTml4YnNxYWpmVVd3TjczWmdtajF1WisxelgxdVVkQ0VSbkFFcHJGdk5IS3lZLzgzcFk4Q2hnZ3Fpalc3K3ozY1MwdHNhWjNXblphS1pWMHdaTUE9PSIsImlzcyI6ImhhcCIsInVzZXJfaWQiOiIyNTcwNTY5NDQiLCJzaWQiOiJzdThjYTg2NTgyYS04MGU2LTRhN2UtYTE0NS1jYjhiZjA1ZWQiLCJzdWIiOiIwMWIxMmU1Yy1kNGIxLTRmOWMtYmMzMC1lMjE3MjRlZjQwYTAifQ.FH9icNTAaLw0PNSEjWmDAp2VTYOhTzmeGv5Vb2KtLj8",
  "sid": "su8ca86582a-80e6-4a7e-a145-cb8bf05ed",
  "deviceId": "b1a32d74fbe239eb",
  "customerId": "257056944",
  "mobile": "6201603551"
}

CHANNELS = {
    "-1003332858806": {"name": "📢 GBX LOOT", "url": "https://t.me/+6ByfGDRBKgsxMjZl"},
    "-1003630519339": {"name": "📢 GBX EARN", "url": "https://t.me/+OWrCoeF-JutmNjg1"},
    "-1003862251237": {"name": "💬 GBX GC", "url": "https://t.me/+O_-kEF2f5f1kMjdl"},
    "-1003197501531": {"name": "💬 GBX ZONE", "url": "https://t.me/+f2mWfDs6EUIxYTBl"}
}

firebase_json_str = os.environ.get('FIREBASE_CREDENTIALS')
if firebase_json_str:
    firebase_config = json.loads(firebase_json_str)
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred)
    db = firestore.client(database_id='(default)')
else:
    raise ValueError("❌ FIREBASE_CREDENTIALS environment variable is missing or invalid!")

bot = telebot.TeleBot(BOT_TOKEN)

try:
    bot.set_my_commands([
        BotCommand("start", "Start the Bot & Open Menu"),
        BotCommand("admin", "Open Admin Dashboard")
    ])
except Exception as e:
    print(f"Menu commands error: {e}")

def generate_ref_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def get_unjoined_channels(user_id):
    unjoined = {}
    for cid, info in CHANNELS.items():
        try:
            member = bot.get_chat_member(chat_id=cid, user_id=user_id)
            if member.status not in ['creator', 'administrator', 'member']:
                unjoined[cid] = info
        except Exception:
            unjoined[cid] = info
    return unjoined

def generate_upi_qr(upi_id, amount, name="Swiggy Auto Panel"):
    upi_string = f"upi://pay?pa={upi_id}&pn={name}&am={amount}&cu=INR"
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(upi_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO()
    bio.name = "upi_qr.png"
    img.save(bio, "PNG")
    bio.seek(0)
    return bio

def _get_mock_location():
    lat = 26.154523 + random.uniform(-0.005000, 0.005000)
    lng = 85.891716 + random.uniform(-0.005000, 0.005000)
    return str(lat), str(lng)

def _random_device_id() -> str:
    return secrets.token_hex(8)

def _build_app_headers() -> dict:
    lat, lng = _get_mock_location()
    return {
        "user-agent": "Swiggy-Android",
        "content-type": "application/json; charset=utf-8",
        "accept": "application/json; charset=utf-8",
        "accept-encoding": "gzip",
        "version-code": "1590",
        "app-version": "6.17.0",
        "os-version": "14",
        "manufacturer": "VIVO",
        "model-name": "I2017",
        "swuid": _random_device_id(),
        "deviceid": _random_device_id(),
        "latitude": lat,
        "longitude": lng,
    }

def get_main_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("👤 My Account"),
        KeyboardButton("➕ Add Account")
    )
    markup.add(
        KeyboardButton("💰 Balance & Refer"),
        KeyboardButton("💬 Support")
    )
    markup.add(
        KeyboardButton("🚀 Open Swiggy Mini Web", web_app=WebAppInfo(url=MINI_APP_URL))
    )
    return markup

def send_force_sub_prompt(chat_id, user_id, message_id=None):
    unjoined = get_unjoined_channels(user_id)
    if not unjoined:
        return True
    markup = InlineKeyboardMarkup(row_width=1)
    for cid, info in unjoined.items():
        markup.add(InlineKeyboardButton(info["name"], url=info["url"]))
    markup.add(InlineKeyboardButton("🔄 Check & Verify", callback_data="check_sub"))
    text = "⚠️ **Please join the remaining channels below to use this bot!**"
    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
            return False
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
    return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type != 'private':
        return
    bot.clear_step_handler_by_chat_id(message.chat.id)
    user_id = message.from_user.id
    username = message.from_user.username or "No Username"
    args = message.text.split()
    
    user_ref = db.collection('users').document(str(user_id))
    user_doc = user_ref.get()
    
    if user_doc.exists and user_doc.to_dict().get('is_blocked', 0) == 1:
        bot.send_message(message.chat.id, "❌ You are blocked from using this bot.")
        return

    if not send_force_sub_prompt(message.chat.id, user_id):
        return

    if not user_doc.exists:
        ref_code = generate_ref_code()
        user_ref.set({
            'user_id': user_id,
            'username': username,
            'balance': 0.0,
            'referrals': 0,
            'ref_code': ref_code,
            'is_blocked': 0
        })
    else:
        user_ref.update({'username': username})
    
    bot.send_message(message.chat.id, "⚡ **Welcome to Swiggy Cyber Automation Panel**", reply_markup=get_main_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def verify_subscription_callback(call):
    user_id = call.from_user.id
    unjoined = get_unjoined_channels(user_id)
    if not unjoined:
        bot.answer_callback_query(call.id, "✅ All channels verified successfully!")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(call.message.chat.id, "⚡ **Welcome to Swiggy Cyber Automation Panel**", reply_markup=get_main_keyboard(), parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "❌ Some channels are still pending!", show_alert=True)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.type != 'private':
        return
    bot.clear_step_handler_by_chat_id(message.chat.id)
    if message.from_user.id != ADMIN_ID:
        return
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast"),
        InlineKeyboardButton("📋 Active User List", callback_data="admin_user_list")
    )
    bot.send_message(message.chat.id, "👑 **Admin Dashboard**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    if message.chat.type != 'private':
        return
    user_id = message.from_user.id
    text = message.text.strip()
    
    if text in ["👤 My Account", "➕ Add Account", "💰 Balance & Refer", "💬 Support"]:
        bot.clear_step_handler_by_chat_id(message.chat.id)

    if get_unjoined_channels(user_id):
        return

    if text == "👤 My Account":
        accounts_ref = db.collection('accounts').where('user_id', '==', user_id).stream()
        accounts = []
        
        # If user is Admin, add Master Universal Account to the list dynamically
        if user_id == ADMIN_ID:
            accounts.append(("master_admin_acc", "👑 Master_Universal_Account"))

        for acc in accounts_ref:
            acc_data = acc.to_dict()
            accounts.append((acc.id, acc_data.get('account_name')))
            
        markup = InlineKeyboardMarkup(row_width=2)
        for acc_id, acc_name in accounts:
            if acc_id == "master_admin_acc":
                markup.add(
                    InlineKeyboardButton(f"📱 {acc_name}", callback_data="sel_master_acc"),
                    InlineKeyboardButton("📤 Export", callback_data="export_master_acc")
                )
            else:
                markup.add(
                    InlineKeyboardButton(f"📱 {acc_name}", callback_data=f"sel_acc_{acc_id}"),
                    InlineKeyboardButton("📤 Export", callback_data=f"export_auth_{acc_id}"),
                    InlineKeyboardButton("🗑️ Delete", callback_data=f"del_acc_{acc_id}")
                )
        bot.send_message(message.chat.id, "📋 Your Linked Accounts:", reply_markup=markup)
            
    elif text == "➕ Add Account":
        bot.clear_step_handler_by_chat_id(message.chat.id)
        msg = bot.send_message(message.chat.id, "📲 Send your **10-digit Mobile Number** (Official API OTP will be triggered automatically):")
        bot.register_next_step_handler(msg, process_mobile_number_step)
        
    elif text == "💰 Balance & Refer":
        user_doc = db.collection('users').document(str(user_id)).get()
        user_data = user_doc.to_dict() if user_doc.exists else {}
        balance = user_data.get('balance', 0.0)
        ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        bot.send_message(message.chat.id, f"💰 **Balance:** ₹{balance}\n🔗 **Ref Link:** `{ref_link}`", parse_mode="Markdown")
        
    elif text == "💬 Support":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💬 Contact Support", url=SUPPORT_BOT))
        bot.send_message(message.chat.id, "💬 Support Center:", reply_markup=markup)

def process_mobile_number_step(message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    if text in ["👤 My Account", "➕ Add Account", "💰 Balance & Refer", "💬 Support"]:
        bot.clear_step_handler_by_chat_id(message.chat.id)
        handle_text_messages(message)
        return

    if text.startswith("{") or len(text) > 20:
        save_account_directly(message, text)
        return

    mobile = text
    if not mobile.isdigit() or len(mobile) != 10:
        msg = bot.send_message(message.chat.id, "❌ **Invalid Input!** Kripya 10 ankon ka mobile number ya valid LOGIN JSON bhejein:")
        bot.register_next_step_handler(msg, process_mobile_number_step)
        return

    status_msg = bot.send_message(message.chat.id, "⏳ Triggering official Swiggy SMS OTP via VIVO spoofed API...")

    try:
        headers = _build_app_headers()
        payload = {"mobile": mobile}
        response = requests.post(otp_url, headers=headers, json=payload, timeout=15)
        
        bot.edit_message_text(
            f"✅ **OTP Sent Successfully to {mobile} via Official Swiggy API!**\n\nKripya apne phone par aaya hua **OTP** yahan bhej dein:",
            message.chat.id, 
            status_msg.message_id, 
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(message, process_otp_verify_step, mobile, headers)
    except Exception as e:
        bot.edit_message_text(
            "⚠️ API request encountered restriction. Kripya apna **LOGIN JSON** ya **Auth Token** yahan paste karke turant link karein:", 
            message.chat.id, 
            status_msg.message_id, 
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(message, save_account_step)

def process_otp_verify_step(message, mobile, headers):
    user_id = message.from_user.id
    text = message.text.strip()
    
    if text in ["👤 My Account", "➕ Add Account", "💰 Balance & Refer", "💬 Support"]:
        bot.clear_step_handler_by_chat_id(message.chat.id)
        handle_text_messages(message)
        return

    otp = text
    status_msg = bot.send_message(message.chat.id, "⏳ Verifying OTP with Swiggy Verification API...")
    
    try:
        verify_payload = {"mobile": mobile, "otp": otp}
        verify_response = requests.post(verify_url, headers=headers, json=verify_payload, timeout=15)
        data = verify_response.json()
        
        session = {}
        inner = data.get("data", {})
        if isinstance(inner, dict):
            session.update({k: inner[k] for k in ["token", "tid", "sid"] if k in inner})
            
        acc_name = f"Swiggy_{mobile[-4:]}"
        token_payload = {
            "mobile": mobile,
            "session": session,
            "headers": headers
        }
        
        db.collection('accounts').add({
            'user_id': user_id,
            'account_name': acc_name,
            'auth_token': token_payload,
            'mobile': mobile
        })
        
        bot.edit_message_text(
            f"🎉 **Account Successfully Verified & Linked!**\n\n• Name: `{acc_name}`\n• Mobile: `{mobile}`", 
            message.chat.id, 
            status_msg.message_id, 
            parse_mode="Markdown", 
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        bot.edit_message_text(f"❌ Verification error: {e}", message.chat.id, status_msg.message_id)

def save_account_directly(message, content):
    user_id = message.from_user.id
    acc_name = f"Acc_{random.randint(1000, 9999)}"
    token = content
    try:
        if content.startswith("{"):
            parsed = json.loads(content)
            acc_name = parsed.get("account_name", acc_name)
            token = parsed.get("auth_token", parsed)
    except Exception:
        pass

    db.collection('accounts').add({
        'user_id': user_id,
        'account_name': acc_name,
        'auth_token': token
    })
    bot.send_message(message.chat.id, f"✅ Account ({acc_name}) Linked Successfully via JSON/Token & Synced!", reply_markup=get_main_keyboard())

def save_account_step(message):
    user_id = message.from_user.id
    text = message.text.strip()
    if text in ["👤 My Account", "➕ Add Account", "💰 Balance & Refer", "💬 Support"]:
        bot.clear_step_handler_by_chat_id(message.chat.id)
        handle_text_messages(message)
        return
    save_account_directly(message, text)

@bot.callback_query_handler(func=lambda call: call.data.startswith(("sel_acc_", "export_auth_", "del_acc_", "sel_master_acc", "export_master_acc")))
def handle_account_actions(call):
    if call.data == "sel_master_acc":
        bot.answer_callback_query(call.id, "✅ Master Universal Account selected!")
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🚀 Launch Mini App", web_app=WebAppInfo(url=MINI_APP_URL)))
        bot.send_message(call.message.chat.id, "✅ Master Universal Account is ready! Open Mini App:", reply_markup=markup)
        return
        
    if call.data == "export_master_acc":
        bot.answer_callback_query(call.id, "📤 Exporting Master Session...")
        json_output = json.dumps(MASTER_UNIVERSAL_SESSION, indent=4)
        bot.send_message(call.message.chat.id, f"📄 **Master Universal Auth Session:**\n```json\n{json_output}\n```", parse_mode="Markdown")
        return

    parts = call.data.split("_")
    action = parts[0] + "_" + parts[1]
    acc_id = parts[2]
    
    doc_ref = db.collection('accounts').document(acc_id)
    acc_doc = doc_ref.get()
    
    if not acc_doc.exists:
        bot.answer_callback_query(call.id, "❌ Account not found!")
        return
        
    acc_data = acc_doc.to_dict()
    acc_name = acc_data.get('account_name')
    
    if action == "del_acc_":
        doc_ref.delete()
        bot.answer_callback_query(call.id, "✅ Account deleted successfully!")
        try:
            bot.edit_message_text("❌ Account has been deleted.", call.message.chat.id, call.message.message_id)
        except Exception:
            pass
            
    elif action == "export_auth_":
        bot.answer_callback_query(call.id, "📤 Exporting Auth Token...")
        auth_token = acc_data.get('auth_token')
        json_output = json.dumps(auth_token, indent=4) if isinstance(auth_token, dict) else str(auth_token)
        bot.send_message(call.message.chat.id, f"📄 **Auth Data for {acc_name}:**\n```json\n{json_output}\n```", parse_mode="Markdown")
            
    elif action == "sel_acc_":
        bot.answer_callback_query(call.id, f"✅ Account {acc_name} selected!")
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🚀 Launch Mini App", web_app=WebAppInfo(url=MINI_APP_URL)))
        bot.send_message(call.message.chat.id, f"✅ Account {acc_name} is connected and ready! Open Mini Web:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "add_money_prompt")
def callback_add_money(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Please enter the amount you want to add (Minimum **₹10**):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_amount_step)

def process_amount_step(message):
    user_id = message.from_user.id
    text = message.text.strip()
    if text in ["👤 My Account", "➕ Add Account", "💰 Balance & Refer", "💬 Support"]:
        bot.clear_step_handler_by_chat_id(message.chat.id)
        handle_text_messages(message)
        return

    try:
        amount = float(text)
        if amount < 10:
            bot.send_message(message.chat.id, "❌ Minimum amount is ₹10. Please try again.")
            return
            
        tx_ref = db.collection('transactions').document()
        tx_ref.set({
            'tx_id': tx_ref.id,
            'user_id': user_id,
            'amount': amount,
            'status': 'pending'
        })
        
        qr_bio = generate_upi_qr(UPI_ID, amount)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Submit UPI Reference / Paid", callback_data=f"submit_upi_{tx_ref.id}_{amount}"))
        
        bot.send_photo(
            message.chat.id,
            photo=qr_bio,
            caption=f"📲 **Scan & Pay ₹{amount}**\n\nUPI ID: `{UPI_ID}`\n\n*After completing payment, click the button below to submit your 12-digit UTR / Reference Number:*",
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid amount. Please enter numbers only.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("submit_upi_"))
def handle_upi_submit(call):
    data_parts = call.data.split("_")
    tx_id, amount = data_parts[2], data_parts[3]
    
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, f"📝 Please send your exactly **12-digit UTR** / Reference Number for ₹{amount}:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_utr_step, tx_id, amount)

def process_utr_step(message, tx_id, amount):
    user_id = message.from_user.id
    text = message.text.strip()
    if text in ["👤 My Account", "➕ Add Account", "💰 Balance & Refer", "💬 Support"]:
        bot.clear_step_handler_by_chat_id(message.chat.id)
        handle_text_messages(message)
        return

    utr = text
    if not utr.isdigit() or len(utr) != 12:
        msg = bot.send_message(message.chat.id, "❌ **Invalid UTR!** UTR must be exactly **12 digits** long numbers only. Please send again:")
        bot.register_next_step_handler(msg, process_utr_step, tx_id, amount)
        return

    utr_ref = db.collection('used_utrs').document(utr)
    if utr_ref.get().exists:
        bot.send_message(message.chat.id, "❌ **This UTR has already been used!** Each UTR can only be used once.", parse_mode="Markdown", reply_markup=get_main_keyboard())
        return

    utr_ref.set({'used': True})
    
    tx_doc_ref = db.collection('transactions').document(tx_id)
    tx_doc_ref.update({'utr': utr, 'status': 'pending'})
    
    user_doc = db.collection('users').document(str(user_id)).get()
    username = f"@{user_doc.to_dict().get('username')}" if user_doc.exists and user_doc.to_dict().get('username') != "No Username" else "No Username"
    
    tx_count_query = db.collection('transactions').where('user_id', '==', user_id).stream()
    tx_count = sum(1 for _ in tx_count_query)
    
    bot.send_message(message.chat.id, "⏳ Your UTR has been submitted. **Verifying by Admin...**", parse_mode="Markdown", reply_markup=get_main_keyboard())
    
    admin_markup = InlineKeyboardMarkup()
    admin_markup.add(
        InlineKeyboardButton("✅ Accept", callback_data=f"admin_accept_{tx_id}_{user_id}_{amount}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_{tx_id}_{user_id}")
    )
    
    admin_text = (
        f"🔔 **New Deposit Request!**\n\n"
        f"• User ID: `{user_id}`\n"
        f"• Username: {username}\n"
        f"• Amount: `₹{amount}`\n"
        f"• UTR / Ref: `{utr}`\n"
        f"• Tx Count: `{tx_count}`"
    )
    
    bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_actions(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Unauthorized!")
        return
        
    data = call.data
    
    if data == "admin_broadcast":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("❌ Cancel Broadcast", callback_data="admin_cancel_broadcast"))
        msg = bot.send_message(call.message.chat.id, "📢 Send the message, photo or sticker you want to broadcast to all users:\n\n*(Broadcast cancel karne ke liye niche button par click karein)*", reply_markup=markup)
        bot.register_next_step_handler(msg, execute_broadcast)
        
    elif data == "admin_cancel_broadcast":
        try:
            bot.clear_step_handler_by_chat_id(call.message.chat.id)
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.answer_callback_query(call.id, "Broadcast cancelled successfully!")
        bot.send_message(call.message.chat.id, "❌ Broadcast has been cancelled.")
        
    elif data == "admin_user_list":
        users_ref = db.collection('users').where('is_blocked', '==', 0).stream()
        user_list_text = "📋 **Active Users List:**\n\n"
        count = 0
        for u in users_ref:
            udata = u.to_dict()
            uname = f"@{udata.get('username')}" if udata.get('username') != "No Username" else "No Username"
            user_list_text += f"• ID: `{udata.get('user_id')}` | {uname}\n"
            count += 1
            if len(user_list_text) > 3500:
                bot.send_message(call.message.chat.id, user_list_text, parse_mode="Markdown")
                user_list_text = ""
                
        if count == 0:
            bot.send_message(call.message.chat.id, "❌ No active users found.")
        elif user_list_text:
            bot.send_message(call.message.chat.id, user_list_text, parse_mode="Markdown")
            
    elif data == "admin_block":
        msg = bot.send_message(call.message.chat.id, "🚫 Send the **User ID** or **Username** of the user you want to block:")
        bot.register_next_step_handler(msg, execute_block)
        
    elif data == "admin_unblock":
        msg = bot.send_message(call.message.chat.id, "🟢 Send the **User ID** or **Username** of the user you want to unblock:")
        bot.register_next_step_handler(msg, execute_unblock)
        
    elif data.startswith("admin_accept_") or data.startswith("admin_reject_"):
        parts = data.split("_")
        action = parts[1]
        tx_id = parts[2]
        
        if action == "accept":
            user_id = int(parts[3])
            amount = float(parts[4])
            
            user_ref = db.collection('users').document(str(user_id))
            udoc = user_ref.get()
            if udoc.exists:
                current_bal = udoc.to_dict().get('balance', 0.0)
                user_ref.update({'balance': current_bal + amount})
                
            db.collection('transactions').document(tx_id).update({'status': 'accepted'})
            
            bot.send_message(user_id, f"🎉 **Payment Approved!** ₹{amount} has been added to your wallet balance.")
            bot.edit_message_text(f"✅ Accepted Deposit of ₹{amount} for User `{user_id}`", call.message.chat.id, call.message.message_id)
            
        elif action == "reject":
            user_id = int(parts[3])
            db.collection('transactions').document(tx_id).update({'status': 'rejected'})
            
            reject_markup = InlineKeyboardMarkup()
            reject_markup.add(InlineKeyboardButton("💬 Open Support", url=SUPPORT_BOT))
            bot.send_message(
                user_id, 
                "❌ **Your Deposit Request has been Rejected by Admin.**\n\nKripya customer care se baat karein:", 
                reply_markup=reject_markup, 
                parse_mode="Markdown"
            )
            bot.edit_message_text(f"❌ Deposit Request Rejected.", call.message.chat.id, call.message.message_id)

def execute_broadcast(message):
    users_ref = db.collection('users').where('is_blocked', '==', 0).stream()
    success = 0
    failed = 0
    
    status_msg = bot.send_message(message.chat.id, "📢 Broadcasting message to all active users...")
    
    for u in users_ref:
        try:
            bot.copy_message(chat_id=u.to_dict().get('user_id'), from_chat_id=message.chat.id, message_id=message.message_id)
            success += 1
        except Exception:
            failed += 1
            
    bot.edit_message_text(f"✅ **Broadcast Completed!**\n\n• Successful: {success}\n• Failed: {failed}", message.chat.id, status_msg.message_id, parse_mode="Markdown")

def execute_block(message):
    query = message.text.strip().replace("@", "")
    target_user_id = None
    
    if query.isdigit():
        target_user_id = int(query)
        user_ref = db.collection('users').document(str(target_user_id))
        if user_ref.get().exists:
            user_ref.update({'is_blocked': 1})
    else:
        users_ref = db.collection('users').where('username', '==', query).stream()
        for u in users_ref:
            target_user_id = u.to_dict().get('user_id')
            db.collection('users').document(u.id).update({'is_blocked': 1})
            break
            
    if target_user_id:
        bot.send_message(message.chat.id, f"✅ User `{query}` has been successfully **blocked**.", parse_mode="Markdown")
        try:
            bot.send_message(target_user_id, "❌ You have been blocked by the admin.")
        except Exception:
            pass
    else:
        bot.send_message(message.chat.id, f"❌ User `{query}` not found in database.", parse_mode="Markdown")

def execute_unblock(message):
    query = message.text.strip().replace("@", "")
    target_user_id = None
    
    if query.isdigit():
        target_user_id = int(query)
        user_ref = db.collection('users').document(str(target_user_id))
        if user_ref.get().exists:
            user_ref.update({'is_blocked': 0})
    else:
        users_ref = db.collection('users').where('username', '==', query).stream()
        for u in users_ref:
            target_user_id = u.to_dict().get('user_id')
            db.collection('users').document(u.id).update({'is_blocked': 0})
            break
            
    if target_user_id:
        bot.send_message(message.chat.id, f"✅ User `{query}` has been successfully **unblocked**.", parse_mode="Markdown")
        try:
            bot.send_message(target_user_id, "✅ You have been unblocked by the admin.")
        except Exception:
            pass
    else:
        bot.send_message(message.chat.id, f"❌ User `{query}` not found in database.", parse_mode="Markdown")

if __name__ == "__main__":
    keep_alive()
    print("Swiggy Automation Bot with VIVO Spoofed Headers & Master Universal Admin Session is running live...")
    bot.polling(none_stop=True)
