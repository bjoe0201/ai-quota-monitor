# AI Monitor Client v4.1 — 效能優化計畫

## 摘要

V4 的 API 攔截架構正確，但存在兩個可驗證的效能問題：
1. **所有 JSON response 無差別 clone + parse**
2. **debug 預設開啟 + `JSON.stringify` 序列化整個物件**

V4.1 以「URL 前置過濾 + 移除 stringify + debug 預設關閉」三項修正為核心，不新增任何功能。

---

## 技術審查

### 問題 1：無差別 clone + parse（影響：中高）

**現況（fetch hook，L586–593）：**
```javascript
if (response.ok) {
    const ct = response.headers.get('content-type') || '';
    if (ct.includes('json')) {
        response.clone().json().then(json => {
            handleInterceptedResponse(url, json);
        });
    }
}
```

- `response.clone()` 本身廉價（不複製 body）
- 但 `.json()` 會觸發完整的 body 消費 + JSON 解析
- claude.ai / OpenAI 頁面在背景頻繁傳輸大型 JSON（對話記錄、message history 等）
- fetch 的 `.json()` 是**非同步**的，不會直接凍結主線程，但仍消耗 CPU 時間與記憶體
- **XHR 的 `JSON.parse()` 則是同步的**（L618–622），對主線程影響更大

**修正：** 在 clone/parse 之前先用 `isUrlRelevant(url)` 檢查 URL 是否匹配任何規則，不相關的直接放行。

### 問題 2：`JSON.stringify` debug 日誌（影響：最高）

**現況（L535、L556）：**
```javascript
console.log('JSON preview:', JSON.stringify(json).substring(0, 800));
```

- `config.debug` 在 L66 預設為 `true`（註解寫「首版預設開啟」）
- 這代表**每個**匹配到的 API 回應都會被 `JSON.stringify` 完整序列化
- `JSON.stringify` 是**同步**操作，對大型物件（如數 MB 的 JSON）會直接凍結 UI
- 瀏覽器 Console 原生支援物件展開，`console.log(json)` 即可達到相同效果且零開銷

**修正：** 移除所有 `JSON.stringify` debug 日誌，改用 `console.log(json)` 直接印出物件。

### 額外發現：debug 預設值應改為 false

- L66：`debug: GM_getValue('aimon_debug', true)` — V4 已非首版測試階段
- 改為 `false` 後，即使不修正問題 2，大部分使用者也不會觸發 stringify 開銷
- 需要 debug 時可透過 `__aimon.debug(true)` 手動開啟

---

## 修改範圍

### 變更檔案

| 檔案 | 動作 |
|------|------|
| `ai-monitor-client-v4.js` | 來源（不修改，保留供對照） |
| `ai-monitor-client-v4.1.js` | **新建** — 複製 V4 並套用下列修正 |

### 修改 1：更新 UserScript Header

```diff
- // @name         AI Quota Monitor Client v4
+ // @name         AI Quota Monitor Client v4.1
- // @version      4.0.0
+ // @version      4.1.0
- // @description  API 攔截版：透過 fetch/XHR hook 直接從 API response 提取額度資料，零 DOM 依賴
+ // @description  API 攔截版（效能優化）：URL 前置過濾 + 精準解析，零 DOM 依賴
```

### 修改 2：debug 預設改為 false（L66）

```diff
  const config = {
      server_url: GM_getValue('aimon_server', 'http://localhost:7890'),
-     debug: GM_getValue('aimon_debug', true),   // 首版預設開啟 debug
+     debug: GM_getValue('aimon_debug', false),   // 預設關閉；透過 __aimon.debug(true) 開啟
  };
```

### 修改 3：新增 `isUrlRelevant()` 前置過濾函式

在 `INTERCEPT HANDLER` 區段之前新增：

```javascript
// ── URL 前置過濾器：決定是否值得消耗 CPU 去解析 response body ──
function isUrlRelevant(url) {
    // 1. 匹配任何 active rule → 一定相關
    if (activeRules.some(rule => rule.p.test(url))) return true;
    // 2. debug 模式 → 額外放行含有相關關鍵字的 URL（用於發現新 API endpoint）
    if (!config.debug) return false;
    const lower = url.toLowerCase();
    return ['billing', 'usage', 'credit', 'cost', 'limit', 'quota', 'balance', 'invoice']
        .some(kw => lower.includes(kw));
}
```

**設計決策：**
- 正常模式：只解析會被 `activeRules` 匹配到的 URL
- debug 模式：額外放行含關鍵字的 URL，供開發者發現新 endpoint
- 關鍵字清單從原始 `interesting` 陣列精簡，移除 `payment`、`organization`、`subscription`、`premium`、`copilot`、`plan` 等過於寬泛的詞

