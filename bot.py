import os
import json
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
import firebase_admin
from firebase_admin import credentials, firestore

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)

# --- YOUR EXACT CONFIGURATION ---
BOT_TOKEN = "8813624728:AAF5v_Rnq3R4LYNP1_Sd_tBQU6TxomBDwK4"
ADMIN_CHAT_ID = 8053042225

CHANNELS = {
    "-1003332858806": {"name": "📢 GBX LOOT 1", "url": "https://t.me/+6ByfGDRBKgsxMjZl"},
    "-1003630519339": {"name": "📢 GBX EARN 2", "url": "https://t.me/+OWrCoeF-JutmNjg1"},
    "-1003862251237": {"name": "💬 GBX GC 1", "url": "https://t.me/+O_-kEF2f5f1kMjdl"},
    "-1003197501531": {"name": "💬 GBX GC 2", "url": "https://t.me/+f2mWfDs6EUIxYTBl"},
}

UPI_ID = "BHARATPE.8R0I1G1N4X31943@fbpe"

# --- FIREBASE INITIALIZATION (VIA ENVIRONMENT VARIABLE) ---
db = None
try:
    env_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if env_json:
        firebase_config = json.loads(env_json)
        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        logging.info("Firebase connected successfully via Environment Variable.")
    else:
        logging.error("CRITICAL ERROR: 'FIREBASE_CREDENTIALS_JSON' environment variable is missing on Render!")
except Exception as e:
    logging.error(f"Firebase Initialization Error: {e}")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# --- FSM STATES FOR DEPOSIT ---
class DepositState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_utr = State()


# --- KEYBOARDS ---
def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Add Account"), KeyboardButton(text="💰 Balance")],
            [KeyboardButton(text="📂 Account"), KeyboardButton(text="🎧 Customer Care")],
            [KeyboardButton(text="🌐 Mini Web")],
        ],
        resize_keyboard=True,
    )


def get_channels_keyboard():
    buttons = [
        [InlineKeyboardButton(text=data["name"], url=data["url"])]
        for chat_id, data in CHANNELS.items()
    ]
    buttons.append([InlineKeyboardButton(text="✅ Verify", callback_data="verify_join")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- 1. START & FORCE SUBSCRIPTION CHECK ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    if db is None:
        await message.answer("⚠️ Database is not connected. Please add FIREBASE_CREDENTIALS_JSON in Render environment variables.")
        return

    user_id = message.from_user.id

    user_ref = db.collection("users").document(str(user_id))
    user_doc = user_ref.get()
    
    if not user_doc.exists:
        user_ref.set({
            "user_id": user_id,
            "balance": 0.0,
            "is_verified": False
        })

    is_member = True
    for chat_id in CHANNELS.keys():
        try:
            member = await bot.get_chat_member(chat_id=int(chat_id), user_id=user_id)
            if member.status in ["left", "kicked"]:
                is_member = False
                break
        except Exception:
            is_member = False

    if not is_member:
        await message.answer(
            "⚠️ **Access Denied!**\nKripya pehle niche diye gaye sabhi channels/groups join karein aur fir 'Verify' par click karein:",
            reply_markup=get_channels_keyboard(),
            parse_mode="Markdown",
        )
    else:
        user_ref.update({"is_verified": True})
        await message.answer(
            "🎉 **Verification Successful!**\nAapka swagat hai. Neeche diye gaye menu ka upyog karein:",
            reply_markup=get_main_menu(),
            parse_mode="Markdown",
        )


@dp.callback_query(F.data == "verify_join")
async def verify_join_callback(callback: CallbackQuery):
    if db is None:
        await callback.answer("⚠️ Database error!", show_alert=True)
        return

    user_id = callback.from_user.id
    is_member = True

    for chat_id in CHANNELS.keys():
        try:
            member = await bot.get_chat_member(chat_id=int(chat_id), user_id=user_id)
            if member.status in ["left", "kicked"]:
                is_member = False
                break
        except Exception:
            is_member = False
            break

    if not is_member:
        await callback.answer("❌ Aapne abhi tak sabhi channels/groups join nahi kiye hain!", show_alert=True)
    else:
        db.collection("users").document(str(user_id)).update({"is_verified": True})
        await callback.message.delete()
        await callback.message.answer(
            "✅ **Verified Successfully!**\nSabhi channels join karne ke liye dhanyawad.",
            reply_markup=get_main_menu(),
            parse_mode="Markdown",
        )


# --- 2. BALANCE & DEPOSIT SYSTEM (UPI & UNIQUE UTR) ---
@dp.message(F.text == "💰 Balance")
async def show_balance(message: Message):
    if db is None:
        await message.answer("⚠️ Database is not connected.")
        return

    user_id = message.from_user.id
    user_doc = db.collection("users").document(str(user_id)).get()
    balance = user_doc.to_dict().get("balance", 0.0) if user_doc.exists else 0.0

    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"

    text = (
        f"💳 **Current Balance:** `₹{balance}`\n\n"
        f"🔗 **Your Referral Link:**\n`{ref_link}`\n\n"
        f"💡 *Agar aapko balance add karna hai, toh kripya neeche click karke amount bhejein.*"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="➕ Add Balance", callback_data="start_deposit")]]
    )
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")


