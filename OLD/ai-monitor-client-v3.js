// ==UserScript==
// @name         AI Quota Monitor Client v3
// @namespace    https://github.com/ai-quota-monitor
// @version      3.2.0
// @description  極簡版：定時擷取 AI 服務額度並 POST 至本地程式，僅一個色點 UI
// @author       AI Quota Monitor
// @match        https://platform.openai.com/settings/organization/billing/overview*
// @match        https://claude.ai/settings/usage*
// @match        https://platform.claude.com/settings/billing*
// @match        https://github.com/settings/billing/premium_requests_usage*
// @run-at       document-idle
// @noframes
// @grant        GM_xmlhttpRequest
// @connect      localhost
// @connect      127.0.0.1
// ==/UserScript==

(function () {
    'use strict';

    // ─────────────────────────────────────────────
    //  PAGE IDENTIFICATION
    // ─────────────────────────────────────────────
    const PAGE_MAP = {
        'platform.openai.com': {
            key: 'openai_billing',
            label: 'OpenAI',
            defaultInterval: 120,
            expectedPath: '/settings/organization/billing',
        },
        'claude.ai': {
            key: 'claude_usage',
            label: 'Claude Usage',
            defaultInterval: 60,
            expectedPath: '/settings/usage',
        },
        'platform.claude.com': {
            key: 'claude_billing',
            label: 'Claude Billing',
            defaultInterval: 120,
            expectedPath: '/settings/billing',
        },
        'github.com': {
            key: 'github_copilot',
            label: 'Copilot',
            defaultInterval: 180,
            expectedPath: '/settings/billing/premium_requests_usage',
        },
    };

    const PAGE = PAGE_MAP[location.hostname];
    if (!PAGE) return;

    function isOnExpectedPage() {
        return location.pathname.startsWith(PAGE.expectedPath);
    }

    // ─────────────────────────────────────────────
    //  CONFIG（硬編碼，移除 GM_getValue/setValue）
    // ─────────────────────────────────────────────
    const config = {
        server_url: 'http://localhost:7890',
        intervals: {
            openai_billing: 120,
            claude_usage: 60,
            claude_billing: 120,
            github_copilot: 180,
        },
    };

    // ─────────────────────────────────────────────
    //  STATE
    // ─────────────────────────────────────────────
    const COLORS = {
        idle:    '#6c7086',
        running: '#f9e2af',
        success: '#a6e3a1',
        error:   '#f38ba8',
    };

    let _lastSent = null;
    let _lastData = null;
    let _timer = null;
    let _busy = false;
    let _dot = null;

    // ─────────────────────────────────────────────
    //  DEFERRED BOOT
    // ─────────────────────────────────────────────
    const _defer = typeof requestIdleCallback === 'function'
        ? (fn) => requestIdleCallback(fn, { timeout: 3000 })
        : (fn) => setTimeout(fn, 50);
    _defer(_boot);
    return;

    // ─────────────────────────────────────────────
    //  UI — 單一色點，zero CSS injection
    // ─────────────────────────────────────────────
    function _boot() {
        _dot = document.createElement('div');
        _dot.style.cssText = [
            'position:fixed',
            'bottom:16px',
            'right:16px',
            'z-index:2147483647',
            'width:36px',
            'height:36px',
            'border-radius:50%',
            'cursor:pointer',
            'background-color:' + COLORS.idle,
            'box-shadow:0 2px 8px rgba(0,0,0,0.5)',
            'border:2px solid rgba(255,255,255,0.15)',
        ].join(';');
        _dot.title = PAGE.label + ' — 點擊立即擷取';
        _dot.addEventListener('click', () => { runExtraction(); });
        document.body.appendChild(_dot);

        _startWork();
    }

    function setStatus(status, msg) {
        if (!_dot) return;
        _dot.style.backgroundColor = COLORS[status] || COLORS.idle;
        if (status === 'success' && _lastSent) {
            _dot.title = PAGE.label + ' ✓ ' + new Date(_lastSent).toLocaleTimeString('zh-TW') + '\n點擊立即擷取';
        } else if (status === 'error') {
            _dot.title = PAGE.label + ' ✗ ' + (msg || '') + '\n點擊重試';
        } else if (status === 'running') {
            _dot.title = PAGE.label + ' — 擷取中...';
        } else {
            _dot.title = PAGE.label + ' — 點擊立即擷取';
        }
    }

    // ─────────────────────────────────────────────
    //  TIMER
    // ─────────────────────────────────────────────
    function startTimer() {
        if (_timer) clearInterval(_timer);
        const ms = (config.intervals[PAGE.key] || 60) * 1000;
        _timer = setInterval(runExtraction, ms);
    }

    // ─────────────────────────────────────────────
    //  DOM UTILITIES
    // ─────────────────────────────────────────────
    function waitForElement(selector, maxMs) {
        return new Promise((resolve) => {
            const el = document.querySelector(selector);
            if (el) { resolve(el); return; }
            const timer = setTimeout(() => { obs.disconnect(); resolve(null); }, maxMs || 8000);
            const obs = new MutationObserver(() => {
                const found = document.querySelector(selector);
                if (found) { clearTimeout(timer); obs.disconnect(); resolve(found); }
            });
            obs.observe(document.body, { childList: true, subtree: true });
        });
    }

    function takePageSnapshot() {
        return document.querySelector('main')
            || document.querySelector('[role="main"]')
            || document.querySelector('#root')
            || document.querySelector('#__next')
            || document.body;
    }

    function findSectionText(fullText, startMarker, endMarker) {
        const si = fullText.indexOf(startMarker);
        if (si === -1) return null;
        if (!endMarker) return fullText.substring(si);
        const ei = fullText.indexOf(endMarker, si + startMarker.length);
        return ei === -1 ? fullText.substring(si) : fullText.substring(si, ei);
    }

    // ─────────────────────────────────────────────
    //  PAGE PARSERS
    // ─────────────────────────────────────────────
    async function parseOpenAIBilling() {
        await waitForElement('[data-testid], .billing-overview, section', 10000);
        await new Promise(r => setTimeout(r, 3000));

        const data = { source: 'openai_billing' };
        const snap = takePageSnapshot();
        const t = snap.textContent;

        for (const p of [
            /Credit\s+balance[\s\S]{0,40}\$([\d,]+(?:\.\d{2})?)/i,
            /\$([\d,]+\.\d{2})\s*(?:USD)?\s*(?:credit|balance)/i,
            /balance[^\$]{0,30}\$([\d,]+\.\d{2})/i,
        ]) {
            const m = t.match(p);
            if (m) { data.balance_usd = parseFloat(m[1].replace(',', '')); break; }
        }

        const gm = t.match(/([\d,]+(?:\.\d{2,})?)\s*(?:of|\/)\s*([\d,]+(?:\.\d{2,})?)\s*(?:credits?|used)/i);
        if (gm) {
            data.credits_used_usd  = parseFloat(gm[1].replace(',', ''));
            data.credits_total_usd = parseFloat(gm[2].replace(',', ''));
        }

        for (const p of [
            /(?:hard\s+limit|monthly\s+limit|spend\s+limit)[^\$]{0,40}\$([\d,]+(?:\.\d{2})?)/i,
            /\$([\d,]+(?:\.\d{2})?)\s*(?:hard\s+limit|spend\s+limit)/i,
        ]) {
            const m = t.match(p);
            if (m) { data.hard_limit_usd = parseFloat(m[1].replace(',', '')); break; }
        }

        const sm = t.match(/(?:soft\s+limit|email\s+alert)[^\$]{0,40}\$([\d,]+(?:\.\d{2})?)/i);
        if (sm) data.soft_limit_usd = parseFloat(sm[1].replace(',', ''));

        const um = t.match(/\$([\d,]+\.\d{2,4})\s*(?:this\s*month|current\s*period)/i)
            || t.match(/(?:this\s*month|current\s*period)[^\$]{0,30}\$([\d,]+\.\d{2,4})/i);
        if (um) data.month_usage_usd = parseFloat(um[1].replace(',', ''));

        const tier = t.match(/(?:usage\s+tier|tier)[:\s]+(\w[\w\s-]{0,20})/i);
        if (tier) data.tier = tier[1].trim();

        if (/auto.?recharge\s*(?:is\s*)?on/i.test(t)) data.auto_recharge = true;

        // Retry if result is empty (React not yet rendered)
        const dataKeys = Object.keys(data).filter(k => k !== 'source');
        if (dataKeys.length <= 1 && data.balance_usd === 0) {
            await new Promise(r => setTimeout(r, 3000));
            const snap2 = takePageSnapshot();
            const t2 = snap2.textContent;
            const gm2 = t2.match(/([\d,]+(?:\.\d{2,})?)\s*(?:of|\/)\s*([\d,]+(?:\.\d{2,})?)\s*(?:credits?|used)/i);
            if (gm2) {
                data.credits_used_usd  = parseFloat(gm2[1].replace(',', ''));
                data.credits_total_usd = parseFloat(gm2[2].replace(',', ''));
            }
            const um2 = t2.match(/\$([\d,]+\.\d{2,4})\s*(?:this\s*month|current\s*period)/i)
                || t2.match(/(?:this\s*month|current\s*period)[^\$]{0,30}\$([\d,]+\.\d{2,4})/i);
            if (um2) data.month_usage_usd = parseFloat(um2[1].replace(',', ''));
        }

        return data;
    }

    async function parseClaudeUsage() {
        await waitForElement('main, h1, [data-testid]', 6000);
        await new Promise(r => setTimeout(r, 1800));

        const data = { source: 'claude_usage' };
        const snap = takePageSnapshot();
        const t = snap.textContent;

        const sess = findSectionText(t, 'Current session', 'Weekly limits')
            || findSectionText(t, 'Plan usage limits', 'Weekly limits');
        if (sess) {
            const p = sess.match(/(\d+)%\s*used/i);
            if (p) data.session_percent = parseInt(p[1]);
            const r = sess.match(/Resets?\s+in\s+((?:\d+\s*hr?s?\s*)?(?:\d+\s*min?s?)?)/i);
            if (r) data.session_reset = r[1].trim();
        }

        const wkly = findSectionText(t, 'Weekly limits', 'Extra usage');
        if (wkly) {
            const p = wkly.match(/(\d+)%\s*used/i);
            if (p) data.weekly_percent = parseInt(p[1]);
            const r = wkly.match(/Resets?\s+in\s+((?:\d+\s*hr?s?\s*)?(?:\d+\s*min?s?)?)/i);
            if (r) data.weekly_reset = r[1].trim();
        }

        const extra = findSectionText(t, 'Extra usage', null);
        if (extra) {
            const spent = extra.match(/\$([\d.]+)\s*spent/i);
            if (spent) data.extra_spent = parseFloat(spent[1]);

            const resets = extra.match(/Resets?\s+([\w]+ \d+)/i);
            if (resets) data.extra_resets = resets[1];

            const limit = extra.match(/\$([\d,]+(?:\.\d{2})?)\s*[\n\r ]*Monthly\s+spend\s+limit/i)
                || extra.match(/Monthly\s+spend\s+limit[^\$]{0,40}\$([\d,]+(?:\.\d{2})?)/i);
            if (limit) data.extra_limit = parseFloat(limit[1].replace(',', ''));

            const balance = extra.match(/\$([\d.]+)\s*[\n\r ]*Current\s+balance/i)
                || extra.match(/Current\s+balance[^\$]{0,20}\$([\d.]+)/i);
            if (balance) data.extra_balance = parseFloat(balance[1]);

            const ep = extra.match(/(\d+)%\s*used/i);
            if (ep) data.extra_percent = parseInt(ep[1]);

            if (/auto.?reload\s+on/i.test(extra)) data.auto_reload = true;
            else if (/auto.?reload\s+off/i.test(extra)) data.auto_reload = false;

            data.extra_enabled = !!(data.extra_spent !== undefined || data.extra_balance !== undefined || data.extra_limit !== undefined);
        }

        if (data.session_percent === undefined) {
            const matches = [...t.matchAll(/(\d{1,3})%\s*used/gi)];
            if (matches[0]) data.session_percent = parseInt(matches[0][1]);
            if (matches[1]) data.weekly_percent  = parseInt(matches[1][1]);
        }
        if (!data.session_reset) {
            const matches = [...t.matchAll(/Resets?\s+in\s+((?:\d+\s*hr?s?\s*)?(?:\d+\s*min?s?)?)/gi)];
            if (matches[0]) data.session_reset = matches[0][1].trim();
            if (matches[1]) data.weekly_reset   = matches[1][1].trim();
        }

        return data;
    }

    async function parseClaudeBilling() {
        await waitForElement('[data-testid="credit-balance"], main, [data-testid]', 6000);
        await new Promise(r => setTimeout(r, 1800));

        const data = { source: 'claude_billing' };
        const snap = takePageSnapshot();
        const t = snap.textContent;

        const pm = t.match(/(?:Current\s+)?[Pp]lan[:\s]+([^\n\r]{1,40})/i)
            || t.match(/(Pro|Team|Enterprise|Developer|Free|Scale)\s+plan/i);
        if (pm) data.plan = pm[1].trim();

        const bd = t.match(/(?:next\s+billing|renews?)[^\d]{0,30}(\w+ \d{1,2},? \d{4})/i);
        if (bd) data.next_billing = bd[1].trim();

        const am = t.match(/\$([\d.]+)\s*\/\s*(?:month|mo)/i)
            || t.match(/\$([\d.]+)\s*per\s+month/i);
        if (am) data.monthly_usd = parseFloat(am[1]);

        const um = t.match(/(?:usage|this\s+month)[^\$]{0,30}\$([\d.]+)/i);
        if (um) data.this_month_usd = parseFloat(um[1]);

        const creditBalanceCard = snap.querySelector('[data-testid="credit-balance"]');
        if (creditBalanceCard) {
            const balText = creditBalanceCard.textContent || '';
            const bm = balText.match(/US\$\s*([\d,]+(?:\.\d+)?)/i)
                || balText.match(/\$([\d,]+(?:\.\d+)?)/);
            if (bm) data.balance_usd = parseFloat(bm[1].replace(/,/g, ''));
        }
        if (data.balance_usd === undefined) {
            const rb = t.match(/(?:US)?\$([\d,]+(?:\.\d+)?)\s*[\n\r\s]*Remaining\s+Balance/i)
                || t.match(/Remaining\s+Balance[\s\S]{0,30}(?:US)?\$([\d,]+(?:\.\d+)?)/i);
            if (rb) data.balance_usd = parseFloat(rb[1].replace(/,/g, ''));
        }

        const sl = t.match(/(?:spend|credit)\s+limit[^\$]{0,30}\$([\d.]+)/i);
        if (sl) data.spend_limit_usd = parseFloat(sl[1]);

        return data;
    }

    async function parseGitHubCopilot() {
        await waitForElement('[data-testid="included-premium-requests-card"]', 10000);
        await new Promise(r => setTimeout(r, 800));

        const data = { source: 'github_copilot' };
        const snap = takePageSnapshot();

        const inclCard = snap.querySelector('[data-testid="included-premium-requests-card"]');
        if (inclCard) {
            const valEl = inclCard.querySelector('[class*="cardValue"]');
            if (valEl) data.included_consumed = parseFloat(valEl.textContent.trim().replace(/,/g, ''));

            const entEl = inclCard.querySelector('[class*="entitlementText"]');
            if (entEl) {
                const nums = entEl.textContent.replace(/,/g, '').match(/[\d.]+/g);
                if (nums && nums.length > 0) data.included_total = parseFloat(nums[0]);
            }

            if (data.included_consumed !== undefined && data.included_total > 0) {
                data.included_percent = Math.round(data.included_consumed / data.included_total * 1000) / 10;
            }
        }

        const billedCard = snap.querySelector('[data-testid="total-billed-amount-card"]');
        if (billedCard) {
            const billedEl = billedCard.querySelector('[class*="cardValue"]');
            if (billedEl) {
                const bm = billedEl.textContent.match(/[\d.]+/);
                if (bm) data.billed_usd = parseFloat(bm[0]);
            }
        }

        const t = snap.textContent;
        const rm = t.match(/resets?\s+in\s+(\d+)\s*days?/i)
            || t.match(/(\d+)\s*days?\s+(?:until\s+)?reset/i);
        if (rm) data.resets_in_days = parseInt(rm[1]);

        const nb = t.match(/resets?\s+in\s+\d+\s*days?\s+on\s+([^\n.]+)/i);
        if (nb) data.next_billing = nb[1].trim();

        return data;
    }

    // ─────────────────────────────────────────────
    //  EXTRACTION ENTRY
    // ─────────────────────────────────────────────
    async function runExtraction() {
        if (_busy) return;
        if (!isOnExpectedPage()) return;
        _busy = true;
        setStatus('running');

        let parsedData;
        try {
            switch (PAGE.key) {
                case 'openai_billing':  parsedData = await parseOpenAIBilling();  break;
                case 'claude_usage':    parsedData = await parseClaudeUsage();    break;
                case 'claude_billing':  parsedData = await parseClaudeBilling();  break;
                case 'github_copilot':  parsedData = await parseGitHubCopilot(); break;
                default: throw new Error('Unknown page: ' + PAGE.key);
            }
        } catch (err) {
            _busy = false;
            setStatus('error', err.message);
            console.error('[AI Monitor v3]', err);
            return;
        }
        _busy = false;

        parsedData.timestamp = new Date().toISOString();
        parsedData.page_url  = location.href;

        // Skip send if no real data
        const SKIP = new Set(['source', 'timestamp', 'page_url']);
        if (Object.keys(parsedData).filter(k => !SKIP.has(k)).length === 0) {
            setStatus('error', '頁面資料為空');
            return;
        }

        // Skip send if nothing changed
        const prev = _lastData;
        const changed = !prev || Object.keys(parsedData).some(k => !SKIP.has(k) && parsedData[k] !== prev[k]);
        _lastData = parsedData;

        if (changed) {
            sendToServer(parsedData);
        } else {
            setStatus('success');
        }
    }

    // ─────────────────────────────────────────────
    //  SERVER COMMUNICATION
    // ─────────────────────────────────────────────
    function sendToServer(data) {
        GM_xmlhttpRequest({
            method:  'POST',
            url:     config.server_url + '/update',
            headers: { 'Content-Type': 'application/json', 'X-AI-Monitor-Client': '1' },
            data:    JSON.stringify(data),
            timeout: 5000,
            onload(resp) {
                if (resp.status >= 200 && resp.status < 300) {
                    _lastSent = Date.now();
                    setStatus('success');
                } else {
                    setStatus('error', '伺服器 ' + resp.status);
                }
            },
            onerror()  { setStatus('error', '無法連線'); },
            ontimeout() { setStatus('error', '連線逾時'); },
        });
    }

    // ─────────────────────────────────────────────
    //  SPA NAVIGATION DETECTION
    // ─────────────────────────────────────────────
    let _lastHref = location.href;
    setInterval(() => {
        if (location.href === _lastHref) return;
        _lastHref = location.href;
        if (isOnExpectedPage()) setTimeout(runExtraction, 2500);
    }, 2000);

    // ─────────────────────────────────────────────
    //  STARTUP
    // ─────────────────────────────────────────────
    function _startWork() {
        startTimer();
        setTimeout(runExtraction, 2500);
    }

    if (document.readyState === 'complete') {
        _startWork();
    } else {
        window.addEventListener('load', _startWork);
    }

})();
