# Variant B — Linear / Raycast 風格 設計規格與實作指南

> 本文件提供給負責修改 `bjoe0201/ai-quota-monitor` Python tkinter 程式碼的 AI agent 使用。
> 目標：把現有的 Catppuccin Macchiato UI 升級為 **Variant B（高對比、現代、Linear / Raycast 風格）**。
>
> **必讀檔案**：
> - `gui/widgets.py` — `ServiceCard`、`ProgressBar`（主視窗卡片）
> - `gui/app.py` — 主視窗
> - `desktop_widget/cards.py` — `CompactServiceCard`（小工具卡片）
> - `desktop_widget/styles.py` — 樣式常數
> - `desktop_widget/app.py` — 小工具主視窗
> - `desktop_widget/clock.py` — 翻頁時鐘
>
> **HTML 設計參考**：開啟 `B-Version-Preview.html` 對照視覺。

---

## 1. 設計 Token（請替換 `desktop_widget/styles.py` 與 `gui/widgets.py` 內 `COLORS`）

```python
# 取代 gui/widgets.py 的 COLORS
COLORS = {
    # 背景
    "bg":            "#0a0a0c",  # 視窗外圍 / 主視窗背景
    "card_bg":       "#111114",  # 卡片背景
    "card_bg_hover": "#16161a",  # 卡片 hover
    "title_bg":      "#0a0a0c",  # 標題列（不再做明顯色塊）
    "row_alt":       "#111114",  # 取消斑馬紋（B 版用底線分隔）

    # 邊框
    "border":        "#1f1f24",  # 主邊框、卡片邊框、KV 列底線
    "border_strong": "#2a2a32",  # 較明顯的邊框（例如選中狀態）
    "card_border":   "#1f1f24",  # 沿用舊 key 名稱

    # 文字（提高對比！這是優化重點之一）
    "text":          "#fafafa",  # 主文字
    "text_muted":    "#a1a1aa",  # 次要說明
    "text_dim":      "#71717a",  # 標籤、timestamp
    "text_faint":    "#52525b",  # 最弱化（例如 :秒數）
    "subtext":       "#71717a",  # 沿用舊 key 名稱

    # 語意色（Tailwind/Linear 風格，比 Catppuccin 飽和度高）
    "success":       "#34d399",  # 綠（餘額、自動儲值已啟用）
    "warning":       "#fbbf24",  # 黃（即將達上限）
    "error":         "#f87171",  # 紅（錯誤、>=85%）
    "info":          "#60a5fa",  # 藍（一般進度條 <60%）
    "violet":        "#a78bfa",  # 紫（重置時間、下次計費）
    "peach":         "#fbbf24",  # 沿用舊 key（已計費金額）

    # 其他舊 key 名稱沿用
    "green":         "#34d399",
    "accent":        "#60a5fa",
    "mauve":         "#a78bfa",
    "teal":          "#34d399",
}

# 服務頂端色塊（用來取代 SERVICE_ACCENTS；變化不大，提高飽和度）
SERVICE_ACCENTS = {
    "OpenAI 帳單 (瀏覽器)":     "#60a5fa",  # blue-400
    "Claude.ai 用量 (瀏覽器)":  "#a78bfa",  # violet-400
    "Claude API 帳單 (瀏覽器)": "#c084fc",  # purple-400
    "GitHub Copilot (瀏覽器)":  "#34d399",  # emerald-400
    "OpenRouter (瀏覽器)":      "#818cf8",  # indigo-400
}

# 桌面小工具的 WIDGET_* 文字色（覆蓋 desktop_widget/styles.py）
WIDGET_LABEL   = "#71717a"   # 取代 #a8b0d0
WIDGET_TEXT    = "#fafafa"   # 取代 #e2e8ff
WIDGET_SUBTEXT = "#52525b"   # 取代 #8890b8
```

---

## 2. 字型與字級

