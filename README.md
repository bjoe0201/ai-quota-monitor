# AI 額度監控 · 桌面小工具

> 跨平台（Windows / macOS）桌面小工具 + Tampermonkey 瀏覽器腳本，即時監控 OpenAI、Claude、GitHub Copilot、OpenRouter 的額度與費用。

<div align="center">
  <img src="PICS/2026-05-09%2015%2040%2018.jpg" alt="桌面小工具完整畫面" width="300">
</div>

---

## ✨ 功能亮點

- **翻頁時鐘**：動畫翻頁效果顯示目前時間，常駐桌面不遮擋視窗
- **5 個服務卡片**：Claude.ai、GitHub Copilot、OpenAI、Claude API、OpenRouter
- **即時同步**：開啟對應網頁，Tampermonkey 腳本自動擷取並推送至小工具
- **一鍵開啟**：右鍵選單可一鍵開啟所有監控頁面（支援 Chrome / Firefox）
- **透明度調整**：可設定視窗透明度（0.3 ~ 1.0），融入桌面背景
- **位置記憶**：拖曳位置自動儲存，支援多螢幕（含負座標）

---

## 支援服務

| 服務 | 監控來源 | 顯示資訊 |
|------|----------|----------|
| **Claude.ai** | claude.ai/new#settings/usage | 工作階段用量 %、每週限額 %、額外用量餘額 |
| **GitHub Copilot** | github.com/settings/copilot/features | Premium Requests 已用 / 總量 / % |
| **GitHub Budgets** | github.com/settings/billing/budgets | Premium SKUs 預算 spent / budget / % |
| **OpenAI** | platform.openai.com/settings/billing | 帳戶餘額、Credits 用量 %、月消費 |
| **Claude API** | platform.claude.com/settings/billing | 帳戶餘額、本月用量、下次計費日 |
| **OpenRouter** | openrouter.ai | 帳戶餘額、本月花費、請求數、Tokens |

---

## 螢幕截圖

<table>
<tr>
  <td align="center">
    <img src="PICS/2026-05-09%2015%2026%2055.jpg" width="220" alt="小工具主畫面"><br>
    <sub>小工具主畫面（部分展開）</sub>
  </td>
  <td align="center">
    <img src="PICS/2026-05-09%2015%2039%2008.jpg" width="220" alt="等待資料狀態"><br>
    <sub>等待瀏覽器資料中</sub>
  </td>
  <td align="center">
    <img src="PICS/2026-05-09%2015%2039%2016.jpg" width="220" alt="右鍵選單"><br>
    <sub>右鍵選單</sub>
  </td>
</tr>
<tr>
  <td align="center">
    <img src="PICS/2026-05-09%2015%2039%2025.jpg" width="220" alt="瀏覽器快速開啟子選單"><br>
    <sub>Chrome / Firefox 快速開啟子選單</sub>
  </td>
  <td align="center">
    <img src="PICS/2026-05-09%2015%2040%2018.jpg" width="220" alt="全部服務展開"><br>
    <sub>全部服務展開完整資訊</sub>
  </td>
  <td></td>
</tr>
</table>

---

## 🚀 快速開始

### 步驟一：安裝桌面程式

**Windows**

```bash
git clone https://github.com/bjoe0201/ai-quota-monitor.git
cd ai-quota-monitor
pip install -r requirements.txt
```

雙擊 `start_widget.bat` 啟動小工具，或執行：

```bash
python widget_main.py
```

**macOS**

> **需求**：Python 3.11+（含 Tcl/Tk 8.6）。系統內建 Python 3.9 不相容，請先安裝：
> ```bash
> brew install python@3.11 python-tk@3.11
> ```

```bash
git clone https://github.com/bjoe0201/ai-quota-monitor.git
cd ai-quota-monitor
pip3.11 install -r requirements.txt
```

雙擊 `start.command` 啟動（首次需在終端機執行 `chmod +x start.command`）。

---

### 步驟二：安裝 Tampermonkey 瀏覽器腳本