### 修改 4：修改 `installFetchHook()`（L567–600）

```diff
  return _realFetch.apply(this, args).then(response => {
-     // 只處理成功的 JSON response
-     if (response.ok) {
+     // 【效能修正】先檢查 URL 是否相關，不相關的完全跳過 clone + parse
+     if (response.ok && isUrlRelevant(url)) {
          const ct = response.headers.get('content-type') || '';
```

### 修改 5：修改 `installXHRHook()`（L603–630）

```diff
  this.addEventListener('load', function () {
-     if (this.status >= 200 && this.status < 300) {
+     const url = this._aimon_url || '';
+     // 【效能修正】先檢查 URL，不相關就跳過同步 JSON.parse
+     if (isUrlRelevant(url) && this.status >= 200 && this.status < 300) {
          const ct = (this.getResponseHeader('content-type') || '');
          if (ct.includes('json') && this.responseText) {
              try {
                  const json = JSON.parse(this.responseText);
-                 handleInterceptedResponse(this._aimon_url || '', json);
+                 handleInterceptedResponse(url, json);
              } catch (e) {}
          }
      }
```

### 修改 6：修改 `handleInterceptedResponse()`（L524–561）

```diff
  dbgGroup('✅ 匹配 API: ' + url);
  if (config.debug) {
-     console.log('JSON preview:', JSON.stringify(json).substring(0, 800));
+     // 直接印出物件，瀏覽器 Console 原生支援展開；不再用 JSON.stringify 避免同步序列化大物件
+     console.log('JSON preview:', json);
  }
```

```diff
  if (!matched && config.debug) {
-     // Debug: 顯示未匹配但可能相關的 API
-     const urlLower = url.toLowerCase();
-     const interesting = ['billing', 'usage', 'credit', 'subscription', 'cost',
-                          'plan', 'quota', 'limit', 'copilot', 'premium',
-                          'organization', 'balance', 'invoice', 'payment'];
-     if (interesting.some(kw => urlLower.includes(kw))) {
-         dbg('🔍 可能相關但未匹配:', url);
-         console.log('   JSON preview:', JSON.stringify(json).substring(0, 300));
-     }
+     // isUrlRelevant 在 debug 模式下已過濾關鍵字，能走到這裡代表 URL 含有相關關鍵字
+     dbg('🔍 可能相關但未匹配:', url);
+     console.log('   JSON preview:', json);
  }
```

### 修改 7：更新 `setStatus()` UI 版本標示

```diff
- _dot.title = PAGE.label + ' v4 — 攔截模式\n點擊重新載入頁面';
+ _dot.title = PAGE.label + ' v4.1 — 攔截模式\n點擊重新載入頁面';
```

---

## 效能影響分析

| 場景 | V4 行為 | V4.1 行為 | 改善 |
|------|--------|----------|------|
| 不相關的大型 JSON fetch（如對話記錄） | clone + async parse | **跳過** | 避免不必要的 CPU + 記憶體消耗 |
| 不相關的大型 JSON XHR | 同步 JSON.parse | **跳過** | 避免主線程阻塞 |
| 匹配到的 API（debug=true） | JSON.stringify 全量序列化 | console.log 直接傳參考 | 避免同步序列化大物件 |
| 匹配到的 API（debug=false） | 同上（因預設 true） | 正常處理，無 debug 開銷 | 預設零 debug 開銷 |

---

## 驗證方式

1. **靜態檢查：** 搜尋 `JSON.stringify` — 僅應出現在 `sendToServer` 的 payload 序列化（必須保留），不應出現在任何 `console.log` 中
2. **靜態檢查：** 確認 `isUrlRelevant` 在 `installFetchHook` 和 `installXHRHook` 中都位於 clone/parse 之前
3. **靜態檢查：** 確認 `config.debug` 預設值為 `false`
4. **手動測試：** Tampermonkey 安裝 v4.1 → 開啟 claude.ai/settings/usage：
   - Chrome DevTools Performance tab 中 CPU 使用率應明顯低於 V4
   - Console 預設不應有大量自動輸出
   - 資料仍正確傳送到 localhost:7890
5. **手動測試：** Console 執行 `__aimon.debug(true)` → 確認印出可展開物件（非截斷字串）

---

## 不在本次範圍內

- 不新增功能
- 不修改 transformer 邏輯
- 不調整 URL pattern / INTERCEPT_RULES
- 不修改 UI 外觀
- 不修改 server 通訊協定
