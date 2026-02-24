# AI 額度監控 · v1.7.0

一個跨平台（Windows / macOS）桌面應用程式，搭配 Tampermonkey 瀏覽器腳本，即時監控各 AI 服務的使用額度與費用。

---

## 支援服務

| 服務 | 擷取來源 | 查看項目 |
|------|----------|----------|
| **OpenAI 帳單** | platform.openai.com | 帳戶餘額、Credits 使用量、月消費 |
| **Claude.ai 用量** | claude.ai | 工作階段配額、每週配額、額外用量 |
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

```bash
git clone https://github.com/your-repo/ai-quota-monitor.git
cd ai-quota-monitor/ai-quota-monitor
pip install -r requirements.txt
python main.py
```

### 2. 安裝 Tampermonkey 瀏覽器腳本

1. 安裝瀏覽器擴充套件 [Tampermonkey](https://www.tampermonkey.net/)
2. 開啟 Tampermonkey > 新增腳本
3. 將 `ai-monitor-client.js` 的全部內容貼入並儲存
4. 開啟以下任一支援頁面，腳本會自動開始擷取：

| 頁面 | URL |
|------|-----|
| OpenAI 帳單 | `https://platform.openai.com/settings/organization/billing/overview` |
| Claude.ai 用量 | `https://claude.ai/settings/usage` |
| Claude API 帳單 | `https://platform.claude.com/settings/billing` |
| GitHub Copilot | `https://github.com/settings/billing/premium_requests_usage` |

### 3. 確認連線

頁面右下角會出現 📊 浮動按鈕，點擊開啟面板：
- 狀態點亮綠色（✓）表示資料已成功傳送至桌面程式
- 桌面程式卡片顯示最新數值即表示連線成功

---

## 瀏覽器腳本功能

點擊頁面右下角 📊 按鈕開啟控制面板：

| 功能 | 說明 |
|------|------|
| **▶ 立即擷取** | 手動觸發一次資料擷取並傳送 |
| **⏹ 停止** | 暫停自動擷取 |
| **💾 儲存** | 儲存擷取間隔、頁面重刷間隔與伺服器位址設定 |
| **自動重新整理頁面** | 設定分頁自動 reload 間隔（0~600 秒，0 = 停用），各頁面獨立 |
| **快速開啟頁面** | 一鍵跳轉至各 AI 服務頁面 |
| **🚀 一鍵全開** | 同時在新分頁開啟全部 4 個支援頁面 |

腳本會自動偵測數值是否變化，**僅在數值更新時才傳送**，節省頻寬。

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

透過 JS 面板可個別調整各頁面的設定：

| 服務 | 擷取間隔 | 頁面重刷間隔 |
|------|----------|--------------|
| OpenAI 帳單 | 120 秒 | 0 秒（停用）|
| Claude.ai 用量 | 60 秒 | 0 秒（停用）|
| Claude API 帳單 | 120 秒 | 0 秒（停用）|
| GitHub Copilot | 180 秒 | 0 秒（停用）|

> **頁面重刷**：設定 > 0 時，頁面會在指定秒數後自動重新載入（0~600 秒，預設 0 = 停用），各頁面獨立設定。

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
> 確認桌面程式已執行，且 JS 面板中的「本地伺服器位址」與程式 Port 設定一致（預設 `http://localhost:7890`）。

**Q: 按「重新整理」後卡片沒有更新？**
> 瀏覽器需要開啟對應頁面且腳本在執行中。按下重新整理後，JS 最多 3 秒內收到通知並開始擷取。

**Q: 一鍵全開只開啟了一個分頁？**
> 已改用 `GM_openInTab` API 解決瀏覽器彈出視窗封鎖問題（v1.4.0 起修正）。

**Q: macOS 上無法開啟 .app 檔案？**
> 在 Finder 中對 .app 按右鍵 > 開啟，或執行：`xattr -cr dist/AI額度監控.app`

---

## 技術架構

- **語言**：Python 3.11+
- **GUI 框架**：tkinter（自繪 Canvas 進度條，Catppuccin Macchiato 深色主題）
- **本地伺服器**：Python `http.server.ThreadingHTTPServer`（port 7890）
- **瀏覽器腳本**：Tampermonkey userscript（`GM_xmlhttpRequest`、`GM_openInTab`）
- **打包工具**：PyInstaller
- **設定儲存**：JSON
- **非同步更新**：threading + queue（避免 GUI 凍結）

### 目錄結構

```
ai-quota-monitor/
├── main.py                  # 程式進入點
├── ai-monitor-client.js     # Tampermonkey 瀏覽器腳本 (v1.6.0)
├── gui/
│   ├── app.py               # 主視窗、卡片佈局、排程
│   └── widgets.py           # ServiceCard、ProgressBar 元件
├── services/
│   ├── base.py              # BaseService、ServiceResult
│   ├── browser_data.py      # 從 local_server 讀取瀏覽器資料
│   └── local_server.py      # HTTP 伺服器（/update、/poll、/status）
└── config/
    └── manager.py           # 設定讀寫
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
| **v1.7.0** | JS 新增「自動重新整理頁面」設定（0~600 秒，各頁面獨立）；GUI 新增「🌐 開啟網頁」下拉選單 |
| **v1.6.0** | GUI 按「重新整理」即時通知 JS 重新擷取；修正卡片寬度；版號同步 |
| **v1.5.0** | GUI 美化（Catppuccin 主題、Canvas 進度條、雙欄卡片）；版號顯示 |
| **v1.4.0** | 一鍵全開改用 `GM_openInTab` 解決彈出視窗封鎖問題；數值變化偵測 |
| **v1.3.0** | 新增快速開啟頁面按鈕、一鍵全開功能 |
| **v1.2.0** | 修正 Claude API 帳單餘額抓取（改用 DOM `data-testid` 定位） |
| **v1.1.0** | 初始版本：Tampermonkey 瀏覽器擷取架構 |