1. 安裝瀏覽器擴充套件 [Tampermonkey](https://www.tampermonkey.net/)
2. 開啟 Tampermonkey > **新增腳本**
3. 將 `ai-monitor-client-v4.4.js` 全部內容貼入並儲存

> ⚠️ **Chrome / Windows 11 輕微卡頓**：建議改用 **Firefox** 執行腳本。

#### 腳本版本

| 版本 | 檔案 | 說明 | 狀態 |
|------|------|------|------|
| **v4.4.7（推薦）** | `ai-monitor-client-v4.4.js` | v4.4.6 + 修復 Claude.ai hash 導航不觸發 Usage API：偵測 `?oclaw=1` 無 hash 時自動設定 hash 並 reload，確保 SPA 全新掛載 | ✅ 目前維護 |

---

### 步驟三：開啟監控頁面

在瀏覽器開啟以下頁面，腳本會自動偵測並擷取資料推送至小工具。

| 服務 | URL |
|------|-----|
| Claude.ai 用量 | `https://claude.ai/new#settings/usage` |
| GitHub Copilot | `https://github.com/settings/copilot/features` |
| GitHub Budgets | `https://github.com/settings/billing/budgets` |
| OpenAI 帳單 | `https://platform.openai.com/settings/organization/billing/overview` |
| Claude API 帳單 | `https://platform.claude.com/settings/billing` |
| OpenRouter | `https://openrouter.ai/settings/credits` |

> 💡 **小技巧**：在小工具上**右鍵 > Chrome（或 Firefox）> 一鍵開啟所有網頁**，可同時開啟全部頁面。

### 步驟四：確認連線

各頁面右下角會出現 ⚡ 色點：

| 顏色 | 狀態 |
|------|------|
| 🔵 藍色 | 監聽中 |
| 🟢 綠色 | 資料已成功推送至桌面程式 |
| 🔴 紅色 | 發生錯誤 |
| ⚪ 白色 | 無回應（桌面程式未執行） |

---

## 🖥 小工具操作說明

| 操作 | 功能 |
|------|------|
| **左鍵拖曳** | 移動視窗位置（自動儲存） |
| **右鍵選單** | 重新整理 / 固定桌面層 / 快速開啟瀏覽器頁面 / 透明度 / 離開 |
| **▼ / ▶ 按鈕** | 展開或收合各服務卡片 |
| **⟳ 按鈕** | 立即重新整理所有卡片 |
| **系統匣圖示** | 右鍵可顯示 / 隱藏視窗或離開 |

---

## 🔧 進階：建置獨立執行檔

不想每次都透過命令列啟動？可打包成獨立執行檔。

### Windows（`.exe`）

```bash
pip install pyinstaller
pyinstaller widget_build.spec --clean
# 輸出：dist/AI額度監控-桌面小工具.exe
```

### macOS（`.app`）

> 必須使用 Homebrew Python 3.11（系統內建 Python 3.9 的 Tcl/Tk 8.5 在 macOS 12+ 會崩潰）

```bash
brew install python@3.11 python-tk@3.11
/opt/homebrew/bin/python3.11 -m pip install pyinstaller requests pystray pillow psutil
/opt/homebrew/bin/python3.11 -m PyInstaller widget_build.spec --clean

# 移除 Gatekeeper 隔離屬性（否則會被阻擋）
xattr -dr com.apple.quarantine dist/AI額度監控.app
# 輸出：dist/AI額度監控.app（可拖至 Applications 或 Dock 使用）
```

---

## 🛠 運作原理

```
瀏覽器 (Tampermonkey)          桌面小工具 (Python)
        │                               │
        │  POST /update (資料)  ────►   │  local_server (port 7890)
        │                               │
        │  GET /poll?seq=N   ◄────      │  點擊「重新整理」
        │                               │
        └── 偵測到變化 → 立即擷取並回傳 ──►│  更新卡片顯示
```

1. 桌面程式在 `localhost:7890` 啟動輕量 HTTP 伺服器
2. Tampermonkey 腳本在對應頁面攔截 API 回應，透過 `POST /update` 推送資料
3. 桌面程式每 1.5 秒輪詢，有新資料即更新對應卡片
4. 按「重新整理」時，透過 `/poll` 通知所有腳本立即重新擷取

---

## 🐛 Debug 模式

安裝腳本後，在瀏覽器 Console（F12）輸入以下指令：

```javascript
__aimon.debug()      // 切換 debug 輸出開關
__aimon.status()     // 查看攔截狀態
__aimon.data()       // 查看最近擷取的資料
__aimon.flush()      // 強制送出暫存資料
__aimon.server(url)  // 設定伺服器位址（預設 http://localhost:7890）
```

---

## 各頁面攔截的 API

| 頁面 | 攔截的 API | 提取欄位 |
|------|------------|----------|
| **OpenAI** | `/billing/subscription`、`/billing/credit_grants` | 方案、餘額、硬上限、自動儲值 |
| **Claude.ai** | `/usage`、`/prepaid/credits`、`/prepaid/bundles` | 工作階段%、每週%、額外用量、餘額、重置日期 |
| **Claude API** | `/prepaid/credits`、`/current_spend`、`/rate_limits`、`/invoices` | 方案、餘額、本月用量、下次計費 |
| **Copilot** | `/copilot_usage_card`、`/copilot_usage_table` | Premium Requests 已用/總量/百分比 |
| **OpenRouter** | `/api/v1/auth/key`、`/api/frontend/stats/user` | 餘額、本月花費、請求數、Tokens、常用模型 |

---

## 版本記錄

詳見 [CHANGELOG.md](CHANGELOG.md)。

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

v4.4 腳本的自動重載間隔為內建設定，各頁面獨立：

| 服務 | 自動重載間隔 |
|------|-------------|
| OpenAI 帳單 | 5 分鐘 |
| Claude.ai 用量 | 3 分鐘 |
| Claude API 帳單 | 5 分鐘 |
| GitHub Copilot | 10 分鐘 |
| OpenRouter | 5 分鐘 |

> v4.4 在資料過期（超過上述間隔未收到新 API 回應）時自動重新載入頁面，無需手動設定。

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
> 瀏覽器需要開啟對應頁面且腳本在執行中。v4.4 會在頁面載入時自動擷取 API 回應，無需手動觸發。

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
- **瀏覽器腳本**：Tampermonkey userscript（v4.4: `fetch`/`XHR` hook + URL 前置過濾 + OpenRouter DOM 解析 + `GM_xmlhttpRequest`）
- **系統匣**：pystray + Pillow
- **打包工具**：PyInstaller
- **設定儲存**：JSON
- **非同步更新**：threading + queue（避免 GUI 凍結）

### 目錄結構

```
ai-quota-monitor/
├── main.py                      # 主程式進入點（啟動桌面小工具）
├── widget_main.py               # 桌面小工具入口（含系統匣）
├── ai-monitor-client-v4.4.js   # Tampermonkey 瀏覽器腳本（v4.4.1 推薦）
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

詳細更新內容請參閱 [CHANGELOG.md](CHANGELOG.md)。