```python
# 在 styles.py 頂端加入（Windows + macOS 共通替代字型）
import platform

if platform.system() == "Darwin":
    UI_FONT = "SF Pro Text"      # macOS 系統字
    MONO_FONT = "SF Mono"
else:
    UI_FONT = "Segoe UI Variable"  # Win 11；不存在會 fallback Segoe UI
    MONO_FONT = "Cascadia Mono"    # Win 11 內建；fallback Consolas

# 字級規則（B 版）
FONT_TITLE       = (UI_FONT, 11, "bold")     # 卡片標題（Service short name）
FONT_HERO        = (MONO_FONT, 28, "bold")   # ★ 主數字（餘額 / 百分比）— 比舊版大很多
FONT_HERO_UNIT   = (MONO_FONT, 14)           # 主數字旁的單位 / 分母（如 /1500）
FONT_HERO_LABEL  = (UI_FONT, 8, "bold")      # 主數字上方的小標（uppercase）
FONT_KV_LABEL    = (UI_FONT, 9)              # KV 列左側標籤
FONT_KV_VALUE    = (MONO_FONT, 10, "bold")   # KV 列右側數值
FONT_BAR_LABEL   = (UI_FONT, 9)              # 進度條標題
FONT_BAR_PCT     = (MONO_FONT, 9, "bold")    # 進度條百分比
FONT_BAR_DETAIL  = (MONO_FONT, 8)            # 進度條下方細節（金額/次數）
FONT_RESET_PILL  = (MONO_FONT, 8, "bold")    # 重置時間 pill
FONT_BADGE       = (UI_FONT, 8)              # 方案 badge
FONT_TIMESTAMP   = (MONO_FONT, 8)            # 右上 timestamp

# tkinter 不直接支援 tabular-nums / letter-spacing，
# 但用等寬字（Mono）就能達到「對齊」效果。
# 所有金額、百分比、時間、tokens 數字都必須用 MONO_FONT。
```

---

## 3. 卡片結構（每張 ServiceCard 的新版本）

舊版結構（label-value 雙欄、斑馬紋）→ 新版結構（Hero + KV stack + 底線分隔）：

```
┌──────────────────────────────────────┐
│ ▣  OpenAI         · 13:42:08         │ ← Header（22×22 色塊圖示 + 短名 + 右側 timestamp）
├──────────────────────────────────────┤
│                                      │
│  帳戶餘額                            │ ← Hero label（uppercase, 8pt, dim）
│  $42.18                              │ ← Hero value（28pt mono bold）
│                                      │
│  ─────────────────────────────       │
│                                      │
│  Credits 用量              74.8%     │ ← Bar label + percent
│  ▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▱▱▱▱▱▱▱▱▱▱      │ ← 28-segment progress bar
│  $3.74 / $5.00          [↻ 5d 後]   │ ← Detail + reset pill
│                                      │
│  本月用量              $1.2341       │ ← KV row（底線分隔）
│  ─────────────────                   │
│  月上限                $120          │
│  ─────────────────                   │
│  用量等級              Tier 1        │
│  ─────────────────                   │
│  自動儲值              已啟用         │ ← 最後一列無底線
└──────────────────────────────────────┘
```

### 視覺重量階層
1. **Hero metric**（28pt）— 每張卡片只有一個
2. **進度條 + 百分比**
3. **KV pairs**（10pt mono）

### 服務的 Hero 取捨原則
| 服務 | Hero 顯示 | Hero 顏色 |
|------|----------|----------|
| OpenAI | 帳戶餘額（金額） | success 綠 |
| Claude.ai 用量 | 每週限額剩餘百分比 | 跟著 pctTone 變色 |
| Claude API | 帳戶餘額（金額） | success 綠 |
| GitHub Copilot | Premium Requests **剩餘次數**（不是已用次數） | 跟著 pctTone 變色 |
| OpenRouter | 帳戶餘額（金額） | success 綠 |

---

## 4. 進度條（重大變更）

把 `gui/widgets.py` 的 `ProgressBar` 從「圓角整條」改為「28 格分段」（Linear/Raycast 風格）：

