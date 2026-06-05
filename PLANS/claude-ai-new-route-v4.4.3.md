# claude.ai 新路由相容修改說明 (v4.4.3)

> 本文件記錄 v4.4.3 的修改內容與原因，供 Android 版本移植參考。

## 背景

Anthropic 將 claude.ai 的 Usage 設定頁面路由從：
```
https://claude.ai/settings/usage
```
遷移至：
```
https://claude.ai/new#settings/usage
```

新路由使用 **hash-based routing**（SPA 內部導航），`#settings/usage` 是 fragment，不會傳送至伺服器。

---

## 修改一：Tampermonkey 腳本 (`ai-monitor-client-v4.4.js`)

### 1. `@match` 新增 `/new*`

```js
// 修改前
// @match        https://claude.ai/settings/usage*

// 修改後
// @match        https://claude.ai/settings/usage*
// @match        https://claude.ai/new*
```

**原因**：Tampermonkey 的 `@match` 在頁面初始載入時比對 URL 路徑（不含 fragment），必須加入 `/new*` 才能在新路由下注入腳本。

**注意**：`/new` 是 claude.ai 的聊天主頁，腳本注入後會在**所有** `/new*` 頁面執行，因此必須搭配修改二，避免干擾正常聊天。

---

### 2. `PAGE_MAP['claude.ai']` 新增 `expectedHash`

```js
// 修改前
'claude.ai': {
    key: 'claude_usage',
    label: 'Claude Usage',
    expectedPath: '/settings/usage',
    refreshInterval: 1 * 60 * 1000,
},

// 修改後
'claude.ai': {
    key: 'claude_usage',
    label: 'Claude Usage',
    expectedPath: ['/settings/usage', '/new'],
    expectedHash: 'settings/usage',   // /new#settings/usage 新路由
    refreshInterval: 1 * 60 * 1000,
},
```

---

### 3. `isOnExpectedPage()` 加入 hash 判斷

```js
// 修改前
function isOnExpectedPage() {
    const paths = Array.isArray(PAGE.expectedPath) ? PAGE.expectedPath : [PAGE.expectedPath];
    return paths.some(p => location.pathname.startsWith(p));
}

// 修改後
function isOnExpectedPage() {
    const paths = Array.isArray(PAGE.expectedPath) ? PAGE.expectedPath : [PAGE.expectedPath];
    const pathMatch = paths.some(p => location.pathname.startsWith(p));
    if (!pathMatch) return false;
    // 若設定了 expectedHash，在 /new 路徑下需額外確認 hash
    if (PAGE.expectedHash && location.pathname === '/new') {
        const hash = location.hash.replace(/^#/, '');
        return hash.startsWith(PAGE.expectedHash);
    }
    return true;
}
```

**邏輯**：
- 路徑為 `/settings/usage` → 直接 true（舊路由相容）
- 路徑為 `/new` 且 hash 以 `settings/usage` 開頭 → true（新路由）
- 路徑為 `/new` 但 hash 是其他（如聊天主頁、其他設定）→ false

---

### 4. fetch hook 加入早期退出（**關鍵修復**）

```js
// 修改前
win.fetch = function (...args) {
    let url;
    try { ... }
    return _realFetch.apply(this, args).then(response => { ... });
};

// 修改後
win.fetch = function (...args) {
    // 不在目標頁面時完全透通，避免干擾其他頁面（例如聊天主頁）
    if (!isOnExpectedPage()) return _realFetch.apply(this, args);

    let url;
    try { ... }
    return _realFetch.apply(this, args).then(response => { ... });
};
```

**原因**：腳本在 `document-start` 時替換 `window.fetch`，此後該頁面所有請求都會經過 hook。若不加早期退出，在聊天主頁時腳本會嘗試攔截所有 API（含 `response.clone()`），導致 **ERR_QUIC_PROTOCOL_ERROR**（HTTP/3 下 clone stream 時序衝突）。

---

### 5. XHR hook 加入早期退出

```js
// 修改前
this.addEventListener('load', function () {
    const url = this._aimon_url || '';
    if (isUrlRelevant(url) && this.status >= 200 && ...) { ... }
});

// 修改後
this.addEventListener('load', function () {
    const url = this._aimon_url || '';
    // 不在目標頁面、或 URL 不相關時跳過
    if (!isOnExpectedPage() || !isUrlRelevant(url)) return;
    if (this.status >= 200 && ...) { ... }
});
```

---

