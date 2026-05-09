# Changelog

本專案所有重要變更均記錄於此文件。

格式依循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)，
版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

---

## [Unreleased]

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

[Unreleased]: https://github.com/bjoe0201/ai-quota-monitor/compare/v4.4.0...HEAD
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