```python
class ProgressBar(tk.Canvas):
    HEIGHT = 8
    SEGMENTS = 28        # ★ 新增：分段數
    SEG_GAP = 2          # 段與段之間留白 px

    def __init__(self, parent, percent=0, color=None, **kw):
        kw.setdefault("height", self.HEIGHT)
        kw.setdefault("bg", COLORS["card_bg"])
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, **kw)
        self._color = color or COLORS["info"]
        self._percent = percent
        self.bind("<Configure>", lambda e: self._draw())
        self._draw()

    def set(self, percent, color=None):
        self._percent = max(0.0, min(100.0, percent))
        if color: self._color = color
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1: return
        seg_total_gap = self.SEG_GAP * (self.SEGMENTS - 1)
        seg_w = (w - seg_total_gap) / self.SEGMENTS
        filled = round((self._percent / 100) * self.SEGMENTS)
        for i in range(self.SEGMENTS):
            x1 = i * (seg_w + self.SEG_GAP)
            x2 = x1 + seg_w
            color = self._color if i < filled else COLORS["border"]
            self.create_rectangle(x1, 0, x2, h, fill=color, outline="", width=0)
```

未填滿的段使用 `COLORS["border"]`，已填滿的段用語意色（info / warn / danger）依百分比決定。

---

## 5. KV row 樣式（取代斑馬紋）

新版使用 1px 底線分隔，無斑馬紋背景：

```python
def _add_row(self, label, value="", value_color=None, bg=None):
    bg = COLORS["card_bg"]            # ★ 不再用 row_alt 交替
    vc = value_color or COLORS["text"]
    row = tk.Frame(self.content_frame, bg=bg)
    row.pack(fill="x")
    inner = tk.Frame(row, bg=bg)
    inner.pack(fill="x", padx=0, pady=6)  # ★ 6px 上下留白

    if value:
        tk.Label(inner, text=label, fg=COLORS["text_dim"], bg=bg,
                 font=FONT_KV_LABEL, anchor="w").pack(side="left")
        tk.Label(inner, text=value, fg=vc, bg=bg,
                 font=FONT_KV_VALUE, anchor="e").pack(side="right")
    else:
        tk.Label(inner, text=label, fg=vc, bg=bg,
                 font=("Segoe UI", 10), anchor="w").pack(fill="x")

    # 1px 底線（最後一列不畫）
    tk.Frame(self.content_frame, bg=COLORS["border"], height=1).pack(fill="x")
```

> 注意：在最後一列（每個服務的 `_format_data` 結尾那一列）**不要加底線**。
> 可以追加參數 `last=False`，或在 render 時判斷 index 是否為 rows 末位。

---

## 6. Hero 區塊（新增方法）

在 `ServiceCard` 加入 `_add_hero(label, value, color, value_unit=None)`：

```python
def _add_hero(self, label, value, color=None, value_unit=None, badge=None):
    """Add a large hero metric block at the top of the content area.

    Args:
        label: 上方小標（uppercase 顯示）
        value: 主要數字（會用 28pt mono 顯示）
        color: value 顏色，預設 COLORS["text"]
        value_unit: 主數字後接的單位/分母，例如 "/1500"
        badge: 右上角徽章（例如方案名稱 "Build" / "Pro"）
    """
    color = color or COLORS["text"]
    block = tk.Frame(self.content_frame, bg=COLORS["card_bg"])
    block.pack(fill="x", pady=(2, 14))

    # 標籤列（含 badge）
    top = tk.Frame(block, bg=COLORS["card_bg"])
    top.pack(fill="x")
    tk.Label(top,
             text=label.upper(),
             fg=COLORS["text_dim"], bg=COLORS["card_bg"],
             font=FONT_HERO_LABEL, anchor="w").pack(side="left")
    if badge:
        # 用 Frame + border 模擬 badge
        b = tk.Frame(top, bg=COLORS["card_bg"],
                     highlightthickness=1, highlightbackground=COLORS["border"])
        b.pack(side="right", padx=4)
        tk.Label(b, text=f" {badge} ",
                 fg=COLORS["text_muted"], bg=COLORS["card_bg"],
                 font=FONT_BADGE).pack()

    # 主數字
    valrow = tk.Frame(block, bg=COLORS["card_bg"])
    valrow.pack(fill="x", anchor="w", pady=(2, 0))
    tk.Label(valrow, text=str(value),
             fg=color, bg=COLORS["card_bg"],
             font=FONT_HERO).pack(side="left", anchor="s")
    if value_unit:
        tk.Label(valrow, text=value_unit,
                 fg=COLORS["text_muted"], bg=COLORS["card_bg"],
                 font=FONT_HERO_UNIT).pack(side="left", anchor="s", padx=(2, 0))
```

