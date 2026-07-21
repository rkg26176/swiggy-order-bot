import os
import threading
import time
from flask import Flask, redirect
import telebot
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    MenuButtonDefault,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

# --- FLASK SERVER ---
app = Flask(__name__)

# Exact Target URL jise kholna hai
TARGET_URL = "https://couponsmafia.shop/sw/home.php?accesscode=A0a5No1EmrujrvMnUMQb0zQaLQw3d08WDThpgL%2FApWXh%2BgQ8P4Mtr40k%2BzstUUF6FDSwCgjxDRRZhaebNbUL6w%3D%3D"


@app.route("/")
def home():
    return "GBX Swiggy Bot Server Active!"


@app.route("/redirect_app")
def redirect_app():
    # JavaScript ke zariye direct clean redirect taaki Telegram parameters bypass ho jayein
    return f"""
    <html>
        <head>
            <meta http-equiv="refresh" content="0; url={TARGET_URL}" />
            <script>
                window.location.href = "{TARGET_URL}";
            </script>
        </head>
        <body>
            <p>Redirecting to Swiggy Bot...</p>
        </body>
    </html>
    """


# --- CONFIGURATION ---
BOT_TOKEN = "8813624728:AAHRdboNnxZiw6jgJR2OyiR1c5ezY2U6k_k"
SUPPORT_BOT_URL = "https://t.me/b_support_bot"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

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


def reset_menu_button():
    try:
        bot.set_chat_menu_button(menu_button=MenuButtonDefault())
    except Exception as e:
        print(f"⚠️ Error resetting menu button: {e}")


def get_user_status_map(user_id):
    status_map = {}
    for channel_id in CHANNELS:
        try:
            member = bot.get_chat_member(
                chat_id=int(channel_id), user_id=user_id
            )
            if member.status in ["left", "kicked", "restricted"]:
                status_map[channel_id] = False
            else:
                status_map[channel_id] = True
        except Exception as e:
            print(f"⚠️ Error checking channel {channel_id}: {e}")
            status_map[channel_id] = False
    return status_map


def show_dynamic_force_join(
    chat_id, user_name, status_map, message_id=None, is_edit=False
):
    text = (
        f"❌ **Access Denied, {user_name}!**\n\n"
        "Aapne humare required channels/GC ko join nahi kiya hai ya leave kar diya hai.\n"
        "Kripya niche diye gaye channels join karein:"
    )

    markup = InlineKeyboardMarkup(row_width=1)
    for ch_id, ch_info in CHANNELS.items():
        if not status_map[ch_id]:
            markup.add(
                InlineKeyboardButton(
                    text=ch_info["name"], url=ch_info["url"]
                )
            )

    markup.add(
        InlineKeyboardButton(
            text="🔄 Check Joined / Verify", callback_data="verify_join"
        )
    )

    if is_edit and message_id:
        try:
            bot.edit_message_text(
                text,
                chat_id,
                message_id,
                reply_markup=markup,
                parse_mode="Markdown",
            )
        except Exception as e:
            print(f"⚠️ Edit error: {e}")
    else:
        bot.send_message(
            chat_id, text, reply_markup=markup, parse_mode="Markdown"
        )


def show_arena_button(chat_id, user_name):
    text = (
        f"✅ **Verification Successful!**\n\n"
        f"Welcome **{user_name}**! Aapka access unlocked hai.\n\n"
        f"👇 Niche **4-Dot Grid Button** par click karke saare options dekhein."
    )

    markup = ReplyKeyboardMarkup(resize_keyboard=True)

    btn_balance = KeyboardButton(text="💰 Balance")
    btn_support = KeyboardButton(text="💬 Support")
    markup.row(btn_balance, btn_support)

    # Render server par jo redirect route banaya hai, uska WebApp link denge
    # Render URL ko automatically utha lega (e.g. https://your-app.onrender.com/redirect_app)
    # Local ya Render domain dynamic handle karne ke liye hum render URL hardcode ya relative use karenge agar possible ho, ya render app domain dalenge.
    # Yahan hum dynamic render domain use karenge ya direct website URL ka bridge banayenge.
    pass


# Render ka app URL yahan automatic set hoga ya aap apni render service ka domain yahan daalein:
# Jaise: "https://gbx-swiggy-bot.onrender.com/redirect_app"
