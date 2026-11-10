const express = require('express');
const path = require('path');
const axios = require('axios');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Serve static frontend assets from the root directory
app.use(express.static(path.join(__dirname)));

// Standard Swiggy Mobile Headers Mock
const getSwiggyHeaders = (deviceId) => ({
    "User-Agent": "Mozilla/5.0 (Linux; Android 11; Pixel 4 Build/RD2A.211001.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/83.0.4103.120 Mobile Safari/537.36",
    "platform": "Swiggy-Android",
    "version-code": "1795",
    "model-name": "PIXEL 4",
    "manufacturer": "GOOGLE",
    "application_name": "swiggy-app",
    "appversion": "4.113.0",
    "cityid": "18",
    "x-requested-with": "in.swiggy.android",
    "x-theme": "base",
    "accept-language": "en-IN,en-US;q=0.9,en;q=0.8",
    "deviceId": deviceId || "default_device_id",
    "swuid": deviceId || "default_device_id"
});

// ==================== MAPS & ADDRESS APIS ====================

// 1. Address Recommendations
app.get('/address/recommend', async (req, res) => {
    try {
        const { latlng } = req.query;
        if (!latlng) return res.status(400).json({ error: "latlng is required" });

        const response = await axios.get(`https://maps.swiggy.com/address/recommend?latlng=${latlng}`, {
            headers: getSwiggyHeaders(req.headers['deviceid'])
        });
        res.json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json({ error: "Failed to fetch address recommend", details: error.message });
    }
});

// 2. Place Autocomplete
app.get('/place/autocomplete', async (req, res) => {
    try {
        const { input, location, radius } = req.query;
        const response = await axios.get(`https://maps.swiggy.com/place/autocomplete`, {
            params: { input, location, radius },
            headers: getSwiggyHeaders(req.headers['deviceid'])
        });
        res.json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json({ error: "Failed autocomplete", details: error.message });
    }
});

// 3. Addresses v1
app.get('/addresses/v1', async (req, res) => {
    try {
        const response = await axios.get(`https://maps.swiggy.com/addresses/v1`, {
            headers: getSwiggyHeaders(req.headers['deviceid'])
        });
        res.json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json({ error: "Failed addresses v1", details: error.message });
    }
});


// ==================== DISCOVERY & FOOD APIS ====================

// 4. Overlays
app.get('/api/v1/overlays', async (req, res) => {
    try {
        const response = await axios.get(`https://disc.swiggy.com/api/v1/overlays`, {
            headers: getSwiggyHeaders(req.headers['deviceid'])
        });
        res.json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json({ error: "Failed overlays", details: error.message });
    }
});

// 5. Skeleton
app.get('/api/v1/skeleton', async (req, res) => {
    try {
        const { lat, lng } = req.query;
        const response = await axios.get(`https://disc.swiggy.com/api/v1/skeleton`, {
            params: { lat, lng },
            headers: getSwiggyHeaders(req.headers['deviceid'])
        });
        res.json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json({ error: "Failed skeleton", details: error.message });
    }
});

// 6. Launch Configs
app.get('/api/v1/launch-configs', async (req, res) => {
    try {
        const response = await axios.get(`https://disc.swiggy.com/api/v1/launch-configs`, {
            headers: getSwiggyHeaders(req.headers['deviceid'])
        });
        res.json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json({ error: "Failed launch-configs", details: error.message });
    }
});

// 7. Food v2 (Main Home Feed)
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
        res.status(error.response?.status || 500).json({ error: "Failed food data", details: error.message });
    }
});

// 8. Auto-Suggest
app.get('/api/v1/auto-suggest', async (req, res) => {
    try {
        const { lat, lng } = req.query;
        const response = await axios.get(`https://disc.swiggy.com/api/v1/auto-suggest/`, {
            params: { lat, lng },
            headers: getSwiggyHeaders(req.headers['deviceid'])
        });
        res.json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json({ error: "Failed auto-suggest", details: error.message });
    }
});

// 9. Search v3
app.get('/api/v3/search', async (req, res) => {
    try {
        const { lat, lng, str } = req.query;
        const response = await axios.get(`https://disc.swiggy.com/api/v3/search/`, {
            params: { lat, lng, str },
            headers: getSwiggyHeaders(req.headers['deviceid'])
        });
        res.json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json({ error: "Failed search", details: error.message });
    }
});

// 10. Restaurant Menu v2
app.get('/api/v2/menu/:restaurantId', async (req, res) => {
    try {
        const { restaurantId } = req.params;
        const { lat, lng } = req.query;
        const response = await axios.get(`https://disc.swiggy.com/api/v2/menu/${restaurantId}`, {
            params: { 'complete-menu': 'true', lat, lng },
            headers: getSwiggyHeaders(req.headers['deviceid'])
        });
        res.json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json({ error: "Failed menu fetch", details: error.message });
    }
});

// 11. Layout Sections (Cross sell, cart updates, etc.)
app.get('/api/v1/layout-section/:sectionName', async (req, res) => {
    try {
        const { sectionName } = req.params;
        const { lat, lng } = req.query;
        const response = await axios.get(`https://disc.swiggy.com/api/v1/layout-section/${sectionName}`, {
            params: { lat, lng },
            headers: getSwiggyHeaders(req.headers['deviceid'])
        });
        res.json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json({ error: "Failed layout-section", details: error.message });
    }
});


// ==================== APP & EXTERNAL SERVICES ====================

// 12. Getlink v1
app.get('/getlink/v1', async (req, res) => {
    try {
        const { aid } = req.query;
        const response = await axios.get(`https://app.swiggy.com/getlink/v1`, {
            params: { aid },
            headers: getSwiggyHeaders(req.headers['deviceid'])
        });
        res.json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json({ error: "Failed getlink", details: error.message });
    }
});

// 13. Payments options proxy
app.get('/api/v3/payment/get-payment-options', async (req, res) => {
    try {
        const response = await axios.get(`https://payments.swiggy.com/api/v3/payment/get-payment-options`, {
            headers: getSwiggyHeaders(req.headers['deviceid'])
        });
        res.json(response.data);
    } catch (error) {
        res.status(error.response?.status || 500).json({ error: "Failed payment options", details: error.message });
    }
});


// Fallback to index.html for Single Page Application routing
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// Start Server
app.listen(PORT, () => {
    console.log(`GBX Support Server is running on port ${PORT}`);
});
