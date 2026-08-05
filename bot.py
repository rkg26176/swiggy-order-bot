import io
import os
import json
import sqlite3
import random
import string
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, BotCommand
import firebase_admin
from firebase_admin import credentials, firestore
import qrcode
from io import BytesIO

# --- Dummy HTTP Server for Render Web Service Port Binding ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# Start dummy server in background thread so Render port check passes
threading.Thread(target=run_server, daemon=True).start()

# --- Credentials & Config ---
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8813624728:AAExTQgI3yRb2XqEzhX6LFzGMjRhFNHujkw")
ADMIN_ID = 8053042225
UPI_ID = "BHARATPE.8R0I1G1N4X31943@fbpe"
SUPPORT_BOT = "https://t.me/gbx_support_bot"
MINI_APP_URL = "https://rkg26176.github.io/swiggy-order-bot/"

# Your Correct Channels Dictionary
CHANNELS = {
    "-1003332858806": {"name": "📢 GBX LOOT", "url": "https://t.me/+6ByfGDRBKgsxMjZl"},
    "-1003630519339": {"name": "📢 GBX EARN", "url": "https://t.me/+OWrCoeF-JutmNjg1"},
    "-1003862251237": {"name": "💬 GBX GC", "url": "https://t.me/+O_-kEF2f5f1kMjdl"},
    "-1003197501531": {"name": "💬 GBX ZONE", "url": "https://t.me/+f2mWfDs6EUIxYTBl"}
}

# Firebase Setup
firebase_json_str = os.environ.get('FIREBASE_CREDENTIALS')
if firebase_json_str:
    firebase_config = json.loads(firebase_json_str)
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    db = None

bot = telebot.TeleBot(BOT_TOKEN)

# Set Telegram Blue Menu Button Commands
try:
    bot.set_my_commands([
        BotCommand("start", "Start the Bot & Open Menu"),
        BotCommand("admin", "Open Admin Dashboard")
    ])
