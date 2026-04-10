# 計畫：ai-monitor-client V4 — API Interception（網路攔截）

## Context

V2/V3 皆使用 **DOM 爬蟲**（regex 解析 `textContent`）取得頁面資料。此方式受限於：
- React hydration 期間搶佔主執行緒導致卡頓
- 頁面結構 / 文字改動即失效
- 需等待渲染完成（`setTimeout` 1.8–3 秒）才能撈文字

V4 改用**降維打擊**策略：直接攔截瀏覽器的 `fetch` / `XMLHttpRequest`，從 API response 的原始 JSON 提取資料。效能開銷趨近 0，完全不依賴 DOM 結構。

## 新檔案

`ai-monitor-client-v4.js`（獨立於 V3，不修改任何現有檔案）

## 核心原理

```
頁面 JS 呼叫 fetch('/api/billing/usage')
        ↓
V4 攔截器（wrappedFetch）
        ↓  response.clone()
        ├─→ 原始 response 原封不動回傳給頁面（頁面毫無感知）
        └─→ clone 的 response → 讀取 JSON → 比對 URL pattern
                                                ↓ 命中
                                        transformer 函式
                                                ↓
                                    轉為 V3 相容格式
                                                ↓
                                    POST localhost:7890/update
```

---

## Phase 1: 骨架與攔截基礎設施

### Step 1 — Tampermonkey Header

```javascript
// ==UserScript==
// @name         AI Quota Monitor Client v4
// @version      4.0.0
// @run-at       document-start          ← 關鍵！搶在頁面 JS 之前安裝 hook
// @grant        unsafeWindow             ← 存取頁面真實 window.fetch
// @grant        GM_xmlhttpRequest        ← 傳送至 localhost
// @grant        GM_getValue
// @grant        GM_setValue
// @connect      localhost
// @connect      127.0.0.1
// @match        https://platform.openai.com/settings/organization/billing/overview*
// @match        https://claude.ai/settings/usage*
// @match        https://platform.claude.com/settings/billing*
// @match        https://github.com/settings/billing/premium_requests_usage*
// @noframes
// ==/UserScript==
```

**為什麼要 `@run-at document-start`？**
因為攔截器必須在頁面 JS 發出第一個 API request **之前**就安裝好。`document-idle` 太晚，會漏掉初始載入的 API 呼叫。

**為什麼要 `unsafeWindow`？**
Tampermonkey 在 `@grant` 非 `none` 時會建立 sandbox，腳本看到的 `window` 不是頁面的真 `window`。必須用 `unsafeWindow` 才能 patch 頁面的 `fetch`。

### Step 2 — 安裝 fetch 攔截器

```javascript
const _realFetch = unsafeWindow.fetch;

unsafeWindow.fetch = function (...args) {
    const url = args[0] instanceof Request ? args[0].url : String(args[0]);

    return _realFetch.apply(this, args).then(response => {
        // 比對 URL pattern
        for (const rule of activeRules) {
            if (rule.urlPattern.test(url)) {
                // clone 後讀取，不影響原始 response
                response.clone().json()
                    .then(json => rule.transform(url, json))
                    .catch(() => {}); // 非 JSON 忽略
            }
        }
        return response; // 原封不動回傳
    });
};
```

### Step 3 — 安裝 XMLHttpRequest 攔截器

```javascript
const _RealXHR = unsafeWindow.XMLHttpRequest;
const _origOpen = _RealXHR.prototype.open;

_RealXHR.prototype.open = function (method, url, ...rest) {
    this._aimon_url = url;
    return _origOpen.call(this, method, url, ...rest);
};

const _origSend = _RealXHR.prototype.send;
_RealXHR.prototype.send = function (...args) {
    this.addEventListener('load', function () {
        const url = this._aimon_url || '';
        for (const rule of activeRules) {
            if (rule.urlPattern.test(url)) {
                try {
                    const json = JSON.parse(this.responseText);
                    rule.transform(url, json);
                } catch (e) {}
            }
        }
    });
    return _origSend.apply(this, args);
};
```

