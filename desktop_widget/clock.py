"""
翻頁時鐘風格元件 (DigitalClock)
HH MM 兩個白色翻頁卡片 + 秒數小字 + 日期 pill
"""
import tkinter as tk
from datetime import datetime

from desktop_widget.styles import (
    COLORS, UI_FONT, MONO_FONT,
)

# Flip-clock palette
FLIP_BG          = "#1a1a1f"   # outer frame background
FLIP_CARD_BG     = "#f5f5f0"   # card face (warm white)
FLIP_CARD_SHADOW = "#0a0a0d"   # bottom shadow stripe
FLIP_DIGIT       = "#0f0f12"   # digit color (near black)
FLIP_DIGIT_SHADE = "#cbcbc4"   # mid-line shade between top/bottom halves
FLIP_LABEL       = "#9a9a92"   # H / M label color
FLIP_SECOND      = "#6a6a72"   # seconds color
FLIP_DATE_BG     = "#2a2a30"   # date pill bg
FLIP_DATE_FG     = "#e5e5e0"   # date pill text


class FlipCard(tk.Canvas):
    """A single flip-clock card showing two digits with rounded corners."""

    WIDTH = 116
    HEIGHT = 96
    RADIUS = 14

    def __init__(self, parent, **kw):
        kw.setdefault("bg", FLIP_BG)
        kw.setdefault("highlightthickness", 0)
        kw.setdefault("bd", 0)
        kw.setdefault("width", self.WIDTH)
        kw.setdefault("height", self.HEIGHT)
        super().__init__(parent, **kw)

        # Rounded rectangle body
        self._draw_round_rect(
            1, 1, self.WIDTH - 1, self.HEIGHT - 1,
            self.RADIUS, fill=FLIP_CARD_BG, outline="#000000",
        )
        # Mid-line seam (flip card divider)
        mid_y = self.HEIGHT // 2
        self.create_line(
            self.RADIUS // 2, mid_y, self.WIDTH - self.RADIUS // 2, mid_y,
            fill=FLIP_DIGIT_SHADE,
        )
        # Digit text — centered
        self._digit_id = self.create_text(
            self.WIDTH // 2, self.HEIGHT // 2,
            text="00", fill=FLIP_DIGIT,
            font=(MONO_FONT, 60, "bold"),
            anchor="center",
        )

    def _draw_round_rect(self, x1, y1, x2, y2, r, **kw):
        # Draw rounded rectangle as a polygon with smoothed corners
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kw)

    def set_value(self, value: str):
        self.itemconfig(self._digit_id, text=value)


class DigitalClock(tk.Frame):
    def __init__(self, parent, **kw):
        kw.setdefault("bg", COLORS["card_bg"])
        super().__init__(parent, **kw)

        # ── Time row: [spacer] HH card + MM card + seconds ──────────────
        time_row = tk.Frame(self, bg=COLORS["card_bg"])
        time_row.pack(anchor="center", pady=(12, 4))

        # Invisible spacer matching seconds width — shifts whole row right
        # so the visible time block is offset by one seconds-glyph width.
        tk.Label(
            time_row, text="00",
            fg=COLORS["card_bg"], bg=COLORS["card_bg"],
            font=(MONO_FONT, 14, "bold"),
        ).pack(side="left", padx=(0, 5))

        self.hour_card = FlipCard(time_row)
        self.hour_card.pack(side="left", padx=(0, 6))

        self.min_card = FlipCard(time_row)
        self.min_card.pack(side="left")

        # Seconds (small, attached to right of MM card)
        self.sec_label = tk.Label(
            time_row, text="00",
            fg=FLIP_SECOND, bg=COLORS["card_bg"],
            font=(MONO_FONT, 14, "bold"),
        )
        self.sec_label.pack(side="left", anchor="s", padx=(5, 0), pady=(0, 8))

        # ── Date pill ──────────────────────────────────────────────────
        date_wrap = tk.Frame(self, bg=COLORS["card_bg"])
        date_wrap.pack(anchor="center", pady=(0, 12))

        date_pill = tk.Frame(
            date_wrap, bg=FLIP_DATE_BG,
            highlightthickness=1,
            highlightbackground="#3a3a40",
        )
        date_pill.pack()

        self.date_label = tk.Label(
            date_pill, text="",
            fg=FLIP_DATE_FG, bg=FLIP_DATE_BG,
            font=(UI_FONT, 9, "bold"),
            padx=14, pady=3,
        )
        self.date_label.pack()

        self._tick()

    def _tick(self):
        now = datetime.now()
        self.hour_card.set_value(now.strftime("%H"))
        self.min_card.set_value(now.strftime("%M"))
        self.sec_label.config(text=now.strftime("%S"))

        _WD = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        self.date_label.config(
            text=now.strftime("%Y/%m/%d") + f"  ·  {_WD[now.weekday()]}"
        )

        ms_left = 1000 - now.microsecond // 1000
        self.after(ms_left, self._tick)


# Keep FlipClock as alias for backward compatibility
FlipClock = DigitalClock