---

## 7. 重置時間 / 重置倒數（新增 reset pill）

舊版：`("重置於", "12 天後")` 用 KV row 顯示
新版：在進度條下方右側加一個獨立 pill（紫色，含 ↻ 圖示），或在 KV row 用 `violet` 顏色強調。

```python
def _add_reset_pill(self, parent, text, urgent=False):
    """重置時間徽章。urgent=True 時用警示色。"""
    color = COLORS["warning"] if urgent else COLORS["violet"]
    bg = COLORS["card_bg"]
    pill = tk.Frame(parent, bg=bg,
                    highlightthickness=1, highlightbackground=color)
    pill.pack(side="right", padx=4)
    tk.Label(pill, text=f" ↻ {text} ",
             fg=color, bg=bg,
             font=FONT_RESET_PILL).pack()
```

放在進度條 detail 列右側：
```
[bar]
$3.74 / $5.00            [↻ 12 天後]
```

倒數 ≤ 3 天 / 工作階段重置 ≤ 1 小時時，`urgent=True` 改用 warning 黃色。

---

## 8. 卡片頂端結構（取消彩色頂條，用色塊圖示替代）

舊版：3px 全寬色條 + 標題列（status dot 在最左）
新版：**取消頂端色條**，標題列改成「22×22 純色塊（含縮寫）+ 短名 + 右側 timestamp（含脈動點）」

```python
def _build_ui(self):
    accent = SERVICE_ACCENTS.get(self.service_name, COLORS["info"])

    # ★ 不再 pack 頂端色條
    # tk.Frame(self, bg=accent, height=3).pack(fill="x", side="top")  # 刪除這行

    # Header
    header = tk.Frame(self, bg=COLORS["card_bg"], padx=16, pady=14)
    header.pack(fill="x")

    # 22×22 色塊（取代原本的小狀態點 + 文字標題）
    glyph_text = self._glyph_for(self.service_name)  # "OA" / "C" / "API" / "GH" / "OR"
    glyph = tk.Frame(header, bg=accent, width=22, height=22)
    glyph.pack(side="left")
    glyph.pack_propagate(False)
    tk.Label(glyph, text=glyph_text, bg=accent, fg=COLORS["bg"],
             font=(MONO_FONT, 8, "bold")).pack(expand=True)

    # 短名
    tk.Label(header, text=f"  {self._short_name()}",
             fg=COLORS["text"], bg=COLORS["card_bg"],
             font=FONT_TITLE).pack(side="left")

    # Timestamp（含 status dot 脈動效果可省略，靜態色點即可）
    self.time_label = tk.Label(header, text="",
                                fg=COLORS["text_faint"], bg=COLORS["card_bg"],
                                font=FONT_TIMESTAMP)
    self.time_label.pack(side="right")
    self.status_dot = tk.Label(header, text="●",
                                fg=COLORS["success"], bg=COLORS["card_bg"],
                                font=("Segoe UI", 6))
    self.status_dot.pack(side="right", padx=(0, 4))

    # 內容區（無分隔線；hero block 自己管 spacing）
    self.content_frame = tk.Frame(self, bg=COLORS["card_bg"], padx=16, pady=0)
    self.content_frame.pack(fill="both", expand=True, pady=(0, 14))

@staticmethod
def _glyph_for(service_name):
    return {
        "OpenAI 帳單 (瀏覽器)":     "OA",
        "Claude.ai 用量 (瀏覽器)":  "C",
        "Claude API 帳單 (瀏覽器)": "API",
        "GitHub Copilot (瀏覽器)":  "GH",
        "OpenRouter (瀏覽器)":      "OR",
    }.get(service_name, "·")

@staticmethod
def _short_name():
    return {
        "OpenAI 帳單 (瀏覽器)":     "OpenAI",
        "Claude.ai 用量 (瀏覽器)":  "Claude.ai",
        "Claude API 帳單 (瀏覽器)": "Claude API",
        "GitHub Copilot (瀏覽器)":  "Copilot",
        "OpenRouter (瀏覽器)":      "OpenRouter",
    }.get(service_name, service_name)
```

