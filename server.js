const express = require('express');
const path = require('path');
const axios = require('axios');
const crypto = require('crypto');
const cors = require('cors');
const TelegramBot = require('node-telegram-bot-api');

const app = express();
const PORT = process.env.PORT || 3000;

// Telegram Bot Setup
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN || '8813624728:AAHxIFtVwuq_6rcPJf9a9tAhnaJa6JS_ivg';
const bot = new TelegramBot(TELEGRAM_BOT_TOKEN, { polling: true });

// Middleware Setup
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Static frontend serve
app.use(express.static(path.join(__dirname)));

// Force Subscribe Channels Dictionary
const CHANNELS = {
    "-1003332858806": { "name": "📢 GBX LOOT", "url": "https://t.me/+6ByfGDRBKgsxMjZl" },
    "-1003630519339": { "name": "📢 GBX EARN", "url": "https://t.me/+OWrCoeF-JutmNjg1" },
    "-1003197501531": { "name": "📢 GBX ZONE", "url": "https://t.me/+f2mWfDs6EUIxYTBl" },
    "-1003862251237": { "name": "💬 Join Group Chat (GC)", "url": "https://t.me/+O_-kEF2f5f1kMjdl" }
};

// Swiggy Auth & OTP Endpoints
const SMS_OTP_URL = "https://profile.swiggy.com/api/v3/app/sms_otp";
const VERIFY_URL = "https://profile.swiggy.com/api/v3/app/login/verify";

// Temporary memory for sessions & User Keys
const PENDING_OTP = {};
const USER_KEYS = {};

function newDeviceId() {
    return crypto.randomBytes(8).toString('hex');
}

function generateUserKey() {
    const part1 = crypto.randomBytes(2).toString('hex').toUpperCase();
    const part2 = crypto.randomBytes(2).toString('hex').toUpperCase();
    const part3 = crypto.randomBytes(3).toString('hex').toUpperCase();
    return `SWG-${part1}-${part2}-${part3}`;
}

// Swiggy Standard Headers
const getSwiggyHeaders = (deviceId) => {
    const d = deviceId || newDeviceId();
    return {
        "Accept": "application/json; charset=utf-8",
        "User-Agent": "Mozilla/5.0 (Linux; Android 11; Pixel 4 Build/RD2A.211001.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/83.0.4103.120 Mobile Safari/537.36",
        "platform": "Swiggy-Android",
        "version-code": "1795",
        "model-name": "PIXEL 4",
        "manufacturer": "GOOGLE",
        "application_name": "swiggy-app",
        "appversion": "4.113.0",
        "cityid": "18",
        "deviceId": d,
        "swuid": d,
        "os-version": "9",
        "pl-version": "131",
        "x-channel": "swiggy",
        "x-requested-with": "in.swiggy.android",
        "x-theme": "base",
        "accept-language": "en-IN,en-US;q=0.9,en;q=0.8"
    };
};

// Helper: Check which channels the user has NOT joined yet
async function getUnjoinedChannels(userId) {
    const unjoined = {};
    for (const [channelId, info] of Object.entries(CHANNELS)) {
        try {
            const member = await bot.getChatMember(channelId, userId);
            const status = member.status;
            // If user left, kicked, or not a member/creator/administrator
            if (['left', 'kicked', 'restricted'].includes(status)) {
                unjoined[channelId] = info;
            }
        } catch (err) {
            // If bot is not admin or cannot check, treat as unjoined to be safe, or skip
            unjoined[channelId] = info;
        }
    }
    return unjoined;
}

// Send Main Menu (When joined all channels)
async function sendMainMenu(chatId, userId) {
    if (!USER_KEYS[userId]) {
        USER_KEYS[userId] = generateUserKey();
    }
    const userKey = USER_KEYS[userId];
    const webAppUrl = `https://storelex.store/swiggy_web/?key=${userKey}`;

    const welcomeMessage = `✨ **WELCOME TO GBX SWIGGY PRO ORDER BOT!**\n\n` +
        `🚀 **YOU CAN USE WEB MINI FOR ORDERS.**\n\n` +
        `🔑 **KEY : \`${userKey}\`**`;

    await bot.sendMessage(chatId, welcomeMessage, {
        parse_mode: "Markdown",
        reply_markup: {
            inline_keyboard: [
                [
                    { text: "📦 BULK LOGIN", callback_data: "bulk_login" },
                    { text: "📥 BULK EXPORT", callback_data: "bulk_export" }
                ],
                [
                    { text: "🌐 OPEN GBX SWIGGY PRO", web_app: { url: webAppUrl } }
                ],
                [
                    { text: "💬 SUPPORT", url: "https://t.me/gbx_support_bot" },
                    { text: "🏆 LEADERBOARD", callback_data: "leaderboard" }
                ]
            ]
        }
    });
}

// Send Force Subscribe Prompt
async function sendForceSubPrompt(chatId, userId) {
    const unjoined = await getUnjoinedChannels(userId);
    const unjoinedKeys = Object.keys(unjoined);

    if (unjoinedKeys.length === 0) {
        // All joined, show main menu
        await sendMainMenu(chatId, userId);
        return;
    }

    let keyboard = [];
    for (const info of Object.values(unjoined)) {
        keyboard.push([{ text: info.name, url: info.url }]);
    }
    // Add Verify button
    keyboard.push([{ text: "🔄 VERIFY JOIN", callback_data: "verify_join" }]);

    const promptMsg = `⚠️ **Please join our update channels & group to use GBX Swiggy Pro Bot:**\n\n` +
        `After joining all channels, click the **VERIFY JOIN** button below.`;

    await bot.sendMessage(chatId, promptMsg, {
        parse_mode: "Markdown",
        reply_markup: { inline_keyboard: keyboard }
    });
}

