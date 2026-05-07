# OpenRouter 服務整合計畫

## Context

目前應用支援 4 個 AI 服務（OpenAI / Claude.ai / Claude API / GitHub Copilot），全數透過 Tampermonkey 腳本攔截瀏覽器 fetch/XHR 取得資料。本計畫新增第 5 個服務 **OpenRouter**，資料來源為兩個官方頁面：

- `https://openrouter.ai/settings/credits` — 帳戶餘額（截圖顯示 `$39.49`）
- `https://openrouter.ai/activity` — 月度花費 / 請求數 / Tokens（截圖顯示 `$0.494` / `12 requests` / `537K tokens`）

整合後，使用者只要在這兩個頁面停留即可被動上傳資料，桌面卡片與小工具同步顯示。

## 設計決策（已與使用者確認）

| 項目 | 決策 |
|---|---|
| 顯示欄位 | 帳戶餘額、本月花費、請求數、Tokens（4 項） |
| 腳本檔案 | **新建** `ai-monitor-client-v4.2.js`，保留 v4.1 對照 |
| @match 路徑 | 兩個頁面：`/activity` 與 `/settings/credits` |
| 卡片色條 | `#7287fd`（Catppuccin lavender 靛紫） |
| 服務名稱 | `OpenRouter (瀏覽器)` |
| source_key | `openrouter` |
| GUI 服務鍵 | `browser_openrouter` |

## source_key 一致性

所有層級必須使用 **`openrouter`** 作為一致的 source key，否則資料無法串接：

```
JS  PAGE_MAP.key = 'openrouter'
 │
 ├─→ POST /update body { "source": "openrouter", ... }
 │
 ├─→ local_server.DATA_STORE["openrouter"]
 │
 ├─→ BrowserOpenRouterService.source_key = "openrouter"
 │
 └─→ BROWSER_SERVICE_SOURCES["browser_openrouter"] = "openrouter"
```

---

## 修改清單

### A. Python 端（5 個檔案）

#### A1. `services/browser_data.py` — 新增服務類別

於檔案末尾新增（仿 `BrowserGitHubCopilotService` 模式，lines 124-140）：

```python
class BrowserOpenRouterService(BaseService):
    name = "OpenRouter (瀏覽器)"
    source_key = "openrouter"

    def fetch(self, config: dict) -> ServiceResult:
        raw = local_server.get_data(self.source_key)
        if not raw:
            return _base_not_connected(self.name)

        data = dict(raw)
        recv = data.get("received_at", "")
        data["updated_at"] = _ts_display(recv)
        warn = _stale_warning(recv)
        if warn:
            data["stale_warning"] = warn

        return ServiceResult(service_name=self.name, success=True, data=data)
```

#### A2. `gui/app.py` — 註冊到 SERVICES 與 BROWSER_SERVICE_SOURCES

```python
# 匯入新增（line 10 區塊）
from services.browser_data import (
    BrowserOpenAIService,
    BrowserClaudeUsageService,
    BrowserClaudeBillingService,
    BrowserGitHubCopilotService,
    BrowserOpenRouterService,   # NEW
)

# SERVICES（lines 21-26）新增一筆
SERVICES = [
    ("browser_openai",         BrowserOpenAIService()),
    ("browser_claude_usage",   BrowserClaudeUsageService()),
    ("browser_claude_billing", BrowserClaudeBillingService()),
    ("browser_github_copilot", BrowserGitHubCopilotService()),
    ("browser_openrouter",     BrowserOpenRouterService()),   # NEW
]

# BROWSER_SERVICE_SOURCES（lines 28-34）新增一筆
BROWSER_SERVICE_SOURCES = {
    "browser_openai":         "openai_billing",
    "browser_claude_usage":   "claude_usage",
    "browser_claude_billing": "claude_billing",
    "browser_github_copilot": "github_copilot",
    "browser_openrouter":     "openrouter",   # NEW
}
```

#### A3. `gui/widgets.py` — 新增色條與顯示分支

```python
# SERVICE_ACCENTS（lines 26-31）新增一筆
SERVICE_ACCENTS = {
    "OpenAI 帳單 (瀏覽器)":    "#74c7ec",
    "Claude.ai 用量 (瀏覽器)": "#c6a0f6",
    "Claude API 帳單 (瀏覽器)":"#cba6f7",
    "GitHub Copilot (瀏覽器)": "#a6e3a1",
    "OpenRouter (瀏覽器)":     "#7287fd",   # NEW lavender
}
```

`_format_data()`（line 269 起）末尾新增分支（仿 OpenAI/Copilot 模式）：

