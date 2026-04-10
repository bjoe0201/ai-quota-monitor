// ==UserScript==
// @name         AI Quota Monitor Client (DEBUG)
// @namespace    https://github.com/ai-quota-monitor
// @version      2.3.0-debug
// @description  分段除錯版 — 依序調高 DEBUG_PHASE (0→8) 來定位卡頓
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

    // ╔══════════════════════════════════════════════════════════╗
    // ║  🔧 DEBUG 控制：把數字從 0 逐步調到 8 來測試每個階段     ║
    // ║                                                          ║
    // ║  Phase 0 — 頁面辨識 + Config + State（純資料，無 DOM）   ║
    // ║  Phase 1 — CSS 樣式 + UI 建立（插入 DOM）                ║
    // ║  Phase 2 — UI 事件綁定 + 狀態 helper + Toast             ║
    // ║  Phase 3 — Timer 管理 + 使用者活動追蹤 + Tab 重刷        ║
    // ║  Phase 4 — DOM 工具（waitForElement / takePageSnapshot） ║
    // ║  Phase 5 — 頁面解析器（4 個 parser）                     ║
    // ║  Phase 6 — 伺服器通訊 + 擷取主函式                       ║
    // ║  Phase 7 — SPA 偵測 + GUI poll 輪詢                      ║
    // ║  Phase 8 — 啟動（觸發首次擷取 + 啟動 timer）            ║
    // ╚══════════════════════════════════════════════════════════╝
    const DEBUG_PHASE = 8;

    const _t_boot = performance.now();
    const _dbg = (phase, tag, msg, ...args) => {
        const elapsed = (performance.now() - _t_boot).toFixed(1);
        console.log(`[AIMon-DBG P${phase}] [+${elapsed}ms] [${tag}] ${msg}`, ...args);
    };

    _dbg(0, 'BOOT', `✅ 腳本載入，DEBUG_PHASE = ${DEBUG_PHASE}`);

    // ═══════════════════════════════════════════════
    //  PHASE 0 — 頁面辨識 + Config + State
    // ═══════════════════════════════════════════════
    console.time('[AIMon] Phase 0: 頁面辨識+Config+State');

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
    if (!PAGE) {
        _dbg(0, 'BOOT', '❌ 不在已知頁面，腳本終止');
        console.timeEnd('[AIMon] Phase 0: 頁面辨識+Config+State');
        return;
    }

    _dbg(0, 'PAGE', `辨識為: ${PAGE.label} (key=${PAGE.key})`);

    function isOnExpectedPage() {
        return location.pathname.startsWith(PAGE.expectedPath);
    }

    // ── Config ──
    const CFG_KEY = 'aimon_config';

    function loadConfig() {
        _dbg(0, 'CONFIG', '讀取 GM_getValue...');
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
        if (!raw) {
            _dbg(0, 'CONFIG', '無已存設定，使用預設值');
            return defaults;
        }
        try {
            const saved = JSON.parse(raw);
            saved.intervals = Object.assign({}, defaults.intervals, saved.intervals || {});
            saved.enabled = Object.assign({}, defaults.enabled, saved.enabled || {});
            saved.tab_refresh = Object.assign({}, defaults.tab_refresh, saved.tab_refresh || {});
            _dbg(0, 'CONFIG', '已載入設定', saved);
            return Object.assign({}, defaults, saved);
        } catch (_) {
            _dbg(0, 'CONFIG', '⚠️ 設定 JSON 解析失敗，使用預設值');
            return defaults;
        }
    }

    function saveConfig(cfg) {
        GM_setValue(CFG_KEY, JSON.stringify(cfg));
        _dbg(0, 'CONFIG', '設定已儲存');
    }

    let config = loadConfig();

    // ── State ──
    let state = {
        status: 'idle',
        lastSent: null,
        lastData: null,
        errorMsg: '',
        timer: null,
        tabRefreshTimer: null,
        forceSend: false,
    };

    _dbg(0, 'STATE', '初始狀態已建立');
    console.timeEnd('[AIMon] Phase 0: 頁面辨識+Config+State');

    if (DEBUG_PHASE < 1) {
        _dbg(0, 'STOP', '🛑 DEBUG_PHASE=0，到此為止');
        return;
    }

    // ═══════════════════════════════════════════════
    //  PHASE 1 — CSS 樣式 + UI 建立
    // ═══════════════════════════════════════════════
    console.time('[AIMon] Phase 1: CSS+UI建立');
    _dbg(1, 'STYLE', '注入 GM_addStyle...');

    GM_addStyle(`
        #aimon-root * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
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

    _dbg(1, 'STYLE', '✅ CSS 注入完成');

    _dbg(1, 'UI', '建立浮動按鈕 + 面板...');
    const btn = document.createElement('div');
    btn.id = 'aimon-btn';
    btn.title = 'AI Quota Monitor';
    btn.innerHTML = `<span class="aimon-icon">📊</span><span class="aimon-dot idle"></span>`;

    const panel = document.createElement('div');
    panel.id = 'aimon-panel';
    panel.innerHTML = `
        <div class="aimon-header">
            <span class="aimon-header-title">📊 AI Quota Monitor <span style="font-size:10px; color:#6c7086; font-weight:400;">v${GM_info.script.version}-DBG</span></span>
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
            <div class="aimon-label">🔧 DEBUG Phase = ${DEBUG_PHASE}</div>
            <div style="font-size:11px; color:#f9e2af; padding:4px;">Phase 0=Config | 1=UI | 2=Events | 3=Timers | 4=DOM工具 | 5=Parser | 6=通訊 | 7=Poll | 8=啟動</div>
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

    _dbg(1, 'UI', '將 btn + panel 插入 DOM...');
    const t_dom0 = performance.now();
    document.body.appendChild(btn);
    document.body.appendChild(panel);
    _dbg(1, 'UI', `✅ DOM 插入完成 (${(performance.now() - t_dom0).toFixed(1)}ms)`);

    // ── Quick-open buttons ──
    _dbg(1, 'UI', '建立快速開啟按鈕...');
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
    _dbg(1, 'UI', '✅ 快速開啟按鈕完成');

    console.timeEnd('[AIMon] Phase 1: CSS+UI建立');

    if (DEBUG_PHASE < 2) {
        _dbg(1, 'STOP', '🛑 DEBUG_PHASE=1，到此為止（可看到浮動按鈕）');
        return;
    }

    // ═══════════════════════════════════════════════
    //  PHASE 2 — UI 事件 + 狀態 helper + Toast
    // ═══════════════════════════════════════════════
    console.time('[AIMon] Phase 2: UI事件+狀態');
    _dbg(2, 'EVENTS', '綁定 UI 事件...');

    // ── Status helpers ──
    function setStatus(status, msg) {
        _dbg(2, 'STATUS', `→ ${status}${msg ? ' : ' + msg : ''}`);
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
        const preview = Object.entries(data)
            .filter(([k]) => !['source', 'timestamp', 'page_url'].includes(k))
            .map(([k, v]) => `${k}: ${v}`)
            .join('\n');
        el.textContent = preview || '（無可顯示的資料）';
    }

    // ── Toast ──
    function showToast(msg) {
        _dbg(2, 'TOAST', msg);
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

    // ── UI events ──
    btn.addEventListener('click', () => {
        _dbg(2, 'EVENT', '浮動按鈕被點擊');
        panel.classList.toggle('visible');
    });

    document.getElementById('aimon-close-btn').addEventListener('click', () => {
        panel.classList.remove('visible');
    });

    document.getElementById('aimon-run-btn').addEventListener('click', () => {
        _dbg(2, 'EVENT', '「立即擷取」按鈕被點擊');
        panel.classList.remove('visible');
        if (typeof runExtraction === 'function') runExtraction();
        else _dbg(2, 'EVENT', '⚠️ runExtraction 尚未定義（Phase 不夠高）');
    });

    document.getElementById('aimon-stop-btn').addEventListener('click', () => {
        _dbg(2, 'EVENT', '「停止」按鈕被點擊');
        if (typeof stopTimer === 'function') stopTimer();
        setStatus('stopped', '手動停止');
    });

    document.getElementById('aimon-save-btn').addEventListener('click', () => {
        _dbg(2, 'EVENT', '「儲存」按鈕被點擊');
        const interval = parseInt(document.getElementById('aimon-interval-input').value, 10) || 60;
        const tabRefresh = Math.max(0, Math.min(600, parseInt(document.getElementById('aimon-tab-refresh-input').value, 10) || 0));
        const server_url = (document.getElementById('aimon-server-input').value || '').trim()
            || 'http://localhost:7890';
        config.intervals[PAGE.key] = interval;
        config.tab_refresh[PAGE.key] = tabRefresh;
        config.server_url = server_url;
        saveConfig(config);
        if (typeof restartTimer === 'function') restartTimer();
        if (typeof startTabRefreshTimer === 'function') startTabRefreshTimer();
        showToast('✓ 設定已儲存');
    });

    document.addEventListener('click', (e) => {
        if (!panel.contains(e.target) && !btn.contains(e.target)) {
            panel.classList.remove('visible');
        }
    }, true);

    _dbg(2, 'EVENTS', '✅ UI 事件綁定完成');
    console.timeEnd('[AIMon] Phase 2: UI事件+狀態');

    if (DEBUG_PHASE < 3) {
        _dbg(2, 'STOP', '🛑 DEBUG_PHASE=2，到此為止（可開關面板）');
        setStatus('idle');
        return;
    }

    // ═══════════════════════════════════════════════
    //  PHASE 3 — Timer 管理 + User Activity + Tab Refresh
    // ═══════════════════════════════════════════════
    console.time('[AIMon] Phase 3: Timer+Activity');
    _dbg(3, 'TIMER', '設定 timer 管理函式...');

    function stopTimer() {
        if (state.timer) {
            clearInterval(state.timer);
            state.timer = null;
            _dbg(3, 'TIMER', '擷取 timer 已停止');
        }
    }

    function startTimer() {
        stopTimer();
        const ms = (config.intervals[PAGE.key] || 60) * 1000;
        _dbg(3, 'TIMER', `啟動擷取 timer，間隔 ${ms}ms`);
        state.timer = setInterval(() => {
            _dbg(3, 'TIMER', '⏰ timer 觸發 runExtraction');
            if (typeof runExtraction === 'function') runExtraction();
        }, ms);
    }

    function restartTimer() {
        if (state.status !== 'stopped') startTimer();
    }

    // ── User activity tracking ──
    _dbg(3, 'ACTIVITY', '設定使用者活動追蹤...');
    let _lastInteractionTime = Date.now();
    let _activityEventCount = 0;

    (function trackUserActivity() {
        let _moveThrottle = false;
        const onMove = () => {
            if (_moveThrottle) return;
            _moveThrottle = true;
            _lastInteractionTime = Date.now();
            _activityEventCount++;
            setTimeout(() => { _moveThrottle = false; }, 1000);
        };
        const update = () => {
            _lastInteractionTime = Date.now();
            _activityEventCount++;
        };
        document.addEventListener('mousemove',  onMove,  { passive: true });
        document.addEventListener('keydown',    update,  { passive: true });
        document.addEventListener('mousedown',  update,  { passive: true });
        document.addEventListener('scroll',     update,  { passive: true });
        document.addEventListener('touchstart', update,  { passive: true });
        _dbg(3, 'ACTIVITY', '✅ 5 個事件監聽器已註冊（mousemove 有 1s throttle）');

        // 每 30 秒報告一次活動量
        setInterval(() => {
            _dbg(3, 'ACTIVITY', `近 30 秒活動事件數: ${_activityEventCount}`);
            _activityEventCount = 0;
        }, 30000);
    })();

    // ── Tab refresh timer ──
    _dbg(3, 'TAB-REFRESH', '設定 tab 自動重刷...');

    function stopTabRefreshTimer() {
        if (state.tabRefreshTimer) {
            clearTimeout(state.tabRefreshTimer);
            state.tabRefreshTimer = null;
            _dbg(3, 'TAB-REFRESH', 'timer 已停止');
        }
    }

    function startTabRefreshTimer() {
        stopTabRefreshTimer();
        const secs = config.tab_refresh[PAGE.key] || 0;
        if (secs <= 0) {
            _dbg(3, 'TAB-REFRESH', '已停用（設定值=0）');
            return;
        }
        const jitter = Math.random() * 5000;
        _dbg(3, 'TAB-REFRESH', `啟動，${secs}s + jitter ${jitter.toFixed(0)}ms`);

        state.tabRefreshTimer = setTimeout(function waitForIdleAndReload() {
            state.tabRefreshTimer = null;
            const isHidden = document.hidden;
            const isIdle   = Date.now() - _lastInteractionTime > 30000;
            _dbg(3, 'TAB-REFRESH', `檢查 idle: hidden=${isHidden}, idle=${isIdle}`);
            if (isHidden || isIdle) {
                _dbg(3, 'TAB-REFRESH', '🔄 執行 location.reload()');
                location.reload();
            } else {
                _dbg(3, 'TAB-REFRESH', '使用者仍在操作，5 秒後重檢');
                state.tabRefreshTimer = setTimeout(waitForIdleAndReload, 5000);
            }
        }, secs * 1000 + jitter);
    }

    _dbg(3, 'TIMER', '✅ 所有 timer 函式已定義');
    console.timeEnd('[AIMon] Phase 3: Timer+Activity');

    if (DEBUG_PHASE < 4) {
        _dbg(3, 'STOP', '🛑 DEBUG_PHASE=3，到此為止（timer 已定義但未啟動）');
        setStatus('idle');
        return;
    }

    // ═══════════════════════════════════════════════
    //  PHASE 4 — DOM 工具函式
    // ═══════════════════════════════════════════════
    console.time('[AIMon] Phase 4: DOM工具');
    _dbg(4, 'DOM', '定義 waitForElement / takePageSnapshot...');

    function waitForElement(selector, maxMs = 8000) {
        _dbg(4, 'DOM', `waitForElement("${selector}", ${maxMs}ms)...`);
        return new Promise((resolve) => {
            const el = document.querySelector(selector);
            if (el) {
                _dbg(4, 'DOM', `waitForElement: 立即找到 "${selector}"`);
                resolve(el);
                return;
            }
            const deadline = Date.now() + maxMs;
            const iv = setInterval(() => {
                const found = document.querySelector(selector);
                if (found) {
                    clearInterval(iv);
                    _dbg(4, 'DOM', `waitForElement: 找到 "${selector}" (耗時 ${maxMs - (deadline - Date.now())}ms)`);
                    resolve(found);
                    return;
                }
                if (Date.now() >= deadline) {
                    clearInterval(iv);
                    _dbg(4, 'DOM', `waitForElement: ⚠️ 逾時未找到 "${selector}"`);
                    resolve(null);
                }
            }, 300);
        });
    }

    async function takePageSnapshot() {
        _dbg(4, 'SNAPSHOT', '開始快照...');
        const t_snap0 = performance.now();
        await new Promise(r => setTimeout(r, 0)); // yield to main thread

        const t_sel0 = performance.now();
        const container = document.querySelector('main')
            || document.querySelector('[role="main"]')
            || document.querySelector('#root')
            || document.querySelector('#__next')
            || document.body;
        const t_sel1 = performance.now();
        _dbg(4, 'SNAPSHOT', `querySelector 容器: <${container.tagName}> (${(t_sel1 - t_sel0).toFixed(1)}ms)`);

        const t_clone0 = performance.now();
        const snap = document.createElement('div');
        snap.innerHTML = container.innerHTML;  // ⚠️ 這裡是最可能的效能瓶頸
        const t_clone1 = performance.now();
        const cloneMs = (t_clone1 - t_clone0).toFixed(1);
        _dbg(4, 'SNAPSHOT', `innerHTML 複製: ${cloneMs}ms ⚠️${cloneMs > 100 ? ' 🔴 過慢！' : cloneMs > 50 ? ' 🟡 稍慢' : ' 🟢 正常'}`);

        const t_text0 = performance.now();
        const textLen = snap.textContent.length;
        const t_text1 = performance.now();
        _dbg(4, 'SNAPSHOT', `textContent 長度: ${textLen} 字元 (${(t_text1 - t_text0).toFixed(1)}ms)`);

        const totalMs = (performance.now() - t_snap0).toFixed(1);
        _dbg(4, 'SNAPSHOT', `✅ 快照完成，總計 ${totalMs}ms`);
        return snap;
    }

    function findSectionText(fullText, startMarker, endMarker) {
        const si = fullText.indexOf(startMarker);
        if (si === -1) return null;
        if (!endMarker) return fullText.substring(si);
        const ei = fullText.indexOf(endMarker, si + startMarker.length);
        return ei === -1 ? fullText.substring(si) : fullText.substring(si, ei);
    }

    _dbg(4, 'DOM', '✅ DOM 工具定義完成');
    console.timeEnd('[AIMon] Phase 4: DOM工具');

    if (DEBUG_PHASE < 5) {
        _dbg(4, 'STOP', '🛑 DEBUG_PHASE=4，到此為止（DOM 工具已定義）');
        setStatus('idle');
        return;
    }

    // ═══════════════════════════════════════════════
    //  PHASE 5 — 頁面解析器
    // ═══════════════════════════════════════════════
    console.time('[AIMon] Phase 5: Parsers');
    _dbg(5, 'PARSER', '定義 4 個 parser...');

    async function parseOpenAIBilling() {
        _dbg(5, 'PARSE-OPENAI', '▶ 開始');
        const t0 = performance.now();

        _dbg(5, 'PARSE-OPENAI', '等待 billing 元素...');
        await waitForElement('[data-testid], .billing-overview, section', 10000);
        _dbg(5, 'PARSE-OPENAI', `waitForElement 完成 (${(performance.now() - t0).toFixed(0)}ms)`);

        _dbg(5, 'PARSE-OPENAI', '等待 React 渲染 3s...');
        await new Promise(r => setTimeout(r, 3000));
        _dbg(5, 'PARSE-OPENAI', `React delay 完成 (${(performance.now() - t0).toFixed(0)}ms)`);

        const data = { source: 'openai_billing' };
        const snap = await takePageSnapshot();
        const t = snap.textContent;

        _dbg(5, 'PARSE-OPENAI', '開始 regex 解析...');
        const t_regex0 = performance.now();

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

        _dbg(5, 'PARSE-OPENAI', `regex 解析完成 (${(performance.now() - t_regex0).toFixed(1)}ms)`);

        const dataKeys = Object.keys(data).filter(k => k !== 'source');
        if (dataKeys.length <= 1 && data.balance_usd === 0) {
            _dbg(5, 'PARSE-OPENAI', '⚠️ 資料不足，3 秒後重試...');
            await new Promise(r => setTimeout(r, 3000));
            const snap2 = await takePageSnapshot();
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

        _dbg(5, 'PARSE-OPENAI', `✅ 完成，總耗時 ${(performance.now() - t0).toFixed(0)}ms`, data);
        return data;
    }

    async function parseClaudeUsage() {
        _dbg(5, 'PARSE-CLAUDE-USAGE', '▶ 開始');
        const t0 = performance.now();

        await waitForElement('main, h1, [data-testid]', 6000);
        _dbg(5, 'PARSE-CLAUDE-USAGE', `waitForElement (${(performance.now() - t0).toFixed(0)}ms)`);

        await new Promise(r => setTimeout(r, 1800));
        _dbg(5, 'PARSE-CLAUDE-USAGE', `React delay (${(performance.now() - t0).toFixed(0)}ms)`);

        const data = { source: 'claude_usage' };
        const snap = await takePageSnapshot();
        const t = snap.textContent;

        _dbg(5, 'PARSE-CLAUDE-USAGE', '開始 regex 解析...');
        const t_regex0 = performance.now();

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

        _dbg(5, 'PARSE-CLAUDE-USAGE', `regex (${(performance.now() - t_regex0).toFixed(1)}ms)`);
        _dbg(5, 'PARSE-CLAUDE-USAGE', `✅ 完成 (${(performance.now() - t0).toFixed(0)}ms)`, data);
        return data;
    }

    async function parseClaudeBilling() {
        _dbg(5, 'PARSE-CLAUDE-BILLING', '▶ 開始');
        const t0 = performance.now();

        await waitForElement('[data-testid="credit-balance"], main, [data-testid]', 6000);
        await new Promise(r => setTimeout(r, 1800));

        const data = { source: 'claude_billing' };
        const snap = await takePageSnapshot();
        const t = snap.textContent;

        _dbg(5, 'PARSE-CLAUDE-BILLING', '開始 regex 解析...');
        const t_regex0 = performance.now();

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

        _dbg(5, 'PARSE-CLAUDE-BILLING', `regex (${(performance.now() - t_regex0).toFixed(1)}ms)`);
        _dbg(5, 'PARSE-CLAUDE-BILLING', `✅ 完成 (${(performance.now() - t0).toFixed(0)}ms)`, data);
        return data;
    }

    async function parseGitHubCopilot() {
        _dbg(5, 'PARSE-GITHUB', '▶ 開始');
        const t0 = performance.now();

        await waitForElement('[data-testid="included-premium-requests-card"]', 10000);
        _dbg(5, 'PARSE-GITHUB', `waitForElement (${(performance.now() - t0).toFixed(0)}ms)`);

        await new Promise(r => setTimeout(r, 800));

        const data = { source: 'github_copilot' };
        const snap = await takePageSnapshot();

        _dbg(5, 'PARSE-GITHUB', '解析 DOM 快照...');
        const t_parse0 = performance.now();

        const inclCard = snap.querySelector('[data-testid="included-premium-requests-card"]');
        if (inclCard) {
            const valEl = inclCard.querySelector('[class*="cardValue"]');
            if (valEl) {
                data.included_consumed = parseFloat(valEl.textContent.trim().replace(/,/g, ''));
            }
            const entEl = inclCard.querySelector('[class*="entitlementText"]');
            if (entEl) {
                const nums = entEl.textContent.replace(/,/g, '').match(/[\d.]+/g);
                if (nums && nums.length > 0) {
                    data.included_total = parseFloat(nums[0]);
                }
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

        _dbg(5, 'PARSE-GITHUB', `DOM 解析 (${(performance.now() - t_parse0).toFixed(1)}ms)`);
        _dbg(5, 'PARSE-GITHUB', `✅ 完成 (${(performance.now() - t0).toFixed(0)}ms)`, data);
        return data;
    }

    _dbg(5, 'PARSER', '✅ 4 個 parser 已定義');
    console.timeEnd('[AIMon] Phase 5: Parsers');

    if (DEBUG_PHASE < 6) {
        _dbg(5, 'STOP', '🛑 DEBUG_PHASE=5，到此為止（parser 已定義但未呼叫）');
        setStatus('idle');
        return;
    }

    // ═══════════════════════════════════════════════
    //  PHASE 6 — 伺服器通訊 + 擷取主函式
    // ═══════════════════════════════════════════════
    console.time('[AIMon] Phase 6: 通訊+擷取');
    _dbg(6, 'COMM', '定義 sendToServer + runExtraction...');

    function sendToServer(data) {
        const SKIP_KEYS = new Set(['source', 'timestamp', 'page_url']);
        const dataKeys = Object.keys(data).filter(k => !SKIP_KEYS.has(k));
        if (dataKeys.length === 0) {
            _dbg(6, 'SEND', '⚠️ 資料為空，略過傳送');
            setStatus('error', '頁面資料為空，請確認已在正確頁面');
            return;
        }
        _dbg(6, 'SEND', `傳送 ${data.source}，${dataKeys.length} 個欄位...`);
        const t_send0 = performance.now();

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
                _dbg(6, 'SEND', `回應 ${resp.status} (${(performance.now() - t_send0).toFixed(0)}ms)`);
                if (resp.status >= 200 && resp.status < 300) {
                    state.lastSent = Date.now();
                    setStatus('success');
                } else {
                    setStatus('error', `伺服器 ${resp.status}`);
                }
            },
            onerror() {
                _dbg(6, 'SEND', `❌ 連線失敗 (${(performance.now() - t_send0).toFixed(0)}ms)`);
                setStatus('error', '無法連線（桌面程式是否已執行？）');
            },
            ontimeout() {
                _dbg(6, 'SEND', `⏰ 連線逾時 (${(performance.now() - t_send0).toFixed(0)}ms)`);
                setStatus('error', '連線逾時');
            },
        });
    }

    let _extractionInProgress = false;

    // 暴露到外層 scope 供 Phase 2 的按鈕使用
    // （因為 Phase 2 用 typeof 檢查，這裡的 function 聲明不會 hoist 跨 block）
    window._aimon_runExtraction = runExtraction;

    async function runExtraction() {
        if (_extractionInProgress) {
            _dbg(6, 'EXTRACT', '⚠️ 上次擷取仍在進行中，略過');
            return;
        }
        if (state.status === 'stopped') {
            _dbg(6, 'EXTRACT', '⏸️ 狀態為 stopped，略過');
            return;
        }
        if (!isOnExpectedPage()) {
            _dbg(6, 'EXTRACT', `⚠️ 不在預期頁面 (path: ${location.pathname})，略過`);
            return;
        }

        _extractionInProgress = true;
        _dbg(6, 'EXTRACT', `▶ 開始擷取 (page: ${PAGE.key})`);
        const t_ext0 = performance.now();
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
            _dbg(6, 'EXTRACT', `❌ parser 拋出例外: ${err.message}`);
            setStatus('error', err.message);
            return;
        }
        _extractionInProgress = false;

        parsedData.timestamp = new Date().toISOString();
        parsedData.page_url  = location.href;

        // ── 比較數值是否有變動 ──
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
            _dbg(6, 'EXTRACT', `📤 有變更，傳送到伺服器`);
            sendToServer(parsedData);
        } else {
            _dbg(6, 'EXTRACT', `🟰 無變更，略過傳送`);
            setStatus('success');
        }

        _dbg(6, 'EXTRACT', `✅ 擷取流程結束 (${(performance.now() - t_ext0).toFixed(0)}ms)`);
    }

    // 讓 Phase 2 的按鈕能呼叫（覆寫型別檢查的 fallback）
    // 由於跨 block scope，我們透過覆寫 onclick
    document.getElementById('aimon-run-btn').onclick = () => {
        _dbg(2, 'EVENT', '「立即擷取」(Phase 6+)');
        panel.classList.remove('visible');
        runExtraction();
    };

    _dbg(6, 'COMM', '✅ 通訊+擷取函式已定義');
    console.timeEnd('[AIMon] Phase 6: 通訊+擷取');

    if (DEBUG_PHASE < 7) {
        _dbg(6, 'STOP', '🛑 DEBUG_PHASE=6，到此為止（可用 ▶ 按鈕手動擷取）');
        setStatus('idle');
        return;
    }

    // ═══════════════════════════════════════════════
    //  PHASE 7 — SPA 偵測 + GUI poll 輪詢
    // ═══════════════════════════════════════════════
    console.time('[AIMon] Phase 7: SPA+Poll');

    // ── SPA navigation detection ──
    _dbg(7, 'SPA', '啟動 URL 變化偵測 (每 2 秒)...');
    let _lastHref = location.href;
    let _spaCheckCount = 0;
    setInterval(() => {
        _spaCheckCount++;
        if (location.href === _lastHref) return;
        _lastHref = location.href;
        _dbg(7, 'SPA', `🔀 URL 變化偵測到: ${location.href} (第 ${_spaCheckCount} 次檢查)`);
        if (isOnExpectedPage()) {
            setTimeout(runExtraction, 2500);
        } else {
            _dbg(7, 'SPA', '已離開目標頁面');
        }
    }, 2000);

    // ── GUI refresh command poll ──
    _dbg(7, 'POLL', '啟動 GUI 指令輪詢...');
    let _pollCount = 0;
    let _pollErrorCount = 0;

    (function startPollLoop() {
        let knownSeq = 0;
        const POLL_INTERVAL = 3000;
        const POLL_MAX_BACKOFF = 60000;
        let _pollErrCount = 0;

        function poll() {
            if (state.status === 'stopped') {
                setTimeout(poll, POLL_INTERVAL);
                return;
            }
            _pollCount++;
            const t_poll0 = performance.now();

            GM_xmlhttpRequest({
                method: 'GET',
                url: `${config.server_url}/poll?seq=${knownSeq}`,
                timeout: 4000,
                onload(res) {
                    const pollMs = (performance.now() - t_poll0).toFixed(0);
                    _pollErrCount = 0;
                    try {
                        const json = JSON.parse(res.responseText);
                        if (json.refresh && json.seq !== knownSeq) {
                            knownSeq = json.seq;
                            _dbg(7, 'POLL', `🔔 收到重新整理指令 (seq=${json.seq}, ${pollMs}ms)`);
                            state.forceSend = true;
                            runExtraction();
                        } else {
                            knownSeq = json.seq;
                            // 每 10 次才印一次，避免刷屏
                            if (_pollCount % 10 === 0) {
                                _dbg(7, 'POLL', `心跳 #${_pollCount} OK (seq=${json.seq}, ${pollMs}ms)`);
                            }
                        }
                    } catch (_) {
                        _dbg(7, 'POLL', `⚠️ 回應解析失敗 (${pollMs}ms)`);
                    }
                    setTimeout(poll, POLL_INTERVAL);
                },
                onerror() {
                    _pollErrCount++;
                    _pollErrorCount++;
                    const delay = Math.min(POLL_INTERVAL * Math.pow(2, _pollErrCount - 1), POLL_MAX_BACKOFF);
                    _dbg(7, 'POLL', `❌ 連線失敗 #${_pollErrorCount} (下次 ${delay}ms 後)`);
                    setTimeout(poll, delay);
                },
                ontimeout() {
                    _dbg(7, 'POLL', `⏰ 逾時 (${(performance.now() - t_poll0).toFixed(0)}ms)`);
                    setTimeout(poll, POLL_INTERVAL);
                },
            });
        }

        setTimeout(poll, POLL_INTERVAL);
    })();

    _dbg(7, 'SPA+POLL', '✅ SPA 偵測 + GUI poll 已啟動');
    console.timeEnd('[AIMon] Phase 7: SPA+Poll');

    if (DEBUG_PHASE < 8) {
        _dbg(7, 'STOP', '🛑 DEBUG_PHASE=7，到此為止（有 poll 但不自動擷取）');
        setStatus('idle');
        return;
    }

    // ═══════════════════════════════════════════════
    //  PHASE 8 — 啟動（觸發首次擷取 + timer）
    // ═══════════════════════════════════════════════
    console.time('[AIMon] Phase 8: 啟動');
    _dbg(8, 'START', '初始化完全啟動流程...');

    setStatus('idle');

    function _startWork() {
        _dbg(8, 'START', `🚀 啟動 — ${PAGE.label} | 擷取間隔: ${config.intervals[PAGE.key]}s | 頁面重刷: ${config.tab_refresh[PAGE.key]}s | 伺服器: ${config.server_url}`);
        startTabRefreshTimer();
        setTimeout(() => {
            _dbg(8, 'START', '⚡ 觸發首次擷取...');
            runExtraction();
            startTimer();
            _dbg(8, 'START', '✅ 週期 timer 已啟動');
        }, 2500);
    }

    if (document.readyState === 'complete') {
        _dbg(8, 'START', 'document.readyState=complete，直接啟動');
        _startWork();
    } else {
        _dbg(8, 'START', `document.readyState=${document.readyState}，等待 load 事件`);
        window.addEventListener('load', _startWork);
    }

    console.timeEnd('[AIMon] Phase 8: 啟動');

    // ── 定期報告摘要 ──
    setInterval(() => {
        _dbg(8, 'HEARTBEAT', [
            `status=${state.status}`,
            `lastSent=${state.lastSent ? new Date(state.lastSent).toLocaleTimeString('zh-TW') : 'never'}`,
            `pollCount=${_pollCount}`,
            `pollErrors=${_pollErrorCount}`,
            `activityEvents=${_activityEventCount}`,
            `extractInProgress=${_extractionInProgress}`,
        ].join(' | '));
    }, 60000);

    _dbg(8, 'BOOT', `🎉 全部 Phase 載入完成，從 boot 到現在共 ${(performance.now() - _t_boot).toFixed(0)}ms`);

})();