---

## 9. `_format_data` 改寫範本（OpenAI 範例）

每個服務的 `_format_data` 需要改寫成「先送 hero，再送 bars / KV rows」。範例：

```python
elif service_name == "OpenAI 帳單 (瀏覽器)":
    self._browser_header_rows(data, rows)

    # ★ 1) Hero — 帳戶餘額
    if "balance_usd" in data:
        rows.append({
            "type": "hero",
            "label": "帳戶餘額",
            "value": f"${data['balance_usd']:.2f}",
            "color": COLORS["success"],
        })

    # 2) Credits 進度條
    if "credits_used_usd" in data and "credits_total_usd" in data:
        used  = data["credits_used_usd"]
        total = data["credits_total_usd"]
        pct = round(used / total * 100, 1) if total > 0 else 0
        rows.append({
            "type": "bar",
            "label": "Credits 用量",
            "percent": pct,
            "detail": f"${used:.2f} / ${total:.2f}",
            "color": self._pct_color(pct),
        })

    # 3) KV pairs
    if "month_usage_usd" in data:
        rows.append(("本月用量", f"${data['month_usage_usd']:.4f}"))
    if "hard_limit_usd" in data:
        rows.append(("月上限", f"${data['hard_limit_usd']:.0f}"))
    if data.get("tier"):
        rows.append(("用量等級", data["tier"]))
    if data.get("auto_recharge"):
        rows.append(("自動儲值", "已啟用", COLORS["success"]))
```

對應的 render 邏輯需要新增 `"hero"` type 處理：
```python
elif isinstance(row, dict) and row.get("type") == "hero":
    self._add_hero(row["label"], row["value"],
                   color=row.get("color"),
                   value_unit=row.get("unit"),
                   badge=row.get("badge"))
```

每個服務的 hero 對應：
- `Claude.ai`：`hero` 用百分比，`label="每週限額"`，`value=f"{data['weekly_percent']:.0f}"`, `unit="%"`, `badge=data.get("plan_type")`
- `Claude API`：hero 用餘額金額，`badge=data.get("plan")`
- `Copilot`：hero 用 **剩餘**（`total - consumed`），`unit=f"/{total:,.0f}"`, `badge=data.get("plan")`
- `OpenRouter`：hero 用餘額金額

---

## 10. 主視窗加入 KPI 摘要列

在 `gui/app.py` 的主視窗 toolbar 下方加入一條 KPI 摘要列：

```
┌────────────┬────────────┬────────────┬────────────┐
│ 總餘額     │ 本月花費   │ 活躍服務   │ 下個重置   │
│ $154.08    │ $23.29     │ 5 / 5      │ 3 天       │
└────────────┴────────────┴────────────┴────────────┘
```