### 6. SPA 導航偵測：補建 UI

```js
// setupSPADetection() 內，新增：
if (isOnExpectedPage() && !_dot) {
    buildUI();
    setupPeriodicRefresh();
    setupTimeoutWarning();
}
```

**場景**：使用者從 `/new`（聊天主頁，`isOnExpectedPage()` 為 false）導航到 `/new#settings/usage` 時，`onDomReady()` 已在最初因路徑不符而跳過 `buildUI()`，需要在 SPA 偵測到 hash 變化時補初始化 UI。

---

## 修改二：Python APP 開啟 URL

### `desktop_widget/app.py`

```python
# 修改前
_PAGE_URLS = [
    ("Claude.ai 用量",  "https://claude.ai/settings/usage?oclaw=1"),
    ...
]
_PAGE_URLS_FF = [
    ("Claude.ai 用量",  "https://claude.ai/settings/usage?oflaw=1"),
    ...
]

# 修改後
_PAGE_URLS = [
    ("Claude.ai 用量",  "https://claude.ai/new?oclaw=1#settings/usage"),
    ...
]
_PAGE_URLS_FF = [
    ("Claude.ai 用量",  "https://claude.ai/new?oflaw=1#settings/usage"),
    ...
]
```

### `gui/app.py`

```python
# 修改前
_PAGE_URLS = [
    ("Claude.ai 用量",     "https://claude.ai/settings/usage?oclaw=1"),
    ...
]

# 修改後
_PAGE_URLS = [
    ("Claude.ai 用量",     "https://claude.ai/new?oclaw=1#settings/usage"),
    ...
]
```

**注意**：`?oclaw=1` / `?oflaw=1` 必須放在 `#` **前面**，否則 query string 會被瀏覽器忽略（fragment 後的內容不傳至伺服器）。這個 query parameter 用於 macOS AppleScript 視窗追蹤（`contains "oclaw=1"`）與 Windows HWND 追蹤。

---

## Android 版本移植注意事項

### 對應修改點

Android 版本若有 WebView 或瀏覽器跳轉功能，需更新以下 URL：

| 功能 | 舊 URL | 新 URL |
|------|--------|--------|
| 開啟 Claude.ai 用量 | `https://claude.ai/settings/usage` | `https://claude.ai/new#settings/usage` |

### Tampermonkey / WebView 注入腳本

若 Android 版本在 WebView 中執行 JS 注入：

1. **注入條件**：改為檢查 `url.startsWith("https://claude.ai/new")` 或 `url.contains("claude.ai")`
2. **頁面識別**：改用 hash 判斷而非路徑判斷：
   ```kotlin
   // Kotlin 範例
   val uri = Uri.parse(url)
   val isUsagePage = uri.host == "claude.ai" &&
       (uri.path == "/settings/usage" ||
        (uri.path == "/new" && uri.fragment?.startsWith("settings/usage") == true))
   ```
3. **fetch/XHR hook**：同樣需要加入早期退出，避免在聊天頁面干擾請求

### SPA hash routing 行為

`claude.ai/new` 是 React SPA，hash 變化：
- **不觸發頁面重載**
- **不觸發 WebViewClient.onPageStarted**
- 需監聽 `WebViewClient.onPageCommitVisible` 或注入 JS 監聽 `hashchange` 事件

```kotlin
// 監聽 hash 變化（WebView 內注入）
webView.evaluateJavascript("""
    window.addEventListener('hashchange', function(e) {
        Android.onHashChange(location.hash);
    });
""", null)
```

### API 端點不變

`transformClaudeUsage()` 攔截的 API 路徑完全不變：
- `/api/organizations/{id}/usage`
- `/api/organizations/{id}/prepaid/credits`
- `/api/organizations/{id}/prepaid/bundles`
- 等

資料結構與欄位名稱均不變，Android 解析邏輯無需修改。

---

## 測試驗證步驟

1. 冷開啟 `https://claude.ai/new?oclaw=1#settings/usage` → 確認頁面正常顯示 Usage，⚡ 圓點出現
2. 先開啟 `https://claude.ai/new`（聊天主頁）→ 確認**無** ERR_QUIC_PROTOCOL_ERROR
3. 在聊天主頁導航到 `#settings/usage` → 確認 ⚡ 圓點出現，資料成功傳送
4. 從 `#settings/usage` 導航回聊天主頁 → 確認 ⚡ 圓點消失（或已移除），聊天功能正常
