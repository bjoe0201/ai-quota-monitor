# AI 額度監控 · v4.2.0

一個跨平台（Windows / macOS）桌面應用程式，搭配 Tampermonkey 瀏覽器腳本，即時監控各 AI 服務的使用額度與費用。
另附輕量**桌面小工具**版本，可常駐桌面顯示翻頁時鐘與即時額度。

---

## 支援服務

| 服務 | 擷取來源 | 查看項目 |
|------|----------|----------|
| **OpenAI 帳單** | platform.openai.com | 帳戶餘額、Credits 使用量、月消費 |
| **Claude.ai 用量** | claude.ai | 工作階段配額、每週配額、**額外用量（已花費／上限／餘額／自動儲值）** |
| **Claude API 帳單** | platform.claude.com | 帳戶餘額、方案資訊、本月用量 |
| **GitHub Copilot** | github.com | Premium Requests 用量、重置日期 |

---

## 運作原理

```
瀏覽器 (Tampermonkey)          桌面應用程式 (Python)
        │                               │
        │  POST /update (資料)  ────►   │  local_server (port 7890)
        │                               │
        │  GET /poll?seq=N   ◄────      │  GUI 按「重新整理」
        │                               │
        └── 偵測到變化 → 立即擷取並回傳 ──►│  更新卡片顯示
```

1. 桌面程式在 `localhost:7890` 啟動一個輕量 HTTP 伺服器
2. Tampermonkey 腳本偵測對應頁面，自動擷取額度資料，透過 `POST /update` 傳送
3. 桌面程式每 1.5 秒輪詢 DATA_STORE，有新資料即更新對應卡片
4. 桌面程式按「重新整理」時，透過 `/poll` 通知所有 JS 立即重新擷取

---

## 安裝步驟

### 1. 安裝桌面應用程式

#### macOS

> **需求**：Python 3.11+（含 Tcl/Tk 8.6）。系統內建 Python 3.9 不相容，請先安裝：
> ```bash
> brew install python@3.11 python-tk@3.11
> ```

```bash
git clone https://github.com/bjoe0201/ai-quota-monitor.git
cd ai-quota-monitor
pip3.11 install -r requirements.txt
```

雙擊 `start.command` 即可啟動（首次需在終端機執行 `chmod +x start.command`）。

#### Windows

```bash
git clone https://github.com/bjoe0201/ai-quota-monitor.git
cd ai-quota-monitor
pip install -r requirements.txt
python main.py
```

### 2. 安裝 Tampermonkey 瀏覽器腳本

本專案提供以下版本的腳本，**建議使用 V4.1**：

| 版本 | 檔案 | 方式 | 狀態 |
|------|------|------|------|
| **V4.1（推薦）** | `ai-monitor-client-v4.1.js` | API 攔截（URL 前置過濾 + 效能優化） | ✅ 目前維護 |
| V4 | `ai-monitor-client-v4.js` | API 攔截（零 DOM 依賴） | ✅ 可用 |

> ℹ️ V4.1 在 V4 基礎上新增 URL 前置過濾與精準解析，效能更佳，Chrome 上的卡頓問題已改善。

> ⚠️ **已知問題（Chrome / Windows 11）**：在 Windows 11 上使用 Chrome 瀏覽器時，Tampermonkey 腳本可能造成頁面輕微卡頓。若遇到此問題，建議改用 **Firefox** 執行腳本。