實作方式：
```python
def _build_kpi_strip(self, parent):
    strip = tk.Frame(parent, bg=COLORS["bg"])
    strip.pack(fill="x", padx=18, pady=(14, 0))
    grid = tk.Frame(strip, bg=COLORS["bg"])
    grid.pack(fill="x")
    self._kpis = []
    for i, (label, default_value, color_key) in enumerate([
        ("總餘額", "—", "success"),
        ("本月花費", "—", "text"),
        ("活躍服務", "—", "info"),
        ("下個重置", "—", "violet"),
    ]):
        cell = tk.Frame(grid, bg=COLORS["bg"])
        cell.grid(row=0, column=i, sticky="nsew",
                  padx=(0 if i == 0 else 1, 0))
        grid.grid_columnconfigure(i, weight=1, uniform="kpi")
        # 左側細邊框（除第一格外）
        if i > 0:
            tk.Frame(cell, bg=COLORS["border"], width=1).pack(side="left", fill="y")
        inner = tk.Frame(cell, bg=COLORS["bg"], padx=14, pady=12)
        inner.pack(fill="both", expand=True)
        tk.Label(inner, text=label.upper(),
                 fg=COLORS["text_dim"], bg=COLORS["bg"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        val = tk.Label(inner, text=default_value,
                       fg=COLORS[color_key], bg=COLORS["bg"],
                       font=(MONO_FONT, 18, "bold"))
        val.pack(anchor="w", pady=(2, 0))
        self._kpis.append(val)

def _refresh_kpis(self, results: list):
    """Aggregate from all ServiceResult and update the KPI strip."""
    total_balance = sum(r.data.get("balance_usd", 0) for r in results if r.success)
    month_spend = sum(
        r.data.get("month_usage_usd", 0) or r.data.get("month_spend_usd", 0) or
        r.data.get("this_month_usd", 0)
        for r in results if r.success
    )
    active = sum(1 for r in results if r.success)
    total = len(results)
    self._kpis[0].config(text=f"${total_balance:.2f}")
    self._kpis[1].config(text=f"${month_spend:.2f}")
    self._kpis[2].config(text=f"{active} / {total}")
    self._kpis[3].config(text=self._next_reset_summary(results))
```

---

## 11. 桌面小工具的時鐘改版

`desktop_widget/clock.py` 翻頁時鐘改為「無翻頁動畫的等寬大字」：

```python
# 取代原本的 FlipClock；保留同一個介面
class DigitalClock(tk.Frame):
    def __init__(self, parent, **kw):
        kw.setdefault("bg", COLORS["card_bg"])
        super().__init__(parent, **kw)
        self.time_label = tk.Label(
            self, text="--:--",
            fg=COLORS["text"], bg=COLORS["card_bg"],
            font=(MONO_FONT, 36, "bold"),
        )
        self.time_label.pack(anchor="w", padx=16, pady=(14, 0))
        self.date_label = tk.Label(
            self, text="",
            fg=COLORS["text_dim"], bg=COLORS["card_bg"],
            font=("Segoe UI", 9),
        )
        self.date_label.pack(anchor="w", padx=16, pady=(2, 12))
        self._tick()

    def _tick(self):
        from datetime import datetime
        now = datetime.now()
        # HH:MM 主體 + :SS 用較小 / 弱化色 — tkinter 沒法在同 Label 裡分顏色，
        # 改用兩個 Label 並排即可（左 HH:MM, 右 :SS）。
        self.time_label.config(text=now.strftime("%H:%M"))
        self.date_label.config(text=now.strftime("%Y/%m/%d · %A"))
        self.after(1000, self._tick)
```

> 若想保留秒數弱化效果：把 `time_label` 拆成 `Frame` 內兩個 `Label`，
> 一個 36pt mono `text` 色顯示 HH:MM，一個 22pt mono `text_faint` 色顯示 `:SS`。

---

## 12. 視窗 / 卡片間距總表

| 元素 | padding (left/right) | padding (top/bottom) | 與下一元素 gap |
|------|----------------------|----------------------|----------------|
| 主視窗外圍 | 18 | 14 | — |
| KPI 列 | 0（cell 內 14） | 12（cell 內） | 0 |
| 卡片格線 | 18 | 14 | — |
| 卡片本體 | — | — | 12 |
| 卡片內 padding | 16 | 14 | — |
| Hero block | 16 | 14（下） | 14 |
| Bar block | 16 | 0 | 12 |
| KV row | 0 | 6 | 0（用 1px 底線） |

桌面小工具的 padding 全部 **-2px**（更緊湊）。

---

## 13. 密度切換（緊湊 / 舒適）

新增一個 `density` 設定，存於 `config/manager.py`：

```python
# config 新欄位
"density": "comfortable",   # "compact" | "comfortable"
```

