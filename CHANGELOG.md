# Changelog

本專案所有重要變更均記錄於此文件。

格式依循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)，
版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

---

## [Unreleased]

---

## [4.4.7] - 2026-06-06

### Fixed
- `ai-monitor-client-v4.4.js`：修復 Claude.ai Usage 頁面 hash 導航不觸發 API 問題（v4.4.7）
  - 根本原因：單純改 `location.hash` 屬於 SPA client-side 路由，不重新掛載 React 組件，故 Usage API 不會被呼叫
  - 修正：Python APP 開啟 `claude.ai/new?oclaw=1`（不含 hash），腳本偵測到無 `#settings/usage` 時先設定 `location.hash`，再立即 `location.reload()`，使瀏覽器以完整 URL `claude.ai/new?oclaw=1#settings/usage` 全新載入，SPA 從 `#settings/usage` 路由初始化，Usage 組件掛載時呼叫 API ✅
  - 移除 v4.4.6 的 sessionStorage 兩步驟暖機（導至 `/` 再跳回），改為更簡潔的 hash + reload 方式
- `gui/app.py`、`desktop_widget/app.py`：Claude.ai URL 移除 `#settings/usage` hash（改由 JS 腳本控制）

### Changed
- `ai-monitor-client-v4.4.js`：新增 `@match https://claude.ai/`（v4.4.6 起，保留至本版）
- 版號更新：`gui/app.py` v4.4.5 → v4.4.7；`desktop_widget/app.py` v4.4.5 → v4.4.7

---

## [4.4.5] - 2026-06-05

### Fixed
- `desktop_widget/app.py`、`gui/app.py`：修復 Claude.ai 用量頁面開啟後出現 ERR_QUIC_PROTOCOL_ERROR
  - 根本原因：直接開啟 `claude.ai/new#settings/usage` 時，SPA 尚未初始化，fetch hook 在過渡期間攔截聊天 API 導致 QUIC 串流損毀
  - 修正：開啟 Claude.ai 用量前先開 `https://claude.ai/`（新分頁）讓 SPA 完成初始載入，等待 1.5 秒後再開 Usage 頁面
  - 新增 `_open_url()` / `_open_in_chrome()` / `_open_in_firefox()` 的 Claude.ai 暖機邏輯
  - 「一鍵全開」（Chrome / Firefox）同步修正：先開其他頁，再以暖機流程開 Claude.ai 用量
  - macOS AppleScript 路徑亦同步處理
- `ai-monitor-client-v4.4.js`：`onDomReady()` 在 `/new` 聊天主頁（hash 不符）時仍安裝 SPA 偵測，確保使用者手動導航到 `#settings/usage` 時能補建 UI

### Changed
- `gui/app.py`：新增 `import time`；`_open_all_in_new_window` / `_open_all_in_firefox` 改用背景執行緒處理暖機延遲
- `desktop_widget/app.py`：新增 `import time`；同上

---

## [4.4.3] - 2026-06-05

### Fixed
- `ai-monitor-client-v4.4.js`：相容 claude.ai 新路由 `/new#settings/usage`（原 `/settings/usage` 已遷移）
  - `@match` 新增 `https://claude.ai/new*`
  - `isOnExpectedPage()` 加入 hash 判斷（`location.hash` 以 `settings/usage` 開頭才視為目標頁面）
  - fetch / XHR hook 加入早期退出：不在目標頁面時完全透通，防止干擾聊天主頁（修復 ERR_QUIC_PROTOCOL_ERROR）
  - SPA 偵測：從 `/new` 其他 hash 導航至 `#settings/usage` 時補建 UI
- `desktop_widget/app.py`：Claude.ai 用量開啟 URL 更新為 `claude.ai/new?oclaw=1#settings/usage` / `?oflaw=1`
- `gui/app.py`：同步更新 Claude.ai 用量 URL

---

## [4.4.2] - 2026-05-27

### Added
- `ai-monitor-client-v4.4.js`：新增 `@match https://github.com/settings/billing/budgets*`，支援 GitHub Billing Budgets 頁面
- `ai-monitor-client-v4.4.js`：新增 `parseDOMGitHubBudgets()`，解析 "All Premium Request SKUs" 預算列（`$X.XX spent` / `$Y.YY budget`），透過 `[class*="LinkText"]` 精確抓取金額
- `gui/widgets.py`：GitHub Copilot 卡片新增 **Premium SKUs 預算** 進度條（`budget_spent_usd` / `budget_limit_usd` / `budget_percent`）
- `desktop_widget/cards.py`：同步新增 Premium SKUs 預算進度條
- `desktop_widget/app.py` / `gui/app.py`：「開啟網頁」選單與一鍵全開（Chrome / Firefox）新增 `GitHub Budgets` 連結

### Changed
- `gui/app.py`：版號更新至 v4.4.2
- `desktop_widget/app.py`：`_WIDGET_VERSION` 更新至 v4.4.2
- `ai-monitor-client-v4.4.js`：github.com `expectedPath` 改為陣列，同時支援 `copilot/features` 與 `billing/budgets` 兩個路徑

---

## [4.4.1] - 2026-05-15

### Fixed
- `ai-monitor-client-v4.4.js`：OpenRouter `/settings/credits` 頁面改版後，原本依賴翻頁動畫 `translateY` 偏移量推算數字的邏輯會抓不到完整餘額（DOM 翻頁格數可能少於實際位數），改為**優先讀取容器 `aria-label="Remaining credits: X.XXX"`**，最精準且不受動畫狀態影響；翻頁動畫解析保留為 fallback

---

## [4.4.0] - 2026-05-09

