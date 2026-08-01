import io
import os
import time
import json
import re
import qrcode
import requests
import telebot
from flask import Flask
import firebase_admin
from firebase_admin import credentials, firestore
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
    BotCommand,
)

# ================= CONFIGURATION & SECRETS =================
BOT_NAME = "GBX PANNEL BOT"
BOT_TOKEN = "8813624728:AAG7ifIbJZAno8pBOO8XbpAaftdcbyPhl1k"
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", 7447932152))

UPI_ID = "BHARATPE.8R0I1G1N4X31943@fbpe"
DIRECT_PAY_AMOUNT = 15.0
MINI_APP_URL = "https://your-mini-web-url.com"

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

user_states = {}

# ================= FIREBASE INITIALIZATION =================
# Railway environment variable ya JSON file se credentials load karein
firebase_creds_json = os.environ.get("FIREBASE_CREDENTIALS")
if firebase_creds_json:
    cred_dict = json.loads(firebase_creds_json)
    cred = credentials.Certificate(cred_dict)
else:
    # Agar local file ho toh uska path dein
    cred = credentials.Certificate("firebase_credentials.json")

firebase_admin.initialize_app(cred)
db = firestore.client()

# ================= CHANNELS & GC STRUCTURE =================
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

PERMANENT_VIP_USERS = [ADMIN_CHAT_ID]

@app.route("/")
def home():
    return "GBX Panel Bot Active with Firebase!"

# ================= DATABASE HELPERS (FIRESTORE) =================
def register_or_get_user(user_id):
    try:
        user_ref = db.collection("users").document(str(user_id))
        doc = user_ref.get()
        is_vip = 1 if user_id in PERMANENT_VIP_USERS else 0
        
        if not doc.exists:
            user_data = {
                "user_id": user_id,
                "points": 0,
                "referred_by": None,
                "referral_count": 0,
                "ref_rewarded": 0,
                "panel_unlocked": is_vip
            }
            user_ref.set(user_data)
            return user_data
        
        data = doc.to_dict()
        if is_vip == 1:
            data["panel_unlocked"] = 1
        return data
    except Exception as e:
        print("DB Error:", e)
        return {"points": 0, "referral_count": 0, "panel_unlocked": 1 if user_id in PERMANENT_VIP_USERS else 0, "referred_by": None}

def update_user_data(user_id, field, value):
    try:
        user_ref = db.collection("users").document(str(user_id))
        user_ref.set({field: value}, merge=True)
    except Exception as e:
        print("Update error:", e)

def get_all_users():
    try:
        users_ref = db.collection("users").stream()
        user_set = {int(doc.id) for doc in users_ref}
        for uid in PERMANENT_VIP_USERS:
            user_set.add(uid)
        return list(user_set)
    except Exception:
        return PERMANENT_VIP_USERS

def is_utr_used(utr):
    try:
        utr_ref = db.collection("used_utrs").document(utr.strip())
        return utr_ref.get().exists
    except Exception:
        return False

def add_used_utr(utr):
    try:
        db.collection("used_utrs").document(utr.strip()).set({"used": True, "time": firestore.SERVER_TIMESTAMP})
    except Exception:
        pass

# ================= FORCE JOIN SYSTEM =================
def get_user_status_map(user_id):
    status_map = {}
    for channel_id in CHANNELS:
        try:
            member = bot.get_chat_member(chat_id=int(channel_id), user_id=user_id)
            status_map[channel_id] = member.status not in [
                "left",
                "kicked",
                "restricted",
            ]
        except Exception:
            status_map[channel_id] = False
    return status_map

def show_dynamic_force_join(chat_id, user_name, status_map, message_id=None):
    text = (
        f"❌ **Access Denied, {user_name}!**\n\n"
        "Aapne humare sabhi required 3 channels aur GC join nahi kiye hain."
    )
    markup = InlineKeyboardMarkup(row_width=1)
    for ch_id, ch_info in CHANNELS.items():
        if not status_map[ch_id]:
            markup.add(
                InlineKeyboardButton(text=ch_info["name"], url=ch_info["url"])
            )
    markup.add(
        InlineKeyboardButton(
            text="🔄 Check Joined / Verify", callback_data="verify_join"
        )
    )
    try:
        if message_id:
            bot.edit_message_text(
                text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown"
            )
        else:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        pass