### Step 4 — URL Pattern Registry

```javascript
const INTERCEPT_RULES = {
    openai_billing: [
        // OpenAI 帳單頁可能呼叫的 API
        { urlPattern: /\/v1\/dashboard\/billing\/credit_grants/i,   transform: transformOpenAI },
        { urlPattern: /\/v1\/dashboard\/billing\/usage/i,           transform: transformOpenAI },
        { urlPattern: /\/v1\/dashboard\/billing\/subscription/i,    transform: transformOpenAI },
        { urlPattern: /\/dashboard\/billing/i,                      transform: transformOpenAI },
        { urlPattern: /\/organization\/costs/i,                     transform: transformOpenAI },
        { urlPattern: /\/organization\/billing/i,                   transform: transformOpenAI },
    ],
    claude_usage: [
        // claude.ai 用量頁可能呼叫的 API
        { urlPattern: /\/api\/organizations\/[^/]+\/usage/i,        transform: transformClaudeUsage },
        { urlPattern: /\/api\/auth\/session_info/i,                 transform: transformClaudeUsage },
        { urlPattern: /\/settings\/usage/i,                         transform: transformClaudeUsage },
    ],
    claude_billing: [
        // platform.claude.com 帳單頁可能呼叫的 API
        { urlPattern: /\/api\/.*billing/i,                          transform: transformClaudeBilling },
        { urlPattern: /\/api\/organizations\/[^/]+\/subscription/i, transform: transformClaudeBilling },
        { urlPattern: /\/v1\/organizations\/[^/]+\/api_billing/i,   transform: transformClaudeBilling },
    ],
    github_copilot: [
        // GitHub Copilot 用量頁可能呼叫的 API
        { urlPattern: /copilot_billing.*usage/i,                    transform: transformGitHubCopilot },
        { urlPattern: /\/billing\/premium_requests/i,               transform: transformGitHubCopilot },
        { urlPattern: /\/copilot\/usage/i,                          transform: transformGitHubCopilot },
    ],
};
```

> ⚠️ **以上 URL patterns 為推測值**。需用 Debug 模式（Phase 3）實際確認各頁面的 API endpoint 後微調。

---

## Phase 2: 資料轉換與傳送

### Step 5 — Transformer 函式

每個 transformer 將攔截到的 API JSON 映射至 **V3 相容格式**（欄位名稱完全一致）：

```javascript
function transformOpenAI(url, json) {
    // 根據不同 API endpoint 提取不同欄位
    // 合併進 pendingData['openai_billing']
    merge('openai_billing', {
        balance_usd:      json.total_available ?? json.balance,
        credits_used_usd: json.total_used,
        credits_total_usd: json.total_granted,
        hard_limit_usd:   json.hard_limit_usd,
        soft_limit_usd:   json.soft_limit_usd,
        month_usage_usd:  json.total_usage,
        tier:             json.tier,
        auto_recharge:    json.auto_recharge,
    });
}

function transformClaudeUsage(url, json) {
    merge('claude_usage', {
        session_percent:  json.session?.percent_used,
        session_reset:    json.session?.reset_in,
        weekly_percent:   json.weekly?.percent_used,
        weekly_reset:     json.weekly?.reset_in,
        extra_enabled:    json.extra_usage?.enabled,
        extra_spent:      json.extra_usage?.amount_spent,
        extra_limit:      json.extra_usage?.spend_limit,
        extra_balance:    json.extra_usage?.balance,
        extra_percent:    json.extra_usage?.percent_used,
        auto_reload:      json.extra_usage?.auto_reload,
    });
}

function transformClaudeBilling(url, json) {
    merge('claude_billing', {
        plan:            json.plan?.name,
        next_billing:    json.next_billing_date,
        monthly_usd:     json.plan?.amount,
        this_month_usd:  json.current_period_usage,
        balance_usd:     json.credit_balance ?? json.remaining_balance,
        spend_limit_usd: json.spend_limit,
    });
}

function transformGitHubCopilot(url, json) {
    merge('github_copilot', {
        included_consumed: json.premium_requests?.consumed,
        included_total:    json.premium_requests?.entitled,
        included_percent:  /* computed */,
        billed_usd:       json.total_billed_amount,
        resets_in_days:    json.days_until_reset,
        next_billing:      json.next_billing_date,
    });
}
```

