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

// Swiggy Auth & OTP Endpoints
const SMS_OTP_URL = "https://profile.swiggy.com/api/v3/app/sms_otp";
const VERIFY_URL = "https://profile.swiggy.com/api/v3/app/login/verify";

// Temporary memory for OTP sessions
const PENDING_OTP = {};

function newDeviceId() {
    return crypto.randomBytes(8).toString('hex');
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

// ==================== TELEGRAM BOT LISTENERS ====================
bot.onText(/\/start/, (msg) => {
    const chatId = msg.chat.id;
    // Render या लोकल होस्ट के हिसाब से अपने ऐप का URL सेट कर लें
    const appUrl = process.env.RENDER_EXTERNAL_URL || `https://${msg.from?.username ? 'swiggy-order-bot.onrender.com' : 'localhost:' + PORT}`;
    
    bot.sendMessage(chatId, "✨ **Swiggy PRO** ऐप में आपका स्वागत है! नीचे दिए गए बटन पर क्लिक करके ऐप खोलें:", {
        parse_mode: "Markdown",
        reply_markup: {
            inline_keyboard: [
                [{ text: "🚀 Open Swiggy Pro App", web_app: { url: `https://storelex.store/swiggy_web/` } }]
            ]
        }
    });
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
