import io
import os
import json
import sqlite3
import random
import string
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import firebase_admin
from firebase_admin import credentials, firestore
import qrcode
from io import BytesIO

# --- Credentials & Config ---
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8813624728:AAExTQgI3yRb2XqEzhX6LFzGMjRhFNHujkw")
ADMIN_ID = int(os.environ.get('ADMIN_ID', 8053042225))
UPI_ID = "BHARATPE.8R0I1G1N4X31943@fbpe"
SUPPORT_BOT = "https://t.me/gbx_support_bot"
MINI_APP_URL = "https://rkg26176.github.io/swiggy-order-bot/"

# 2. Firebase Setup
firebase_json_str = os.environ.get('FIREBASE_CREDENTIALS')
if firebase_json_str:
    firebase_config = json.loads(firebase_json_str)
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    db = None

bot = telebot.TeleBot(BOT_TOKEN)

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect("swiggy_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        balance REAL DEFAULT 0.0,
                        referrals INTEGER DEFAULT 0,
                        referred_by INTEGER,
                        ref_code TEXT
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        account_name TEXT,
                        auth_token TEXT
                    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
                        tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        amount REAL,
                        status TEXT DEFAULT 'pending'
                    )''')
    conn.commit()
    conn.close()

init_db()

def generate_ref_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# --- Helper: Generate UPI QR Code Image ---
def generate_upi_qr(upi_id, amount, name="Swiggy Auto Panel"):
    upi_string = f"upi://pay?pa={upi_id}&pn={name}&am={amount}&cu=INR"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_string)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    bio = io.BytesIO()
    bio.name = "upi_qr.png"
    img.save(bio, "PNG")
    bio.seek(0)
    return bio

# --- Main Reply Keyboard (नीचे चार डॉट / मेनू वाला कीबोर्ड) ---
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
        KeyboardButton("🚀 Open Swiggy Mini Web")
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    args = message.text.split()
    
    conn = sqlite3.connect("swiggy_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        ref_code = generate_ref_code()
        referred_by = None
        if len(args) > 1 and args[1].isdigit():
            ref_id = int(args[1])
            if ref_id != user_id:
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (ref_id,))
                if cursor.fetchone():
                    referred_by = ref_id
                    cursor.execute("UPDATE users SET referrals = referrals + 1, balance = balance + 3.0 WHERE user_id = ?", (ref_id,))
        
        cursor.execute("INSERT INTO users (user_id, balance, referrals, referred_by, ref_code) VALUES (?, 0.0, 0, ?, ?)", 
                       (user_id, referred_by, ref_code))
        conn.commit()
    conn.close()
    
    bot.send_message(
        message.chat.id, 
        "⚡ **Welcome to Swiggy Cyber Automation Panel**\n\nChoose an option from the menu below:", 
        reply_markup=get_main_keyboard(), 
        parse_mode="Markdown"
    )

# --- Handle Text Messages from Bottom Keyboard ---
@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    user_id = message.from_user.id
    text = message.text
    
    conn = sqlite3.connect("swiggy_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    
    if text == "👤 My Account":
        cursor.execute("SELECT account_name FROM accounts WHERE user_id = ?", (user_id,))
        accounts = cursor.fetchall()
        if not accounts:
            bot.send_message(message.chat.id, "❌ You haven't added any Swiggy accounts yet. Click '➕ Add Account' to link one.", reply_markup=get_main_keyboard())
        else:
            acc_list = "\n".join([f"🔹 {acc[0]}" for acc in accounts])
            bot.send_message(message.chat.id, f"📋 **Your Linked Accounts:**\n\n{acc_list}\n\n*Open Mini Web to switch and use them.*", parse_mode="Markdown", reply_markup=get_main_keyboard())
            
    elif text == "➕ Add Account":
        msg = bot.send_message(message.chat.id, "📲 Please send your Swiggy **Auth Token** or registered **Mobile Number** to link your account:")
        bot.register_next_step_handler(msg, save_account_step)
        
    elif text == "💰 Balance & Refer":
        cursor.execute("SELECT balance, referrals, ref_code FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        balance, referrals, ref_code = user_data[0], user_data[1], user_data[2]
        ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        
        resp_text = (
            f"💰 **Your Wallet & Referral Details**\n\n"
            f"• **Total Balance:** ₹{balance}\n"
            f"• **Total Referrals:** {referrals} (Earned ₹{referrals * 3})\n\n"
            f"🔗 **Your Referral Link:**\n`{ref_link}`\n\n"
            f"*(Note: ₹3 added per successful referral)*"
        )
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ Add Money (Min ₹10)", callback_data="add_money_prompt"))
        
        bot.send_message(message.chat.id, resp_text, reply_markup=markup, parse_mode="Markdown")
        
    elif text == "💬 Support":
        bot.send_message(message.chat.id, f"💬 Contact Support here: {SUPPORT_BOT}", reply_markup=get_main_keyboard())
        
    elif text == "🚀 Open Swiggy Mini Web":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🚀 Launch Mini App", web_app=WebAppInfo(url=MINI_APP_URL)))
        bot.send_message(message.chat.id, "Click below to open the Mini App:", reply_markup=markup)
        
    conn.close()

def save_account_step(message):
    user_id = message.from_user.id
    token_or_number = message.text.strip()
    conn = sqlite3.connect("swiggy_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    acc_name = f"Account_{random.randint(1000, 9999)}"
    cursor.execute("INSERT INTO accounts (user_id, account_name, auth_token) VALUES (?, ?, ?)", (user_id, acc_name, token_or_number))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"✅ **Account Successfully Linked!** Open the Mini Web to start using it.", reply_markup=get_main_keyboard())

# --- Callback Handler for Inline Buttons (Like Add Money) ---
@bot.callback_query_handler(func=lambda call: call.data == "add_money_prompt")
def callback_add_money(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Please enter the amount you want to add (Minimum **₹10**):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_amount_step)

# --- Process Amount & Send QR Code Image ---
def process_amount_step(message):
    user_id = message.from_user.id
    try:
        amount = float(message.text.strip())
        if amount < 10:
            bot.send_message(message.chat.id, "❌ Minimum amount is ₹10. Please try again.")
            return
            
        conn = sqlite3.connect("swiggy_bot.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO transactions (user_id, amount, status) VALUES (?, ?, 'pending')", (user_id, amount))
        tx_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Generate Dynamic UPI QR Code Image with exact amount
        qr_bio = generate_upi_qr(UPI_ID, amount)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Submit UPI Reference / Paid", callback_data=f"submit_upi_{tx_id}_{amount}"))
        
        bot.send_photo(
            message.chat.id,
            photo=qr_bio,
            caption=f"📲 **Scan & Pay ₹{amount}**\n\nUPI ID: `{UPI_ID}`\n\n*After completing the payment, click the button below to submit for admin verification:*",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid amount. Please enter numbers only.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("submit_upi_"))
def handle_upi_submit(call):
    data_parts = call.data.split("_")
    tx_id, amount = data_parts[2], data_parts[3]
    user_id = call.from_user.id
    
    bot.edit_message_caption("⏳ Your payment details have been submitted. **Verifying by Admin...**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    
    admin_markup = InlineKeyboardMarkup()
    admin_markup.add(
        InlineKeyboardButton("✅ Accept", callback_data=f"admin_accept_{tx_id}_{user_id}_{amount}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_{tx_id}")
    )
    
    bot.send_message(
        ADMIN_ID, 
        f"🔔 **New Deposit Request!**\n\n• User ID: `{user_id}`\n• Amount: `₹{amount}`\n• Tx ID: `{tx_id}`", 
        reply_markup=admin_markup, 
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_action(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Unauthorized!")
        return
        
    data = call.data.split("_")
    action = data[1]
    tx_id = data[2]
    
    conn = sqlite3.connect("swiggy_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    
    if action == "accept":
        user_id = int(data[3])
        amount = float(data[4])
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        cursor.execute("UPDATE transactions SET status = 'accepted' WHERE tx_id = ?", (tx_id,))
        conn.commit()
        
        bot.send_message(user_id, f"🎉 **Payment Approved!** ₹{amount} has been added to your wallet balance.")
        bot.edit_message_text(f"✅ Accepted Deposit of ₹{amount} for User `{user_id}`", call.message.chat.id, call.message.message_id)
        
    elif action == "reject":
        cursor.execute("UPDATE transactions SET status = 'rejected' WHERE tx_id = ?", (tx_id,))
        conn.commit()
        bot.edit_message_text(f"❌ Deposit Request Rejected.", call.message.chat.id, call.message.message_id)
        
    conn.close()

if __name__ == "__main__":
    print("Swiggy Automation Bot with QR Generator is running live...")
    bot.infinity_polling()
