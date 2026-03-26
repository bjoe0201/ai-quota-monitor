# 計畫：新建極簡 Tampermonkey 腳本 (ai-monitor-client-v3.js)

## Context
原腳本 v2.4.x 因 UI 樣式、事件監聽、/poll 輪詢等累積複雜度，在某些頁面仍造成 Chrome 主執行緒卡頓。
使用者要求：**新建一個獨立的 JS 檔**，徹底移除非必要功能，只保留：
1. 定時自動擷取頁面資料
2. POST 到 localhost:7890
3. 一個手動觸發按鈕（純色點顯示狀態）

## 新檔案
`d:\GitHub\Tools2025\ai-quota-monitor\ai-quota-monitor\ai-monitor-client-v3.js`

（原 v2.4.2 保留不動，v3 為全新獨立腳本）

## 設計原則（極簡）
- **零 CSS 動畫**：完全不用 `animation`、`transition`，只換 `backgroundColor`
- **零 innerHTML 指派**：UI 用 `createElement` + `appendChild` 建立，不用 `.innerHTML =`
- **零 /poll 輪詢**：不再每 3 秒 GET /poll
- **零 GM_addStyle**：改用 inline style（`el.style.xxx`），不注入 `<style>`
- **最小 DOM**：只有一個固定位置的圓點按鈕（直徑 36px），點擊立即擷取
- **頁面解析**：完整保留四個 parser 的 regex 邏輯，`takePageSnapshot` 直接回傳 live DOM 節點

## 圓點 UI 規格
```
位置：position:fixed; bottom:16px; right:16px; z-index:2147483647
大小：width:36px; height:36px; border-radius:50%
顏色：
  idle    → #6c7086（灰）
  running → #f9e2af（黃）  // 純色，不 animate
  success → #a6e3a1（綠）
  error   → #f38ba8（紅）
點擊：呼叫 runExtraction()
title tooltip：顯示最後成功時間或錯誤訊息
```

## 保留功能
| 功能 | 保留 |
|------|------|
| PAGE_MAP / 頁面識別 | ✅ |
| GM_getValue/setValue 設定 | ✅（只保留 server_url 和 intervals） |
| waitForElement | ✅ |
| takePageSnapshot（live DOM） | ✅ |
| 四個 parser（openai/claude_usage/claude_billing/copilot） | ✅ |
| hasChange 比較，無變化略過傳送 | ✅ |
| sendToServer（GM_xmlhttpRequest） | ✅ |
| 定時器 setInterval | ✅ |
| SPA URL 輪詢（每 2 秒） | ✅ |
| requestIdleCallback 延遲啟動 | ✅ |

## 移除功能
| 功能 | 移除原因 |
|------|----------|
| GM_addStyle + 完整 CSS | 換 inline style |
| panel 展開面板（340px） | 不需要設定 UI |
| 快速開啟按鈕 / 一鍵全開 | 非核心 |
| /poll GUI 輪詢 | 使用者選擇移除 |
| toast 通知 | 非必要 |
| tab_refresh 定時重載 | 非必要 |
| 使用者活動追蹤（mousemove 等） | 配合 tab_refresh 才需要 |
| console.log 效能計時 | 減少噪音 |

## 關鍵檔案
- 新建：`ai-monitor-client-v3.js`
- 參考：`ai-monitor-client.js`（v2.4.2）的 parser 邏輯（第 590–866 行）

## 驗證方式
1. 在 Tampermonkey 新增 v3 腳本（停用 v2.4.2）
2. 開啟 `claude.ai/settings/usage`，確認右下角出現灰色圓點
3. 等待自動擷取（~2.5s 後）圓點變黃→綠
4. 確認桌面程式收到資料（DataStore 有 `claude_usage` 鍵）
5. 點擊圓點確認可手動觸發
6. 開啟 `platform.openai.com` 等其他頁面重複測試
7. 操作頁面過程中確認無卡頓感
