# AI 額度監控 - Windows 桌面小工具 實作計畫

> 建立日期：2026-02-26
> 目標：將 AI 額度監控移植為 Windows 桌面小工具，含翻頁時鐘，固定顯示於桌面

---

## 一、視覺設計

### 整體佈局（由上至下）

```
┌──────────────────────────────────┐  ← 拖拉區（隱形，右鍵選單）
│                                  │
│   ┌────────┐     ┌────────┐      │
│   │        │     │        │      │
│   │  1  3  │  :  │  2  0  │      │  ← 翻頁時鐘 (flip clock)
│   │        │     │        │      │
│   └────────┘     └────────┘      │
│       H               M          │
│            2026/2/26             │  ← 日期
│                                  │
├──────────────────────────────────┤
│ ● OpenAI 帳單                    │  ← 服務卡片 1
│   餘額 $123.45                   │
│   Credits ████████░░  75.0%      │
├──────────────────────────────────┤
│ ● Claude.ai 用量                 │  ← 服務卡片 2
│   本次工作階段 ██████░░  60%     │
│   每週限額   ████░░░░  45%       │
├──────────────────────────────────┤
│ ● Claude API 帳單                │  ← 服務卡片 3
│   本月 $5.12    餘額 $75.50      │
├──────────────────────────────────┤
│ ● GitHub Copilot                 │  ← 服務卡片 4
│   Individual   ✓ 啟用            │
├──────────────────────────────────┤
│ 最後更新: 14:32:15    ⟳          │  ← 狀態列
└──────────────────────────────────┘
```

### 尺寸
- 預設視窗大小：**360 × 620 px**
- 時鐘區塊：**360 × 160 px**
- 每個服務卡片：**360 × ~100 px**（依內容自適應）

### 翻頁時鐘設計（flip clock）
參考照片風格：
- 每個數字為圓角矩形磁貼，深色背景 + 白色數字
- 字型：大字體（建議使用 `Segoe UI` 或 `Consolas Bold`，72px）
- 翻頁動畫：用 tkinter Canvas 繪製，每秒以「上半/下半翻轉」模擬翻頁效果
- 時鐘顯示：`HH : MM`（小時與分鐘各兩個磁貼）
- 可選顯示秒數（第三組磁貼，較小）
- 日期顯示在時鐘下方，格式 `YYYY/M/D 星期X`

---

## 二、技術方案

### 框架選擇
| 項目 | 選擇 | 原因 |
|------|------|------|
| GUI 框架 | **tkinter** | 與現有專案一致，無需額外依賴 |
| 桌面層級 | **Win32 ctypes** | 將視窗置於桌面層（HWND_BOTTOM） |
| 系統匣 | **pystray + Pillow** | 系統匣圖示與右鍵選單 |
| 翻頁動畫 | **tkinter Canvas** | 原生繪製，無外部依賴 |

### 桌面層級視窗實作
```python
import ctypes

def set_window_to_desktop_level(hwnd):
    """將視窗置於所有視窗底層（桌面層級）"""
    HWND_BOTTOM = 1
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOACTIVATE = 0x0010
    ctypes.windll.user32.SetWindowPos(
        hwnd, HWND_BOTTOM, 0, 0, 0, 0,
        SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE
    )
```

> **注意：** 採用 `HWND_BOTTOM` 方法，按 `Win+D` 顯示桌面時視窗會消失（與 Windows 桌面小工具行為一致）。
> 若需在顯示桌面後仍可見，可改用 WorkerW 父視窗嵌入方式（實作複雜度較高，列為可選）。

---

## 三、新增檔案結構

```
ai-quota-monitor/
├── widget_main.py                  # 桌面小工具獨立入口點
├── widget_build.spec               # PyInstaller 打包設定
├── desktop_widget/
│   ├── __init__.py
│   ├── app.py                      # DesktopWidget 主視窗類別（tk.Tk）
│   ├── clock.py                    # FlipClock 翻頁時鐘元件（Canvas）
│   ├── cards.py                    # CompactServiceCard 精簡服務卡片元件
│   ├── tray.py                     # SystemTray 系統匣圖示（pystray）
│   └── styles.py                   # COLORS、字型常數（從 gui/widgets.py 提取）
```

### 不修改的現有檔案
- `main.py` — 主視窗入口不動
- `services/` — 完全複用
- `config/manager.py` — 擴充 widget 設定區塊，不破壞現有結構

---

## 四、各檔案說明

### `widget_main.py`
- 啟動 `local_server`（若未執行）
- 建立 `DesktopWidget` 視窗
- 建立 `SystemTray` 並與視窗連結
- 啟動 tkinter mainloop

### `desktop_widget/app.py` — DesktopWidget
- 繼承 `tk.Tk`
- `wm_overrideredirect(True)` — 無標題列
- `wm_attributes('-alpha', opacity)` — 半透明
- 讀取 config 中 `widget.x / widget.y` 還原上次位置
- 右鍵選單（替代標題列）：
  - 移至最上層 / 固定在桌面層
  - 開啟完整視窗（啟動 main.py）
  - 設定（透明度、尺寸）
  - 離開
- 拖拉移動：滑鼠左鍵按住拖拉
- 每秒呼叫 `FlipClock.tick()`
- 每 1.5 秒呼叫 `_poll_browser_live()`（複用現有邏輯）
- 每 200ms 呼叫 `_poll_queue()` 更新服務卡片

### `desktop_widget/clock.py` — FlipClock
```
class FlipClock(tk.Frame):
    - __init__(parent, width, height)
    - tick()                      # 每秒呼叫，更新時間並觸發翻頁動畫
    - _draw_digit(canvas, digit)  # 在 Canvas 上繪製單個數字磁貼
    - _animate_flip(canvas, old, new)  # 翻頁動畫（10 步，每步 16ms）
    - _draw_date()               # 更新日期文字
```