except Exception as e:
    print(f"Menu commands error: {e}")

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect("swiggy_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        balance REAL DEFAULT 0.0,
                        referrals INTEGER DEFAULT 0,
                        referred_by INTEGER,
                        ref_code TEXT,
                        is_blocked INTEGER DEFAULT 0
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

# --- Helper: Get Unjoined Channels for a User ---
def get_unjoined_channels(user_id):
    unjoined = {}
    for cid, info in CHANNELS.items():
        try:
            member = bot.get_chat_member(chat_id=cid, user_id=user_id)
            if member.status not in ['creator', 'administrator', 'member']:
                unjoined[cid] = info
        except Exception as e:
            print(f"Error checking channel {cid} for user {user_id}: {e}")
            unjoined[cid] = info
    return unjoined

# --- Helper: Generate UPI QR Code Image ---
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

# --- Main Reply Keyboard ---
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

# --- Send Dynamic Force Sub Message ---
def send_force_sub_prompt(chat_id, user_id, message_id=None):
    unjoined = get_unjoined_channels(user_id)
    if not unjoined:
        return True
        
    markup = InlineKeyboardMarkup(row_width=1)
    for cid, info in unjoined.items():
        markup.add(InlineKeyboardButton(info["name"], url=info["url"]))
    markup.add(InlineKeyboardButton("🔄 Check & Verify", callback_data="check_sub"))
    
    text = "⚠️ **Please join the remaining channels below to use this bot!**\n\n(Jo channel tumne join kar liye hain, ve verify karte hi automatic hat jayenge):"
    
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
    user_id = message.from_user.id
    username = message.from_user.username or "No Username"
    args = message.text.split()
    
    conn = sqlite3.connect("swiggy_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    
    if res and res[0] == 1:
        conn.close()
        bot.send_message(message.chat.id, "❌ You are blocked from using this bot.")
        return

    if not send_force_sub_prompt(message.chat.id, user_id):
        conn.close()
        return

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
        
        cursor.execute("INSERT INTO users (user_id, username, balance, referrals, referred_by, ref_code, is_blocked) VALUES (?, ?, 0.0, 0, ?, ?, 0)", 
                       (user_id, username, referred_by, ref_code))
        conn.commit()
    else:
        cursor.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
        conn.commit()
    conn.close()
    
    bot.send_message(
        message.chat.id, 
        "⚡ **Welcome to Swiggy Cyber Automation Panel**\n\nChoose an option from the menu below:", 
        reply_markup=get_main_keyboard(), 
        parse_mode="Markdown"
    )

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
        
        bot.send_message(
            call.message.chat.id,
            "⚡ **Welcome to Swiggy Cyber Automation Panel**\n\nChoose an option from the menu below:",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
    else:
        markup = InlineKeyboardMarkup(row_width=1)
        for cid, info in unjoined.items():
            markup.add(InlineKeyboardButton(info["name"], url=info["url"]))
        markup.add(InlineKeyboardButton("🔄 Check & Verify", callback_data="check_sub"))
        
        try:
            bot.edit_message_text(
                "❌ Aapne abhi tak sabhi channel join nahi kiye hain!\n\nJo channel bache hain, unhe join karke dobara '🔄 Check & Verify' par click karein:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except Exception:
            pass
        bot.answer_callback_query(call.id, "❌ Some channels are still pending!", show_alert=True)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Yah command sirf admin ke liye hai.")
        return
        
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast"),
        InlineKeyboardButton("📋 Active User List", callback_data="admin_user_list")
    )
    markup.add(
        InlineKeyboardButton("🚫 Block User", callback_data="admin_block"),
        InlineKeyboardButton("🟢 Unblock User", callback_data="admin_unblock")
    )
    
    bot.send_message(
        message.chat.id, 
        "👑 **Welcome to Admin Dashboard**\n\nSelect an action below:", 
        reply_markup=markup, 
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    user_id = message.from_user.id
    
    unjoined = get_unjoined_channels(user_id)
    if unjoined:
        markup = InlineKeyboardMarkup(row_width=1)
        for cid, info in unjoined.items():
            markup.add(InlineKeyboardButton(info["name"], url=info["url"]))
        markup.add(InlineKeyboardButton("🔄 Check & Verify", callback_data="check_sub"))
        
        bot.send_message(
            message.chat.id,
            "⚠️ **Access Denied!** Aapne hamara koi channel chhod (Leave) diya hai. Kripya niche diye gaye channel ko dobara join karein aur verify karein:",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return

    conn = sqlite3.connect("swiggy_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if res and res[0] == 1:
        conn.close()
        bot.send_message(message.chat.id, "❌ You are blocked from using this bot.")
        return

    text = message.text
    
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

@bot.callback_query_handler(func=lambda call: call.data == "add_money_prompt")
def callback_add_money(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "💳 Please enter the amount you want to add (Minimum **₹10**):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_amount_step)

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
def admin_actions(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Unauthorized!")
        return
        
    data = call.data
    
    if data == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 Send the message, photo or sticker you want to broadcast to all users:")
        bot.register_next_step_handler(msg, execute_broadcast)
        
    elif data == "admin_user_list":
        conn = sqlite3.connect("swiggy_bot.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username FROM users WHERE is_blocked = 0")
        users = cursor.fetchall()
        conn.close()
        
        if not users:
            bot.send_message(call.message.chat.id, "❌ No active users found.")
            return
            
        user_list_text = "📋 **Active Users List:**\n\n"
        for u in users:
            uname = f"@{u[1]}" if u[1] != "No Username" else "No Username"
            user_list_text += f"• ID: `{u[0]}` | {uname}\n"
            
            if len(user_list_text) > 3500:
                bot.send_message(call.message.chat.id, user_list_text, parse_mode="Markdown")
                user_list_text = ""
                
        if user_list_text:
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
        
        conn = sqlite3.connect("swiggy_bot.db", check_same_thread=False)
        cursor = conn.cursor()
        
        if action == "accept":
            user_id = int(parts[3])
            amount = float(parts[4])
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

def execute_broadcast(message):
    conn = sqlite3.connect("swiggy_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE is_blocked = 0")
    users = cursor.fetchall()
    conn.close()
    
    success = 0
    failed = 0
    
    status_msg = bot.send_message(message.chat.id, "📢 Broadcasting message to all active users...")
    
    for u in users:
        try:
            bot.copy_message(chat_id=u[0], from_chat_id=message.chat.id, message_id=message.message_id)
            success += 1
        except Exception:
            failed += 1
            
    bot.edit_message_text(f"✅ **Broadcast Completed!**\n\n• Successful: {success}\n• Failed: {failed}", message.chat.id, status_msg.message_id, parse_mode="Markdown")

def execute_block(message):
    query = message.text.strip().replace("@", "")
    conn = sqlite3.connect("swiggy_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    
    if query.isdigit():
        cursor.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (int(query),))
    else:
        cursor.execute("UPDATE users SET is_blocked = 1 WHERE username = ?", (query,))
        
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    if affected > 0:
        bot.send_message(message.chat.id, f"✅ User `{query}` has been successfully **blocked**.", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, f"❌ User `{query}` not found in database.", parse_mode="Markdown")

def execute_unblock(message):
    query = message.text.strip().replace("@", "")
    conn = sqlite3.connect("swiggy_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    
    if query.isdigit():
        cursor.execute("UPDATE users SET is_blocked = 0 WHERE user_id = ?", (int(query),))
    else:
        cursor.execute("UPDATE users SET is_blocked = 0 WHERE username = ?", (query,))
        
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    if affected > 0:
        bot.send_message(message.chat.id, f"✅ User `{query}` has been successfully **unblocked**.", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, f"❌ User `{query}` not found in database.", parse_mode="Markdown")

if __name__ == "__main__":
    print("Swiggy Automation Bot is running live...")
    bot.infinity_polling()