@dp.callback_query(F.data == "start_deposit")
async def start_deposit(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Kripya add karne ke liye **Amount (Numbers me)** bhejein (jaise: 100):")
    await state.set_state(DepositState.waiting_for_amount)
    await callback.answer()


@dp.message(DepositState.waiting_for_amount)
async def process_deposit_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Kripya ek valid numeric amount bhejein.")
        return

    amount = int(message.text)
    await state.update_data(amount=amount)

    payment_text = (
        f"💳 **Payment Details**\n\n"
        f"Pay to UPI ID: `{UPI_ID}`\n"
        f"Amount: `₹{amount}`\n\n"
        f"Payment karne ke baad apna **12-digit UTR Number** neeche bhejein."
    )
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="cancel_deposit")]]
    )
    
    await message.answer(payment_text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(DepositState.waiting_for_utr)


@dp.message(DepositState.waiting_for_utr)
async def process_utr(message: Message, state: FSMContext):
    if db is None:
        await message.answer("⚠️ Database is not connected.")
        return

    utr = message.text.strip()
    if len(utr) != 12 or not utr.isdigit():
        await message.answer("❌ Invalid UTR! Kripya 12 digit ka valid UTR number bhejein.")
        return

    utr_query = db.collection("transactions").document(utr).get()
    if utr_query.exists:
        await message.answer("⚠️ **Error:** Yeh UTR pehle hi use kiya ja chuka hai! Duplicate UTR allowed nahi hai.")
        return

    data = await state.get_data()
    amount = data.get("amount")
    user_id = message.from_user.id

    tx_data = {
        "user_id": user_id,
        "amount": amount,
        "utr": utr,
        "status": "pending"
    }
    db.collection("transactions").document(utr).set(tx_data)

    await state.clear()
    await message.answer("✅ **UTR Submitted Successfully!** Admin approval ke baad balance add kar diya jayega.", reply_markup=get_main_menu())

    admin_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Accept", callback_data=f"approve_{utr}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{utr}"),
            ]
        ]
    )
    await bot.send_message(
        ADMIN_CHAT_ID,
        f"🔔 **New Deposit Request!**\n\nUser ID: `{user_id}`\nAmount: `₹{amount}`\nUTR: `{utr}`",
        reply_markup=admin_kb,
        parse_mode="Markdown",
    )


# --- 3. ADMIN APPROVAL / REJECTION HANDLER ---
@dp.callback_query(F.data.startswith(("approve_", "reject_")))
async def handle_admin_decision(callback: CallbackQuery):
    if db is None:
        await callback.answer("⚠️ Database error!", show_alert=True)
        return

    if callback.from_user.id != ADMIN_CHAT_ID:
        await callback.answer("⚠️ Yeh action sirf admin ke liye hai!", show_alert=True)
        return

    action, utr = callback.data.split("_", 1)
    tx_ref = db.collection("transactions").document(utr)
    tx_doc = tx_ref.get()

    if not tx_doc.exists or tx_doc.to_dict().get("status") != "pending":
        await callback.answer("⚠️ Yeh transaction pehle hi process ho chuki hai.", show_alert=True)
        return

    tx_data = tx_doc.to_dict()
    user_id = tx_data["user_id"]
    amount = tx_data["amount"]

    if action == "approve":
        tx_ref.update({"status": "approved"})
        user_ref = db.collection("users").document(str(user_id))
        current_bal = user_ref.get().to_dict().get("balance", 0.0)
        user_ref.update({"balance": current_bal + amount})
        
        await callback.message.edit_text(callback.message.text + "\n\n✅ **Approved & Balance Added!**")
        await bot.send_message(user_id, f"🎉 Aapka ₹{amount} ka deposit accept ho gaya hai aur balance add kar diya gaya hai!")
    else:
        tx_ref.update({"status": "rejected"})
        await callback.message.edit_text(callback.message.text + "\n\n❌ **Rejected!**")
        await bot.send_message(user_id, f"❌ Aapka ₹{amount} ka deposit reject kar diya gaya hai.")
    
    await callback.answer()


# --- 4. CUSTOMER CARE & OTHER MENU BUTTONS ---
@dp.message(F.text == "🎧 Customer Care")
async def customer_care(message: Message):
    support_link = "https://t.me/YourSupportUsername"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💬 Chat with Support", url=support_link)]]
    )
    await message.answer("Kisi bhi samasya ke liye hamare support se sampark karein:", reply_markup=kb)


@dp.message(F.text.in_(["➕ Add Account", "📂 Account", "🌐 Mini Web"]))
async def dummy_sections(message: Message):
    await message.answer("⚠️ Yeh feature jald hi live hoga ya iska Mini Web module connected hai.")


# --- 5. MAIN FUNCTION ---
async def main():
    print("Bot is starting...")
    # Purane webhook / conflicts clear karne ke liye drop_pending_updates=True use kiya gaya hai
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
