/**
 * Swiggy Order Food — Cart tab
 * Shows the restaurant cart built in Search (sr.cart in search.js): items, delivery spot,
 * best coupon (auto-applied), bill, order preferences and UPI / Pay-on-Delivery availability.
 * Backend: /api/search/cart, /api/checkout/{coupons,apply_coupon,best_coupon,payment_options}
 */

const SC_PREFS_KEY = 'swiggy_cart_prefs';

const sc = {
    coupons: null,        // list for the coupon sheet
    couponBusy: false,
    autoKey: '',          // cart state the best coupon was last picked for
    pay: null,            // payment options
    payKey: '',
    method: 'upi',
    placing: false,
    pollStop: false,
    order: null,
};

function scPrefs() {
    let p = {};
    try { p = JSON.parse(localStorage.getItem(SC_PREFS_KEY) || '{}'); } catch (e) { p = {}; }
    // on by default: every order goes incognito (Swiggy drops it from order history after 3 hours)
    return { incognito: p.incognito !== false };
}

function scToggleIncognito() {
    const on = !scPrefs().incognito;
    localStorage.setItem(SC_PREFS_KEY, JSON.stringify({ ...scPrefs(), incognito: on }));
    scSyncIncogBtn();
    showToast(on ? 'Incognito on — order history deletes in 3 hours' : 'Incognito off — order stays in history', !on, 2000);
    if (sr.cart.lines.length) { sc.autoKey = ''; srSyncCart(); }
}

function scSyncIncogBtn() {
    const btn = scEl('scIncogBtn');
    if (btn) btn.classList.toggle('on', scPrefs().incognito);
}

// our wording for some of Swiggy's bill rows
const SC_BILL_LABELS = {
    total_discount_cart_v2: 'Coupon Discount',
    offerCashReward: 'Extra discount for you',
    trade_discount: 'Offer Discount',
    discount: 'Coupon Savings',
    swiggy_cash: 'Swiggy Money / Free Cash',
    taxes_and_charges: 'GST & other charges',
    positive_delivery_charges_exclusive_swiggy_one: 'Delivery Fee',
};

const scEl = id => document.getElementById(id);
const scMoney = v => '₹' + (Math.round((Number(v) || 0) * 100) / 100).toLocaleString('en-IN', { maximumFractionDigits: 2 });

/* ── tab entry ─────────────────────────────────────── */

function renderCartView() {
    const has = !!state.activeSession;
    scEl('cartNoAccountBanner').style.display = has ? 'none' : 'flex';
    scEl('cartContent').style.display = has ? 'block' : 'none';
    if (!has) return;
    if (sr.cart.mobile && sr.cart.mobile !== String(state.activeMobile)) srResetCart();
    scSyncIncogBtn();
    scRenderAddr();
    scRender();
    // reprice on open so coupon / bill / payment are fresh
    if (sr.cart.lines.length && srCartPoint() && !sr.cart.syncing) srSyncCart();
}

function scRenderAddr() {
    const t = scEl('scAddrTitle'), sub = scEl('scAddrSub');
    if (!t) return;
    const card = t.closest('.sc-addr-card');
    card.classList.toggle('pending', !!sc.addrPending);
    if (sc.addrPending) {
        t.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> ' + srEsc(sc.addrPending);
        sub.textContent = 'Please wait…';
        return;
    }
    if (!sr.addr || !sr.addr.addressId) {
        t.textContent = 'Select Delivery Address';
        sub.textContent = sr.loc ? `Prices for ${sr.loc.title}. Pick a saved address to order` : 'Tap to choose a saved address';
        card.classList.remove('set');
        return;
    }
    t.textContent = `Delivering to ${sr.addr.title}`;
    sub.textContent = sr.addr.sub || '';
    card.classList.add('set');
}

/* ── delivery address sheet: saved addresses only ── */

// same card as the Address tab (renderSingleAddressCard), with a check instead of delete
function scAddrRowHtml(a, i) {
    const tag = String(a.annotation || a.address_type || a.label || 'Home');
    const name = formatTitleCase(a.receiver_name || a.name || (state.activeSession ? state.activeSession.name : '') || 'Receiver');
    const phone = a.receiver_mobile || a.phone || a.mobile || state.activeMobile || '';
    const text = a.display || a.address || a.formatted_address || `${a.house || ''} ${a.area || ''}`.trim() || 'Saved Address';
    const on = sr.addr && ((!a.is_global && String(sr.addr.addressId) === String(a.id)) || (a.is_global && sr.addr.savedId === a.id));
    return `<div class="addr-card sc-ad-card ${on ? 'active' : ''}" onclick="scPickAddr(${i})">
        <div class="addr-card-content">
            <div class="addr-card-info">
                <span class="addr-label ${tag.toLowerCase() === 'home' ? 'home' : 'work'}">${srEsc(tag)}</span>${a.is_global ? '' : '<span class="addr-acc-tag">Account address</span>'}
                <div class="addr-name-row">${srEsc(name)} ${phone ? `| <span style="font-weight:normal; color:var(--text-muted);">+91 ${srEsc(phone)}</span>` : ''}</div>
                <div class="addr-details-row">${srEsc(text)}</div>
            </div>
            <span class="sc-po-radio"><i class="fa-solid fa-check"></i></span>
        </div>
    </div>`;
}

async function scOpenAddrSheet() {
    if (sc.addrPending) { showToast('Setting the delivery address, one moment…', false, 1400); return; }
    scEl('scAddrSheet').classList.remove('hidden');
    const list = scEl('scAddrList');
    list.innerHTML = srLoader('Loading your addresses');
    const d = await srJson(`/api/addresses/${state.activeMobile}?force=false`).catch(() => ({}));
    const all = (d.addresses || []).filter(a => a.lat && a.lng);
    // our saved (database) addresses first, then the ones already on the account
    sc.addrs = all.filter(a => a.is_global).concat(all.filter(a => !a.is_global));
    list.innerHTML = sc.addrs.length ? sc.addrs.map(scAddrRowHtml).join('')
        : `<div class="full-page-empty compact"><div class="fpe-title">No saved address</div><div class="fpe-sub">Add one from the Address tab first</div></div>`;
}

function scUseAddr(acc, savedId) {
    const text = acc.display || acc.formatted_address || acc.address || '';
    sr.addr = {
        lat: Number(acc.lat), lng: Number(acc.lng),
        title: String(acc.annotation || acc.address_type || acc.label || 'Home'),
        sub: text.length > 70 ? text.slice(0, 70) + '…' : text,
        addressId: String(acc.address_id || acc.id || ''),
        savedId: savedId || '',
        addr: acc,
    };
    localStorage.setItem(SR_ADDR_KEY, JSON.stringify(sr.addr));
}

async function scPickAddr(i) {
    const a = (sc.addrs || [])[i];
    if (!a || sc.addrPending) return;
    srCloseSheet(null, 'scAddrSheet');
    if (!a.is_global) {
        // already on the account: select it and check the cart there
        scUseAddr(a, '');
        showToast('Delivery address updated', false, 1400);
    } else {
        // a database address: reuse the account's copy if it has one, else add it, then select it
        sc.addrPending = 'Adding address to account';
        scRenderAddr(); scRenderSections();
        const d = await srJson('/api/cart/add_address_to_account', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mobile: state.activeMobile, address: a }),
        }).catch(() => ({ success: false, error: 'Network error' }));
        sc.addrPending = '';
        if (d.success && d.address && d.address.id) {
            scUseAddr({ ...a, ...d.address, lat: d.address.lat || a.lat, lng: d.address.lng || a.lng }, a.id);
            showToast(d.existing ? 'Delivery address updated' : 'Address added to account & selected', false, 1800);
        } else {
            showToast(d.error || 'Could not add this address to the account', true, 2400);
            scRenderAddr(); scRenderSections();
            return;
        }
    }
    scRenderAddr();
    sc.payKey = '';
    if (sr.cart.lines.length) srSyncCart();
}

