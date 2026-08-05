import sqlite3
import random
import string
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# --- Credentials & Config ---
BOT_TOKEN = "8813624728:AAExTQgI3yRb2XqEzhX6LFzGMjRhFNHujkw"
ADMIN_ID = 8053042225
UPI_ID = "BHARATPE.8R0I1G1N4X31943@fbpe"
SUPPORT_BOT = "https://t.me/gbx_support_bot"
MINI_APP_URL = "https://rkg26176.github.io/swiggy-order-bot/"

# Required Channels & Group Chats Dictionary
CHANNELS = {
    "-1003332858806": {"name": "📢 GBX LOOT 1", "url": "https://t.me/+6ByfGDRBKgsxMjZl"},
    "-1003630519339": {"name": "📢 GBX EARN 2", "url": "https://t.me/+OWrCoeF-JutmNjg1"},
    "-1003862251237": {"name": "💬 GBX GC 1", "url": "https://t.me/+O_-kEF2f5f1kMjdl"},
    "-1003197501531": {"name": "💬 GBX GC 2", "url": "https://t.me/+f2mWfDs6EUIxYTBl"}
}

bot = telebot.TeleBot(BOT_TOKEN)

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect("swiggy_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        balance REAL DEFAULT 0.0,
                        referrals INTEGER DEFAULT 0,
                        referred_by INTEGER,
                        ref_code TEXT
                    )''')
    
    # Accounts Table (Auth Tokens)
    cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        account_name TEXT,
                        auth_token TEXT
                    )''')
    
    # Transactions Table (Add Money)
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
                        tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        amount REAL,
                        status TEXT DEFAULT 'pending'
                    )''')
    
    conn.commit()
    conn.close()

init_db()

# Helper: Generate Ref Code
def generate_ref_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# --- Check Force Subscription ---
def check_subscription(user_id):
    for channel_id in CHANNELS:
        try:
            member = bot.get_chat_member(channel_id, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception:
            # If bot is not admin in channel, skip or handle gracefully
            pass
    return True

# --- Handlers: Start & Main Menu ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    # Optional: Force Join Check can be added here if needed
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
                    # Add ₹3 referral bonus per successful referral
                    cursor.execute("UPDATE users SET referrals = referrals + 1, balance = balance + 3.0 WHERE user_id = ?", (ref_id,))
        
        cursor.execute("INSERT INTO users (user_id, balance, referrals, referred_by, ref_code) VALUES (?, 0.0, 0, ?, ?)", 
                       (user_id, referred_by, ref_code))
        conn.commit()
    
    conn.close()
    
    # Main Keyboard Layout (5 Buttons as requested)
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👤 My Account", callback_data="my_account"),
        InlineKeyboardButton("➕ Add Account", callback_data="add_account")
    )
    markup.add(
        InlineKeyboardButton("💰 Balance & Refer", callback_data="balance_menu"),
        InlineKeyboardButton("💬 Support", url=SUPPORT_BOT)
    )
    markup.add(
        InlineKeyboardButton("🚀 Open Swiggy Mini Web", web_app=WebAppInfo(url=MINI_APP_URL))
    )
    
    bot.send_message(
        message.chat.id, 
        "⚡ **Welcome to Swiggy Cyber Automation Panel**\n\n"
        "Manage your accounts, check your live balance, and launch the mini app securely below:", 
        reply_markup=markup, 
        parse_mode="Markdown"
    )

# --- Callbacks Handler ---
@bot.callback_query_handler(func=lambda call: call.data in ["my_account", "add_account", "balance_menu", "add_money", "main_menu"])
def handle_callbacks(call):
    user_id = call.from_user.id
    conn = sqlite3.connect("swiggy_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    
    if call.data == "my_account":
        cursor.execute("SELECT account_name FROM accounts WHERE user_id = ?", (user_id,))
        accounts = cursor.fetchall()
        
        if not accounts:
            bot.answer_callback_query(call.id, "No accounts added yet!")
            bot.send_message(call.id, "❌ You haven't added any Swiggy accounts yet. Click '➕ Add Account' to link one.")
        else:
            acc_list = "\n".join([f"🔹 {acc[0]}" for acc in accounts])
            bot.send_message(call.id, f"📋 **Your Linked Accounts:**\n\n{acc_list}\n\n*Open Mini Web to switch and use them instantly.*", parse_mode="Markdown")
            
    elif call.data == "add_account":
        msg = bot.send_message(call.id, "📲 Please send your Swiggy **Auth Token** or registered **Mobile Number** to link your account:")
        bot.register_next_step_handler(msg, save_account_step)
        
    elif call.data == "balance_menu":
        cursor.execute("SELECT balance, referrals, ref_code FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        balance, referrals, ref_code = user_data[0], user_data[1], user_data[2]
        
        ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        
        text = (
            f"💰 **Your Wallet & Referral Details**\n\n"
            f"• **Total Balance:** ₹{balance}\n"
            f"• **Total Referrals:** {referrals} (Earned ₹{referrals * 3})\n\n"
            f"🔗 **Your Referral Link:**\n`{ref_link}`\n\n"
            f"*(Note: ₹3 added automatically per successful referral)*"
        )
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ Add Money (Min ₹10)", callback_data="add_money"))
        markup.add(InlineKeyboardButton("« Back to Menu", callback_data="main_menu"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        
    elif call.data == "add_money":
        msg = bot.send_message(call.id, "💳 Please enter the amount you want to add (Minimum **₹10**):")
        bot.register_next_step_handler(msg, process_amount_step)
        
    elif call.data == "main_menu":
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("👤 My Account", callback_data="my_account"),
            InlineKeyboardButton("➕ Add Account", callback_data="add_account")
        )
        markup.add(
            InlineKeyboardButton("💰 Balance & Refer", callback_data="balance_menu"),
            InlineKeyboardButton("💬 Support", url=SUPPORT_BOT)
        )
        markup.add(
            InlineKeyboardButton("🚀 Open Swiggy Mini Web", web_app=WebAppInfo(url=MINI_APP_URL))
        )
        bot.edit_message_text("⚡ **Swiggy Cyber Automation Panel**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    conn.close()

# --- Save Account Step ---
def save_account_step(message):
    user_id = message.from_user.id
    token_or_number = message.text.strip()
    
    conn = sqlite3.connect("swiggy_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    
    acc_name = f"Account_{random.randint(1000, 9999)}"
    cursor.execute("INSERT INTO accounts (user_id, account_name, auth_token) VALUES (?, ?, ?)", (user_id, acc_name, token_or_number))
    conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id, f"✅ **Account Successfully Linked!**\n\nYour session has been securely mapped. Open the Mini Web to start using it.")

# --- Add Money Workflow ---
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
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Submit UPI Reference / Paid", callback_data=f"submit_upi_{tx_id}_{amount}"))
        markup.add(InlineKeyboardButton("« Cancel", callback_data="balance_menu"))
        
        bot.send_message(
            message.chat.id, 
            f"📲 **Scan / Pay to UPI:**\n`{UPI_ID}`\n\nAmount: **₹{amount}**\n\nAfter payment, click submit below:", 
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
    
    bot.edit_message_text("⏳ Your payment details have been submitted. **Verifying by Admin...**", call.message.chat.id, call.message.message_id)
    
    # Notify Admin
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

# --- Admin Accept / Reject Handlers ---
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
    print("Swiggy Automation Bot is running live...")
    bot.infinity_polling()