翻頁動畫原理：
1. 繪製「上半靜止」（新數字）+ 「下半翻轉中」（舊數字漸縮）
2. 共 10 幀，每幀 16ms（~60fps）
3. 用 Canvas `coords` + `itemconfig` 更新，不重建元件

### `desktop_widget/cards.py` — CompactServiceCard
- 精簡版 `ServiceCard`，適合小尺寸
- 每張卡片顯示：服務名稱、2~3 個關鍵數值、進度條（若有）
- `update_result(ServiceResult)` — 更新顯示
- `set_loading()` — 顯示載入中

### `desktop_widget/tray.py` — SystemTray
```
class SystemTray:
    - __init__(widget_app)
    - start()        # 在背景執行緒啟動 pystray
    - stop()
    - _on_show()     # 顯示/隱藏視窗
    - _on_open_main()  # 啟動主視窗 (subprocess)
    - _on_quit()
```

---

## 五、設定擴充

### config/manager.py 新增 `widget` 區塊
```json
{
  "widget": {
    "x": -1,
    "y": -1,
    "width": 360,
    "height": 620,
    "opacity": 0.92,
    "desktop_level": true,
    "show_seconds": false,
    "minimized": false
  }
}
```
- `x / y = -1` 代表首次啟動自動置中（右下角）
- `desktop_level`: true = HWND_BOTTOM，false = 一般浮動視窗

---

## 六、相依套件

### requirements.txt 新增
```
pystray>=0.19.4
Pillow>=9.0.0
```
（`ctypes` 為 Python 標準庫，無需安裝）

---

## 七、實作步驟（Phase）

### Phase 1 — 基本框架（無動畫、靜態顯示）
1. 建立 `desktop_widget/__init__.py`
2. 建立 `desktop_widget/styles.py`（從 `gui/widgets.py` 提取 COLORS、字型）
3. 建立 `desktop_widget/clock.py`（靜態時鐘，無翻頁動畫）
4. 建立 `desktop_widget/cards.py`（精簡服務卡片）
5. 建立 `desktop_widget/app.py`（組合視窗，可拖拉，無邊框）
6. 建立 `widget_main.py`（入口，啟動服務器 + 視窗）
7. **驗收**：能執行、能顯示時鐘與空白卡片、能拖拉移動

### Phase 2 — 資料整合
8. 在 `app.py` 複用 `local_server`、`browser_data` 服務
9. 移植 `_poll_browser_live()` 與 `_poll_queue()` 邏輯
10. `CompactServiceCard.update_result()` 顯示真實資料
11. **驗收**：有瀏覽器資料時，卡片正確更新

### Phase 3 — Win32 桌面整合
12. 實作 `set_window_to_desktop_level()` (ctypes)
13. 加入位置儲存/還原（讀寫 config `widget.x/y`）
14. 加入右鍵選單
15. **驗收**：視窗固定在桌面層，位置記憶正確

### Phase 4 — 翻頁動畫
16. 完善 `FlipClock`，加入 Canvas 翻頁動畫
17. 加入秒數顯示選項
18. **驗收**：每秒翻頁動畫流暢

### Phase 5 — 系統匣 & 收尾
19. 建立 `desktop_widget/tray.py`（pystray）
20. 最小化/還原、開啟主視窗、離開
21. 建立 `widget_build.spec`（PyInstaller 打包）
22. 測試打包後的 `.exe`
23. **驗收**：系統匣圖示正確，打包後可獨立執行

---

## 八、打包設定

### widget_build.spec 重點
```python
# 入口改為 widget_main.py
# 輸出名稱: AI額度監控-桌面小工具.exe
# 與主程式共用相同的 services/、config/ 目錄
```

---

## 九、與現有程式的關係

| 項目 | 說明 |
|------|------|
| 主程式 `main.py` | **完全不修改** |
| `services/` | **完全複用**，不修改 |
| `gui/` | **不修改**，桌面小工具有獨立 UI |
| `config/manager.py` | **擴充** widget 設定區塊，向下相容 |
| 同時執行 | 主視窗與桌面小工具**可同時執行**（共用同一個 local_server） |

---

## 十、已知限制

1. **Win+D 顯示桌面** — 使用 `HWND_BOTTOM` 時，視窗會隨桌面一起隱藏（符合一般使用者預期）
2. **pystray 圖示** — 需動態產生 PNG 圖示（用 Pillow 繪製），不依賴外部 ICO 檔案
3. **翻頁動畫** — tkinter Canvas 動畫在低效能機器可能略有延遲
4. **多螢幕** — 首次啟動自動偵測主螢幕右下角，多螢幕位置記憶依賴 config x/y

---

## 附：翻頁時鐘 Canvas 草圖

```
 ┌──────────────────────────────────────┐
 │         ← 時鐘區 160px 高 →          │
 │                                      │
 │  ┌──────┐ ┌──────┐   ┌──────┐ ┌──────┐ │
 │  │  1   │ │  3   │ : │  2   │ │  0   │ │  ← 數字磁貼
 │  └──────┘ └──────┘   └──────┘ └──────┘ │    (Canvas, 圓角矩形)
 │     H         H    :     M        M    │
 │                                      │
 │           2026/2/26 星期四           │  ← 日期文字
 └──────────────────────────────────────┘

 單個磁貼：
 ┌─────────┐  ← 圓角矩形背景 (#1a1a2e)
 │─────────│  ← 中線分隔（淡灰色）
 │    1    │  ← 白色大字，Consolas Bold 72px
 └─────────┘
 翻頁時：下半部高度從 50% → 0% → (新數字) → 50%
```