/* ── group cart link -> items in this cart ─────────── */

async function scFetchGroupLink() {
    const input = scEl('scLinkInput'), btn = document.querySelector('.sc-link-btn-go');
    const v = (input.value || '').trim();
    if (!v) { showToast('Paste a group cart link first', true); return; }
    if (!srCartPoint()) { showToast('Select a location first', true); srOpenLocationSheet(); return; }
    if (btn.disabled) return;
    btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    const d = await srJson('/api/cart/import_group', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mobile: state.activeMobile, link: v, address_id: sr.addr?.addressId || '', lat: srCartPoint().lat, lng: srCartPoint().lng }),
    }).catch(() => ({ success: false, error: 'Network error' }));
    btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-arrow-right"></i>';
    if (!d.success) { showToast(d.error || 'Could not read that group cart', true); return; }

    const apply = replace => {
        if (replace) srResetCart();
        sr.cart.restaurant = d.restaurant;
        sr.cart.mobile = String(state.activeMobile);
        const ids = [];
        d.items.forEach(it => {
            const key = srLineKey(it.id, it.addons);
            const line = sr.cart.lines.find(l => l.key === key);
            if (line) line.quantity += it.quantity;
            else sr.cart.lines.push({ key, id: it.id, name: it.name, image_id: it.image_id, price: it.price, is_veg: it.is_veg, addons: it.addons, variants: it.variants || [], quantity: it.quantity });
            ids.push(it.id);
        });
        input.value = '';
        srCartChanged(ids);
        const n = d.items.reduce((t, i) => t + i.quantity, 0);
        showToast(`${n} item${n > 1 ? 's' : ''} added from ${d.restaurant.name}`, false, 1500);
        if (d.skipped && d.skipped.length) setTimeout(() => showToast(`Unavailable: ${d.skipped.join(', ')}`, true, 1500), 1700);
    };
    const other = sr.cart.restaurant && String(sr.cart.restaurant.id) !== String(d.restaurant.id) && sr.cart.lines.length;
    if (other) {
        customConfirm('Replace cart items?', `Your cart has items from ${sr.cart.restaurant.name}. Clear it and use ${d.restaurant.name}'s group cart?`, () => apply(true), 'Replace');
    } else {
        apply(false);
    }
}

/* ── hooks from search.js ──────────────────────────── */

function scCartKey() {
    return sr.cart.cartId + '|' + sr.cart.lines.map(l => l.key + 'x' + l.quantity).join(',');
}

function scOnCartReset() {
    sc.coupons = null; sc.pay = null; sc.autoKey = ''; sc.payKey = '';
    if (state.activeTab === 'cart') scRender();
}

function scOnCartPriced(d) {
    if (!d || !d.success || !sr.cart.cartId) { scRenderSections(); return; }
    const key = scCartKey();
    const coupon = d.coupon || {};
    // auto-apply the highest discount once per cart state, unless a valid coupon is already on
    if (!(coupon.code && coupon.valid) && sc.autoKey !== key) {
        sc.autoKey = key;
        scApplyBest(true);
    } else {
        sc.autoKey = key;
        scLoadPayments();
    }
    scRenderSections();
}

/* ── API calls ─────────────────────────────────────── */

function scBody(extra = {}) {
    return JSON.stringify({
        mobile: state.activeMobile, cart_id: sr.cart.cartId, address_id: sr.addr?.addressId || '',
        lat: srCartPoint()?.lat, lng: srCartPoint()?.lng, restaurant_id: sr.cart.restaurant?.id || '',
        cart_value: sr.cart.cartValue || sr.cart.bill?.item_total || 0, ...extra,
    });
}

const scPost = (url, extra) => srJson(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: scBody(extra) })
    .catch(() => ({ success: false, error: 'Network error' }));

function scTakeCart(d) {
    sr.cart.bill = d.bill; sr.cart.billLines = d.bill_lines || []; sr.cart.coupon = d.coupon; sr.cart.cartValue = d.cart_value;
    if (d.swiggy_one) sr.cart.one = d.swiggy_one;
    srSaveCart(); srUpdateCartBar();
}

async function scApplyBest(silent) {
    if (!sr.cart.cartId || sc.couponBusy) return;
    sc.couponBusy = true; scRenderSections();
    const d = await scPost('/api/checkout/best_coupon');
    sc.couponBusy = false;
    if (d.coupons) sc.coupons = d.coupons;
    if (d.success) {
        const fresh = d.coupon.code !== (sr.cart.coupon && sr.cart.coupon.valid ? sr.cart.coupon.code : '');
        scTakeCart(d);
        if (fresh && d.coupon.discount > 0) showToast(`${d.coupon.code} applied · ${scMoney(d.coupon.discount)} off`, 'fa-ticket', 1800);
    } else if (!silent) showToast(d.error || 'No coupon applies to this cart', true);
    scRenderSections();
    scLoadPayments();
}

async function scApply(code) {
    if (!sr.cart.cartId || sc.couponBusy) return;
    sc.couponBusy = true; sc.applyingCode = code; scRenderSections(); scRenderCoupons();
    const d = await scPost('/api/checkout/apply_coupon', { code });
    sc.couponBusy = false; sc.applyingCode = '';
    if (d.success) {
        scTakeCart(d);
        srCloseSheet(null, 'scCouponSheet');
        scEl('scCouponCode').value = '';
        showToast(`${d.coupon.code || code} applied · ${scMoney(d.coupon.discount)} off`, 'fa-ticket', 1800);
        scLoadPayments();
    } else showToast(d.error || `${code} could not be applied`, true, 2200);
    scRenderSections(); scRenderCoupons();
}

async function scOpenCoupons() {
    scEl('scCouponSheet').classList.remove('hidden');
    if (!sc.coupons) {
        scEl('scCouponList').innerHTML = srLoader('Loading coupons');
        const d = await scPost('/api/checkout/coupons');
        sc.coupons = d.coupons || [];
    }
    scRenderCoupons();
}

async function scLoadPayments() {
    if (!sr.cart.cartId) return;
    const key = scCartKey() + '|' + (sr.cart.coupon?.code || '');
    if (sc.payKey === key && sc.pay) return;
    sc.payKey = key;
    sc.pay = { loading: true };
    scRenderSections();
    const d = await scPost('/api/checkout/payment_options');
    if (sc.payKey !== key) return;
    sc.pay = d.success ? d : { error: d.error || 'Could not load payment options' };
    if (sc.pay.upi && !sc.pay.upi.enabled && sc.pay.cod?.enabled) sc.method = 'cod';
    if (sc.pay.cod && !sc.pay.cod.enabled && sc.method === 'cod') sc.method = 'upi';
    scRenderSections();
}

// A coupon made for card payments (its allowed methods are only cards, or "using ... card") locks UPI and cash.
function scCouponCardOnly() {
    const code = sr.cart.coupon && sr.cart.coupon.valid ? sr.cart.coupon.code : '';
    const c = code && (sc.coupons || []).find(x => x.code === code);
    if (!c) return '';
    const pm = String(c.payment || '').split(',').map(x => x.trim()).filter(Boolean);
    const text = `${c.subtitle || ''} ${c.description || ''}`;
    const only = pm.length > 0 && pm.every(x => /card/i.test(x) && !/upi|cod|cash|wallet|netbank/i.test(x));
    const using = /(using|on|with)[^.]{0,40}(credit|debit)?\s*cards?/i.test(text) && !/upi|cod|cash/i.test(text);
    return only || using ? code : '';
}