**安裝步驟：**
1. 安裝瀏覽器擴充套件 [Tampermonkey](https://www.tampermonkey.net/)
2. 開啟 Tampermonkey > 新增腳本
3. 將 `ai-monitor-client-v4.1.js` 全部內容貼入並儲存
4. 開啟以下任一支援頁面，腳本會自動開始擷取：

| 頁面 | URL |
|------|-----|
| OpenAI 帳單 | `https://platform.openai.com/settings/organization/billing/overview` |
| Claude.ai 用量 | `https://claude.ai/settings/usage` |
| Claude API 帳單 | `https://platform.claude.com/settings/billing` |
| GitHub Copilot | `https://github.com/settings/copilot/features` |

### 3. 確認連線

頁面右下角會出現 ⚡ 色點，綠色表示資料已成功傳送至桌面程式。

---

## 桌面小工具（Desktop Widget）

輕量版常駐小工具，為預設啟動畫面，與主視窗共用同一資料來源（port 7890）。

### 啟動方式

| 平台 | 方式 |
|------|------|
| **macOS** | 雙擊 `start.command` |
| **Windows** | 雙擊 `start_widget.bat` |

```bash
# 直接執行
python widget_main.py
```

### 功能特色

| 功能 | 說明 |
|------|------|
| **翻頁時鐘** | 動畫翻頁效果顯示 HH:MM + 秒數，底部顯示日期 |
| **4 張額度卡片** | 顯示與主視窗完全相同的資料欄位 |
| **無邊框浮動** | `wm_overrideredirect`，不出現於工作列 |
| **常駐桌面層** | Win32 `SetWindowPos HWND_BOTTOM`，不遮擋其他視窗 |
| **自動調整高度** | 資料載入後自動展開卡片高度 |
| **位置記憶** | 記錄每次拖曳後的位置，重開後還原；超出螢幕自動歸位 |
| **多螢幕支援** | 使用虛擬桌面座標驗證，第二顆螢幕（含負座標）位置正確還原 |
| **透明度調整** | 右鍵選單 > 透明度設定（0.3 ~ 1.0） |

### 操作方式

| 操作 | 說明 |
|------|------|
| **左鍵拖曳** | 移動視窗位置（自動儲存） |
| **右鍵選單** | 重新整理 / 固定桌面層 / Chrome 子選單 / Firefox 子選單 / 透明度 / 離開 |
| **⟳ 按鈕** | 狀態列右側，點擊立即重新整理所有卡片 |
| **系統匣圖示** | 右鍵可顯示/隱藏視窗或離開 |

### 建置獨立執行檔

#### Windows

```bash
pip install pyinstaller
pyinstaller widget_build.spec --clean
# 輸出：dist/AI額度監控-桌面小工具.exe
```

#### macOS

> **必須使用 Homebrew Python 3.11**（系統內建 Python 3.9 連結 Tcl/Tk 8.5，在 macOS 12+ 執行時會崩潰）：
> ```bash
> brew install python@3.11 python-tk@3.11
> /opt/homebrew/bin/python3.11 -m pip install pyinstaller requests pystray pillow psutil
> ```

```bash
/opt/homebrew/bin/python3.11 -m PyInstaller widget_build.spec --clean
# 移除 Gatekeeper 隔離屬性
xattr -dr com.apple.quarantine dist/AI額度監控.app
# 輸出：dist/AI額度監控.app（可拖至 Dock 使用）
```

---

## 瀏覽器腳本功能說明

### `ai-monitor-client-v4.1.js`（推薦）

V4.1 採用 **API 攔截**（Network Interception）架構，在頁面載入前安裝 `fetch` / `XHR` hook，並加入 URL 前置過濾與精準解析，自動擷取 API response 中的額度資料。

| 特性 | 說明 |
|------|------|
| **零 DOM 依賴** | 不讀取任何 DOM 元素，不受頁面改版影響 |
| **即時擷取** | API 回應到達時立即提取，無需定時輪詢 |
| **URL 前置過濾** | 僅攔截已知 API 路徑，減少不必要的處理開銷 |
| **合併傳送** | 2 秒合併視窗（debounce），多個 API 回應合併為一次傳送 |
| **變化偵測** | 僅在資料有變化時才傳送至伺服器 |
| **自動重載** | 資料過期後自動重新載入頁面（OpenAI 5 分鐘、Claude 3-5 分鐘、Copilot 10 分鐘） |
| **⚡ 狀態色點** | 右下角色點：🔵 監聽中 / 🟢 成功 / 🔴 錯誤 / ⚪ 無回應 |

#### Debug 模式

預設開啟 debug 輸出。在瀏覽器 Console 輸入以下指令：

```javascript
__aimon.debug()      // 切換 debug 開關
__aimon.status()     // 查看攔截狀態
__aimon.data()       // 查看最近擷取的資料
__aimon.flush()      // 強制送出暫存資料
__aimon.server(url)  // 設定伺服器位址
```

#### 各頁面攔截的 API

| 頁面 | 攔截的 API | 提取欄位 |
|------|------------|----------|
| **OpenAI** | `/billing/subscription`、`/billing/credit_grants` | 方案、餘額、硬上限、自動儲值 |
| **Claude.ai** | `/usage`、`/prepaid/credits`、`/prepaid/bundles` | 工作階段%、每週%、額外用量、餘額、重置日期 |
| **Claude API** | `/prepaid/credits`、`/current_spend`、`/rate_limits`、`/invoices` | 方案、餘額、本月用量、下次計費 |
| **Copilot** | `/copilot_usage_card`、`/copilot_usage_table` | Premium Requests 已用/總量/百分比、計費金額 |

---

## 桌面應用程式功能

| 操作 | 說明 |
|------|------|
| **⟳ 重新整理** | 通知所有瀏覽器頁面立即重新擷取，並更新顯示 |
| **⚙ 設定** | 設定自動更新間隔與本地伺服器 Port |
| 自動偵測 | 每 1.5 秒自動偵測瀏覽器傳來的新資料 |
| 自動更新 | 可設定每 5 / 15 / 30 / 60 分鐘自動通知瀏覽器重整 |

---

## 設定

### 更新間隔

透過桌面程式「設定」頁籤可調整：
- **自動更新間隔**：桌面程式定期通知 JS 重新擷取（預設 30 分鐘）
- **本地伺服器 Port**：預設 `7890`，需與 JS 腳本設定一致

V4.1 腳本的自動重載間隔為內建設定，各頁面獨立：

| 服務 | 自動重載間隔 |
|------|-------------|
| OpenAI 帳單 | 5 分鐘 |
| Claude.ai 用量 | 3 分鐘 |
| Claude API 帳單 | 5 分鐘 |
| GitHub Copilot | 10 分鐘 |

> V4.1 在資料過期（超過上述間隔未收到新 API 回應）時自動重新載入頁面，無需手動設定。

### 設定檔位置

| 作業系統 | 路徑 |
|----------|------|
| Windows | `C:\Users\<帳號>\.config\ai-quota-monitor\config.json` |
| macOS | `~/.config/ai-quota-monitor/config.json` |

---

## 常見問題

**Q: 桌面程式卡片顯示「等待瀏覽器連線...」？**
> 確認 Tampermonkey 腳本已安裝，且已開啟對應的 AI 服務頁面。

**Q: 瀏覽器腳本狀態點一直是紅色？**
> 確認桌面程式已執行，且伺服器位址與程式 Port 設定一致（預設 `http://localhost:7890`）。可在 Console 輸入 `__aimon.server()` 查看目前設定。

**Q: 按「重新整理」後卡片沒有更新？**
> 瀏覽器需要開啟對應頁面且腳本在執行中。V4.1 會在頁面載入時自動擷取 API 回應，無需手動觸發。

**Q: 顯示「未偵測到 API 回應」？**
> 在 Console 執行 `__aimon.debug(true)`，若無任何 `✅ 匹配 API` 輸出，請重新載入頁面。若仍無效，可能是網站 API 路徑已變更，請通報 issue。

**Q: macOS 上無法開啟 .app 檔案？**
> 在 Finder 中對 .app 按右鍵 > 開啟，或執行：`xattr -dr com.apple.quarantine dist/AI額度監控.app`

**Q: macOS 上 .app 開啟後立即崩潰（Abort trap / NSUpdateCycleInitialize）？**
> 必須使用 Homebrew Python 3.11 打包。系統 Python 3.9 使用 Tcl/Tk 8.5（macOS 12+ 已損壞），Homebrew Python 3.11 使用 Tcl/Tk 8.6。另外 `widget_build.spec` 使用 onedir 模式（非 onefile），因為 macOS 安全機制不允許 .app bundle 在執行時解壓縮至 /tmp。

**Q: 桌面小工具重開後位置跑掉？**
> 若發生螢幕解析度變更或拔除副螢幕，偵測到位置超出虛擬桌面範圍時會自動歸位至主螢幕右下角。

---

## 技術架構

- **語言**：Python 3.11+
- **GUI 框架**：tkinter（自繪 Canvas 進度條、翻頁動畫，Catppuccin Macchiato 深色主題）
- **本地伺服器**：Python `http.server.ThreadingHTTPServer`（port 7890）
- **瀏覽器腳本**：Tampermonkey userscript（V4.1: `fetch`/`XHR` hook + URL 前置過濾 + `GM_xmlhttpRequest`）
- **系統匣**：pystray + Pillow
- **打包工具**：PyInstaller
- **設定儲存**：JSON
- **非同步更新**：threading + queue（避免 GUI 凍結）

### 目錄結構

```
ai-quota-monitor/
├── main.py                      # 主程式進入點（啟動桌面小工具）
├── widget_main.py               # 桌面小工具入口（含系統匣）
├── ai-monitor-client-v4.1.js   # Tampermonkey 瀏覽器腳本（V4.1 推薦）
├── ai-monitor-client-v4.js     # Tampermonkey 瀏覽器腳本（V4 可用）
├── start.command                # macOS 雙擊啟動腳本
├── start.bat / start.ps1        # Windows 啟動腳本
├── start_widget.bat             # Windows 小工具啟動腳本（無 CMD 視窗）
├── widget_build.spec            # PyInstaller 設定（onedir 模式）
├── gui/
│   ├── app.py                   # 主視窗（ServiceCard 管理、刷新邏輯）
│   └── widgets.py               # ServiceCard、ProgressBar 元件
├── desktop_widget/
│   ├── app.py                   # 桌面小工具主視窗
│   ├── clock.py                 # 翻頁時鐘（AnimatedDigit、FlipClock）
│   ├── cards.py                 # CompactServiceCard 精簡卡片
│   ├── styles.py                # 小工具樣式常數
│   └── tray.py                  # 系統匣圖示（pystray）
├── services/
│   ├── base.py                  # BaseService、ServiceResult
│   ├── browser_data.py          # 從 local_server 讀取瀏覽器資料
│   └── local_server.py          # HTTP 伺服器（/update、/poll、/status）
└── config/
    └── manager.py               # 設定讀寫
```

---

## 安全性與隱私

### 網路通訊
- 本應用在 `127.0.0.1:7890` 啟動本地 HTTP 伺服器，**僅允許本機存取**，外部網路無法連線
- Tampermonkey 腳本僅與 localhost 通訊，不經過任何第三方伺服器
- 所有資料僅在本機記憶體中暫存，程式關閉後自動清除

### 資料蒐集
本應用從您已登入的瀏覽器頁面擷取以下資訊，僅顯示於本機桌面，不上傳至任何外部服務：
- AI 服務的額度使用量與帳戶餘額
- 帳戶顯示名稱（僅用於 GUI 顯示）

### 設定檔安全性
> ⚠️ 若您曾設定 API keys 或 session cookies，這些資訊以 **Base64 編碼（非加密）** 儲存於本機設定檔，請注意保護該檔案：

```bash
# macOS / Linux — 限制設定檔只有自己可讀寫
chmod 600 ~/.config/ai-quota-monitor/config.json
```

設定檔位置：
- Windows：`C:\Users\<帳號>\.config\ai-quota-monitor\config.json`
- macOS / Linux：`~/.config/ai-quota-monitor/config.json`

---

## 版本紀錄

| 版本 | 主要變更 |
|------|----------|
| **v4.2.0** | 右鍵選單新增 Chrome / Firefox 分類子選單；更新 GitHub Copilot URL；調整使用量與計費數據顯示邏輯 |
| **v4.1.0** | JS 新增 URL 前置過濾與精準解析，效能優化；改善 Chrome 卡頓問題 |
| **v4.0.0** | JS 改採 API 攔截架構（fetch/XHR hook），零 DOM 依賴，不受頁面改版影響 |
| **v1.8.4** | macOS 一鍵開啟／關閉網頁改用 AppleScript；新增 `--openurl` 啟動參數 |
| **v1.8.3** | 一鍵開啟所有額度網頁至同一個新 Chrome 視窗；新增「一鍵關閉所有網頁」功能 |
| **v1.8.2** | macOS 完整支援；桌面小工具設為預設啟動；Claude.ai 額外用量顯示優化 |
| **v1.8.0** | 新增桌面小工具（翻頁時鐘 + 精簡卡片 + 系統匣） |
| **v1.7.0** | JS 新增自動重新整理頁面設定；GUI 新增開啟網頁下拉選單 |
| **v1.1.0** | 初始版本：Tampermonkey 瀏覽器擷取架構 |
