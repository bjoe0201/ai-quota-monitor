// ==UserScript==
// @name         AI Quota Monitor Client
// @namespace    https://github.com/ai-quota-monitor
// @version      2.1.0
// @description  讀取 AI 服務額度資料並傳送給 AI Quota Monitor 桌面程式
// @author       AI Quota Monitor
// @match        https://platform.openai.com/settings/organization/billing/overview*
// @match        https://claude.ai/settings/usage*
// @match        https://platform.claude.com/settings/billing*
// @match        https://github.com/settings/billing/premium_requests_usage*
// @run-at       document-idle
// @grant        GM_xmlhttpRequest
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_addStyle
// @grant        GM_openInTab
// @grant        GM_info
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
            label: 'OpenAI 帳單',
            defaultInterval: 120,
            expectedPath: '/settings/organization/billing',
        },
        'claude.ai': {
            key: 'claude_usage',
            label: 'Claude.ai 用量',
            defaultInterval: 60,
            expectedPath: '/settings/usage',
        },
        'platform.claude.com': {
            key: 'claude_billing',
            label: 'Claude API 帳單',
            defaultInterval: 120,
            expectedPath: '/settings/billing',
        },
        'github.com': {
            key: 'github_copilot',
            label: 'GitHub Copilot',
            defaultInterval: 180,
            expectedPath: '/settings/billing/premium_requests_usage',
        },
    };

    const host = location.hostname;
    const PAGE = PAGE_MAP[host];
    if (!PAGE) return;

    /** 確認目前 URL 是否仍在正確頁面路徑 */
    function isOnExpectedPage() {
        return location.pathname.startsWith(PAGE.expectedPath);
    }

    // ─────────────────────────────────────────────
    //  CONFIG (persistent via GM_setValue)
    // ─────────────────────────────────────────────
    const CFG_KEY = 'aimon_config';

    function loadConfig() {
        const raw = GM_getValue(CFG_KEY, null);
        const defaults = {
            server_url: 'http://localhost:7890',
            intervals: {
                openai_billing: 120,
                claude_usage: 60,
                claude_billing: 120,
                github_copilot: 180,
            },
            enabled: {
                openai_billing: true,
                claude_usage: true,
                claude_billing: true,
                github_copilot: true,
            },
            tab_refresh: {
                openai_billing: 0,
                claude_usage: 0,
                claude_billing: 0,
                github_copilot: 0,
            },
        };
        if (!raw) return defaults;
        try {
            const saved = JSON.parse(raw);
            saved.intervals = Object.assign({}, defaults.intervals, saved.intervals || {});
            saved.enabled = Object.assign({}, defaults.enabled, saved.enabled || {});
            saved.tab_refresh = Object.assign({}, defaults.tab_refresh, saved.tab_refresh || {});
            return Object.assign({}, defaults, saved);
        } catch (_) {
            return defaults;
        }
    }

    function saveConfig(cfg) {
        GM_setValue(CFG_KEY, JSON.stringify(cfg));
    }

    let config = loadConfig();

    // ─────────────────────────────────────────────
    //  STATE
    // ─────────────────────────────────────────────
    let state = {
        status: 'idle',   // idle | running | success | error | stopped
        lastSent: null,
        lastData: null,
        errorMsg: '',
        timer: null,
        tabRefreshTimer: null,
        forceSend: false,  // set true when GUI requests refresh, bypasses hasChange check
    };

    // ─────────────────────────────────────────────
    //  STYLES
    // ─────────────────────────────────────────────
    GM_addStyle(`
        #aimon-root * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }

        /* Floating button */
        #aimon-btn {
            position: fixed; bottom: 20px; right: 20px; z-index: 2147483646;
            width: 44px; height: 44px; border-radius: 50%;
            background: #1e1e2e; border: 2px solid #89b4fa;
            cursor: pointer; display: flex; align-items: center; justify-content: center;
            box-shadow: 0 4px 16px rgba(0,0,0,0.5);
            transition: transform 0.2s, box-shadow 0.2s;
            user-select: none;
        }
        #aimon-btn:hover { transform: scale(1.1); box-shadow: 0 6px 20px rgba(0,0,0,0.6); }
        #aimon-btn .aimon-icon { font-size: 20px; line-height: 1; }
        #aimon-btn .aimon-dot {
            position: absolute; top: 2px; right: 2px;
            width: 12px; height: 12px; border-radius: 50%;
            border: 2px solid #1e1e2e;
            transition: background 0.3s;
        }
        #aimon-btn .aimon-dot.idle     { background: #6c7086; }
        #aimon-btn .aimon-dot.running  { background: #f9e2af; animation: aimon-pulse 1s infinite; will-change: opacity; }
        #aimon-btn .aimon-dot.success  { background: #a6e3a1; }
        #aimon-btn .aimon-dot.error    { background: #f38ba8; }
        #aimon-btn .aimon-dot.stopped  { background: #6c7086; }

        @keyframes aimon-pulse {
            0%, 100% { opacity: 1; } 50% { opacity: 0.3; }
        }

        /* Panel */
        #aimon-panel {
            position: fixed; bottom: 72px; right: 20px; z-index: 2147483645;
            width: 340px;
            background: #1e1e2e; color: #cdd6f4;
            border: 1px solid #3a3a5e; border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.6);
            overflow: hidden;
            display: none;
        }
        #aimon-panel.visible { display: block; }

        .aimon-header {
            background: #181825; padding: 12px 16px;
            display: flex; align-items: center; justify-content: space-between;
            border-bottom: 1px solid #3a3a5e;
        }
        .aimon-header-title { font-weight: 700; font-size: 13px; color: #89dceb; }
        .aimon-close {
            background: none; border: none; color: #6c7086; cursor: pointer;
            font-size: 18px; line-height: 1; padding: 0 4px;
        }
        .aimon-close:hover { color: #cdd6f4; }

        .aimon-section { padding: 12px 16px; border-bottom: 1px solid #2a2a3e; }
        .aimon-section:last-child { border-bottom: none; }
        .aimon-label { font-size: 11px; color: #7f849c; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }

        .aimon-status-row {
            display: flex; align-items: center; gap: 8px;
            padding: 6px 8px; border-radius: 6px;
            font-size: 12px;
        }
        .aimon-status-row.current { background: #2a2a3e; }
        .aimon-status-dot {
            width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
        }
        .aimon-status-dot.idle     { background: #6c7086; }
        .aimon-status-dot.running  { background: #f9e2af; animation: aimon-pulse 1s infinite; will-change: opacity; }
        .aimon-status-dot.success  { background: #a6e3a1; }
        .aimon-status-dot.error    { background: #f38ba8; }
        .aimon-status-dot.stopped  { background: #6c7086; }
        .aimon-status-text { flex: 1; font-weight: 600; }
        .aimon-status-time { color: #6c7086; font-size: 11px; }

        .aimon-input-row {
            display: flex; align-items: center; gap: 8px; margin-bottom: 8px;
        }
        .aimon-input-row label { font-size: 12px; color: #a6adc8; flex: 1; }
        .aimon-input {
            background: #181825; border: 1px solid #3a3a5e; color: #cdd6f4;
            border-radius: 6px; padding: 4px 8px; font-size: 12px;
            width: 80px; text-align: right;
        }
        .aimon-input:focus { outline: none; border-color: #89b4fa; }
        .aimon-input.url-input { width: 180px; text-align: left; }

        .aimon-btn-row { display: flex; gap: 8px; margin-top: 8px; }
        .aimon-action-btn {
            flex: 1; padding: 7px; border: none; border-radius: 6px;
            font-size: 12px; font-weight: 600; cursor: pointer;
            transition: opacity 0.2s;
        }
        .aimon-action-btn:hover { opacity: 0.85; }
        .aimon-action-btn.run  { background: #89b4fa; color: #1e1e2e; }
        .aimon-action-btn.stop { background: #3a3a5e; color: #cdd6f4; }
        .aimon-action-btn.save { background: #a6e3a1; color: #1e1e2e; }
        .aimon-action-btn.link { background: #313244; color: #cdd6f4; }
        .aimon-action-btn.link.active-page { background: #2a3a5e; color: #89b4fa; border: 1px solid #89b4fa; }

        .aimon-data-pre {
            background: #181825; border-radius: 6px; padding: 8px;
            font-size: 11px; color: #a6adc8; word-break: break-all;
            max-height: 120px; overflow-y: auto;
            white-space: pre-wrap;
            margin-top: 4px;
        }

        .aimon-badge {
            display: inline-block; border-radius: 4px;
            padding: 1px 6px; font-size: 10px; font-weight: 700;
        }
        .aimon-badge.current-page { background: #313244; color: #89b4fa; }
    `);

    // ─────────────────────────────────────────────
    //  UI CREATION
    // ─────────────────────────────────────────────
    const btn = document.createElement('div');
    btn.id = 'aimon-btn';
    btn.title = 'AI Quota Monitor';
    btn.innerHTML = `<span class="aimon-icon">📊</span><span class="aimon-dot idle"></span>`;

    const panel = document.createElement('div');
    panel.id = 'aimon-panel';
    panel.innerHTML = `
        <div class="aimon-header">
            <span class="aimon-header-title">📊 AI Quota Monitor <span style="font-size:10px; color:#6c7086; font-weight:400;">v${GM_info.script.version}</span></span>
            <button class="aimon-close" id="aimon-close-btn">✕</button>
        </div>

        <div class="aimon-section">
            <div class="aimon-label">目前頁面狀態</div>
            <div class="aimon-status-row current">
                <div class="aimon-status-dot idle" id="aimon-cur-dot"></div>
                <span class="aimon-status-text">${PAGE.label}</span>
                <span class="aimon-badge current-page">此頁面</span>
            </div>
            <div style="font-size:11px; color:#6c7086; margin-top:6px; padding-left:4px;" id="aimon-cur-status-text">尚未執行</div>
        </div>

        <div class="aimon-section">
            <div class="aimon-label">此頁面更新間隔</div>
            <div class="aimon-input-row">
                <label>每隔幾秒重新擷取</label>
                <input class="aimon-input" id="aimon-interval-input" type="number" min="10" max="3600"
                    value="${config.intervals[PAGE.key]}" />
                <span style="font-size:11px;color:#6c7086;">秒</span>
            </div>
            <div class="aimon-input-row">
                <label>自動重新整理頁面 <span style="color:#6c7086;">(0=停用)</span></label>
                <input class="aimon-input" id="aimon-tab-refresh-input" type="number" min="0" max="600"
                    value="${config.tab_refresh[PAGE.key]}" />
                <span style="font-size:11px;color:#6c7086;">秒</span>
            </div>
        </div>

        <div class="aimon-section">
            <div class="aimon-label">本地伺服器位址</div>
            <div class="aimon-input-row">
                <label>URL</label>
                <input class="aimon-input url-input" id="aimon-server-input" type="text"
                    value="${config.server_url}" />
            </div>
            <div style="font-size:10px;color:#6c7086;">請確認 AI Quota Monitor 桌面程式已執行</div>
        </div>

        <div class="aimon-section">
            <div class="aimon-btn-row">
                <button class="aimon-action-btn run"  id="aimon-run-btn">▶ 立即擷取</button>
                <button class="aimon-action-btn stop" id="aimon-stop-btn">⏹ 停止</button>
                <button class="aimon-action-btn save" id="aimon-save-btn">💾 儲存</button>
            </div>
        </div>

        <div class="aimon-section">
            <div class="aimon-label">快速開啟頁面</div>
            <div class="aimon-btn-row" id="aimon-quickopen-row" style="flex-wrap:wrap; gap:6px;"></div>
            <button class="aimon-action-btn run" id="aimon-openall-btn" style="width:100%; margin-top:8px;">🚀 一鍵全開</button>
        </div>

        <div class="aimon-section">
            <div class="aimon-label">最後擷取資料預覽</div>
            <div class="aimon-data-pre" id="aimon-data-preview">尚無資料</div>
        </div>
    `;

    document.body.appendChild(btn);
    document.body.appendChild(panel);

    // ─────────────────────────────────────────────
    //  QUICK-OPEN BUTTONS
    // ─────────────────────────────────────────────
    const PAGE_URLS = {
        'platform.openai.com': 'https://platform.openai.com/settings/organization/billing/overview',
        'claude.ai':           'https://claude.ai/settings/usage',
        'platform.claude.com': 'https://platform.claude.com/settings/billing',
        'github.com':          'https://github.com/settings/billing/premium_requests_usage',
    };

    (function buildQuickOpenButtons() {
        const row = document.getElementById('aimon-quickopen-row');
        if (!row) return;
        Object.entries(PAGE_MAP).forEach(([pageHost, info]) => {
            const isActive = pageHost === host;
            const btn2 = document.createElement('button');
            btn2.className = 'aimon-action-btn link' + (isActive ? ' active-page' : '');
            btn2.textContent = (isActive ? '● ' : '') + info.label;
            btn2.title = PAGE_URLS[pageHost];
            btn2.addEventListener('click', (e) => {
                e.stopPropagation();
                GM_openInTab(PAGE_URLS[pageHost], { active: false });
            });
            row.appendChild(btn2);
        });

        document.getElementById('aimon-openall-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            Object.values(PAGE_URLS).forEach(url => {
                GM_openInTab(url, { active: false });
            });
        });
    })();

    // ─────────────────────────────────────────────
    //  UI EVENTS
    // ─────────────────────────────────────────────
    btn.addEventListener('click', () => panel.classList.toggle('visible'));

    document.getElementById('aimon-close-btn').addEventListener('click', () => {
        panel.classList.remove('visible');
    });

    document.getElementById('aimon-run-btn').addEventListener('click', () => {
        panel.classList.remove('visible');
        runExtraction();
    });

    document.getElementById('aimon-stop-btn').addEventListener('click', () => {
        stopTimer();
        setStatus('stopped', '手動停止');
    });

    document.getElementById('aimon-save-btn').addEventListener('click', () => {
        const interval = parseInt(document.getElementById('aimon-interval-input').value, 10) || 60;
        const tabRefresh = Math.max(0, Math.min(600, parseInt(document.getElementById('aimon-tab-refresh-input').value, 10) || 0));
        const server_url = (document.getElementById('aimon-server-input').value || '').trim()
            || 'http://localhost:7890';
        config.intervals[PAGE.key] = interval;
        config.tab_refresh[PAGE.key] = tabRefresh;
        config.server_url = server_url;
        saveConfig(config);
        restartTimer();
        startTabRefreshTimer();
        showToast('✓ 設定已儲存');
    });

    // Close panel on outside click
    document.addEventListener('click', (e) => {
        if (!panel.contains(e.target) && !btn.contains(e.target)) {
            panel.classList.remove('visible');
        }
    }, true);

    // ─────────────────────────────────────────────
    //  STATUS HELPERS
    // ─────────────────────────────────────────────
    function setStatus(status, msg) {
        state.status = status;
        state.errorMsg = msg || '';

        const dot = btn.querySelector('.aimon-dot');
        const curDot = document.getElementById('aimon-cur-dot');
        const curText = document.getElementById('aimon-cur-status-text');

        if (dot) dot.className = `aimon-dot ${status}`;
        if (curDot) curDot.className = `aimon-status-dot ${status}`;

        const timeStr = state.lastSent
            ? new Date(state.lastSent).toLocaleTimeString('zh-TW')
            : '';
        const labels = {
            idle:    '準備就緒',
            running: '⏳ 擷取中...',
            success: `✓ 成功${timeStr ? ' — ' + timeStr : ''}`,
            error:   `✗ 失敗：${msg}`,
            stopped: '⏹ 已停止',
        };
        if (curText) curText.textContent = labels[status] || status;
    }

    function updateDataPreview(data) {
        const el = document.getElementById('aimon-data-preview');
        if (!el) return;
        // Show cleaned preview (no internal keys)
        const preview = Object.entries(data)
            .filter(([k]) => !['source', 'timestamp', 'page_url'].includes(k))
            .map(([k, v]) => `${k}: ${v}`)
            .join('\n');
        el.textContent = preview || '（無可顯示的資料）';
    }

    // ─────────────────────────────────────────────
    //  TOAST
    // ─────────────────────────────────────────────
    function showToast(msg) {
        let t = document.getElementById('aimon-toast');
        if (!t) {
            t = document.createElement('div');
            t.id = 'aimon-toast';
            Object.assign(t.style, {
                position: 'fixed', bottom: '72px', right: '20px',
                background: '#a6e3a1', color: '#1e1e2e',
                padding: '8px 16px', borderRadius: '8px',
                fontSize: '12px', fontWeight: '700',
                zIndex: '2147483647', pointerEvents: 'none',
                transition: 'opacity 0.4s',
                opacity: '0',
            });
            document.body.appendChild(t);
        }
        t.textContent = msg;
        t.style.opacity = '1';
        clearTimeout(t._timer);
        t._timer = setTimeout(() => { t.style.opacity = '0'; }, 2500);
    }

    // ─────────────────────────────────────────────
    //  TIMER MANAGEMENT
    // ─────────────────────────────────────────────
    function stopTimer() {
        if (state.timer) { clearInterval(state.timer); state.timer = null; }
    }

    function startTimer() {
        stopTimer();
        const ms = (config.intervals[PAGE.key] || 60) * 1000;
        state.timer = setInterval(runExtraction, ms);
    }

    function restartTimer() {
        if (state.status !== 'stopped') startTimer();
    }

    // ─────────────────────────────────────────────
    //  USER ACTIVITY TRACKING（用於 tab 重載 idle 偵測）
    // ─────────────────────────────────────────────
    let _lastInteractionTime = Date.now();
    (function trackUserActivity() {
        // mousemove 每秒幾十次，加 throttle 限制每 1 秒最多更新一次
        let _moveThrottle = false;
        const onMove = () => {
            if (_moveThrottle) return;
            _moveThrottle = true;
            _lastInteractionTime = Date.now();
            setTimeout(() => { _moveThrottle = false; }, 1000);
        };
        const update = () => { _lastInteractionTime = Date.now(); };
        document.addEventListener('mousemove',  onMove,  { passive: true });
        document.addEventListener('keydown',    update,  { passive: true });
        document.addEventListener('mousedown',  update,  { passive: true });
        document.addEventListener('scroll',     update,  { passive: true });
        document.addEventListener('touchstart', update,  { passive: true });
    })();

    // ─────────────────────────────────────────────
    //  TAB REFRESH TIMER
    // ─────────────────────────────────────────────
    function stopTabRefreshTimer() {
        if (state.tabRefreshTimer) { clearTimeout(state.tabRefreshTimer); state.tabRefreshTimer = null; }
    }

    function startTabRefreshTimer() {
        stopTabRefreshTimer();
        const secs = config.tab_refresh[PAGE.key] || 0;
        if (secs <= 0) return;
        // 加入最多 5 秒隨機 jitter，避免多個 tab 同時重載
        const jitter = Math.random() * 5000;

        state.tabRefreshTimer = setTimeout(function waitForIdleAndReload() {
            state.tabRefreshTimer = null;
            // tab 在背景，或使用者已停止互動超過 30 秒 → 立即重載（使用者感受不到卡頓）
            const isHidden = document.hidden;
            const isIdle   = Date.now() - _lastInteractionTime > 30000;
            if (isHidden || isIdle) {
                location.reload();
            } else {
                // 使用者仍在操作，每 5 秒重新檢查一次，直到閒置為止
                state.tabRefreshTimer = setTimeout(waitForIdleAndReload, 5000);
            }
        }, secs * 1000 + jitter);
    }

    // ─────────────────────────────────────────────
    //  DOM UTILITIES
    // ─────────────────────────────────────────────

    /** Wait for element matching selector (up to maxMs ms). */
    function waitForElement(selector, maxMs = 8000) {
        return new Promise((resolve) => {
            const el = document.querySelector(selector);
            if (el) { resolve(el); return; }
            const deadline = Date.now() + maxMs;
            const iv = setInterval(() => {
                const found = document.querySelector(selector);
                if (found) { clearInterval(iv); resolve(found); return; }
                if (Date.now() >= deadline) { clearInterval(iv); resolve(null); }
            }, 300);
        });
    }

    /**
     * 讀取頁面文字前先 yield 主執行緒，讓瀏覽器刷新待渲染的幀。
     * 只讀取主要內容區域（main / #root），跳過 DataDog RUM、Intercom 等
     * 第三方注入的大量隱藏 DOM 節點，避免讀取整個 React DOM 樹（可能超過 10MB）
     * 造成主執行緒同步阻塞。
     */
    async function readPageText() {
        await new Promise(r => setTimeout(r, 0));
        const container = document.querySelector('main')
            || document.querySelector('[role="main"]')
            || document.querySelector('#root')
            || document.querySelector('#__next')
            || document.body;
        return container.textContent;
    }

    /** Extract text block between two marker strings. */
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
        // Wait for a billing-specific element; fall back to generic after 10s
        await waitForElement('[data-testid], .billing-overview, section', 10000);
        // OpenAI billing page loads numbers via React — wait longer to ensure data is rendered
        await new Promise(r => setTimeout(r, 3000));

        const data = { source: 'openai_billing' };
        const t = await readPageText();

        // Credit balance
        for (const p of [
            /Credit\s+balance[\s\S]{0,40}\$([\d,]+(?:\.\d{2})?)/i,
            /\$([\d,]+\.\d{2})\s*(?:USD)?\s*(?:credit|balance)/i,
            /balance[^\$]{0,30}\$([\d,]+\.\d{2})/i,
        ]) {
            const m = t.match(p);
            if (m) { data.balance_usd = parseFloat(m[1].replace(',', '')); break; }
        }

        // Credits used vs total
        const gm = t.match(/([\d,]+(?:\.\d{2,})?)\s*(?:of|\/)\s*([\d,]+(?:\.\d{2,})?)\s*(?:credits?|used)/i);
        if (gm) {
            data.credits_used_usd  = parseFloat(gm[1].replace(',', ''));
            data.credits_total_usd = parseFloat(gm[2].replace(',', ''));
        }

        // Hard/monthly limit
        for (const p of [
            /(?:hard\s+limit|monthly\s+limit|spend\s+limit)[^\$]{0,40}\$([\d,]+(?:\.\d{2})?)/i,
            /\$([\d,]+(?:\.\d{2})?)\s*(?:hard\s+limit|spend\s+limit)/i,
        ]) {
            const m = t.match(p);
            if (m) { data.hard_limit_usd = parseFloat(m[1].replace(',', '')); break; }
        }

        // Soft limit
        const sm = t.match(/(?:soft\s+limit|email\s+alert)[^\$]{0,40}\$([\d,]+(?:\.\d{2})?)/i);
        if (sm) data.soft_limit_usd = parseFloat(sm[1].replace(',', ''));

        // This month usage
        const um = t.match(/\$([\d,]+\.\d{2,4})\s*(?:this\s*month|current\s*period)/i)
            || t.match(/(?:this\s*month|current\s*period)[^\$]{0,30}\$([\d,]+\.\d{2,4})/i);
        if (um) data.month_usage_usd = parseFloat(um[1].replace(',', ''));

        // Tier
        const tier = t.match(/(?:usage\s+tier|tier)[:\s]+(\w[\w\s-]{0,20})/i);
        if (tier) data.tier = tier[1].trim();

        // Auto-recharge
        if (/auto.?recharge\s*(?:is\s*)?on/i.test(t)) data.auto_recharge = true;

        // If only balance_usd was found (possibly $0 placeholder before React render),
        // retry once after extra delay to ensure full page load
        const dataKeys = Object.keys(data).filter(k => k !== 'source');
        if (dataKeys.length <= 1 && data.balance_usd === 0) {
            await new Promise(r => setTimeout(r, 3000));
            const t2 = await readPageText();
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
        const t = await readPageText();

        // ── Current session ──
        const sess = findSectionText(t, 'Current session', 'Weekly limits')
            || findSectionText(t, 'Plan usage limits', 'Weekly limits');
        if (sess) {
            const p = sess.match(/(\d+)%\s*used/i);
            if (p) data.session_percent = parseInt(p[1]);
            const r = sess.match(/Resets?\s+in\s+((?:\d+\s*hr?s?\s*)?(?:\d+\s*min?s?)?)/i);
            if (r) data.session_reset = r[1].trim();
        }

        // ── Weekly limits ──
        const wkly = findSectionText(t, 'Weekly limits', 'Extra usage');
        if (wkly) {
            const p = wkly.match(/(\d+)%\s*used/i);
            if (p) data.weekly_percent = parseInt(p[1]);
            const r = wkly.match(/Resets?\s+in\s+((?:\d+\s*hr?s?\s*)?(?:\d+\s*min?s?)?)/i);
            if (r) data.weekly_reset = r[1].trim();
        }

        // ── Extra usage ──
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

            // Extra usage percent (e.g. "6% used")
            const ep = extra.match(/(\d+)%\s*used/i);
            if (ep) data.extra_percent = parseInt(ep[1]);

            // Auto-reload status
            if (/auto.?reload\s+on/i.test(extra)) data.auto_reload = true;
            else if (/auto.?reload\s+off/i.test(extra)) data.auto_reload = false;

            // extra_enabled: 有資料就視為已開啟，不依賴 DOM toggle selector
            data.extra_enabled = !!(data.extra_spent !== undefined || data.extra_balance !== undefined || data.extra_limit !== undefined);
        }

        // Fallback: scan full body for percentages
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
        const t = await readPageText();

        // Plan
        const pm = t.match(/(?:Current\s+)?[Pp]lan[:\s]+([^\n\r]{1,40})/i)
            || t.match(/(Pro|Team|Enterprise|Developer|Free|Scale)\s+plan/i);
        if (pm) data.plan = pm[1].trim();

        // Next billing date
        const bd = t.match(/(?:next\s+billing|renews?)[^\d]{0,30}(\w+ \d{1,2},? \d{4})/i);
        if (bd) data.next_billing = bd[1].trim();

        // Monthly amount
        const am = t.match(/\$([\d.]+)\s*\/\s*(?:month|mo)/i)
            || t.match(/\$([\d.]+)\s*per\s+month/i);
        if (am) data.monthly_usd = parseFloat(am[1]);

        // Current usage
        const um = t.match(/(?:usage|this\s+month)[^\$]{0,30}\$([\d.]+)/i);
        if (um) data.this_month_usd = parseFloat(um[1]);

        // Balance — prefer DOM element [data-testid="credit-balance"] which contains
        // the "Remaining Balance" card (e.g. US$1.38), fall back to text regex.
        const creditBalanceCard = document.querySelector('[data-testid="credit-balance"]');
        if (creditBalanceCard) {
            const balText = creditBalanceCard.innerText || '';
            const bm = balText.match(/US\$\s*([\d,]+(?:\.\d+)?)/i)
                || balText.match(/\$([\d,]+(?:\.\d+)?)/);
            if (bm) data.balance_usd = parseFloat(bm[1].replace(/,/g, ''));
        }
        if (data.balance_usd === undefined) {
            // Fallback: look for "Remaining Balance" label proximity in full text
            const rb = t.match(/(?:US)?\$([\d,]+(?:\.\d+)?)\s*[\n\r\s]*Remaining\s+Balance/i)
                || t.match(/Remaining\s+Balance[\s\S]{0,30}(?:US)?\$([\d,]+(?:\.\d+)?)/i);
            if (rb) data.balance_usd = parseFloat(rb[1].replace(/,/g, ''));
        }

        // Spend limit
        const sl = t.match(/(?:spend|credit)\s+limit[^\$]{0,30}\$([\d.]+)/i);
        if (sl) data.spend_limit_usd = parseFloat(sl[1]);

        return data;
    }

    async function parseGitHubCopilot() {
        // 等待 included-premium-requests-card 出現（React 頁面）
        await waitForElement('[data-testid="included-premium-requests-card"]', 10000);
        await new Promise(r => setTimeout(r, 800));

        const data = { source: 'github_copilot' };

        // ── Included premium requests consumed (726.59) ──
        const inclCard = document.querySelector('[data-testid="included-premium-requests-card"]');
        if (inclCard) {
            // 大數字：class 含 cardValue
            const valEl = inclCard.querySelector('[class*="cardValue"]');
            if (valEl) {
                data.included_consumed = parseFloat(valEl.textContent.trim().replace(/,/g, ''));
            }
            // 額度：class 含 entitlementText，內文 "of\n1,500\nincluded"
            const entEl = inclCard.querySelector('[class*="entitlementText"]');
            if (entEl) {
                const nums = entEl.textContent.replace(/,/g, '').match(/[\d.]+/g);
                if (nums && nums.length > 0) {
                    data.included_total = parseFloat(nums[0]);
                }
            }
            // 計算百分比
            if (data.included_consumed !== undefined && data.included_total > 0) {
                data.included_percent = Math.round(data.included_consumed / data.included_total * 1000) / 10;
            }
        }

        // ── Billed premium requests ($0.00) ──
        const billedCard = document.querySelector('[data-testid="total-billed-amount-card"]');
        if (billedCard) {
            const billedEl = billedCard.querySelector('[class*="cardValue"]');
            if (billedEl) {
                const bm = billedEl.textContent.match(/[\d.]+/);
                if (bm) data.billed_usd = parseFloat(bm[0]);
            }
        }

        // ── 重置倒數（文字："resets in 5 days"）──
        const t = await readPageText();
        const rm = t.match(/resets?\s+in\s+(\d+)\s*days?/i)
            || t.match(/(\d+)\s*days?\s+(?:until\s+)?reset/i);
        if (rm) data.resets_in_days = parseInt(rm[1]);

        // ── 下次重置日（文字："resets in 5 days on 2026年3月1日"）──
        const nb = t.match(/resets?\s+in\s+\d+\s*days?\s+on\s+([^\n.]+)/i);
        if (nb) data.next_billing = nb[1].trim();

        return data;
    }

    // ─────────────────────────────────────────────
    //  MAIN EXTRACTION ENTRY
    // ─────────────────────────────────────────────
    let _extractionInProgress = false;

    async function runExtraction() {
        if (_extractionInProgress) {
            console.log('[AI Monitor] 上次擷取仍在進行中，略過');
            return;
        }
        if (state.status === 'stopped') return;
        // Guard: only run when still on the expected page (SPA navigation may have left)
        if (!isOnExpectedPage()) {
            console.log('[AI Monitor] 跳轉到其他頁面，略過擷取 (path:', location.pathname, ')');
            return;
        }
        _extractionInProgress = true;
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
            _extractionInProgress = false;
            setStatus('error', err.message);
            console.error('[AI Monitor]', err);
            return;
        }
        _extractionInProgress = false;

        parsedData.timestamp = new Date().toISOString();
        parsedData.page_url  = location.href;

        // ── 比較數值是否有變動，只在有變化時才傳送（GUI refresh 強制傳送）──
        const SKIP_KEYS = new Set(['source', 'timestamp', 'page_url']);
        const prev = state.lastData;
        const hasChange = state.forceSend || !prev || Object.keys(parsedData).some(k => {
            if (SKIP_KEYS.has(k)) return false;
            return parsedData[k] !== prev[k];
        });
        state.forceSend = false;

        state.lastData = parsedData;
        updateDataPreview(parsedData);

        if (hasChange) {
            sendToServer(parsedData);
        } else {
            console.log('[AI Monitor] 數值無變化，略過傳送');
            setStatus('success');
        }
    }

    // ─────────────────────────────────────────────
    //  SERVER COMMUNICATION
    // ─────────────────────────────────────────────
    function sendToServer(data) {
        // Guard: skip if data is effectively empty (only meta keys, no real values)
        const SKIP_KEYS = new Set(['source', 'timestamp', 'page_url']);
        const dataKeys = Object.keys(data).filter(k => !SKIP_KEYS.has(k));
        if (dataKeys.length === 0) {
            console.warn('[AI Monitor] 資料為空，略過傳送 (可能頁面尚未載入)');
            setStatus('error', '頁面資料為空，請確認已在正確頁面');
            return;
        }
        GM_xmlhttpRequest({
            method:  'POST',
            url:     `${config.server_url}/update`,
            headers: {
                'Content-Type': 'application/json',
                'X-AI-Monitor-Client': '1',
            },
            data:    JSON.stringify(data),
            timeout: 5000,
            onload(resp) {
                if (resp.status >= 200 && resp.status < 300) {
                    state.lastSent = Date.now();
                    setStatus('success');
                    console.log('[AI Monitor] ✓ 傳送成功', data.source);
                } else {
                    setStatus('error', `伺服器 ${resp.status}`);
                    console.warn('[AI Monitor] 傳送失敗', resp.status);
                }
            },
            onerror() {
                setStatus('error', '無法連線（桌面程式是否已執行？）');
            },
            ontimeout() {
                setStatus('error', '連線逾時');
            },
        });
    }

    // ─────────────────────────────────────────────
    //  SPA NAVIGATION DETECTION
    // ─────────────────────────────────────────────
    // 每 2 秒輕量輪詢 URL，完全不監聽 DOM 變動，不干擾頁面運作
    let _lastHref = location.href;
    setInterval(() => {
        if (location.href === _lastHref) return;
        _lastHref = location.href;
        if (isOnExpectedPage()) {
            setTimeout(runExtraction, 2500);
        } else {
            console.log('[AI Monitor] SPA 跳轉離開目標頁面，停止擷取');
        }
    }, 2000);

    // ─────────────────────────────────────────────
    //  STARTUP
    // ─────────────────────────────────────────────
    setStatus('idle');

    // ─────────────────────────────────────────────
    //  GUI REFRESH COMMAND POLL
    // ─────────────────────────────────────────────
    (function startPollLoop() {
        let knownSeq = 0;
        const POLL_INTERVAL = 3000; // ms
        const POLL_MAX_BACKOFF = 60000; // ms — 伺服器找不到時最大間隔
        let _pollErrCount = 0;

        function poll() {
            if (state.status === 'stopped') {
                setTimeout(poll, POLL_INTERVAL);
                return;
            }
            GM_xmlhttpRequest({
                method: 'GET',
                url: `${config.server_url}/poll?seq=${knownSeq}`,
                timeout: 4000,
                onload(res) {
                    _pollErrCount = 0;
                    try {
                        const json = JSON.parse(res.responseText);
                        if (json.refresh && json.seq !== knownSeq) {
                            knownSeq = json.seq;
                            console.log('[AI Monitor] 收到 GUI 重新整理指令，立即擷取');
                            state.forceSend = true;
                            runExtraction();
                        } else {
                            knownSeq = json.seq;
                        }
                    } catch (_) {}
                    setTimeout(poll, POLL_INTERVAL);
                },
                onerror() {
                    _pollErrCount++;
                    const delay = Math.min(POLL_INTERVAL * Math.pow(2, _pollErrCount - 1), POLL_MAX_BACKOFF);
                    setTimeout(poll, delay);
                },
                ontimeout(){ setTimeout(poll, POLL_INTERVAL); },
            });
        }

        setTimeout(poll, POLL_INTERVAL);
    })();

    // 等頁面完全載入後，再等 2.5 秒讓 React 完成渲染，才開始擷取
    function _startWork() {
        console.log(`[AI Monitor] 已啟動 — ${PAGE.label} | 間隔: ${config.intervals[PAGE.key]}s | 頁面重刷: ${config.tab_refresh[PAGE.key]}s | 伺服器: ${config.server_url}`);
        startTabRefreshTimer();
        setTimeout(() => {
            runExtraction();
            startTimer();
        }, 2500);
    }

    if (document.readyState === 'complete') {
        _startWork();
    } else {
        window.addEventListener('load', _startWork);
    }

})();