> ⚠️ **以上 JSON 欄位路徑為推測值**。真實 API response 結構需 debug 模式確認。

### Step 6 — 資料聚合（Debounce 合併）

同一頁面可能同時發出多個 API call（如 OpenAI 同時呼叫 credit_grants + usage），需合併為一筆資料再送出：

```javascript
const pendingData = {};   // { source: { ...fields } }
const mergeTimers = {};   // { source: timeoutId }
const MERGE_WINDOW = 2000; // 2 秒合併視窗

function merge(source, fields) {
    // 移除 undefined 值
    const clean = {};
    for (const [k, v] of Object.entries(fields)) {
        if (v !== undefined && v !== null) clean[k] = v;
    }
    if (Object.keys(clean).length === 0) return;

    pendingData[source] = { ...(pendingData[source] || {}), ...clean };

    // 重置 debounce timer
    if (mergeTimers[source]) clearTimeout(mergeTimers[source]);
    mergeTimers[source] = setTimeout(() => flushSource(source), MERGE_WINDOW);
}

function flushSource(source) {
    const data = pendingData[source];
    if (!data || Object.keys(data).length === 0) return;

    data.source = source;
    data.timestamp = new Date().toISOString();
    data.page_url = location.href;

    // Change detection（同 V3 邏輯）
    const SKIP = new Set(['source', 'timestamp', 'page_url']);
    const prev = lastData[source];
    const changed = !prev || Object.keys(data).some(k => !SKIP.has(k) && data[k] !== prev[k]);
    lastData[source] = { ...data };

    if (changed) sendToServer(data);

    delete pendingData[source];
    delete mergeTimers[source];
}
```

### Step 7 — 傳送至本地伺服器

完全複用 V3 邏輯：

```javascript
function sendToServer(data) {
    GM_xmlhttpRequest({
        method:  'POST',
        url:     config.server_url + '/update',
        headers: { 'Content-Type': 'application/json', 'X-AI-Monitor-Client': '1' },
        data:    JSON.stringify(data),
        timeout: 5000,
        onload(resp) {
            if (resp.status >= 200 && resp.status < 300) {
                setStatus('success');
            } else {
                setStatus('error', '伺服器 ' + resp.status);
            }
        },
        onerror()   { setStatus('error', '無法連線'); },
        ontimeout() { setStatus('error', '連線逾時'); },
    });
}
```

---

## Phase 3: Discovery / Debug 模式（優先開發）

### Step 8 — 內建 API 探索工具

**這是整個 V4 開發的首要步驟**。因為我們目前**不確定各頁面的確切 API URL 和 JSON 結構**，需要 debug 模式來探測。

```javascript
const DEBUG = GM_getValue('aimon_debug', true); // 首版預設開啟

// 在攔截器中加入 debug 日誌
if (DEBUG) {
    console.group(`[AI Monitor v4] 攔截到 ${method} ${url}`);
    console.log('Status:', response.status);
    console.log('JSON preview:', JSON.stringify(json).substring(0, 500));
    console.groupEnd();
}
```

**Debug 模式下的 console 輸出範例：**
```
[AI Monitor v4] 攔截到 GET https://api.claude.ai/api/organizations/xxx/usage
  Status: 200
  JSON preview: {"session":{"percent_used":45,"reset_in":"4 mins"},...}

[AI Monitor v4] ✓ 匹配規則: claude_usage
  提取欄位: { session_percent: 45, session_reset: "4 mins", ... }
```

**使用者操作流程：**
1. 安裝 V4 腳本（debug 預設開啟）
2. 分別開啟四個監控頁面
3. 打開 DevTools Console (F12)
4. 觀察 `[AI Monitor v4]` 前綴的日誌
5. 回報各頁面攔截到的 API URL 和 JSON 結構
6. 據此微調 `INTERCEPT_RULES` 和 transformer 函式

