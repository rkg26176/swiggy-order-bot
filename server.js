const express = require('express');
const path = require('path');
const axios = require('axios');
const crypto = require('crypto');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Static frontend serve
app.use(express.static(path.join(__dirname)));

// Swiggy Endpoints
const SMS_OTP_URL = "https://profile.swiggy.com/api/v3/app/sms_otp";
const VERIFY_URL = "https://profile.swiggy.com/api/v3/app/login/verify";

// Temporary memory for OTP session storage (जैसे आपके फ्लस्क कोड में था)
const PENDING_OTP = {};

function newDeviceId() {
    return crypto.randomBytes(8).toString('hex');
}

// Standard Swiggy Headers Generator
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


// ==================== AUTH & OTP ROUTES (Flask के लॉजिक जैसा) ====================

app.post('/api/send_otp', async (req, res) => {
    try {
        const bodyData = req.body || {};
        const mobile = String(bodyData.mobile || "").strip ? bodyData.mobile.trim().slice(-10) : String(bodyData.mobile || "").slice(-10);
        
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

        res.json({ status: "success", message: "OTP Sent successfully" });
    } catch (error) {
        res.status(500).json({ status: "error", message: error.message });
    }
});

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

        res.json({ status: "success", data: response.data });
    } catch (error) {
        res.status(500).json({ status: "error", message: error.message });
    }
});


// ==================== MAPS & DISCOVERY PROXIES (Dynamic lat/lng) ====================

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

// Fallback to frontend index.html
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// Server Listen
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});