// ==================== TELEGRAM BOT LISTENERS ====================
bot.onText(/\/start/, async (msg) => {
    const chatId = msg.chat.id;
    const userId = msg.from.id;
    await sendForceSubPrompt(chatId, userId);
});

bot.on('callback_query', async (query) => {
    const chatId = query.message.chat.id;
    const userId = query.from.id;
    const data = query.data;

    if (data === "verify_join") {
        const unjoined = await getUnjoinedChannels(userId);
        if (Object.keys(unjoined).length > 0) {
            bot.answerCallbackQuery(query.id, { text: "❌ You have not joined all channels yet!", show_alert: true });
        } else {
            bot.answerCallbackQuery(query.id, { text: "✅ Verified successfully!" });
            try {
                await bot.deleteMessage(chatId, query.message.message_id);
            } catch(e) {}
            await sendMainMenu(chatId, userId);
        }
    } else if (data === "bulk_login") {
        bot.answerCallbackQuery(query.id, { text: "Bulk Login feature is active via Web App." });
        bot.sendMessage(chatId, "📦 **Bulk Login:** Please open the Web App to manage and login multiple accounts securely.");
    } else if (data === "bulk_export") {
        bot.answerCallbackQuery(query.id, { text: "Bulk Export feature is ready." });
        bot.sendMessage(chatId, "📥 **Bulk Export:** You can export your session JSON directly from the accounts tab inside the Web App.");
    } else if (data === "leaderboard") {
        bot.answerCallbackQuery(query.id, { text: "Loading Leaderboard..." });
        bot.sendMessage(chatId, "🏆 **GBX Leaderboard:** Top order placers of this week are active in the network!");
    }
});

// ==================== OTP SEND ROUTE ====================
app.post('/api/send_otp', async (req, res) => {
    try {
        const bodyData = req.body || {};
        const mobile = String(bodyData.mobile || "").trim().slice(-10);
        
        if (mobile.length !== 10) {
            return res.status(400).json({ status: "error", message: "10-digit mobile number required" });
        }

        const deviceId = newDeviceId();
        const response = await axios.get(`${SMS_OTP_URL}?mobile=${mobile}`, {
            headers: getSwiggyHeaders(deviceId),
            timeout: 30000
        });

        const resData = response.data || {};
        PENDING_OTP[mobile] = {
            tid: resData.tid,
            sid: resData.sid,
            device_id: deviceId
        };

        return res.json({ status: "success", message: "OTP Sent successfully" });
    } catch (error) {
        console.error("Send OTP Error:", error.message);
        return res.status(500).json({ status: "error", message: error.response?.data?.message || error.message });
    }
});

// ==================== OTP VERIFY ROUTE ====================
app.post('/api/verify_otp', async (req, res) => {
    try {
        const bodyData = req.body || {};
        const mobile = String(bodyData.mobile || "").trim().slice(-10);
        const otp = String(bodyData.otp || "").trim();

        const st = PENDING_OTP[mobile];
        if (!st) {
            return res.status(400).json({ status: "error", message: "Session expired, please resend OTP" });
        }

        const h = {
            ...getSwiggyHeaders(st.device_id),
            "sid": st.sid,
            "Tid": st.tid,
            "Content-Type": "application/json; charset=utf-8"
        };

        const p = {
            "cloningSignalsData": {
                "appFilesDirPathInvalid": 0, "developerModeEnabled": 0,
                "deviceModelVmos": 0, "emulatorStatus": 0,
                "packageName": "in.swiggy.android", "workProfileEnabled": 0
            },
            "otp": otp
        };

        const response = await axios.post(`${VERIFY_URL}?otp_source=Sms-automatic`, p, {
            headers: h,
            timeout: 30000
        });

        return res.json({ status: "success", data: response.data });
    } catch (error) {
        console.error("Verify OTP Error:", error.message);
        return res.status(500).json({ status: "error", message: error.response?.data?.message || error.message });
    }
});

// ==================== MAPS & DISCOVERY PROXIES ====================
app.get('/address/recommend', async (req, res) => {
    try {
        const { latlng } = req.query;
        if (!latlng) return res.status(400).json({ error: "latlng is required" });

        const response = await axios.get(`https://maps.swiggy.com/address/recommend?latlng=${latlng}`, {
            headers: getSwiggyHeaders(req.headers['deviceid'])
        });
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/v2/food', async (req, res) => {
    try {
        const { lat, lng, isTopNavEntry } = req.query;
        if (!lat || !lng) return res.status(400).json({ error: "lat and lng are required" });

        const response = await axios.get(`https://disc.swiggy.com/api/v2/food`, {
            params: { lat, lng, isTopNavEntry: isTopNavEntry || 'true' },
            headers: getSwiggyHeaders(req.headers['deviceid'])
        });
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/v1/auto-suggest', async (req, res) => {
    try {
        const { lat, lng } = req.query;
        const response = await axios.get(`https://disc.swiggy.com/api/v1/auto-suggest/`, {
            params: { lat, lng },
            headers: getSwiggyHeaders(req.headers['deviceid'])
        });
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/v3/search', async (req, res) => {
    try {
        const { lat, lng, str } = req.query;
        const response = await axios.get(`https://disc.swiggy.com/api/v3/search/`, {
            params: { lat, lng, str },
            headers: getSwiggyHeaders(req.headers['deviceid'])
        });
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// SPA Fallback
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// Start Server
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});
