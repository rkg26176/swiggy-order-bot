const express = require('express');
const path = require('path');
const axios = require('axios');
const crypto = require('crypto');
const cors = require('cors');
const TelegramBot = require('node-telegram-bot-api');
const { HttpsProxyAgent } = require('https-proxy-agent');
const { db } = require('./firebase'); // Firebase DB connection

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

// 3 Proxy List Rotation Setup
const PROXIES = [
    "http://ZAhaiMvE:Y39OCfsKR0@103.163.55.57:50101",
    "http://Me01WF2K:OHVb4nh60D@103.163.55.125:50101",
    "http://aRSVpM7F:VDheTt93j0@103.171.77.18:50101"
];

let proxyIndex = 0;
function getProxyAgent() {
    const proxyUrl = PROXIES[proxyIndex];
    proxyIndex = (proxyIndex + 1) % PROXIES.length; // Rotate proxies automatically
    return new HttpsProxyAgent(proxyUrl);
}

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

const getAxiosConfig = (headers) => {
    return {
        headers,
        timeout: 30000,
        httpsAgent: getProxyAgent()
    };
};

// Helper: Check unjoined channels
async function getUnjoinedChannels(userId) {
    const unjoined = {};
    for (const [channelId, info] of Object.entries(CHANNELS)) {
        try {
            const member = await bot.getChatMember(channelId, userId);
            if (['left', 'kicked', 'restricted'].includes(member.status)) {
                unjoined[channelId] = info;
            }
        } catch (err) {
            unjoined[channelId] = info;
        }
    }
    return unjoined;
}

// Get or Create User Data from Firebase DB
async function getOrCreateUser(userId, username) {
    const userRef = db.collection('users').doc(String(userId));
    const doc = await userRef.get();

    if (doc.exists) {
        return doc.data();
    } else {
        const newUser = {
            userId: userId,
            username: username || 'User',
            key: generateUserKey(),
            balance: 0,
            totalDeposit: 0,
            accounts: [],
            orders: [],
            createdAt: new Date().toISOString()
        };
        await userRef.set(newUser);
        return newUser;
    }
}

// Send Main Menu
async function sendMainMenu(chatId, userId, username) {
    const userData = await getOrCreateUser(userId, username);
    const userKey = userData.key;
    const accountCount = userData.accounts ? userData.accounts.length : 0;
    const totalOrdersCount = userData.orders ? userData.orders.length : 0;
    const balance = userData.balance || 0;

    const webAppUrl = `https://swiggy-order-bot-production.up.railway.app/?key=${userKey}`;

    const welcomeMessage = `✨ **WELCOME TO SWIGGY GBX SWIGGY PRO ORDER BOT!** ✨\n\n` +
        `🚀 **You can use mini web for orders.**\n\n` +
        `📊 **STATS:**\n` +
        `👤 **Linked Accounts:** \`${accountCount}\`\n` +
        `📦 **Total Orders:** \`${totalOrdersCount}\`\n` +
        `💰 **Total Balance:** \`₹${balance}\`\n` +
        `🏷️ **Order Fee:** \`Free\`\n\n` +
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
                    { text: "💰 WALLET", callback_data: "wallet_menu" },
                    { text: "💬 SUPPORT", url: "https://t.me/gbx_support_bot" }
                ]
            ]
        }
    });
}

// Force Sub Prompt
async function sendForceSubPrompt(chatId, userId, username) {
    const unjoined = await getUnjoinedChannels(userId);
    if (Object.keys(unjoined).length === 0) {
        await sendMainMenu(chatId, userId, username);
        return;
    }

    let keyboard = [];
    for (const info of Object.values(unjoined)) {
        keyboard.push([{ text: info.name, url: info.url }]);
    }
    keyboard.push([{ text: "🔄 VERIFY JOIN", callback_data: "verify_join" }]);

    await bot.sendMessage(chatId, `⚠️ **Please join our channels to use the bot:**`, {
        parse_mode: "Markdown",
        reply_markup: { inline_keyboard: keyboard }
    });
}

// ==================== TELEGRAM LISTENERS ====================
bot.onText(/\/start/, async (msg) => {
    if (['group', 'supergroup'].includes(msg.chat.type)) return;
    await sendForceSubPrompt(msg.chat.id, msg.from.id, msg.from.username);
});