差異：
| 項目 | 舒適 | 緊湊 |
|------|------|------|
| KV row pady | 6 | 3 |
| Hero `pady` | (2, 14) | (0, 8) |
| Bar gap | 12 | 6 |
| Card gap | 12 | 6 |

把 padding 數字改用 `compact_or(comfortable_value, compact_value)` helper 取得。

---

## 14. 卡片摺疊（可選功能）

每張卡片右上加一個「▾ / ▸」按鈕，按下時隱藏 `content_frame`，僅保留 header + 一行摘要：

```
▣ OpenAI                    $42.18  ▸
```

實作方式：在 `ServiceCard` 增加：
```python
def toggle_collapsed(self):
    self._collapsed = not self._collapsed
    if self._collapsed:
        self.content_frame.pack_forget()
        self._show_summary()
    else:
        self._hide_summary()
        self.content_frame.pack(fill="both", expand=True)

def _summary_value(self, data):
    """主數字摘要：金額 / 百分比"""
    if "balance_usd" in data: return f"${data['balance_usd']:.2f}"
    if "weekly_percent" in data: return f"週 {data['weekly_percent']:.0f}%"
    if "included_percent" in data: return f"{data['included_percent']:.0f}%"
    return ""
```

---

## 15. 服務排序拖曳

主視窗的卡片格線改成「可拖曳排序」。tkinter 沒有原生 DnD，但可以用 `<Button-1>` + `<B1-Motion>` 偵測拖曳，並以 `cv.coords()` 重排。比較簡單的替代：在每張卡片右上加 ▲ ▼ 兩個按鈕，順序變更後寫回 config。

```python
def _move_card(self, service_name, direction):
    order = self.config.get("card_order", [])
    if service_name not in order: return
    i = order.index(service_name)
    j = i + direction
    if 0 <= j < len(order):
        order[i], order[j] = order[j], order[i]
        self.config["card_order"] = order
        self._rebuild_cards()
```

---

## 16. 實作順序建議

1. **先改 token**（`COLORS` / `SERVICE_ACCENTS` / `WIDGET_*` / 字型常數）— 視覺上會立刻變很多
2. **改 `ProgressBar` 為 28-segment**
3. **加入 `_add_hero`** + 在每個 `_format_data` 開頭呼叫
4. **改 KV row 為底線分隔**（取消斑馬紋）
5. **改 header**（拿掉頂端色條 + 加入色塊圖示）
6. **加入 reset pill**
7. **主視窗加 KPI strip**
8. **時鐘改為等寬大字**
9. **加入密度切換、摺疊、排序**（可選）

每改完一步用 `python widget_main.py` 跑一次驗證。

---

## 17. 不要動的部分

- `services/` 整個資料夾（資料模型、HTTP server）
- `ai-monitor-client-v4.x.js`（瀏覽器腳本）
- `config/manager.py` 的核心結構（只新增欄位 `density`、`card_order`、`collapsed` dict）
- `ServiceResult` 的欄位
- 主迴圈、輪詢機制

---

## 附錄：完整顏色對應表（Catppuccin → Linear/Raycast）

| 用途 | 舊色 | 新色 |
|------|------|------|
| 主背景 | `#1e1e2e` | `#0a0a0c` |
| 卡片背景 | `#24273a` | `#111114` |
| 邊框 | `#363a4f` | `#1f1f24` |
| 主文字 | `#cad3f5` | `#fafafa` |
| 次要文字 | `#6e738d` | `#a1a1aa` |
| 弱化文字 | — | `#71717a` |
| 成功 | `#a6e3a1` | `#34d399` |
| 警告 | `#f9e2af` | `#fbbf24` |
| 錯誤 | `#f38ba8` | `#f87171` |
| 資訊 | `#89b4fa` | `#60a5fa` |
| 紫（重置） | `#c6a0f6` | `#a78bfa` |

---

**設計稿對照**：請開啟 `B-Version-Preview.html`（standalone HTML），左邊 widget、中間主視窗、右邊狀態，所有元素都是按上述規格實作的可運作版本。