// the payment option as the buyer can use it now (a card-only coupon blocks UPI and cash)
function scPayOpt(key) {
    let raw = sc.pay && sc.pay[key];
    if (raw === undefined || raw === null) return { enabled: false, message: 'Not available' };
    let m;
    if (typeof raw === 'boolean') {
        m = { enabled: raw, message: raw ? '' : 'Not available' };
    } else if (typeof raw === 'object') {
        m = { ...raw, enabled: raw.enabled !== undefined ? !!raw.enabled : true, message: raw.message || (raw.enabled ? '' : 'Not available') };
    } else {
        m = { enabled: !!raw, message: '' };
    }
    const code = scCouponCardOnly();
    if (code && key !== 'card') return { ...m, enabled: false, coupon_locked: true, message: `Coupon ${code} works only with card payment` };
    return m;
}

// keep the chosen method usable: after a card coupon, pay by card
function scFixMethod() {
    if (!sc.pay || sc.pay.loading || sc.pay.error) return;
    const ok = k => (scPayOpt(k) || {}).enabled;
    if (ok(sc.method)) return;
    const next = ['card', 'upi', 'cod'].find(ok);
    if (next) sc.method = next;
}

function scPick(method) {
    const m = scPayOpt(method);
    if (m && !m.enabled) { showToast(m.message, true, 2200); return; }
    sc.method = method;
    scRenderSections();
}

/* ── placing the order: payment page + order placed page ── */

const SC_STATUS_STEPS = ['Placed', 'Confirmed', 'Preparing', 'On the way', 'Delivered'];

function scPay() {
    const b = sr.cart.bill;
    if (!b || sc.placing) return;
    if (!sr.addr || !sr.addr.addressId) { showToast('Select a saved delivery address to order', true); scOpenAddrSheet(); return; }
    scFixMethod();
    const m = scPayOpt(sc.method);
    if (m && !m.enabled) { showToast(m.message, true); return; }
    scPlace();
}

// a later "already finalized" answer must not wipe what the first one told us
function scMerge(d) {
    const f = d && d.finalized;
    const keep = sc.order.finalized;
    Object.assign(sc.order, d);
    if (keep && (!f || f.already)) sc.order.finalized = { ...keep, ...(f || {}), address_deleted: keep.address_deleted || (f && f.address_deleted), address_deleting: keep.address_deleting || (f && f.address_deleting) };
}

async function scCall(path, extra = {}) {
    return srJson(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: scBody(extra) })
        .catch(() => ({ success: false, error: 'Network error' }));
}

// what the payment / success pages show, kept after the cart is cleared
function scSnapshot() {
    const c = sr.cart;
    return {
        restaurant: c.restaurant?.name || '',
        loc: sr.addr ? { title: sr.addr.title, sub: sr.addr.sub, addr: sr.addr.addr || null } : null,
        itemsHtml: c.lines.map(l => `
            <div class="sc-line sp-line">
                <div class="sc-line-info"><div class="sc-line-name">${srEsc(l.name)}</div>
                ${srLineExtras(l).length ? `<div class="sc-line-addons">${srEsc(srLineExtras(l).join(', '))}</div>` : ''}</div>
                <span class="sp-qty">× ${l.quantity}</span>
                <div class="sc-line-price">${srRs(srLinePrice(l) * l.quantity)}</div>
            </div>`).join(''),
        billHtml: scFullBillHtml(),
        name: state.activeSession?.name || '',
        phone: state.activeMobile,
        server: scServerSnap(),
    };
}

function scServerSnap() {
    const c = sr.cart, a = sr.addr?.addr || {};
    const cap = t => String(t || '').replace(/\b\w/g, ch => ch.toUpperCase());
    const short = [a.house, a.area, a.locality, a.city].filter(Boolean).filter((v, i, arr) => arr.indexOf(v) === i).join(', ');
    return {
        restaurant: c.restaurant?.name || '',
        account_name: state.activeSession?.name || '',
        items: c.lines.map(l => ({ name: l.name, quantity: l.quantity, price: srLinePrice(l) * l.quantity, veg: !!l.is_veg, variants: (l.variants || []).map(v => v.name), addons: l.addons.map(x => ({ name: x.name, price: Number(x.price || 0) })) })),
        bill_lines: (c.billLines || []).map(l => ({ label: SC_BILL_LABELS[l.key] || l.label, value: l.value, negative: !!l.negative, total: !!l.total })),
        coupon: c.coupon && c.coupon.valid ? c.coupon.code : '',
        address: {
            text: cap(short || a.display || a.formatted_address || sr.addr?.sub || ''),
            name: cap(a.receiver_name || a.name || state.activeSession?.name || ''),
            phone: a.receiver_mobile || a.phone || a.mobile || state.activeMobile || '',
        },
    };
}

function scFullBillHtml() { return scBillHtml(); }

// blinkit_bot layout: "Deliver To" (short address) then "Receiver Contact" under a dashed line
function scAddrCardHtml(snap) {
    const l = snap.loc;
    if (!l) return '<div class="sp-muted">No address</div>';
    const a = l.addr || {};
    const cap = t => String(t || '').replace(/\b\w/g, ch => ch.toUpperCase());
    const name = cap(a.receiver_name || a.name || snap.name || 'Receiver');
    const phone = a.receiver_mobile || a.phone || a.mobile || snap.phone || '';
    const short = [a.house, a.area, a.locality, a.city].filter(Boolean).filter((v, i, arr) => arr.indexOf(v) === i).join(', ');
    const text = short || a.display || a.formatted_address || a.address || l.sub || '';
    const pin = a.postal_code ? ` - ${a.postal_code}` : '';
    return `<div class="sp-addr">
        <div class="sp-addr-row"><span>Deliver To:</span><div>${srEsc(cap(text))}${srEsc(pin)}</div></div>
        <div class="sp-addr-row sp-addr-recv"><span>Receiver Contact:</span><div>${srEsc(name)}${phone ? ` | ${srEsc(phone)}` : ''}</div></div>
    </div>`;
}

async function scPlace() {
    const b = sr.cart.bill;
    if (!b || sc.placing) return;
    if (sc.method === 'card') { const ce = scCardError(); if (ce) { showToast(ce, true, 2500); return; } }
    sc.placing = true; sc.pollStop = false;
    sc.order = { amount: b.to_pay, method: sc.method, restaurant: sr.cart.restaurant?.name || '', snap: scSnapshot() };
    scRenderPayBar();
    showToast('Processing your order…', false, 1500);
    const d = await scCall('/api/checkout/place', { amount: b.to_pay, method: sc.method, snap: sc.order.snap.server,
        ...(sc.method === 'card' ? { card: { ...SC_CARD } } : {}) });
    if (sc.method === 'card') { SC_CARD.number = SC_CARD.cvv = SC_CARD.expiry = ''; }
    if (!d.success) {
        sc.placing = false; scRenderPayBar();
        if (d.unconfirmed) {
            // the cash order exists at Swiggy but was not confirmed: don't let them place it twice blindly
            customConfirm('Order not confirmed yet', d.error, () => switchTab('orders'), 'Open Orders', null, 'Close');
            return;
        }
        showToast(d.error || 'Could not place the order', true, 3500);
        return;
    }
    scMerge(d);
    if (d.method === 'cod') { scOrderPlaced(); return; }
    scShowPaymentPage();
    if (d.method === 'card') scOpenBank();
    showToast(`Order #${d.order_id} created. Complete the payment`, false, 2500);
}

/* payment page (UPI) */