**替代方案：** 使用者也可以直接在 DevTools → Network tab → 篩選 XHR/Fetch，手動記錄 API URL 和 response 結構。

---

## Phase 4: UI 與生命週期

### Step 9 — 極簡色點 UI（複用 V3 方案）

```
位置：position:fixed; bottom:16px; right:16px; z-index:2147483647
大小：width:36px; height:36px; border-radius:50%
顏色：
  idle      → #6c7086（灰）
  listening → #89b4fa（藍）← 新增：攔截器已安裝，等待 API call
  success   → #a6e3a1（綠）
  error     → #f38ba8（紅）
點擊：location.reload() 強制重新載入（讓 API 重新呼叫被攔截）
title tooltip：最後成功時間 + 已攔截 API 數量
```

**UI 建立時機：** 攔截器在 `document-start` 安裝（此時無 DOM），色點 UI 等到 `DOMContentLoaded` 才建立。

### Step 10 — 生命週期

```
@run-at document-start
    │
    ├─ 同步：安裝 fetch + XHR 攔截器（此時頁面 JS 尚未執行）
    │
    ├─ DOMContentLoaded → 建立色點 UI
    │
    ├─ 頁面 JS 開始執行 → API calls 被攔截 → transformer → merge → send
    │
    ├─ 每 2 秒：檢查 location.href 是否改變（SPA 導航偵測）
    │
    ├─ 每 N 分鐘（可選）：location.reload() 強制重新載入（確保資料不過期）
    │
    └─ 15 秒超時：若未攔截到任何匹配 API → 色點顯示 ⚠ idle
```

### Step 11 — 定時刷新策略

V3 靠定時器重新執行 DOM parser，V4 改為被動攔截模式。資料只在頁面發出 API call 時更新。

**解決方案：保留低頻定時 reload**

```javascript
const REFRESH_INTERVALS = {
    openai_billing: 5 * 60 * 1000,  // 5 分鐘
    claude_usage:   3 * 60 * 1000,  // 3 分鐘（用量變化較快）
    claude_billing: 5 * 60 * 1000,  // 5 分鐘
    github_copilot: 10 * 60 * 1000, // 10 分鐘
};

// 若距離上次成功超過 interval，reload 頁面
setInterval(() => {
    if (lastSuccessTime && Date.now() - lastSuccessTime > REFRESH_INTERVALS[PAGE.key]) {
        location.reload();
    }
}, 60000); // 每分鐘檢查一次
```

---

## 輸出格式（V3 相容）

V4 的 transformer **必須**產出與 V3 parser 完全相同的欄位名稱和型別：

### openai_billing
```json
{
    "source": "openai_billing",
    "balance_usd": 15.42,
    "credits_used_usd": 10.5,
    "credits_total_usd": 100,
    "hard_limit_usd": 500,
    "soft_limit_usd": 200,
    "month_usage_usd": 8.75,
    "tier": "Pay-as-you-go",
    "auto_recharge": true,
    "timestamp": "2026-03-26T14:32:05.123Z",
    "page_url": "https://platform.openai.com/..."
}
```

### claude_usage
```json
{
    "source": "claude_usage",
    "session_percent": 45,
    "session_reset": "4 mins",
    "weekly_percent": 23,
    "weekly_reset": "3 days",
    "extra_enabled": true,
    "extra_spent": 0.50,
    "extra_resets": "April 1",
    "extra_limit": 50.00,
    "extra_balance": 49.50,
    "extra_percent": 1,
    "auto_reload": true,
    "timestamp": "2026-03-26T14:32:05.123Z",
    "page_url": "https://claude.ai/..."
}
```

### claude_billing
```json
{
    "source": "claude_billing",
    "plan": "Pro",
    "next_billing": "April 1, 2026",
    "monthly_usd": 20.00,
    "this_month_usd": 12.50,
    "balance_usd": 7.50,
    "spend_limit_usd": 50.00,
    "timestamp": "2026-03-26T14:32:05.123Z",
    "page_url": "https://platform.claude.com/..."
}
```