bot.on('callback_query', async (query) => {
    const chatId = query.message.chat.id;
    const userId = query.from.id;
    const data = query.data;
    const userRef = db.collection('users').doc(String(userId));
    const userDoc = await userRef.get();
    const userData = userDoc.exists ? userDoc.data() : null;

    if (data === "verify_join") {
        const unjoined = await getUnjoinedChannels(userId);
        if (Object.keys(unjoined).length > 0) {
            bot.answerCallbackQuery(query.id, { text: "❌ Please join all channels first!", show_alert: true });
        } else {
            bot.answerCallbackQuery(query.id, { text: "✅ Verified!" });
            try { await bot.deleteMessage(chatId, query.message.message_id); } catch(e) {}
            await sendMainMenu(chatId, userId, query.from.username);
        }
    } else if (data === "bulk_login") {
        bot.sendMessage(chatId, "📦 **Bulk Login:** Send your Swiggy JSON session data here in a single message or bulk lines. It will be injected directly into your account.");
    } else if (data === "bulk_export") {
        if (!userData || !userData.accounts || userData.accounts.length === 0) {
            bot.sendMessage(chatId, "📥 No accounts found to export.");
        } else {
            bot.sendMessage(chatId, `📥 **Your Accounts JSON Export:**\n\n\`\`\`json\n${JSON.stringify(userData.accounts, null, 2)}\n\`\`\``, { parse_mode: "Markdown" });
        }
    } else if (data === "wallet_menu") {
        const balance = userData?.balance || 0;
        const totalDeposit = userData?.totalDeposit || 0;
        bot.sendMessage(chatId, `💳 **WALLET PANEL**\n\n💰 **Balance:** ₹${balance}\n📥 **Total Deposit:** ₹${totalDeposit}\n🏷️ **Order Fee:** Free\n\nClick Deposit to add funds.`, {
            parse_mode: "Markdown",
            reply_markup: {
                inline_keyboard: [
                    [{ text: "➕ DEPOSIT", callback_data: "deposit_funds" }],
                    [{ text: "🔙 BACK TO MENU", callback_data: "back_menu" }]
                ]
            }
        });
    } else if (data === "deposit_funds") {
        bot.sendMessage(chatId, "💡 **Deposit:** Please enter minimum ₹15 to add to your wallet balance.");
    } else if (data === "back_menu") {
        try { await bot.deleteMessage(chatId, query.message.message_id); } catch(e) {}
        await sendMainMenu(chatId, userId, query.from.username);
    }
});

bot.on('message', async (msg) => {
    if (['group', 'supergroup'].includes(msg.chat.type)) return;
    if (!msg.text || msg.text.startsWith('/')) return;

    const userId = msg.from.id;
    const text = msg.text.trim();

    if (text.startsWith('[') || text.startsWith('{')) {
        try {
            const parsedData = JSON.parse(text);
            const userRef = db.collection('users').doc(String(userId));
            const doc = await userRef.get();
            
            let accounts = doc.exists ? (doc.data().accounts || []) : [];
            if (Array.isArray(parsedData)) {
                accounts.push(...parsedData);
            } else {
                accounts.push(parsedData);
            }

            await userRef.update({ accounts });
            bot.sendMessage(msg.chat.id, `✅ **Success!** Added accounts via Bulk Login. Total linked: ${accounts.length}`);
        } catch (err) {
            // Invalid JSON ignored
        }
    }
});

// ==================== WEB API ENDPOINTS ====================

app.get('/api/user-data', async (req, res) => {
    try {
        const { key } = req.query;
        if (!key) return res.status(400).json({ error: "Key is required" });

        const snapshot = await db.collection('users').where('key', '==', key).get();
        if (snapshot.empty) {
            return res.status(404).json({ error: "Invalid Key" });
        }

        const userData = snapshot.docs[0].data();
        res.json({ success: true, user: userData });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/api/send_otp', async (req, res) => {
    try {
        const { mobile } = req.body;
        const cleanMobile = String(mobile || "").trim().slice(-10);
        if (cleanMobile.length !== 10) return res.status(400).json({ error: "10-digit mobile required" });

        const deviceId = newDeviceId();
        const response = await axios.get(`${SMS_OTP_URL}?mobile=${cleanMobile}`, getAxiosConfig(getSwiggyHeaders(deviceId)));
        
        res.json({ status: "success", data: response.data, deviceId });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// SPA Fallback Route
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// Start Server for Railway (Fixed Host Binding)
const HOST = '0.0.0.0';
app.listen(PORT, HOST, () => {
    console.log(`GBX Swiggy Bot Server running on port ${PORT}`);
});