function scShowPaymentPage() {
    const o = sc.order, snap = o.snap;
    const card = o.method === 'card';
    const url = o.upi_url || o.upi_uri || o.pay_url || '';
    const qr = o.qr || (url ? `https://api.qrserver.com/v1/create-qr-code/?size=300x300&margin=0&data=${encodeURIComponent(url)}` : '');
    scEl('scPayPage').innerHTML = `
        <button type="button" class="sp-back" onclick="scLeavePayment()"><i class="fa-solid fa-arrow-left"></i> Back to Cart</button>
        ${card ? `<div class="card sp-qr-card">
            <div class="sp-title">Complete the card payment</div>
            <div class="sp-sub">Enter the OTP on your bank's page, then come back here</div>
            <div class="sp-amount">${scMoney(o.amount)}</div>
            <div class="sp-btns">
                <a href="#" onclick="scOpenBank(event)" class="sp-pay-btn"><i class="fa-solid fa-building-columns"></i> Open Bank Page</a>
                <button type="button" id="scCheckBtn" class="sp-check-btn" onclick="scCheckPaymentNow()"><i class="fa-solid fa-rotate"></i> Check Payment</button>
            </div>
            <div class="sp-wait" id="scPayState" style="display:none"></div>
        </div>` : `<div class="card sp-qr-card">
            <div class="sp-title">Scan to Pay with UPI</div>
            <div class="sp-sub">Pay with GPay, PhonePe, Paytm or any UPI App</div>
            <div class="sp-qr">${qr ? `<img src="${qr}" alt="UPI QR Code">` : '<i class="fa-solid fa-qrcode"></i>'}</div>
            <div class="sp-amount">${scMoney(o.amount)}</div>
            <div class="sp-btns">
                <a href="#" onclick="scOpenUpiApp(event)" class="sp-pay-btn"><i class="fa-solid fa-bolt"></i> Pay via UPI App</a>
                <button type="button" id="scCheckBtn" class="sp-check-btn" onclick="scCheckPaymentNow()"><i class="fa-solid fa-rotate"></i> Check Payment</button>
            </div>
            <div class="sp-wait" id="scPayState" style="display:none"></div>
        </div>`}
        <div class="card sp-card"><div class="sp-card-title"><i class="fa-solid fa-location-dot"></i> Selected Delivery Address</div>${scAddrCardHtml(snap)}</div>
        <div class="card sp-card"><div class="sp-card-title"><i class="fa-solid fa-basket-shopping"></i> Order Items Summary</div>${snap.itemsHtml}</div>
        <div class="card sp-card"><div class="sp-card-title"><i class="fa-solid fa-file-invoice-dollar"></i> Bill Details Breakdown</div>${snap.billHtml}</div>`;
    switchTab('payment');
    scPollPayment();
}

// the bank's 3-D Secure page needs a real browser tab (Telegram's in-app view can't hold the OTP flow)
function scOpenBank(e) {
    if (e) e.preventDefault();
    const u = sc.order && sc.order.auth_url;
    if (!u) { showToast('No bank page available', true); return; }
    const tg = window.Telegram && window.Telegram.WebApp;
    if (tg && tg.initData && tg.openLink) tg.openLink(u);
    else window.open(u, '_blank');
}

function scLeavePayment() {
    sc.pollStop = true; sc.placing = false;
    switchTab('cart');
}

// open the UPI app (same as blinkit_bot). Telegram's in-app browser can't open upi:// or intent://
// (ERR_UNKNOWN_URL_SCHEME), so inside Telegram open our /api/pay/upi page in the phone's real browser
// (openLink only takes https) and that page hands the payment to GPay / PhonePe / Paytm.
// sc.order.upi_pkg = the app the order was placed for (BHIM for a BHIM coupon); empty = let the phone choose
function scUpiPayPage(u) {
    const pkg = sc.order && sc.order.upi_pkg;
    return window.location.origin + location.pathname.replace(/\/[^/]*$/, '') + '/api/pay/upi?u=' + encodeURIComponent(u)
        + (pkg ? '&pkg=' + encodeURIComponent(pkg) : '');
}

function scOpenUpiApp(e) {
    if (e) e.preventDefault();
    const u = sc.order && (sc.order.upi_url || sc.order.upi_uri || sc.order.pay_url);
    if (!u || !u.startsWith('upi://')) { showToast('No UPI link available yet', true); return; }
    const tg = window.Telegram && window.Telegram.WebApp;
    if (tg && tg.initData && tg.openLink) {
        tg.openLink(scUpiPayPage(u));
        showToast(sc.order.upi_pkg ? 'Opening your browser, it will open BHIM' : 'Opening your browser, pick your UPI app there', false, 1500);
        return;
    }
    if (/Android/i.test(navigator.userAgent)) {
        const pkg = sc.order.upi_pkg;
        window.location.href = 'intent://' + u.slice('upi://'.length) + '#Intent;scheme=upi;' + (pkg ? 'package=' + pkg + ';' : '')
            + 'S.browser_fallback_url=' + encodeURIComponent(scUpiPayPage(u)) + ';end';
    } else {
        window.location.href = u;
        showToast('On a computer? Scan the QR code with your phone', false, 3000);
    }
}

function scPayState(html, bad) {
    const el = scEl('scPayState');
    if (!el) return;
    el.innerHTML = html || '';
    el.style.display = html ? 'flex' : 'none';
    el.classList.toggle('bad', !!bad);
}

// the line goes back to "Awaiting payment confirmation..." while we keep polling


async function scPollPayment() {
    const o = sc.order, id = o.order_id;
    const gap = Math.max(1000, o.poll_ms || 1000);
    const until = Date.now() + Math.max(o.confirm_ms || 45000, 45000) * 3;   // a few minutes to pay
    while (!sc.pollStop && sc.order.order_id === id && Date.now() < until) {
        await new Promise(r => setTimeout(r, gap));
        if (sc.pollStop || sc.order.order_id !== id) return;
        const d = await scCall('/api/checkout/payment_status', { txn_id: o.txn_id, method: o.method });
        scMerge(d);
        if (d.paid) { scConfirmOrder(false); return; }
        if (d.failed) { scPayFailed('Payment failed. Any amount deducted is refunded by Swiggy.'); return; }
    }
    if (!sc.pollStop && sc.order.order_id === id) scConfirmOrder(true);
}