def show_main_menu(chat_id, user_name):
    user_data = register_or_get_user(chat_id)
    panel_unlocked = 1 if chat_id in PERMANENT_VIP_USERS else int(user_data.get("panel_unlocked", 0))

    markup = InlineKeyboardMarkup(row_width=1)
    
    if panel_unlocked == 1:
        text = (
            f"✅ **Welcome back to GBX Pannel Bot, {user_name}!**\n\n"
            "🎉 Aapka Web Panel unlocked hai! Niche diye gaye button se open karein 👇"
        )
        markup.add(
            InlineKeyboardButton(
                text="🌐 Open Web Mini App Panel",
                web_app=WebAppInfo(url=MINI_APP_URL),
            )
        )
    else:
        text = (
            f"✅ **Welcome to GBX Pannel Bot, {user_name}!**\n\n"
            "Web Panel ka access lene ke liye ₹15 ki direct payment karein 👇"
        )
        markup.add(
            InlineKeyboardButton(
                text="💳 ₹15 Pay to Unlock Web Panel", callback_data="menu_pay"
            ),
        )

    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

# ================= BOT COMMANDS =================
@bot.message_handler(commands=["start"])
def start_command(message):
    if message.chat.type != "private":
        return
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    user_states.pop(user_id, None)

    register_or_get_user(user_id)

    status_map = get_user_status_map(user_id)
    if all(status_map.values()):
        show_main_menu(message.chat.id, user_name)
    else:
        show_dynamic_force_join(message.chat.id, user_name, status_map)

@bot.message_handler(commands=["panel"])
def panel_command(message):
    if message.chat.type != "private":
        return
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    status_map = get_user_status_map(user_id)
    if all(status_map.values()):
        show_main_menu(message.chat.id, user_name)
    else:
        show_dynamic_force_join(message.chat.id, user_name, status_map)

@bot.message_handler(commands=["admin"])
def admin_command(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(text="📬 Inbox (Broadcast)", callback_data="admin_broadcast_mode"),
    )
    bot.send_message(
        message.chat.id,
        "🛠️ **Admin Master Dashboard**",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def handle_verification(call):
    if call.message.chat.type != "private":
        return
    user_id = call.from_user.id
    register_or_get_user(user_id)

    status_map = get_user_status_map(user_id)
    if all(status_map.values()):
        bot.answer_callback_query(call.id, "🎉 Success!")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        show_main_menu(call.message.chat.id, call.from_user.first_name)
    else:
        bot.answer_callback_query(
            call.id, "❌ Saare 3 channels aur GC join karein!", show_alert=True
        )
        show_dynamic_force_join(
            call.message.chat.id,
            call.from_user.first_name,
            status_map,
            call.message.message_id,
        )

@bot.callback_query_handler(func=lambda call: call.data == "menu_pay")
def handle_pay_menu(call):
    if call.message.chat.type != "private":
        return
    user_id = call.from_user.id
    user_states[user_id] = None

    upi_url = f"upi://pay?pa={UPI_ID}&pn=GBX_Panel&am={DIRECT_PAY_AMOUNT}&cu=INR"
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    caption_text = (
        "💳 **Unlock Web Panel via Direct Payment**\n\n"
        f"💰 **Amount:** `₹{DIRECT_PAY_AMOUNT}`\n"
        f"📍 **UPI ID:** `{UPI_ID}`\n\n"
        "📲 **Instructions:**\n"
        "1. QR Code ko scan karke ₹15 ki exact payment karein.\n"
        "2. Payment hone ke baad niche **'📝 Submit UTR'** button par click karke apna 12-digit UTR Number bhejein."
    )
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(text="📝 Submit UTR", callback_data="start_utr_input"),
        InlineKeyboardButton(text="⬅️ Back", callback_data="back_home"),
    )

    bot.send_photo(
        call.message.chat.id,
        photo=buffer,
        caption=caption_text,
        reply_markup=markup,
        parse_mode="Markdown",
    )

@bot.callback_query_handler(func=lambda call: call.data == "start_utr_input")
def handle_start_utr(call):
    if call.message.chat.type != "private":
        return
    user_id = call.from_user.id
    user_states[user_id] = "waiting_for_utr"

    bot.answer_callback_query(call.id, "Kripya apna 12-digit UTR number type karke bhejein!")
    try:
        bot.send_message(
            call.message.chat.id,
            "✍️ **Ab apna 12-digit UTR Number chat mein type karke bhejein:**",
            parse_mode="Markdown",
        )
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data == "back_home")
def handle_back_home(call):
    if call.message.chat.type != "private":
        return
    user_id = call.from_user.id
    user_states.pop(user_id, None)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    show_main_menu(call.message.chat.id, call.from_user.first_name)

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast_mode")
def admin_broadcast_callback(call):
    if call.from_user.id != ADMIN_CHAT_ID:
        return
    user_states[ADMIN_CHAT_ID] = "waiting_for_broadcast"
    bot.answer_callback_query(call.id, "Broadcast mode active!")
    bot.send_message(
        call.message.chat.id,
        "✍️ **Ab aap jo bhi message bhejenge, vah sabhi users ke paas broadcast ho jayega.**\n\n❌ Cancel ke liye `/cancel` likhein.",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["cancel"])