### Added
- 新增 `CHANGELOG.md` 版本變更記錄

### Changed
- `README.md`：版本紀錄表格改為指向 `CHANGELOG.md` 的參考連結
- `.gitignore`：移除重複的 `dist/`、`build/`；`.vscode/` 改為只排除 `settings.json`；補充 `venv/`、`.venv/`、`env/`、`*.log`

---

## [4.3.0] - 2026-05-09

### Added
- `ai-monitor-client-v4.3.js`：新增 **OpenRouter** 監控支援（activity / credits）
- `services/browser_data.py`：新增 `BrowserOpenRouterService`
- `gui/app.py`：將 OpenRouter 加入 `SERVICES` 清單與 `BROWSER_SERVICE_SOURCES`
- `gui/widgets.py`：新增 OpenRouter 卡片顯示邏輯（帳戶餘額、本月花費、請求數、Tokens）
- `widget_build.spec` 打包支援 Windows 與 macOS（onedir 模式）

---

## [4.2.0] - 2026-05-01

### Added
- 右鍵選單新增 **Chrome / Firefox** 分類子選單，可一鍵開啟各服務監控頁面

### Changed
- 更新 GitHub Copilot 監控頁面 URL（`/settings/billing/premium_requests_usage`）
- 調整 Copilot 使用量與計費數據顯示邏輯

---

## [4.1.0] - 2026-04-15

### Changed
- `ai-monitor-client-v4.1.js`：新增 **URL 前置過濾**，僅攔截已知 API 路徑，減少不必要處理
- 精準解析各服務 API response 欄位
- 改善 Chrome on Windows 11 的頁面卡頓問題

---

## [4.0.0] - 2026-04-01

### Changed
- 瀏覽器腳本全面改採 **API 攔截架構**（`fetch` / `XHR` hook）
- 零 DOM 依賴，不受頁面改版影響
- 即時在 API 回應到達時提取資料，無需定時輪詢 DOM

---

## [1.12.0] - 2026-03-20

### Added
- 卡片標題列新增**展開／收合切換鈕**，並以服務 accent 色染色
- 時鐘左下角新增「全部展開／收合」icon 按鈕

### Changed
- 翻頁時鐘改為雙白卡片風格
- KV 資料改為兩兩成對 pair 排版
- 重置時間 pill 移至進度條同行
- 移除 Claude.ai 重複的「每週限額」欄位

---

## [1.8.4] - 2026-03-10

### Added
- macOS：一鍵開啟／關閉網頁改用 **AppleScript** 實作
- 新增 `--openurl` 啟動參數

---

## [1.8.3] - 2026-03-05

### Added
- **一鍵開啟所有額度網頁**至同一個新 Chrome 視窗
- 新增「一鍵關閉所有網頁」功能

---

## [1.8.2] - 2026-03-01

### Added
- macOS 完整支援（Homebrew Python 3.11 + Tcl/Tk 8.6）

### Changed
- 桌面小工具設為預設啟動入口
- Claude.ai 額外用量欄位顯示優化

---

## [1.8.0] - 2026-02-15

### Added
- **桌面小工具**（Desktop Widget）
  - 翻頁時鐘（AnimatedDigit + FlipClock）
  - 精簡額度卡片（CompactServiceCard）
  - 系統匣圖示（pystray）
  - 無邊框浮動視窗，常駐桌面底層
  - 位置記憶與多螢幕支援
  - 右鍵選單（透明度調整、重整、離開）

---

## [1.7.0] - 2026-02-01

### Added
- JS 腳本新增**自動重新整理頁面**設定（各服務獨立間隔）
- GUI 新增開啟網頁下拉選單

---

## [1.1.0] - 2026-01-01

### Added
- 初始版本
- Tampermonkey 瀏覽器擷取架構
- 本地 HTTP 伺服器（port 7890）接收瀏覽器資料
- tkinter GUI 顯示 OpenAI、Claude.ai、Claude API、GitHub Copilot 額度

---

[Unreleased]: https://github.com/bjoe0201/ai-quota-monitor/compare/v4.4.1...HEAD
[4.4.1]: https://github.com/bjoe0201/ai-quota-monitor/compare/v4.4.0...v4.4.1
[4.4.0]: https://github.com/bjoe0201/ai-quota-monitor/compare/v4.3.0...v4.4.0
[4.3.0]: https://github.com/bjoe0201/ai-quota-monitor/compare/v4.2.0...v4.3.0
[4.2.0]: https://github.com/bjoe0201/ai-quota-monitor/compare/v4.1.0...v4.2.0
[4.1.0]: https://github.com/bjoe0201/ai-quota-monitor/compare/v4.0.0...v4.1.0
[4.0.0]: https://github.com/bjoe0201/ai-quota-monitor/compare/v1.12.0...v4.0.0
[1.12.0]: https://github.com/bjoe0201/ai-quota-monitor/compare/v1.8.4...v1.12.0
[1.8.4]: https://github.com/bjoe0201/ai-quota-monitor/compare/v1.8.3...v1.8.4
[1.8.3]: https://github.com/bjoe0201/ai-quota-monitor/compare/v1.8.2...v1.8.3
[1.8.2]: https://github.com/bjoe0201/ai-quota-monitor/compare/v1.8.0...v1.8.2
[1.8.0]: https://github.com/bjoe0201/ai-quota-monitor/compare/v1.7.0...v1.8.0
[1.7.0]: https://github.com/bjoe0201/ai-quota-monitor/compare/v1.1.0...v1.7.0
[1.1.0]: https://github.com/bjoe0201/ai-quota-monitor/releases/tag/v1.1.0