async function scCheckPaymentNow() {
    const btn = scEl('scCheckBtn');
    if (btn) { if (btn.disabled) return; btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-rotate fa-spin"></i> Checking...'; }
    const reset = () => { if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-rotate"></i> Check Payment'; } };
    const d = await scCall('/api/checkout/payment_status', { txn_id: sc.order.txn_id, order_id: sc.order.order_id, manual: true, method: sc.order.method });
    reset();
    if (d.is_expired) { showToast(d.error || 'Session expired. Please login again.', true, 3500); return; }
    if (!d.success) {
        const m = d.error || 'Could not check the payment';
        showToast(m, true, 3000);
        return;
    }
    scMerge(d);
    if (d.paid) { showToast('Payment received', false, 2000); scConfirmOrder(false); return; }
    if (d.failed) { scPayFailed('Payment failed. Any amount deducted is refunded by Swiggy.'); return; }
    showToast('⏳ Payment pending. Please complete the payment.', true, 1500);
}

async function scConfirmOrder(lastTry) {
    sc.pollStop = true;
    scPayState('<span class="sp-ring"></span> Payment received, confirming your order...');
    const d = await scCall('/api/checkout/confirm', { order_id: sc.order.order_id });
    if (d.success && d.confirmed) { scMerge(d); scOrderPlaced(); return; }
    scPayFailed(lastTry ? 'Payment not received. If money was deducted, Swiggy refunds it within 4 days.'
        : (d.detail || d.error || 'Order not confirmed'));
}

function scPayFailed(msg) {
    sc.placing = false; sc.pollStop = true;
    showToast(msg, true, 3500);
    scPayState(`<i class="fa-solid fa-circle-xmark"></i> ${srEsc(msg)} <button type="button" class="sp-retry" onclick="scLeavePayment()">Try again</button>`, true);
}

/* order placed page */

function scOrderPlaced() {
    sc.placing = false; sc.pollStop = false;
    const o = sc.order, snap = o.snap;
    const s = state.sessions.find(x => String(x.mobile) === String(state.activeMobile));
    if (s) { s.is_done = true; if (window.renderAccountsList) renderAccountsList(); }
    const fin = o.finalized || {};
    o.track = fin.tracking_link || fin.tracking_url || o.tracking_url || (o.order_id ? (String(o.order_id).startsWith('http') ? o.order_id : 'https://jhantu.alwaysdata.net/swiggy/store.html?track=' + o.order_id) : '');
    scAfterOrderAddress(fin);
    srResetCart();
    scEl('scDonePage').innerHTML = `
        <div id="scConfetti" class="sp-confetti"></div>
        <div class="sp-hero">
            <div class="sp-check"><i class="fa-solid fa-check"></i><span></span></div>
            <h2>Order Placed!</h2>
            <div class="odp-rest"><i class="fa-solid fa-store"></i>${srEsc(o.restaurant)}</div>
            <p>${o.eta_min ? `Arriving in about ${srEsc(o.eta_min)} minutes 🛵` : 'Your food is on its way soon 🛵'}</p>
        </div>
        <div class="card sp-card"><div class="sp-card-title"><i class="fa-solid fa-file-invoice"></i> Order Information</div>
            <div class="sp-row"><span>Order ID</span><b><span class="sp-id">#${srEsc(o.order_id)}</span><button type="button" class="odk-copy" onclick="scCopy('${srEsc(o.order_id)}', 'Order ID copied')" title="Copy"><i class="fa-regular fa-copy"></i></button></b></div>
            <div class="sp-row"><span>Paid Via</span><b><span class="odk-pay">${o.method === 'cod' ? 'Cash on Delivery' : o.method === 'card' ? 'Card' : 'UPI'}</span></b></div>
            <div class="sp-row"><span>Placed On</span><b>${srEsc(window.odTime ? odTime(Date.now()) : new Date().toLocaleString('en-IN'))}</b></div>
            <div class="sp-row"><span>Tracking</span><b><span class="od-trk"><button type="button" class="sp-track" id="scTrackLink" onclick="scOpenTrack()"><i class="fa-solid fa-location-crosshairs"></i> Track order</button>
                <button type="button" class="odk-copy" onclick="scCopy(sc.order.track, 'Tracking link copied')" title="Copy link"><i class="fa-regular fa-copy"></i></button></span></b></div>
            <div class="sp-row" id="scDeRow"><span>Delivery Partner</span><b id="scDeName"><span class="od-muted">Not assigned yet</span></b></div>
            <div class="sp-row sp-dash"><span>Live status</span><b id="scLiveStatus">Placed</b></div>
        </div>
        <div class="card sp-card"><div class="sp-card-title"><i class="fa-solid fa-location-dot"></i> Delivery Address</div>${scAddrCardHtml(snap)}</div>
        <div class="card sp-card"><div class="sp-card-title"><i class="fa-solid fa-basket-shopping"></i> Ordered Items Summary</div>${snap.itemsHtml}</div>
        <div class="card sp-card"><div class="sp-card-title"><i class="fa-solid fa-receipt"></i> Payment &amp; Bill Summary</div>${snap.billHtml}</div>
        <button type="button" class="sp-btn primary sp-full" onclick="scCloseDone()"><i class="fa-solid fa-house"></i> Back to Home</button>`;
    scRenderSteps(0);
    switchTab('success');
    scConfetti();
    scTrackStatus();
}

// the address this order used is deleted from the Swiggy account: tell the user and stop using it
function scAfterOrderAddress(fin) {
    // the server deletes it from the Swiggy account in the background
    if (!fin.address_deleted && !fin.address_deleting) return;
    showToast('Address removed from account', false, 1500);
    if (sr.addr) {
        sr.addr = null;
        localStorage.removeItem(SR_ADDR_KEY);
        if (window.scRenderAddr) scRenderAddr();
    }
    sc.addrs = null;
}

// tracking link in the real browser (Telegram mini app too), copy helpers
function scOpenTrack() {
    if (sc.order && sc.order.order_id) {
        if (window.openOrderDetail) {
            openOrderDetail(sc.order.order_id);
            return;
        }
        if (window.switchTab) {
            window.switchTab('orders');
            return;
        }
    }
    if (!sc.order || !sc.order.track) return;
    if (window.odOpenLink) odOpenLink(sc.order.track); else window.open(sc.order.track, '_blank', 'noopener');
}

function scCopy(text, msg) {
    if (!text) return;
    (navigator.clipboard ? navigator.clipboard.writeText(String(text)) : Promise.reject()).then(() => showToast(msg, 'fa-circle-check')).catch(() => showToast(String(text), 'fa-copy'));
}

function scCloseDone() {
    sc.pollStop = true;
    switchTab('home');
}

function scConfetti() {
    const box = scEl('scConfetti');
    if (!box) return;
    const colors = ['#fc8019', '#10b981', '#00A3FF', '#f2d74e', '#e879f9', '#ff6b6b'];
    for (let i = 0; i < 44; i++) {
        const c = document.createElement('i');
        const sz = 5 + Math.random() * 6;
        c.style.cssText = `left:${Math.random() * 100}%;width:${sz}px;height:${sz}px;background:${colors[i % colors.length]};` +
            `border-radius:${Math.random() > .5 ? '50%' : '2px'};animation-duration:${2.2 + Math.random() * 2.2}s;animation-delay:${Math.random() * .8}s`;
        box.appendChild(c);
    }
    setTimeout(() => { box.innerHTML = ''; }, 6000);
}

function scStepIndex(status) {
    const t = String(status || '').toLowerCase();
    if (/deliver/.test(t) && !/out|way|will/.test(t)) return 4;
    if (/arrived|reached|out for|on the way|picked|pick|dispatch/.test(t)) return 3;
    if (/prepar|assign|restaurant|ready/.test(t)) return 2;
    if (/confirm|accept|process/.test(t)) return 1;
    return 0;
}

function scRenderSteps(idx) {
    const el = scEl('scSteps');
    if (el) el.innerHTML = SC_STATUS_STEPS.map((t, i) => `<div class="sc-ord-step ${i <= idx ? 'done' : ''}"><span></span><em>${t}</em></div>`).join('');
}

async function scTrackStatus() {
    const id = sc.order.order_id;
    for (let i = 0; i < 80 && !sc.pollStop && sc.order && sc.order.order_id === id; i++) {
        await new Promise(r => setTimeout(r, i < 3 ? 4000 : 15000));   // first answers come quickly, then every 15s
        if (sc.pollStop || !sc.order || sc.order.order_id !== id) return;
        const d = await scCall('/api/checkout/order_status', { order_id: id });
        if (!d.success) continue;
        if (d.status) {
            const lbl = scEl('scLiveStatus');
            if (lbl) lbl.textContent = d.status + (d.eta && !d.final ? ' · ' + d.eta : '');
            scRenderSteps(d.final && /deliver/i.test(d.status) ? 4 : scStepIndex(d.status));
        }
        if (d.tracking_link) sc.order.track = d.tracking_link;
        const de = scEl('scDeName');
        if (de && (d.de_name || d.de_phone)) {
            const cap = t => String(t || '').toLowerCase().replace(/\b\w/g, ch => ch.toUpperCase());
            de.textContent = [cap(d.de_name || 'Delivery partner'), d.de_phone].filter(Boolean).join(' | ');
        }
        if (d.final) return;
    }
}

/* ── rendering ─────────────────────────────────────── */

// busy = a change is waiting to sync, the cart is syncing, or a coupon is being applied
function scBusy() { return !!(sr.cart.dirty || sr.cart.syncing || sc.couponBusy || sc.addrPending); }

function scRefresh() {
    if (scBusy()) { showToast('Cart is syncing, please wait…', false, 1400); return; }
    if (!sr.cart.lines.length) return;
    sc.payKey = '';
    srSyncCart();
}

function scRender() {
    const box = scEl('scCart');
    if (!box || state.activeTab !== 'cart') return;
    const c = sr.cart;
    if (!c.lines || !c.lines.length) {
        box.dataset.mode = 'empty';
        box.innerHTML = `
            <div class="full-page-empty compact">
                <div class="fpe-ring">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
                </div>
                <div class="fpe-title">Your cart is empty</div>
                <div class="fpe-sub">Search a restaurant and add dishes to see them here</div>
            </div>`;
        scRenderPayBar();
        return;
    }
    // build the sections once; afterwards each one updates in place (no full-page redraw)
    if (box.dataset.mode !== 'cart') {
        box.dataset.mode = 'cart';
        box.innerHTML = `
            <div class="sc-head">Your Order<span id="scOrderHead"></span></div>
            <div class="card sc-order">
                <div id="scOrderBody"></div>
            </div>
            <div id="scErrorBox"></div>
            <div id="scCouponBox"></div>
            <div id="scOneBox"></div>
            <div class="card sc-bill" id="scBillCard">
                <div class="sc-sec-head">
                    <span class="sc-card-title"><i class="fa-solid fa-receipt"></i> Bill Details</span>
                    <button type="button" id="scBillRefresh" class="sc-refresh icon" onclick="scRefresh()" title="Refresh bill"><i class="fa-solid fa-arrows-rotate"></i></button>
                </div>
                <div id="scBillBody"></div>
            </div>
            <div class="card sc-pay" id="scPayCard">
                <div class="sc-card-title"><i class="fa-solid fa-wallet"></i> Payment Method</div>
                <div id="scPayBody"></div>
            </div>
            <div style="height:70px"></div>`;
    }
    scRenderOrder();
    scRenderSections();
}

function scRenderOrder() {
    const body = scEl('scOrderBody');
    if (!body) return;
    const c = sr.cart, r = c.restaurant || {};
    const count = c.lines.reduce((n, l) => n + l.quantity, 0);
    const total = c.lines.reduce((n, l) => n + srLinePrice(l) * l.quantity, 0);
    scEl('scOrderHead').textContent = `${count} item${count > 1 ? 's' : ''} · ${srRs(total)}`;
    body.innerHTML = `
        <div class="sc-rest">
            <span class="sc-rest-img">${r.image ? `<img src="${srEsc(r.image)}" alt="" onerror="this.remove()">` : ''}<i class="fa-solid fa-store"></i></span>
            <span class="sc-rest-text"><b>${srEsc(r.name || '')}</b><small>${srEsc([r.area, r.sla && r.sla.toLowerCase()].filter(Boolean).join(' · '))}</small></span>
            <button type="button" class="sc-icon-btn" onclick="srClearCart()" title="Clear cart"><i class="fa-solid fa-trash-can"></i></button>
        </div>
        ${c.lines.map((l, i) => `
        <div class="sc-line ${(sr.cart.oos || []).includes(String(l.id)) ? 'oos' : ''}">
            <span class="sr-diet ${l.is_veg ? 'veg' : 'nonveg'}"><i></i></span>
            <div class="sc-line-info">
                <div class="sc-line-name">${srEsc(l.name)}${(sr.cart.oos || []).includes(String(l.id)) ? '<span class="sc-oos">Out of stock</span>' : ''}</div>
                ${srLineExtras(l).length ? `<div class="sc-line-addons">${srEsc(srLineExtras(l).join(', '))}</div>` : ''}
            </div>
            <div class="sc-qty">
                <button type="button" onclick="srCartStep(${i},-1)"><i class="fa-solid ${l.quantity === 1 ? 'fa-trash-can' : 'fa-minus'}"></i></button>
                <span>${l.quantity}</span>
                <button type="button" onclick="srCartStep(${i},1)"><i class="fa-solid fa-plus"></i></button>
            </div>
            <div class="sc-line-price">${srRs(srLinePrice(l) * l.quantity)}</div>
        </div>`).join('')}
        <button type="button" class="sc-add-more" onclick="switchTab('search')"><i class="fa-solid fa-plus"></i> Add more items</button>`;
}

// everything below the item list: error, coupon, bill, payment, locks, pay bar
function scRenderSections() {
    if (state.activeTab !== 'cart' || !scEl('scBillBody')) return;
    const c = sr.cart, busy = scBusy();
    scEl('scErrorBox').innerHTML = c.error && !busy
        ? `<div class="sc-error"><i class="fa-solid fa-circle-exclamation"></i><span>${srEsc(c.error)}<small>Remove that item or re-add it from the menu, then try again.</small></span>
            <button type="button" onclick="scRefresh()">Retry</button></div>` : '';
    scEl('scCouponBox').innerHTML = scCouponCardHtml();
    scEl('scOneBox').innerHTML = scOneCardHtml() + scCashCardHtml();
    scEl('scBillBody').innerHTML = scBillHtml();
    // like blinkit_bot: payment choices only once the cart is settled
    const oos = (c.oos || []).length;
    if (oos && !busy && !c.error) {
        scEl('scErrorBox').innerHTML = `<div class="sc-error"><i class="fa-solid fa-box-open"></i><span>${oos} item${oos > 1 ? 's are' : ' is'} out of stock<small>Remove ${oos > 1 ? 'them' : 'it'} to continue with this order.</small></span></div>`;
    }
    // the bill stays readable; the payment card is what gets blocked until the new price is confirmed
    const lock = busy || !!(sc.pay && sc.pay.loading);
    const showPay = c.cartId && !c.error && c.bill;
    scEl('scPayCard').style.display = showPay ? '' : 'none';
    if (showPay && !sc.pay && !busy) setTimeout(scLoadPayments, 0);   // restored cart / reset state: fetch the options now
    if (showPay) {
        const ready = sc.pay && !sc.pay.loading;
        const inner = ready ? scPaymentHtml() : srLoader('Checking payment options');
        scEl('scPayBody').innerHTML = lock && ready
            ? `<div class="sc-updating"><div class="sc-updating-body">${inner}</div><span class="sc-updating-chip"><span class="ring sm"></span>Updating bill</span></div>`
            : inner;
    }
    ['scCartRefresh', 'scBillRefresh'].forEach(id => {
        const btn = scEl(id);
        if (!btn) return;
        btn.disabled = lock;
        btn.classList.toggle('locked', lock);
        btn.querySelector('i').classList.toggle('fa-spin', lock);
    });
    scRenderPayBar();
}

function scCouponCardHtml() {
    const cp = sr.cart.coupon || {};
    if (sc.couponBusy) {
        return `<div class="card sc-coupon busy"><span class="sc-coupon-ico"><i class="fa-solid fa-ticket"></i></span>
            <span class="sc-row-text"><b>Finding the best coupon</b><em>${srLoader('Checking offers for this cart')}</em></span></div>`;
    }
    if (cp.code && cp.valid) {
        return `<div class="card sc-coupon applied">
            <span class="sc-coupon-ico"><i class="fa-solid fa-champagne-glasses"></i></span>
            <span class="sc-cp-line">Coupon <b>'${srEsc(cp.code)}'</b> applied <em>${scMoney(cp.discount)} off</em></span>
            <button type="button" class="sc-link-btn" onclick="scOpenCoupons()">Change</button>
        </div>`;
    }
    return `<div class="card sc-coupon" onclick="${sr.cart.cartId && !sr.cart.error ? 'scOpenCoupons()' : ''}">
        <span class="sc-coupon-ico"><i class="fa-solid fa-ticket"></i></span>
        <span class="sc-row-text"><b>Apply coupon</b><em>${sr.cart.cartId && !sr.cart.error ? 'See offers for this restaurant' : sr.cart.error ? 'Available once the cart is priced' : 'Pricing your cart…'}</em></span>
        <i class="fa-solid fa-chevron-right sc-row-go"></i>
    </div>`;
}

/* ── Swiggy One (swiggy_one.har): plan sent as a subscription item on the cart ── */

function scOneCardHtml() {
    const o = sr.cart.one;
    if (!o || !o.available || !sr.cart.cartId || sr.cart.error) return '';
    const busy = scBusy();
    const price = o.price ? `<span class="sc-one-price">${srEsc(o.price)}</span>` : '';
    const logo = o.logo ? `<img src="${srEsc(o.logo)}" alt="Swiggy One" onerror="this.replaceWith(Object.assign(document.createElement('b'),{textContent:'ONE'}))">` : '<b>ONE</b>';
    return `<div class="card sc-one ${o.added ? 'on' : ''}">
        <span class="sc-one-logo">${logo}</span>
        <span class="sc-row-text">
            <b>${o.added ? 'Swiggy One added' : 'Add Swiggy One'} ${price}</b>
            <em>${srEsc(o.added ? (o.benefit || o.text || `${o.tenure} of free deliveries`) : (o.text || `Free deliveries for ${o.tenure}`))}</em>
        </span>
        <button type="button" class="sc-one-btn ${o.added ? 'remove' : ''}" ${busy ? 'disabled' : ''} onclick="scToggleOne()">${o.added ? 'Remove' : 'Add'}</button>
    </div>`;
}

function scToggleOne() {
    const o = sr.cart.one;
    if (!o || scBusy()) return;
    sr.cart.planId = o.added ? '' : o.plan_id;
    showToast(o.added ? 'Swiggy One removed' : 'Swiggy One added', false, 1200);
    sc.payKey = '';
    srSyncCart();
}

function scCashCardHtml() {
    const b = sr.cart.bill;
    if (!b || !b.swiggy_cash_available || b.swiggy_cash_available <= 0) return '';
    const used = (b.swiggy_cash_used || 0) > 0;
    const avail = b.swiggy_cash_available;
    return `<div class="card sc-cash ${used ? 'on' : ''}" style="display:flex;align-items:center;gap:12px;padding:12px;background:rgba(255,165,0,0.08);border:1px solid rgba(255,165,0,0.25);border-radius:12px;margin-bottom:12px">
        <span style="font-size:22px">💰</span>
        <span class="sc-row-text" style="flex:1">
            <b style="color:#d97706;display:block">Swiggy Money / Free Cash: ₹${avail.toFixed(2)}</b>
            <em style="font-size:12px;color:var(--tx-sub, #666)">${used ? `₹${b.swiggy_cash_used.toFixed(2)} applied to this order` : 'Available to use on this order'}</em>
        </span>
        <button type="button" class="sc-link-btn" style="padding:6px 12px;border-radius:8px;font-size:12px;font-weight:600;background:#d97706;color:#fff;border:none;cursor:pointer" onclick="scToggleCash()">${used ? 'Remove' : 'Use Cash'}</button>
    </div>`;
}

async function scToggleCash() {
    if (scBusy()) return;
    const d = await scPost('/api/cart/toggle_free_cash');
    if (d && d.ok) {
        showToast(d.use_free_cash ? 'Swiggy Cash applied' : 'Swiggy Cash removed', false, 1200);
        srSyncCart();
    }
}

function scBillHtml() {
    const b = sr.cart.bill;
    const row = (label, v, cls = '') => v ? `<div class="sc-bill-row ${cls}"><span>${label}</span><span>${cls === 'save' ? '−' : ''}${scMoney(v)}</span></div>` : '';
    if (!b) {
        if (sr.cart.error && !scBusy()) return '<div class="sc-bill-fail">Final price shows once Swiggy accepts the cart</div>';
        return srLoader('Getting the final price from Swiggy');
    }
    // Swiggy's own bill rows (rendering_details) when present
    const lines = sr.cart.billLines || [];
    const fmtVal = (v, isNeg) => {
        if (!v) return '';
        const s = String(v).trim();
        if (s.toUpperCase() === 'FREE') return 'FREE';
        const clean = s.replace(/^[−\-]\s*/, '').replace(/^[₹\s]+/, '').replace(/,/g, '');
        const num = parseFloat(clean);
        const formatted = isNaN(num) ? srEsc(s) : scMoney(num);
        return (isNeg ? '−' : '') + formatted;
    };
    const body = lines.length ? lines.map(l => `
        <div class="sc-bill-row ${l.total ? 'total' : ''} ${l.negative ? 'save' : ''}">
            <span>${srEsc(SC_BILL_LABELS[l.key] || l.label)}${l.note ? `<i class="sc-bill-note">${srEsc(l.note)}</i>` : ''}</span>
            <span>${l.strike ? `<s>${fmtVal(l.strike, false)}</s> ` : ''}${fmtVal(l.value, l.negative)}</span>
        </div>`).join('')
        : `${row('Item total', b.item_total)}${row('Extra discount for you', b.trade_discount, 'save')}${row('Coupon discount', b.coupon_discount, 'save')}${row('Swiggy Money / Free Cash', b.swiggy_cash_used, 'save')}${row('Delivery fee', b.delivery)}${row('GST & other charges', b.charges)}
           <div class="sc-bill-row total"><span>To Pay</span><span>${scMoney(b.to_pay)}</span></div>`;
    return body;
}

// card details live only in this form and in the one request that places the order; never saved
const SC_CARD = { number: '', name: '', expiry: '', cvv: '' };

function scCardFormHtml() {
    const f = (id, label, ph, extra = '') => `<label class="sc-card-f"><span>${label}</span>
        <input id="scCard_${id}" value="${srEsc(SC_CARD[id])}" placeholder="${ph}" ${extra} oninput="scCardInput('${id}', this)"></label>`;
    return `<div class="sc-card-form">
        ${f('number', 'Card number', '1234 5678 9012 3456', 'inputmode="numeric" autocomplete="cc-number" maxlength="23"')}
        ${f('name', 'Name on card', 'As printed on the card', 'autocomplete="cc-name"')}
        <div class="sc-card-row">
            ${f('expiry', 'Expiry', 'MM/YY', 'inputmode="numeric" autocomplete="cc-exp" maxlength="5"')}
            ${f('cvv', 'CVV', '•••', 'inputmode="numeric" type="password" autocomplete="cc-csc" maxlength="4"')}
        </div>
        <div class="sc-card-note"><i class="fa-solid fa-lock"></i> Sent straight to Swiggy's payment partner. We don't store card details.</div>
    </div>`;
}

function scCardInput(id, el) {
    let v = el.value;
    if (id === 'number') v = v.replace(/\D/g, '').slice(0, 19).replace(/(.{4})/g, '$1 ').trim();
    else if (id === 'expiry') { v = v.replace(/\D/g, '').slice(0, 4); if (v.length > 2) v = v.slice(0, 2) + '/' + v.slice(2); }
    else if (id === 'cvv') v = v.replace(/\D/g, '').slice(0, 4);
    else v = v.replace(/[^A-Za-z .'-]/g, '').slice(0, 40);
    SC_CARD[id] = v;
    if (el.value !== v) el.value = v;
}

function scCardError() {
    const num = SC_CARD.number.replace(/\D/g, '');
    if (num.length < 13) return 'Enter the card number';
    if (!SC_CARD.name.trim()) return 'Enter the name on the card';
    const m = SC_CARD.expiry.match(/^(\d{2})\/(\d{2})$/);
    if (!m || +m[1] < 1 || +m[1] > 12) return 'Enter the expiry as MM/YY';
    if (SC_CARD.cvv.length < 3) return 'Enter the CVV';
    return '';
}

function scPaymentHtml() {
    const p = sc.pay;
    scFixMethod();
    let body;
    if (sr.cart.error && !sr.cart.bill) body = '<div class="sc-bill-fail">Payment options show once the cart is priced</div>';
    else if (!sr.cart.cartId || !p || p.loading) body = srLoader('Checking payment options');
    else if (p.error) body = `<div class="sc-hint"><i class="fa-solid fa-circle-exclamation"></i> ${srEsc(p.error)}</div>`;
    else {
        // same layout as blinkit_bot's payment list: round icon, title, line under it, check radio
        const opt = (key, icon, title, sub) => {
            const m = scPayOpt(key);
            const on = sc.method === key && m.enabled;
            const msg = (m.message && m.message !== 'undefined') ? m.message : 'Not available';
            return `<div class="sc-po ${on ? 'active' : ''} ${m.enabled ? '' : 'disabled'}" onclick="scPick('${key}')">
                <span class="sc-po-icon"><i class="fa-solid ${icon}"></i></span>
                <span class="sc-po-body"><span class="sc-po-title">${title}</span><span class="sc-po-sub ${m.enabled ? '' : 'bad'}">${srEsc(m.enabled ? sub : 'Not available · ' + msg)}</span></span>
                <span class="sc-po-radio"><i class="fa-solid fa-check"></i></span>
            </div>`;
        };
        const apps = (p.upi && p.upi.apps || []).map(a => a.replace(/\s*UPI$/i, '')).slice(0, 3);
        const only = p.upi && p.upi.coupon_apps && p.upi.coupon_apps.length;   // the coupon works with these apps only
        body = `<div class="sc-po-list">
            ${opt('upi', 'fa-qrcode', 'UPI / QR', only ? `Pays with ${apps.join(', ')} only (coupon)` : apps.length ? `${apps.join(', ')} & any UPI app` : 'GPay, PhonePe, Paytm & any UPI app')}
            ${opt('card', 'fa-credit-card', 'Credit / Debit Card', 'Visa, Mastercard, RuPay · OTP at your bank')}
            ${sc.method === 'card' && (p.card || {}).enabled ? scCardFormHtml() : ''}
            ${opt('cod', 'fa-hand-holding-dollar', 'Cash on Delivery', 'Pay cash or ask for QR code when it arrives')}
        </div>`;
    }
    return body;
}

function scRenderPayBar() {
    let bar = scEl('scPayBar');
    if (!bar) {
        bar = document.createElement('div');
        bar.id = 'scPayBar';
        bar.className = 'sc-pay-bar';
        document.body.appendChild(bar);
    }
    const b = sr.cart.bill;
    if (state.activeTab !== 'cart' || !sr.cart.lines.length) { bar.style.display = 'none'; return; }
    scFixMethod();
    const m = scPayOpt(sc.method);
    const busy = scBusy() || !!(sc.pay && sc.pay.loading);
    const placing = !!sc.placing;
    const base = !placing && b && !sr.cart.error && !busy && m && m.enabled && !(sr.cart.oos || []).length;
    const hasAddr = !!(sr.addr && sr.addr.addressId);
    const ready = base && hasAddr;
    const needAddr = base && !hasAddr;
    bar.style.display = 'flex';
    bar.innerHTML = `
        <div class="sc-pay-bar-left"><small>${sc.method === 'cod' ? 'Pay on Delivery' : sc.method === 'card' ? 'Pay by Card' : 'Pay using UPI'}</small><b>${b && !scBusy() ? scMoney(b.to_pay) : '—'}</b></div>
        <button type="button" class="sc-pay-btn" ${ready || needAddr ? '' : 'disabled'} onclick="scPay()">${needAddr ? '<i class="fa-solid fa-location-dot"></i> Select Address' : placing ? '<i class="fa-solid fa-spinner fa-spin"></i> Processing' : busy ? '<i class="fa-solid fa-spinner fa-spin"></i> Updating' : `${sc.method === 'cod' ? 'Place Order' : 'Pay Now'} <i class="fa-solid fa-arrow-right"></i>`}</button>`;
}

function scApplyTyped() {
    const v = (scEl('scCouponCode').value || '').trim();
    if (!v) { showToast('Enter a coupon code first', true); return; }
    scApply(v.toUpperCase());
}

function scRenderCoupons() {
    const list = scEl('scCouponList');
    if (!list || !sc.coupons) return;
    const applied = sr.cart.coupon?.valid ? sr.cart.coupon.code : '';
    if (!sc.coupons.length) { list.innerHTML = '<div class="sr-empty-line">No coupons for this cart</div>'; return; }
    const usable = sc.coupons.filter(c => c.applicable), locked = sc.coupons.filter(c => !c.applicable);
    const applying = sc.applyingCode || '';
    const row = c => {
        const on = applied === c.code;
        const action = on ? '<span class="sc-cpr-done"><i class="fa-solid fa-circle-check"></i></span>'
            : c.applicable ? (applying === c.code
                ? '<button type="button" class="sc-cpr-apply busy" disabled><i class="fa-solid fa-spinner fa-spin"></i> Applying...</button>'
                : `<button type="button" class="sc-cpr-apply" ${sc.couponBusy ? 'disabled' : ''} onclick="event.stopPropagation(); scApply('${srEsc(c.code)}')">Apply</button>`)
            : '<span class="sc-cpr-lock"><i class="fa-solid fa-lock"></i></span>';
        const tap = c.applicable && !on && !sc.couponBusy ? ` onclick="scApply('${srEsc(c.code)}')"` : '';
        return `<div class="sc-cpr ${c.applicable ? '' : 'off'} ${on ? 'on' : ''} ${applying === c.code ? 'busy' : ''} ${c.applicable && !on ? 'tap' : ''}"${tap} title="${srEsc(c.description)}">
            <span class="sc-cpr-ico"><i class="fa-solid fa-ticket"></i></span>
            <span class="sc-cpr-text">
                <span class="sc-cpr-top"><b>${srEsc(c.code)}</b>${c.ribbon ? `<em>${srEsc(c.ribbon)}</em>` : ''}</span>
                <small>${srEsc(c.subtitle || c.description)}</small>
            </span>
            ${action}
        </div>`;
    };
    list.innerHTML =
        (usable.length ? `<div class="sc-cpr-head">Available coupons <span>${usable.length}</span></div>${usable.map(row).join('')}` : '') +
        (locked.length ? `<div class="sc-cpr-head">More offers <span>${locked.length}</span></div>${locked.map(row).join('')}` : '');
}

// leaving the tab hides the floating pay bar
(function scInit() {
    const orig = window.switchTab;
    window.switchTab = function (tabId, ...rest) {
        orig(tabId, ...rest);
        if (tabId !== 'cart') { const bar = scEl('scPayBar'); if (bar) bar.style.display = 'none'; }
        if (tabId === 'payment' || tabId === 'success') {
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            const n = scEl('nav-cart'); if (n) n.classList.add('active');
        }
    };
})();