def cancel_command(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return
    user_states.pop(ADMIN_CHAT_ID, None)
    bot.send_message(message.chat.id, "❌ Action cancel kar diya gaya hai.")

# ================= MESSAGE & ANTI-FRAUD UTR HANDLER =================
@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'sticker', 'audio', 'animation'])
def handle_all_messages(message):
    if message.chat.type != "private":
        return
    user_id = message.from_user.id
    register_or_get_user(user_id)

    # Broadcast handler
    if user_id == ADMIN_CHAT_ID and user_states.get(ADMIN_CHAT_ID) == "waiting_for_broadcast":
        user_states.pop(ADMIN_CHAT_ID, None)
        users = get_all_users()
        success = fail = 0
        status_msg = bot.send_message(ADMIN_CHAT_ID, "🚀 Broadcasting message...")

        for uid in users:
            try:
                bot.copy_message(chat_id=uid, from_chat_id=ADMIN_CHAT_ID, message_id=message.message_id)
                success += 1
                time.sleep(0.05)
            except Exception:
                fail += 1

        bot.edit_message_text(
            f"✅ **Broadcast Completed!**\nSuccess: `{success}`\nFailed: `{fail}`",
            ADMIN_CHAT_ID,
            status_msg.message_id,
            parse_mode="Markdown"
        )
        return

    # UTR Input & Anti-Fraud Duplicate Check Handler
    state = user_states.get(user_id)
    if state == "waiting_for_utr":
        if not message.text or not message.text.strip().isdigit() or len(message.text.strip()) != 12:
            bot.send_message(message.chat.id, "❌ Kripya valid 12-digit UTR Number hi dalein.")
            return

        text = message.text.strip()
        
        # 🛡️ DEDUPLICATION CHECK (Prevents UTR reuse fraud)
        if is_utr_used(text):
            bot.send_message(message.chat.id, "❌ Yeh UTR Number pehle hi use ho chuka hai! Duplicate UTR not allowed.")
            user_states.pop(user_id, None)
            return

        add_used_utr(text)
        user_states.pop(user_id, None)

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton(text="✅ Accept", callback_data=f"adm_accept:{user_id}:{text}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"adm_reject:{user_id}:{text}"),
        )

        try:
            bot.send_message(
                ADMIN_CHAT_ID,
                f"📥 **Panel Payment Request!**\nUser ID: `{user_id}`\nAmount: ₹{DIRECT_PAY_AMOUNT}\nUTR: `{text}`",
                reply_markup=markup,
                parse_mode="Markdown",
            )
        except Exception as e:
            print("Admin Send Error:", e)

        bot.send_message(
            message.chat.id,
            "⏳ Payment Verification Pending by Admin. Kripya intezaar karein."
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_action(call):
    if call.from_user.id != ADMIN_CHAT_ID:
        bot.answer_callback_query(call.id, "Unauthorized!")
        return

    data = call.data.split(":")
    action = data[0]
    target = int(data[1])
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    if action == "adm_accept":
        update_user_data(target, "panel_unlocked", 1)
        try:
            bot.edit_message_text(
                f"✅ Approved! Web Panel unlocked for User `{target}`.",
                call.message.chat.id,
                call.message.message_id,
            )
        except Exception:
            pass
        try:
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton(
                    text="🌐 Open Web Mini App Panel",
                    web_app=WebAppInfo(url=MINI_APP_URL),
                )
            )
            bot.send_message(
                target,
                "🎉 **Payment Verified Successfully!**\nAapka Web Mini App Panel unlock kar diya gaya hai 👇",
                reply_markup=markup,
                parse_mode="Markdown",
            )
        except Exception:
            pass
    else:
        try:
            bot.edit_message_text(
                f"❌ Rejected request for User `{target}`.",
                call.message.chat.id,
                call.message.message_id,
            )
        except Exception:
            pass
        try:
            bot.send_message(target, "❌ Aapki payment request Admin dwara reject kar di gayi hai.")
        except Exception:
            pass

def set_bot_commands(bot_instance):
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("panel", "Open Web Panel / Unlock Menu"),
        BotCommand("admin", "Open Admin Dashboard")
    ]
    try:
        bot_instance.set_my_commands(commands)
    except Exception as e:
        print("Set commands error:", e)

def run_bot():
    while True:
        try:
            bot.remove_webhook()
            time.sleep(1)
            set_bot_commands(bot)
            print("Bot Polling Active with Firebase...")
            bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
        except Exception as e:
            print("Polling error:", e)
            time.sleep(5)

if __name__ == "__main__":
    import threading
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
