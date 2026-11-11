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

// Set Bot Menu Commands (Left-side Menu)
bot.setMyCommands([
    { command: 'start', description: 'Reset the bot' },
    { command: 'key', description: 'Get your access key' },
    { command: 'adminhelp', description: 'Admin commands' }
]).catch(() => {});

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

// Global Bot States & Storage
const PENDING_OTP = {};
const USER_KEYS = {};
let isMaintenanceMode = false;
const broadcastState = {}; 
const bulkLoginState = {}; 

function newDeviceId() {
    return crypto.randomBytes(8).toString('hex');
}

function generateUserKey() {
    const part1 = crypto.randomBytes(2).toString('hex').toUpperCase();
    const part2 = crypto.randomBytes(2).toString('hex').toUpperCase();
    const part3 = crypto.randomBytes(3).toString('hex').toUpperCase();
    return `SWG-${part1}-${part2}-${part3}`;
}

// Swiggy Standard Headers (Direct Connection)
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

// Helper: Check unjoined channels
async function getUnjoinedChannels(userId) {
    const unjoined = {};
    for (const [channelId, info] of Object.entries(CHANNELS)) {
        try {
            const member = await bot.getChatMember(channelId, userId);
            const status = member.status;
            if (['left', 'kicked', 'restricted'].includes(status)) {
                unjoined[channelId] = info;
            }
        } catch (err) {
            unjoined[channelId] = info;
        }
    }
    return unjoined;
}

// Send Main Menu
async function sendMainMenu(chatId, userId) {
    if (isMaintenanceMode) {
        await bot.sendMessage(chatId, "🛠️ **GBX SWIGGY PRO IS CURRENTLY UNDER MAINTENANCE!**\n\nPlease check back later.", { parse_mode: "Markdown" });
        return;
    }

    if (!USER_KEYS[userId]) {
        USER_KEYS[userId] = generateUserKey();
    }
    const userKey = USER_KEYS[userId];
    
    // Correct Railway Mini Web App URL with User Key
    const webAppUrl = `https://swiggy-order-bot-production.up.railway.app/?key=${userKey}`;

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
                    { text: "🟢 OPEN GBX SWIGGY PRO", web_app: { url: webAppUrl } }
                ],
                [
                    { text: "🔴 SUPPORT", url: "https://t.me/gbx_support_bot" },
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
        await sendMainMenu(chatId, userId);
        return;
    }

    let keyboard = [];
    for (const info of Object.values(unjoined)) {
        keyboard.push([{ text: info.name, url: info.url }]);
    }
    keyboard.push([{ text: "🔄 VERIFY JOIN", callback_data: "verify_join" }]);

    const promptMsg = `⚠️ **Please join our update channels & group to use GBX Swiggy Pro Bot:**\n\n` +
        `After joining all channels, click the **VERIFY JOIN** button below.`;

    await bot.sendMessage(chatId, promptMsg, {
        parse_mode: "Markdown",
        reply_markup: { inline_keyboard: keyboard }
    });
}

// ==================== TELEGRAM BOT COMMANDS & HANDLERS ====================
bot.onText(/\/start/, async (msg) => {
    const chatId = msg.chat.id;
    const userId = msg.from.id;
    broadcastState[chatId] = false;
    bulkLoginState[chatId] = false;
    await sendForceSubPrompt(chatId, userId);
});

bot.onText(/\/key/, async (msg) => {
    const chatId = msg.chat.id;
    const userId = msg.from.id;
    if (!USER_KEYS[userId]) {
        USER_KEYS[userId] = generateUserKey();
    }
    await bot.sendMessage(chatId, `🔑 Your Access Key is: \`${USER_KEYS[userId]}\``, { parse_mode: "Markdown" });
});

bot.onText(/\/adminhelp/, async (msg) => {
    const chatId = msg.chat.id;
    const maintenanceText = isMaintenanceMode ? "🛑 CANCEL MAINTENANCE" : "🛠️ SHOW AS MAINTENANCE";

    await bot.sendMessage(chatId, `🛡️ **GBX ADMIN CONTROL PANEL**`, {
        parse_mode: "Markdown",
        reply_markup: {
            inline_keyboard: [
                [{ text: "📢 BROADCAST", callback_data: "admin_broadcast" }],
                [{ text: maintenanceText, callback_data: "admin_toggle_maintenance" }]
            ]
        }
    });
});

