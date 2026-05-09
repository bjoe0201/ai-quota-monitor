"""
數位時鐘元件 (DigitalClock)
等寬大字 HH:MM + :SS（弱化）+ 日期
"""
import tkinter as tk
from datetime import datetime

from desktop_widget.styles import (
    COLORS, UI_FONT, MONO_FONT,
    WIDGET_LABEL,
)


class DigitalClock(tk.Frame):
    def __init__(self, parent, **kw):
        kw.setdefault("bg", COLORS["card_bg"])
        super().__init__(parent, **kw)

        # Time row: HH:MM (large) + :SS (dimmed)
        time_row = tk.Frame(self, bg=COLORS["card_bg"])
        time_row.pack(anchor="w", padx=16, pady=(14, 0))

        self.time_label = tk.Label(
            time_row, text="--:--",
            fg=COLORS["text"], bg=COLORS["card_bg"],
            font=(MONO_FONT, 36, "bold"),
        )
        self.time_label.pack(side="left", anchor="s")

        self.sec_label = tk.Label(
            time_row, text=":00",
            fg=COLORS["text_faint"], bg=COLORS["card_bg"],
            font=(MONO_FONT, 22, "bold"),
        )
        self.sec_label.pack(side="left", anchor="s", padx=(2, 0), pady=(0, 2))

        # Date row
        self.date_label = tk.Label(
            self, text="",
            fg=COLORS["text_dim"], bg=COLORS["card_bg"],
            font=(UI_FONT, 9),
        )
        self.date_label.pack(anchor="w", padx=16, pady=(2, 12))

        self._tick()

    def _tick(self):
        now = datetime.now()
        self.time_label.config(text=now.strftime("%H:%M"))
        self.sec_label.config(text=now.strftime(":%S"))

        _WD = ["Monday", "Tuesday", "Wednesday", "Thursday",
               "Friday", "Saturday", "Sunday"]
        self.date_label.config(
            text=now.strftime("%Y/%m/%d") + f" \u00b7 {_WD[now.weekday()]}"
        )

        ms_left = 1000 - now.microsecond // 1000
        self.after(ms_left, self._tick)


# Keep FlipClock as alias for backward compatibility
FlipClock = DigitalClock