```python
elif service_name == "OpenRouter (瀏覽器)":
    self._browser_header_rows(data, rows)
    if "balance_usd" in data:
        rows.append(("帳戶餘額", f"${data['balance_usd']:.2f}", COLORS["green"]))
    if "month_spend_usd" in data:
        rows.append(("本月花費", f"${data['month_spend_usd']:.4f}"))
    if data.get("month_requests") is not None:
        rows.append(("本月請求", f"{data['month_requests']:,} 次"))
    if data.get("month_tokens") is not None:
        rows.append(("本月 Tokens", _format_tokens(data["month_tokens"])))
    if data.get("top_model"):
        rows.append(("主要模型", data["top_model"]))
```

於 `widgets.py` 模組層級新增 helper（K/M 縮寫，呼應截圖 `537K`）：

```python
def _format_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return f"{n:,}"
```

#### A4. `desktop_widget/cards.py` — 桌面小工具同步分支

`_format_data()`（line 186 起）末尾新增同樣的 OpenRouter 分支（與 A3 相同欄位邏輯，但複用 `gui/widgets._format_tokens` 或在此檔內再放一份）。

#### A5. `config/manager.py` — DEFAULT_CONFIG 新增條目

`DEFAULT_CONFIG["services"]`（lines 52-63）末尾新增：

```python
"browser_openrouter": {
    "enabled": True
}
```

`load()` 既有的合併邏輯會自動把這個鍵補進舊 config 檔，**現有使用者無需手動編輯 config.json**。

---

### B. JavaScript 端 — 新建 `ai-monitor-client-v4.2.js`

複製 `ai-monitor-client-v4.1.js` → `ai-monitor-client-v4.2.js`，套用以下修改：

#### B1. UserScript header

```javascript
// @name         AI Quota Monitor Client v4.2
// @version      4.2.0
// @description  v4.1 + OpenRouter 支援
// @match        https://platform.openai.com/settings/organization/billing/overview*
// @match        https://claude.ai/settings/usage*
// @match        https://platform.claude.com/settings/billing*
// @match        https://github.com/settings/copilot/features*
// @match        https://openrouter.ai/activity*
// @match        https://openrouter.ai/settings/credits*
```

#### B2. PAGE_MAP（line 27 起）— 新增條目

```javascript
'openrouter.ai': {
    key: 'openrouter',
    label: 'OpenRouter',
    expectedPath: ['/activity', '/settings/credits'],   // 兩個頁面共用同一 source
    refreshInterval: 5 * 60 * 1000,
},
```

`isOnExpectedPage()`（line 57）需相容陣列：

```javascript
function isOnExpectedPage() {
    const paths = Array.isArray(PAGE.expectedPath) ? PAGE.expectedPath : [PAGE.expectedPath];
    return paths.some(p => location.pathname.startsWith(p));
}
```

#### B3. INTERCEPT_RULES（line 539 起）— 新增 openrouter 區塊

```javascript
openrouter: [
    // 寬鬆 pattern；用 __aimon.debug(true) 確認真實 URL 後可縮窄
    { p: /\/api\/v1\/credits/i,         t: transformOpenRouter },
    { p: /\/api\/frontend\/credits/i,   t: transformOpenRouter },
    { p: /\/api\/.*\/credits/i,         t: transformOpenRouter },
    { p: /\/api\/v1\/auth\/key/i,       t: transformOpenRouter },
    { p: /\/api\/.*\/activity/i,        t: transformOpenRouter },
    { p: /\/api\/.*\/usage/i,           t: transformOpenRouter },
    { p: /\/api\/.*\/stats/i,           t: transformOpenRouter },
],
```

#### B4. transformOpenRouter — 新增 transformer

放在 `transformGitHubCopilot` 之後：

```javascript
function transformOpenRouter(url, json) {
    if (!json || typeof json !== 'object') return {};
    const d = {};

    // ─── /settings/credits 相關 ───
    // 餘額（OpenRouter 常見欄位：balance / total_credits / remaining）
    if (json.balance !== undefined) {
        d.balance_usd = parseFloat(json.balance) || 0;
    } else if (json.data && json.data.balance !== undefined) {
        d.balance_usd = parseFloat(json.data.balance) || 0;
    } else if (json.total_credits !== undefined && json.total_usage !== undefined) {
        d.balance_usd = parseFloat(json.total_credits) - parseFloat(json.total_usage);
    } else if (json.remaining !== undefined) {
        d.balance_usd = parseFloat(json.remaining) || 0;
    }

    // ─── /activity 相關 ───
    // 期間花費 / 請求數 / tokens（單一欄位或聚合陣列）
    let spend = 0, reqs = 0, toks = 0, top = null, topSpend = -1;

    const rows = json.activity || json.data || json.rows || (Array.isArray(json) ? json : null);
    if (Array.isArray(rows)) {
        for (const r of rows) {
            const s = parseFloat(r.cost ?? r.spend ?? r.usage ?? 0) || 0;
            const q = parseInt(r.requests ?? r.request_count ?? r.count ?? 0) || 0;
            const t = parseInt(r.tokens ?? r.total_tokens ?? r.token_count ?? 0) || 0;
            spend += s; reqs += q; toks += t;
            const m = r.model || r.model_id || r.name;
            if (m && s > topSpend) { topSpend = s; top = m; }
        }
        if (spend > 0)  d.month_spend_usd = spend;
        if (reqs > 0)   d.month_requests = reqs;
        if (toks > 0)   d.month_tokens = toks;
        if (top)        d.top_model = top;
    } else {
        // 純彙總物件
        if (json.total_cost !== undefined)   d.month_spend_usd = parseFloat(json.total_cost) || 0;
        if (json.total_spend !== undefined)  d.month_spend_usd = parseFloat(json.total_spend) || 0;
        if (json.total_requests !== undefined) d.month_requests = parseInt(json.total_requests) || 0;
        if (json.total_tokens !== undefined)   d.month_tokens   = parseInt(json.total_tokens) || 0;
    }

    return d;
}
```

