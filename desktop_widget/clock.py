"""
翻頁時鐘元件 (FlipClock)
顯示 HH:MM + 秒數小磁貼 + 日期。
AnimatedDigit 支援自訂磁貼尺寸，用於時分（大）與秒（小）。
"""
import tkinter as tk
from datetime import datetime

from desktop_widget.styles import (
    COLORS, TILE_W, TILE_H, TILE_R,
    TILE_BG, TILE_TEXT, TILE_DIM, TILE_SHADOW, DIGIT_FONT,
    WIDGET_LABEL,
)

_WIDGET_BG    = COLORS["bg"]
_DIVIDER_COLOR = "#c4c4d8"
_DIGIT_GAP    = 4


class AnimatedDigit(tk.Canvas):
    """
    單個翻頁數字磁貼。
    支援自訂磁貼寬高（w, h），字型大小依高度自動縮放。
    """
    ANIM_STEPS = 10
    ANIM_MS    = 18

    def __init__(self, parent, w: int = TILE_W, h: int = TILE_H, **kw):
        self._W = w
        self._H = h
        self._R = max(4, int(TILE_R * h / TILE_H))
        # 字型大小依磁貼高度等比縮放（基準：50pt @ 90px）
        fs = max(14, int(50 * h / TILE_H))
        self._font = ("Consolas", fs, "bold")

        super().__init__(
            parent,
            width=self._W, height=self._H,
            bg=_WIDGET_BG,
            highlightthickness=0,
            **kw,
        )
        self._char     = "0"
        self._old      = "0"
        self._animating = False
        self._step     = 0
        self._draw_static("0")

    def set_char(self, c: str):
        if c == self._char:
            return
        if self._animating:
            self._char = c
            return
        self._old  = self._char
        self._char = c
        self._step = 0
        self._animating = True
        self._tick()

    # ── 動畫循環 ──────────────────────────────────────────────────────────

    def _tick(self):
        if self._step >= self.ANIM_STEPS:
            self._animating = False
            self._draw_static(self._char)
            return
        self._draw_frame(self._step)
        self._step += 1
        self.after(self.ANIM_MS, self._tick)

    # ── 繪製 ──────────────────────────────────────────────────────────────

    def _draw_static(self, char: str):
        self.delete("all")
        self._draw_full_tile(char)

    def _draw_frame(self, step: int):
        self.delete("all")
        W, H = self._W, self._H
        mid  = H // 2
        half = self.ANIM_STEPS // 2

        if step < half:
            t      = step / half
            fold_h = int(mid * (1.0 - t))
            self._rrect(0, 0, W, H, self._R, fill=TILE_BG)
            self.create_text(W // 2, H // 2, text=self._old,
                             font=self._font, fill=TILE_TEXT, anchor="center")
            self.create_rectangle(0, mid + fold_h, W, H, fill=TILE_BG, outline="")
            if fold_h > 2:
                self.create_rectangle(2, mid, W - 2, mid + fold_h,
                                      fill=TILE_SHADOW, outline="")
                self.create_rectangle(2, mid + fold_h - 2, W - 2, mid + fold_h,
                                      fill="#909098", outline="")
        else:
            t        = (step - half) / half
            reveal_h = int(mid * t)
            self._rrect(0, 0, W, H, self._R, fill=TILE_BG)
            self.create_text(W // 2, H // 2, text=self._char,
                             font=self._font, fill=TILE_TEXT, anchor="center")
            if reveal_h < mid:
                self.create_rectangle(0, mid + reveal_h, W, H, fill=TILE_BG, outline="")
            if reveal_h > 1:
                self.create_rectangle(2, mid, W - 2, mid + 3,
                                      fill="#d0d0e8", outline="")

        self.create_rectangle(0, mid - 1, W, mid,     fill=_DIVIDER_COLOR, outline="")
        self.create_rectangle(0, mid,     W, mid + 2, fill=TILE_DIM,       outline="")
        self._punch_corners()

    def _draw_full_tile(self, char: str):
        W, H = self._W, self._H
        self._rrect(0, 0, W, H, self._R, fill=TILE_BG)
        self.create_text(W // 2, H // 2, text=char,
                         font=self._font, fill=TILE_TEXT, anchor="center")
        mid = H // 2
        self.create_rectangle(0, mid - 1, W, mid,     fill=_DIVIDER_COLOR, outline="")
        self.create_rectangle(0, mid,     W, mid + 2, fill=TILE_DIM,       outline="")
        self._punch_corners()

    def _punch_corners(self):
        bg = _WIDGET_BG
        r  = self._R + 1
        W, H = self._W, self._H
        opts = dict(style="pieslice", fill=bg, outline="")
        self.create_arc(-1,       -1,       2*r,   2*r,   start=90,  extent=90, **opts)
        self.create_arc(W - 2*r, -1,        W + 1, 2*r,   start=0,   extent=90, **opts)
        self.create_arc(-1,       H - 2*r,  2*r,   H + 1, start=180, extent=90, **opts)
        self.create_arc(W - 2*r,  H - 2*r,  W + 1, H + 1, start=270, extent=90, **opts)

    def _rrect(self, x1, y1, x2, y2, r, **kw):
        r = min(r, (x2 - x1) // 2, (y2 - y1) // 2)
        self.create_arc(x1,       y1,       x1+2*r, y1+2*r, start=90,  extent=90, style="pieslice", **kw)
        self.create_arc(x2-2*r,   y1,       x2,     y1+2*r, start=0,   extent=90, style="pieslice", **kw)
        self.create_arc(x1,       y2-2*r,   x1+2*r, y2,     start=180, extent=90, style="pieslice", **kw)
        self.create_arc(x2-2*r,   y2-2*r,   x2,     y2,     start=270, extent=90, style="pieslice", **kw)
        self.create_rectangle(x1+r, y1,   x2-r, y2,   **kw)
        self.create_rectangle(x1,   y1+r, x2,   y2-r, **kw)


# ── 秒數磁貼尺寸（比時分磁貼小） ─────────────────────────────────────────
_SEC_W = 44
_SEC_H = 58


class FlipClock(tk.Frame):
    """
    翻頁時鐘：HH:MM（大磁貼） + :SS（小磁貼） + 日期。
    每秒更新，同步至系統時間。
    """

    def __init__(self, parent, **kw):
        kw.setdefault("bg", _WIDGET_BG)
        super().__init__(parent, **kw)
        self._digits: list[AnimatedDigit] = []   # HH:MM (4 個大磁貼)
        self._last_hhmm = ""
        self._build()
        self._tick()

    def _build(self):
        outer = tk.Frame(self, bg=_WIDGET_BG)
        outer.pack(fill="x", pady=(16, 0))

        # 左右佔位欄（初始 0 寬；80ms 後同步為相同寬度使 HH:MM 精確居中）
        left_f = tk.Frame(outer, bg=_WIDGET_BG)
        left_f.pack(side="left", fill="y")
        left_f.pack_propagate(False)

        # ── 中欄：HH:MM ──────────────────────────────────────────────────
        hm_frame = tk.Frame(outer, bg=_WIDGET_BG)
        hm_frame.pack(side="left")

        # 小時組
        h_frame = tk.Frame(hm_frame, bg=_WIDGET_BG)
        h_frame.pack(side="left")
        h_row = tk.Frame(h_frame, bg=_WIDGET_BG)
        h_row.pack()
        for i in range(2):
            d = AnimatedDigit(h_row)
            d.pack(side="left", padx=(0, _DIGIT_GAP if i == 0 else 0))
            self._digits.append(d)
        tk.Label(h_frame, text="H", fg=WIDGET_LABEL, bg=_WIDGET_BG,
                 font=("Segoe UI", 8)).pack()

        # 冒號
        tk.Label(hm_frame, text=":",
                 fg=COLORS["subtext"], bg=_WIDGET_BG,
                 font=("Consolas", 40, "bold"),
                 ).pack(side="left", padx=(2, 2), anchor="n", pady=(8, 0))

        # 分鐘組
        m_frame = tk.Frame(hm_frame, bg=_WIDGET_BG)
        m_frame.pack(side="left")
        m_row = tk.Frame(m_frame, bg=_WIDGET_BG)
        m_row.pack()
        for i in range(2):
            d = AnimatedDigit(m_row)
            d.pack(side="left", padx=(0, _DIGIT_GAP if i == 0 else 0))
            self._digits.append(d)
        tk.Label(m_frame, text="M", fg=WIDGET_LABEL, bg=_WIDGET_BG,
                 font=("Segoe UI", 8)).pack()

        # 右欄：fill="y" 使高度與 HH:MM 齊高，sec_label 才能真正底部對齊
        right_f = tk.Frame(outer, bg=_WIDGET_BG)
        right_f.pack(side="left", fill="y")
        right_f.pack_propagate(False)
        self.sec_label = tk.Label(
            right_f, text="00",
            fg=WIDGET_LABEL, bg=_WIDGET_BG,
            font=("Consolas", 15, "bold"),
        )
        self.sec_label.pack(side="bottom", anchor="w", padx=4, pady=(0, 18))

        # 量測 hm_frame 實際寬度後，將兩側設為同一數值 → HH:MM 精確居中
        self.after(80, lambda: self._sync_spacers(outer, hm_frame, left_f, right_f))

        # ── 日期行 ────────────────────────────────────────────────────────
        self.date_label = tk.Label(
            self, text="",
            fg=COLORS["accent"], bg=_WIDGET_BG,
            font=("Segoe UI", 9),
        )
        self.date_label.pack(pady=(4, 12))

    def _sync_spacers(self, outer, hm_frame, left_f, right_f):
        """量測 hm_frame 寬度，將左右佔位欄設為相同值，使 HH:MM 精確居中。"""
        self.update_idletasks()
        W  = outer.winfo_width()
        Wm = hm_frame.winfo_reqwidth()
        side = max(28, (W - Wm) // 2)
        left_f.configure(width=side)
        right_f.configure(width=side)

    def _tick(self):
        now  = datetime.now()
        hhmm = now.strftime("%H%M")

        # 更新時分（有變化才觸發翻頁動畫）
        if hhmm != self._last_hhmm:
            for i, d in enumerate(self._digits):
                d.set_char(hhmm[i])
            self._last_hhmm = hhmm
            _WD = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
            self.date_label.config(
                text=now.strftime("%Y/%m/%d") + f"  {_WD[now.weekday()]}"
            )

        # 秒數每次都更新（純文字，無動畫）
        self.sec_label.config(text=now.strftime("%S"))

        # 對齊到下一個整秒
        ms_left = 1000 - now.microsecond // 1000
        self.after(ms_left, self._tick)