### github_copilot
```json
{
    "source": "github_copilot",
    "included_consumed": 726.59,
    "included_total": 1500,
    "included_percent": 48.4,
    "billed_usd": 0.00,
    "resets_in_days": 5,
    "next_billing": "2026年3月1日",
    "timestamp": "2026-03-26T14:32:05.123Z",
    "page_url": "https://github.com/..."
}
```

---

## 相關檔案

| 檔案 | 角色 |
|------|------|
| `ai-monitor-client-v4.js`（新建） | V4 主腳本 |
| `ai-monitor-client-v3.js` | 參考：output schema、UI、sendToServer |
| `services/browser_data.py` | 驗證：Python 端期望的欄位名稱（`BrowserXxxService.fetch()`） |
| `services/local_server.py` | 驗證：POST /update 接收邏輯（`DATA_STORE[source]`） |
| `gui/widgets.py` | 驗證：`_format_data()` 的 `service_name` 分支 |
| `desktop_widget/cards.py` | 驗證：桌面小工具的顯示邏輯 |

---

## 與 V3 的差異對照

| 項目 | V3（DOM 爬蟲） | V4（API 攔截） |
|------|---------------|---------------|
| 資料來源 | DOM `textContent` + regex | fetch/XHR response JSON |
| `@run-at` | `document-idle` | `document-start` |
| 渲染等待 | `setTimeout` 1.8–3 秒 | 不需要（直接讀 API response） |
| DOM 依賴 | 完全依賴 | 零依賴 |
| 效能影響 | 中（regex 掃描整頁文字） | 趨近 0（只 clone + parse 匹配的 response） |
| 頁面結構變動 | 易壞 | 不受影響（只要 API 不變） |
| API 結構變動 | 不受影響 | 易壞（但 API 通常比 UI 穩定） |
| 輸出格式 | V3 格式 | **完全相同** |
| 定時策略 | `setInterval` 重跑 parser | 被動攔截 + 定時 `location.reload()` |
| Debug 工具 | 無 | Console 日誌所有攔截的 API |

---

## 驗證步驟

1. **Phase 3 優先**：用 `DEBUG_MODE` 分別開啟四個頁面，在 DevTools Console 確認各頁面的 API URL 被正確攔截並印出 JSON
2. **確認 URL pattern**：根據 debug 日誌微調 `INTERCEPT_RULES`
3. **確認 JSON 結構**：根據 debug 日誌調整 transformer 的欄位映射
4. **欄位對齊**：比對 V4 transformer 輸出與 V3 parser 輸出，欄位名稱和型別必須一致
5. **後端接收**：啟動 Python 程式，確認 `DATA_STORE` 收到 V4 的資料且格式正確
6. **UI 顯示**：確認桌面程式的 ServiceCard / DesktopWidget 正常顯示 V4 送來的資料
7. **效能**：操作頁面確認無卡頓（API 攔截 overhead 應趨近 0）
8. **邊界測試**：頁面 reload、SPA 導航、伺服器離線、API 回傳錯誤

---

## 開放問題（待確認）

1. **各頁面的確切 API URL 和 JSON 結構**
   - 需請使用者先跑 debug 版本回報，或在 DevTools Network tab 手動記錄
   - 這是開發的首要瓶頸

2. **定時 reload 間隔是否合適？**
   - Claude 用量頁 3 分鐘、其他 5–10 分鐘
   - 太頻繁影響體驗，太稀疏資料過期

3. **是否需要 DOM fallback？**
   - V4 首版不含（純攔截）
   - 若某些頁面不透過 API 載入資料（直接 SSR），則需要 fallback
   - 可作為 V4.1 迭代

4. **Tampermonkey `@run-at document-start` + `unsafeWindow` 的相容性**
   - 理論上支援，但需實測確認能否搶在頁面 JS 之前安裝 hook
   - 備案：若 `unsafeWindow` 不可用，可嘗試 `@grant none` + 直接 patch `window.fetch`（但會失去 `GM_xmlhttpRequest`，需改用 `navigator.sendBeacon` 或自建 `fetch` 傳送）