> **注意：** OpenRouter 真實 API 結構需用 debug 模式（在 OpenRouter 頁面開 Console，輸入 `__aimon.debug(true)` 後重整）確認後再縮窄 patterns / 對齊欄位名稱。第一版採寬鬆策略，避免漏接。

---

### C. 文件同步

#### C1. `README.md` — 服務表新增一列（line 12 區塊）

```
| **OpenRouter** | openrouter.ai | 帳戶餘額、本月花費、請求數、Tokens |
```

並更新版本號（README 標題 line 1：`v4.2.0` → `v4.3.0` 或視語意自行決定）。

#### C2. `CLAUDE.md` 與 `.github/copilot-instructions.md`

兩檔頂部互為映射，需**同步**更新。在「資料流程」「未啟用的服務類別」段落中：

- 「四個 `BaseService` 子類別」 → 「五個 `BaseService` 子類別」
- 「四個監控頁面」 → 「五個監控頁面」
- 抓取器清單加入 `parseOpenRouter`（或 `transformOpenRouter`，視文件用詞）

---

## 關鍵檔案速查表

| 檔案 | 動作 |
|---|---|
| `services/browser_data.py` | 新增 `BrowserOpenRouterService` |
| `gui/app.py` | `SERVICES` + `BROWSER_SERVICE_SOURCES` 各加一筆，匯入新類別 |
| `gui/widgets.py` | `SERVICE_ACCENTS` 加色、`_format_data()` 加分支、新增 `_format_tokens` helper |
| `desktop_widget/cards.py` | `_format_data()` 加同樣分支（小工具同步） |
| `config/manager.py` | `DEFAULT_CONFIG["services"]["browser_openrouter"]` |
| `ai-monitor-client-v4.2.js` | **新建**：複製 v4.1 + 5 處 OpenRouter 修改（header、PAGE_MAP、isOnExpectedPage、INTERCEPT_RULES、transformOpenRouter） |
| `README.md` | 服務表 + 版本號 |
| `CLAUDE.md` / `.github/copilot-instructions.md` | 服務數量 4→5 |

---

## 驗證計畫

1. **啟動桌面程式：** `py main.py`，確認啟動無 ImportError，主視窗出現 5 張卡片，OpenRouter 卡顯示「等待瀏覽器資料…」
2. **安裝 v4.2 腳本：** Tampermonkey → 新增 → 貼上 `ai-monitor-client-v4.2.js`
3. **開啟 OpenRouter 兩個頁面：** `https://openrouter.ai/activity` 與 `https://openrouter.ai/settings/credits`，確認頁面右下角出現 ⚡ 圓點（來自 `buildUI()`）
4. **debug 模式驗證：** 在 OpenRouter Console 執行 `__aimon.debug(true)` 後重整頁面，觀察攔截 log，確認：
   - 圓點轉為綠色（success）= 已成功 POST
   - log 中印出實際 API URL 與 JSON 結構
   - 必要時據此回頭縮窄 `INTERCEPT_RULES.openrouter` 與 `transformOpenRouter`
5. **桌面卡同步：** 1.5 秒內 OpenRouter 卡片應更新，欄位顯示為餘額（截圖 `$39.49`）/ 花費（`$0.4940`）/ 請求（`12 次`）/ Tokens（`537K`）
6. **stale 檢測：** 關閉 OpenRouter 分頁等 10 分鐘以上，卡片應顯示「資料已 X 分鐘未更新…」黃字警告
7. **桌面小工具：** `py widget_main.py`，確認小工具版本同樣顯示 OpenRouter 資料（A4 修改生效）
8. **打包驗證（可選）：** `pyinstaller widget_build.spec` 後執行 `dist/` 內產物，確認新服務未被遺漏
9. **舊 config 升級：** 暫時備份 `~/.config/ai-quota-monitor/config.json`、執行程式、檢查回寫後新欄位 `browser_openrouter` 已自動補齊

本專案無單元測試，全部以實機操作驗證為主。