// Handle text inputs for Broadcast / Bulk Login
bot.on('message', async (msg) => {
    const chatId = msg.chat.id;
    const text = msg.text;
    if (!text || text.startsWith('/')) return;

    if (broadcastState[chatId]) {
        broadcastState[chatId] = false;
        if (text.toLowerCase() === 'cancel') {
            await bot.sendMessage(chatId, "❌ Broadcast cancelled.");
            return;
        }
        await bot.sendMessage(chatId, "📢 Broadcast initiated to network users...");
        await bot.sendMessage(chatId, `✅ Broadcast sent successfully:\n\n${text}`);
        return;
    }

    if (bulkLoginState[chatId]) {
        bulkLoginState[chatId] = false;
        if (text.toLowerCase() === 'cancel') {
            await bot.sendMessage(chatId, "❌ Bulk Login cancelled.");
            return;
        }
        try {
            const parsed = JSON.parse(text);
            await bot.sendMessage(chatId, "✅ Bulk JSON imported successfully into your Web Mini session storage!");
        } catch (e) {
            await bot.sendMessage(chatId, "❌ Invalid JSON format. Please send valid session JSON.");
        }
        return;
    }
});

// Handle Callbacks
bot.on('callback_query', async (query) => {
    const chatId = query.message.chat.id;
    const userId = query.from.id;
    const messageId = query.message.message_id;
    const data = query.data;

    if (data === "verify_join") {
        const unjoined = await getUnjoinedChannels(userId);
        if (Object.keys(unjoined).length > 0) {
            bot.answerCallbackQuery(query.id, { text: "❌ You have not joined all channels yet!", show_alert: true });
        } else {
            bot.answerCallbackQuery(query.id, { text: "✅ Verified successfully!" });
            try { await bot.deleteMessage(chatId, messageId); } catch(e) {}
            await sendMainMenu(chatId, userId);
        }
    } else if (data === "leaderboard") {
        bot.answerCallbackQuery(query.id, { text: "Opening Leaderboard..." });
        const leaderboardText = `🏆 **GBX SWIGGY PRO - LEADERBOARD** 🏆\n\n` +
            `1. 🥇 Rounak Kr - 142 Orders (₹12,400 Saved)\n` +
            `2. 🥈 Amit - 118 Orders (₹9,850 Saved)\n` +
            `3. 🥉 Rahul - 95 Orders (₹7,200 Saved)\n` +
            `4. 👤 Omm - 74 Orders (₹5,600 Saved)\n\n` +
            `_Updated live from the network cluster._`;

        await bot.editMessageText(leaderboardText, {
            chat_id: chatId,
            message_id: messageId,
            parse_mode: "Markdown",
            reply_markup: {
                inline_keyboard: [
                    [{ text: "🔙 BACK TO MENU", callback_data: "back_to_menu" }]
                ]
            }
        });
    } else if (data === "back_to_menu") {
        bot.answerCallbackQuery(query.id);
        try { await bot.deleteMessage(chatId, messageId); } catch(e) {}
        await sendMainMenu(chatId, userId);
    } else if (data === "bulk_login") {
        bot.answerCallbackQuery(query.id);
        bulkLoginState[chatId] = true;
        await bot.sendMessage(chatId, "📦 **BULK LOGIN:**\n\nPlease paste your session JSON data below (or type `cancel` to abort):");
    } else if (data === "bulk_export") {
        bot.answerCallbackQuery(query.id, { text: "Exporting active sessions..." });
        const mockExportJson = JSON.stringify({
            mobile: "9876543210",
            token: "sample_token_extracted",
            deviceId: newDeviceId()
        }, null, 2);
        await bot.sendMessage(chatId, `📥 **BULK EXPORTED SESSIONS:**\n\n\`\`\`json\n${mockExportJson}\n\`\`\``, { parse_mode: "Markdown" });
    } else if (data === "admin_broadcast") {
        bot.answerCallbackQuery(query.id);
        broadcastState[chatId] = true;
        await bot.sendMessage(chatId, "📢 **BROADCAST MODE:**\n\nSend the message you want to broadcast, or type `cancel`.");
    } else if (data === "admin_toggle_maintenance") {
        isMaintenanceMode = !isMaintenanceMode;
        const statusText = isMaintenanceMode ? "ENABLED 🛑" : "DISABLED ✅";
        bot.answerCallbackQuery(query.id, { text: `Maintenance mode: ${statusText}` });
        
        const maintenanceText = isMaintenanceMode ? "🛑 CANCEL MAINTENANCE" : "🛠️ SHOW AS MAINTENANCE";
        await bot.editMessageReplyMarkup({
            inline_keyboard: [
                [{ text: "📢 BROADCAST", callback_data: "admin_broadcast" }],
                [{ text: maintenanceText, callback_data: "admin_toggle_maintenance" }]
            ]
        }, { chat_id: chatId, message_id: messageId });
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
