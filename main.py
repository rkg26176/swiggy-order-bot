import os
import threading
import time
from flask import Flask
import telebot
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    MenuButtonDefault,
    ReplyKeyboardMarkup,
)

# --- FLASK SERVER ---
app = Flask(__name__)


@app.route("/")
def home():
    return "GBX Swiggy Bot Server Active!"


# --- CONFIGURATION ---
BOT_TOKEN = "8813624728:AAHRdboNnxZiw6jgJR2OyiR1c5ezY2U6k_k"
# Direct Website URL jise aap browser me paste karte hain
WEB_APP_URL = "https://couponsmafia.shop/sw/home.php?accesscode=A0a5No1EmrujrvMnUMQb0zQaLQw3d08WDThpgL%252FApWXh%252BgQ8P4Mtr40k%252BzstUUF6FDSwCgjxDRRZhaebNbUL6w%253D%253D"
SUPPORT_BOT_URL = "https://t.me/gbx_support_bot"

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

    # 4-Dot Menu ke andar URL button (Direct link open karega bina kisi tg data ke)
    btn_webapp = KeyboardButton(text="🎯 Swiggy Order Bot")
    markup.row(btn_webapp)

    bot.send_message(
        chat_id, text, reply_markup=markup, parse_mode="Markdown"
    )


@bot.message_handler(commands=["start"])
def start_command(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    status_map = get_user_status_map(user_id)
    if all(status_map.values()):
        show_arena_button(message.chat.id, user_name)
    else:
        show_dynamic_force_join(
            message.chat.id, user_name, status_map, is_edit=False
        )


@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def handle_verification(call):
    user_id = call.from_user.id
    user_name = call.from_user.first_name

    status_map = get_user_status_map(user_id)

    if all(status_map.values()):
        bot.answer_callback_query(call.id, "🎉 Success! Unlocked.")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        show_arena_button(call.message.chat.id, user_name)
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


@bot.message_handler(
    func=lambda msg: msg.text in ["💰 Balance", "💬 Support", "🎯 Swiggy Order Bot"]
)
def handle_keyboard_buttons(message):
    if message.text == "💰 Balance":
        bot.send_message(
            message.chat.id,
            "💰 **Your Current Balance:** `₹0.00`",
            parse_mode="Markdown",
        )
    elif message.text == "💬 Support":
        markup = InlineKeyboardMarkup()
        btn_support = InlineKeyboardButton(
            text="💬 Contact Support Bot", url=SUPPORT_BOT_URL
        )
        markup.add(btn_support)
        bot.send_message(
            message.chat.id, "👇", reply_markup=markup, parse_mode="Markdown"
        )
    elif message.text == "🎯 Swiggy Order Bot":
        # Jaise hi user click karega, direct website ka link button ke sath mil jayega jo bina error ke open hoga
        markup = InlineKeyboardMarkup()
        btn_open = InlineKeyboardButton(
            text="🌐 Click Here to Open Swiggy Bot", url=WEB_APP_URL
        )
        markup.add(btn_open)
        bot.send_message(
            message.chat.id,
            "👇 **Apna link yahan se direct kholein:**",
            reply_markup=markup,
            parse_mode="Markdown",
        )


@bot.message_handler(content_types=["web_app_data"])
def handle_web_app_data(message):
    raw_payload = message.web_app_data.data
    bot.send_message(
        message.chat.id,
        f"🎉 **Order Received!**\n\n`{raw_payload}`",
        parse_mode="Markdown",
    )


def run_bot():
    reset_menu_button()
    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"Webhook warning: {e}")

    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=20)
        except Exception as e:
            print(f"Polling Error: {e}")
            time.sleep(3)


bot_thread = threading.Thread(target=run_bot)
bot_thread.daemon = True
bot_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    
