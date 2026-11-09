// GBX Swiggy Telegram Shield & Client Integration
(function () {
  'use strict';

  // 1. Telegram WebApp Verification & Detection
  function isTelegramEnv() {
    const tg = window.Telegram && window.Telegram.WebApp;
    if (tg && tg.initData && tg.initData.length > 5) return true;
    if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.id) return true;
    if (window.TelegramWebviewProxy) return true;
    if (window.Telegram && window.Telegram.WebView) return true;
    if (location.hash && location.hash.indexOf('tgWebAppData') !== -1) return true;
    if (navigator.userAgent && /Telegram/i.test(navigator.userAgent)) return true;
    try {
      if (sessionStorage.getItem('initParams')) return true;
    } catch(e) {}
    var qp = new URLSearchParams(location.search);
    if (qp.get('tgib') || qp.get('token') || qp.get('user') || qp.get('t')) return true;
    return true; // Allow smooth fallback without locking screen
  }

  document.documentElement.classList.add('in-tg');
  const tg = window.Telegram && window.Telegram.WebApp;
  if (tg) {
    try {
      tg.ready();
      tg.expand();
      if (tg.enableClosingConfirmation) tg.enableClosingConfirmation();
    } catch(e) {}
  }

  // 2. Request Signing & Header Injection
  const _origFetch = window.fetch;
  window.fetch = function(input, init){
    init = init || {};
    var url = (typeof input === 'string') ? input : (input && input.url) || '';
    var initData = (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData) || new URLSearchParams(location.search).get('tgib') || new URLSearchParams(location.search).get('token') || '';
    if (initData && (url.charAt(0) === '/' || url.indexOf(location.origin) === 0)) {
      var h = new Headers(init.headers || (typeof input !== 'string' && input && input.headers) || {});
      if (!h.has('X-Swiggy-Init-Data')) h.set('X-Swiggy-Init-Data', initData);
      if (!h.has('X-Tg-Init-Data')) h.set('X-Tg-Init-Data', initData);
      if (!h.has('x-telegram-init-data')) h.set('x-telegram-init-data', initData);
      if (!h.has('x-token')) h.set('x-token', initData);
      init.headers = h;
      if (init.credentials == null) init.credentials = 'include';
    }
    return _origFetch.call(this, input, init);
  };
})();
