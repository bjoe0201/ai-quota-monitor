# CLAUDE.md

> **⚠️ 同步提示：** 本檔案（`CLAUDE.md`）與 `.github/copilot-instructions.md` 內容保持一致。
> 修改任一檔案時，請同步更新另一個檔案。

本檔案提供 Claude Code（claude.ai/code）在此專案中工作時的指引。

## 指令

```bash
# 安裝依賴套件
pip install -r requirements.txt

# 執行應用程式
python main.py

# 打包獨立執行檔
# Windows (.exe)
pyinstaller widget_build.spec
# 輸出：dist/AI額度監控-桌面小工具.exe

# macOS (.app) — 必須使用 Homebrew Python 3.11（系統內建 Python 3.9 的 Tcl/Tk 8.5 在 macOS 12+ 上會崩潰）
/opt/homebrew/bin/python3.11 -m PyInstaller widget_build.spec
# 輸出：dist/AI額度監控.app
# macOS 打包後需移除隔離屬性：
xattr -dr com.apple.quarantine dist/AI額度監控.app
```

本專案沒有測試套件。

## 架構

這是一個 Python 3.11+ tkinter 桌面應用程式，用於監控 AI 服務的額度使用量。應用程式有兩條資料取得路徑：**瀏覽器資料路徑**（目前啟用中）和 **API 路徑**（服務類別已存在，但尚未接入 `gui/app.py`）。

### 資料流程

**瀏覽器路徑（啟用中）：**
1. 使用者將 `ai-monitor-client.js` 安裝為 Tampermonkey 使用者腳本
2. 腳本抓取頁面資料（OpenAI 帳單、claude.ai 用量、platform.claude.com 帳單、GitHub Copilot 設定），並以 JSON 格式 POST 至 `http://localhost:7890/update`
3. `services/local_server.py` 接收 POST 請求，以 `source` 欄位為鍵儲存至模組層級的 `DATA_STORE` 字典
4. `MainApp._poll_browser_live()` 每 1.5 秒執行一次，檢查 `DATA_STORE` 是否有新時間戳，並啟動執行緒呼叫 `BrowserXxxService.fetch()` 讀取資料
5. 結果放入 `_result_queue`；`_poll_queue()` 每 200ms 在主執行緒呼叫 `ServiceCard.update_result()` 更新 UI

**執行緒模型：** 所有 `service.fetch()` 呼叫均在 daemon 執行緒中執行。結果透過 `queue.Queue` 傳回主（GUI）執行緒，由 `after(200, _poll_queue)` 定期清空。**禁止從 service 執行緒直接操作 tkinter 元件。**

### 關鍵模組

| 模組 | 職責 |
|---|---|
| `main.py` | 程式入口；處理 PyInstaller `sys._MEIPASS` 路徑修正，然後啟動 `DesktopWidget` |
| `widget_main.py` | 替代入口，同時啟動 `SystemTray` 與 `DesktopWidget`；由 `widget_build.spec` 使用 |
| `widget_build.spec` | macOS/Windows 打包用的 PyInstaller spec；使用 **onedir 模式**，搭配 `COLLECT` + `BUNDLE`（onefile 模式在 macOS 上因安全限制會崩潰） |
| `gui/app.py` | `MainApp(tk.Tk)` 管理視窗、服務卡片、刷新邏輯與設定對話框。頂部的 `SERVICES` 清單定義啟用的服務；`BROWSER_SERVICE_SOURCES` 將服務鍵對應至 `DATA_STORE` 的來源鍵 |
| `gui/widgets.py` | `ServiceCard` 小工具，含 `update_result()`、`set_loading()`。`_format_data()` 依 `service_name` 字串分支處理顯示邏輯；`COLORS` 字典定義深色主題（Catppuccin 風格）；`SERVICE_ACCENTS` 定義各服務卡片頂部色條 |
| `services/base.py` | `BaseService` 抽象基底類別，定義 `fetch(config) → ServiceResult`。`ServiceResult` 為 dataclass，包含 `service_name`、`success`、`data: dict`、`error` |
| `services/local_server.py` | 監聽 `127.0.0.1:7890` 的 `ThreadingHTTPServer`。模組層級的 `DATA_STORE: dict[str, dict]` 為共享資料庫；公開 API：`start(port)` / `stop()` / `is_running()` / `get_data(key)` / `request_refresh()` |
| `services/browser_data.py` | 四個 `BaseService` 子類別（每個監控頁面一個），從 `local_server.DATA_STORE` 讀取資料，並標記 `updated_at`；若資料超過 10 分鐘未更新則顯示過期警告 |
| `config/manager.py` | `ConfigManager` 讀寫 `~/.config/ai-quota-monitor/config.json`。敏感欄位（token、API 金鑰）在磁碟上以 Base64 編碼儲存（非加密）。`load()` 會將已儲存設定與 `DEFAULT_CONFIG` 合併，確保新增的鍵永遠有預設值 |
| `ai-monitor-client.js` | Tampermonkey 使用者腳本。執行各頁面的抓取器（`parseOpenAIBilling`、`parseClaudeUsage`、`parseClaudeBilling`、`parseGitHubCopilot`），並 POST 至本地伺服器。頁面內有浮動 UI（📊 按鈕）可查看狀態與設定 |
| `desktop_widget/tray.py` | `SystemTray` 使用 `pystray`。在 macOS 上必須呼叫 `icon.run_detached()`（不能在執行緒中呼叫 `icon.run()`），因為 AppKit 需要主執行緒，而主執行緒已被 tkinter 佔用 |

### 設定檔位置

- Windows：`C:\Users\<user>\.config\ai-quota-monitor\config.json`
- macOS/Linux：`~/.config/ai-quota-monitor/config.json`

## 慣例

### 新增服務

1. 建立 `services/your_service.py`，類別繼承 `BaseService`；設定 `name` 並實作 `fetch(config) → ServiceResult`
2. 在 `config/manager.py` 的 `DEFAULT_CONFIG["services"]` 中新增設定項目
3. 將服務實例加入 `gui/app.py` 的 `SERVICES` 清單；若為瀏覽器資料服務，同時在 `BROWSER_SERVICE_SOURCES` 新增對應的來源鍵
4. 在 `gui/widgets.py` 的 `ServiceCard._format_data()` 中新增對應 `service_name` 的顯示邏輯

### 未啟用的服務類別

`services/` 中包含基於 API 的服務類別（`claude_api.py`、`claude_web.py`、`github_copilot.py`、`github_copilot_web.py`、`openai_api.py`、`google_gemini.py`），這些類別**未**出現在 `gui/app.py` 的 `SERVICES` 清單中。若要重新啟用某服務，需將其加入 `SERVICES` 與 `BROWSER_SERVICE_SOURCES`（或修改 `refresh_all` 直接呼叫）。

### 打包注意事項

`widget_build.spec` 使用 **onedir 模式**（`COLLECT` + `BUNDLE`），不使用 onefile。onefile 模式在 macOS 上因安全限制會崩潰。

### 敏感設定欄位

Token 與 API 金鑰在寫入 `config.json` 前會以 Base64 編碼（非加密）。`ConfigManager.save()` 負責編碼，`load()` 負責解碼。請勿以明文儲存敏感資訊。

### UI 主題

所有顏色來自 `gui/widgets.py` 的 `COLORS` 字典（Catppuccin 風格深色主題）。各服務卡片頂部色條顏色由 `SERVICE_ACCENTS` 字典定義，以服務的 `name` 字串為鍵。
