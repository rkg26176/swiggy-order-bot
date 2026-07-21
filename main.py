import os
import threading
from flask import Flask
import telebot
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    WebAppInfo,
)

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot & WebApp Gateway Active!"


# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get(
    "BOT_TOKEN", "8813624728:AAHRdboNnxZiw6jgJR2OyiR1c5ezY2U6k_k"
)
WEB_APP_URL = "https://couponsmafia.shop/sw/?v=1784645347"

bot = telebot.TeleBot(BOT_TOKEN)

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


# Telegram Chat Menu Button (4-dot Icon) Setup
def setup_menu_button():
    try:
        web_app_info = WebAppInfo(url=WEB_APP_URL)
        menu_button = MenuButtonWebApp(
            type="web_app", text="🎯 OPEN LOOT ARENA", web_app=web_app_info
        )
        bot.set_chat_menu_button(menu_button=menu_button)
        print("Menu button set successfully!")
    except Exception as e:
        print(f"Error setting menu button: {e}")


# Verification Status Checker
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
            print(f"Error checking channel {channel_id}: {e}")
            status_map[channel_id] = False
    return status_map


# Dynamic Force Join Menu
def show_dynamic_force_join(
    chat_id, user_name, status_map, message_id=None, is_edit=False
):
    text = (
        f"❌ **Access Denied, {user_name}!**\n\n"
        "Aapne humare required channels/GC ko leave kar diya hai ya join nahi kiya hai.\n"
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
            print(f"Edit error: {e}")
    else:
        bot.send_message(
            chat_id, text, reply_markup=markup, parse_mode="Markdown"
        )


def show_arena_button(chat_id, user_name, message_id=None, is_edit=False):
    text = (
        f"✅ **Verification Successful!**\n\n"
        f"Welcome **{user_name}**! Aapka access unlocked hai.\n\n"
        f"👇 Niche **4-dot Menu Icon** par click karke ya is button se WebApp kholein:"
    )

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            text="🎯 OPEN LOOT ARENA", web_app=WebAppInfo(url=WEB_APP_URL)
        )
    )

    if is_edit and message_id:
        bot.edit_message_text(
            text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown"
        )
    else:
        bot.send_message(
            chat_id, text, reply_markup=markup, parse_mode="Markdown"
        )


@bot.message_handler(commands=["start"])
def start_command(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    status_map = get_user_status_map(user_id)
    if all(status_map.values()):
        show_arena_button(message.chat.id, user_name, is_edit=False)
    else:
        show_dynamic_force_join(
            message.chat.id, user_name, status_map, is_edit=False
        )


# Har message par Live Check: Agar leave kiya toh block karega
@bot.message_handler(func=lambda message: True)
def auto_check_all_messages(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    status_map = get_user_status_map(user_id)
    if not all(status_map.values()):
        show_dynamic_force_join(
            message.chat.id, user_name, status_map, is_edit=False
        )
    else:
        show_arena_button(message.chat.id, user_name, is_edit=False)


@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def handle_verification(call):
    user_id = call.from_user.id
    user_name = call.from_user.first_name

    status_map = get_user_status_map(user_id)

    if all(status_map.values()):
        bot.answer_callback_query(call.id, "🎉 Success! Unlocked.")
        show_arena_button(
            call.message.chat.id,
            user_name,
            call.message.message_id,
            is_edit=True,
        )
    else:
        bot.answer_callback_query(
            call.id, "❌ Kripya saare channels join karein!", show_alert=True
        )
        show_dynamic_force_join(
            call.message.chat.id,
            user_name,
            status_map,
            call.message.message_id,
            is_edit=True,
        )


@bot.message_handler(content_types=["web_app_data"])
def handle_web_app_data(message):
    raw_payload = message.web_app_data.data
    bot.send_message(
        message.chat.id,
        f"🎉 **Order / Action Received!**\n\n`{raw_payload}`",
        parse_mode="Markdown",
    )


def run_bot():
    setup_menu_button()
    bot.infinity_polling(timeout=10, long_polling_timeout=5)


if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
        
