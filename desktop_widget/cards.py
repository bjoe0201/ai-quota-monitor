"""
精簡版服務卡片元件 (CompactServiceCard)
資料欄位與主視窗 gui/widgets.py 的 ServiceCard 完全一致。
"""
import tkinter as tk
from services.base import ServiceResult
from desktop_widget.styles import (
    COLORS, SERVICE_ACCENTS, format_tokens, ProgressBar,
    COMPACT_CARD_PAD_X, COMPACT_CARD_PAD_Y,
    WIDGET_LABEL, WIDGET_TEXT, WIDGET_SUBTEXT,
)


class CompactServiceCard(tk.Frame):
    """
    桌面小工具用服務卡片。
    顯示與主視窗相同的所有欄位，高度隨內容自動展開。
    """

    def __init__(self, parent, service_name: str, **kw):
        kw.setdefault("bg", COLORS["card_bg"])
        kw.setdefault("relief", "flat")
        kw.setdefault("bd", 0)
        super().__init__(parent, **kw)
        self.service_name = service_name
        self._pbars: list[ProgressBar] = []
        self._build_ui()

    def _build_ui(self):
        accent = SERVICE_ACCENTS.get(self.service_name, COLORS["info"])

        # 頂部色條
        tk.Frame(self, bg=accent, height=3).pack(fill="x")

        # 標題列
        header = tk.Frame(self, bg=COLORS["card_bg"],
                          padx=COMPACT_CARD_PAD_X, pady=6)
        header.pack(fill="x")

        self.status_dot = tk.Label(
            header, text="●",
            fg=WIDGET_LABEL, bg=COLORS["card_bg"],
            font=("Segoe UI", 8),
        )
        self.status_dot.pack(side="left")

        display_name = self.service_name.replace(" (瀏覽器)", "")
        tk.Label(
            header,
            text=f"  {display_name}",
            fg=WIDGET_TEXT, bg=COLORS["card_bg"],
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left")

        # 分隔線
        tk.Frame(self, bg=COLORS["card_border"], height=1).pack(fill="x")

        # 內容區（高度隨內容自動展開）
        self.content = tk.Frame(
            self, bg=COLORS["card_bg"],
            padx=COMPACT_CARD_PAD_X, pady=COMPACT_CARD_PAD_Y,
        )
        self.content.pack(fill="both", expand=True)

        self._show_placeholder("載入中...")

        tk.Frame(self, bg=COLORS["card_bg"], height=4).pack()

    # ── 公開方法 ──────────────────────────────────────────────────────────

    def update_result(self, result: ServiceResult):
        self._clear()
        if not result.success:
            if result.error and "等待瀏覽器" in result.error:
                self.status_dot.config(fg=COLORS["warning"])
                self._show_placeholder("等待瀏覽器資料...", WIDGET_SUBTEXT)
            else:
                self.status_dot.config(fg=COLORS["error"])
                self._show_placeholder(result.error or "未知錯誤", COLORS["error"])
            return

        self.status_dot.config(fg=COLORS["success"])
        rows = self._format_data(result.service_name, result.data)
        self._render(rows)

    def set_loading(self):
        self.status_dot.config(fg=COLORS["warning"])
        self._clear()
        self._show_placeholder("更新中...", COLORS["warning"])

    # ── 內部繪製 ──────────────────────────────────────────────────────────

    def _clear(self):
        for w in self.content.winfo_children():
            w.destroy()
        self._pbars.clear()

    def _show_placeholder(self, text: str, color: str = None):
        tk.Label(
            self.content, text=text,
            fg=color or WIDGET_LABEL, bg=COLORS["card_bg"],
            font=("Segoe UI", 8), anchor="w",
        ).pack(fill="x", pady=1)

    def _render(self, rows: list):
        for i, row in enumerate(rows):
            if isinstance(row, dict):
                if row.get("type") == "bar":
                    bg = COLORS["row_alt"] if i % 2 == 0 else COLORS["card_bg"]
                    self._add_bar_row(
                        row["label"], row["percent"],
                        row.get("detail", ""), row.get("color", COLORS["info"]),
                        bg=bg,
                    )
                elif row.get("type") == "divider":
                    tk.Frame(self.content, bg=COLORS["card_border"],
                             height=1).pack(fill="x", pady=(4, 2))
                    tk.Label(
                        self.content, text=row["label"],
                        fg=WIDGET_SUBTEXT, bg=COLORS["card_bg"],
                        font=("Segoe UI", 7), anchor="w",
                    ).pack(fill="x")
            else:
                bg = COLORS["row_alt"] if i % 2 == 0 else COLORS["card_bg"]
                label, value, *rest = row if isinstance(row, (list, tuple)) else (row, "", [])
                vc = rest[0] if rest else WIDGET_TEXT
                self._add_row(label, value, vc, bg)

    def _add_row(self, label: str, value: str = "",
                 value_color: str = None, bg: str = None):
        bg = bg or COLORS["card_bg"]
        vc = value_color or WIDGET_TEXT
        row = tk.Frame(self.content, bg=bg)
        row.pack(fill="x", pady=1)
        inner = tk.Frame(row, bg=bg)
        inner.pack(fill="x", padx=2, pady=1)
        if value:
            tk.Label(inner, text=label,
                     fg=WIDGET_LABEL, bg=bg,
                     font=("Segoe UI", 7), anchor="w", width=9,
                     ).pack(side="left")
            tk.Label(inner, text=value,
                     fg=vc, bg=bg,
                     font=("Segoe UI", 8, "bold"), anchor="w",
                     ).pack(side="left", fill="x", expand=True)
        else:
            tk.Label(inner, text=label,
                     fg=vc, bg=bg,
                     font=("Segoe UI", 8), anchor="w",
                     ).pack(fill="x")

    def _add_bar_row(self, label: str, percent: float,
                     detail: str = "", color: str = None, bg: str = None):
        bg = bg or COLORS["card_bg"]
        color = color or self._pct_color(percent)
        row = tk.Frame(self.content, bg=bg)
        row.pack(fill="x", pady=(2, 1))
        inner = tk.Frame(row, bg=bg, padx=2)
        inner.pack(fill="x")

        top = tk.Frame(inner, bg=bg)
        top.pack(fill="x")
        tk.Label(top, text=label, fg=WIDGET_LABEL, bg=bg,
                 font=("Segoe UI", 7), anchor="w").pack(side="left")
        tk.Label(top, text=f"{percent:.1f}%", fg=color, bg=bg,
                 font=("Segoe UI", 8, "bold"), anchor="e").pack(side="right")

        pb = ProgressBar(inner, percent=percent, color=color, height=6)
        pb.pack(fill="x", pady=(1, 0))
        self._pbars.append(pb)

        if detail:
            tk.Label(inner, text=detail, fg=WIDGET_SUBTEXT, bg=bg,
                     font=("Segoe UI", 7), anchor="w").pack(fill="x")

    @staticmethod
    def _pct_color(pct: float) -> str:
        if pct >= 85:
            return COLORS["error"]
        elif pct >= 60:
            return COLORS["warning"]
        return COLORS["info"]

    # ── 資料格式化（與主視窗 gui/widgets.py _format_data 完全一致）────────

    def _format_data(self, service_name: str, data: dict) -> list:
        rows = []

        if service_name == "OpenAI 帳單 (瀏覽器)":
            self._browser_header(data, rows)
            if "balance_usd" in data:
                rows.append(("帳戶餘額", f"${data['balance_usd']:.2f}", COLORS["green"]))
            if "credits_used_usd" in data and "credits_total_usd" in data:
                used = data["credits_used_usd"]
                total = data["credits_total_usd"]
                pct = round(used / total * 100, 1) if total > 0 else 0
                rows.append({"type": "bar", "label": "Credits", "percent": pct,
                             "detail": f"${used:.2f} / ${total:.2f}",
                             "color": self._pct_color(pct)})
            if "month_usage_usd" in data:
                rows.append(("本月用量", f"${data['month_usage_usd']:.4f}"))
            if "hard_limit_usd" in data:
                rows.append(("月上限", f"${data['hard_limit_usd']:.2f}"))
            if data.get("tier"):
                rows.append(("用量等級", data["tier"]))
            if data.get("auto_recharge"):
                rows.append(("自動儲值", "已啟用", COLORS["success"]))

        elif service_name == "Claude.ai 用量 (瀏覽器)":
            self._browser_header(data, rows)
            if data.get("session_percent") is not None:
                pct = data["session_percent"]
                reset = data.get("session_reset", "")
                rows.append({"type": "bar", "label": "本次工作階段", "percent": pct,
                             "detail": f"重置於: {reset}" if reset else "",
                             "color": self._pct_color(pct)})
            if data.get("weekly_percent") is not None:
                pct = data["weekly_percent"]
                reset = data.get("weekly_reset", "")
                rows.append({"type": "bar", "label": "每週限額", "percent": pct,
                             "detail": f"重置於: {reset}" if reset else "",
                             "color": self._pct_color(pct)})
            if data.get("extra_enabled"):
                rows.append({"type": "divider", "label": "額外用量"})
                if "extra_spent" in data:
                    rows.append(("已花費", f"${data['extra_spent']:.2f}"))
                if "extra_limit" in data:
                    rows.append(("每月上限", f"${data['extra_limit']:.2f}"))
                if "extra_balance" in data:
                    rows.append(("目前餘額", f"${data['extra_balance']:.2f}", COLORS["green"]))
                if data.get("extra_resets"):
                    rows.append(("重置日期", data["extra_resets"]))

        elif service_name == "Claude API 帳單 (瀏覽器)":
            self._browser_header(data, rows)
            if data.get("plan"):
                rows.append(("方案", data["plan"]))
            if "monthly_usd" in data:
                rows.append(("月費", f"${data['monthly_usd']:.2f}"))
            if "this_month_usd" in data:
                rows.append(("本月用量", f"${data['this_month_usd']:.4f}"))
            if "balance_usd" in data:
                rows.append(("帳戶餘額", f"${data['balance_usd']:.2f}", COLORS["green"]))
            if "spend_limit_usd" in data:
                rows.append(("消費上限", f"${data['spend_limit_usd']:.2f}"))
            if data.get("next_billing"):
                rows.append(("下次計費", data["next_billing"]))

        elif service_name == "GitHub Copilot (瀏覽器)":
            self._browser_header(data, rows)
            if data.get("plan"):
                rows.append(("方案", data["plan"]))
            pct = data.get("included_percent")
            if pct is not None:
                consumed = data.get("included_consumed")
                total = data.get("included_total")
                detail = (f"{consumed:.1f} / {total:.0f} 次"
                          if consumed is not None and total is not None else "")
                rows.append({"type": "bar", "label": "Premium Requests",
                             "percent": pct, "detail": detail,
                             "color": self._pct_color(pct)})
            if data.get("billed_usd") and data["billed_usd"] > 0:
                rows.append(("已計費", f"${data['billed_usd']:.2f}", COLORS["peach"]))
            if data.get("resets_in_days") is not None:
                rows.append(("重置於", f"{data['resets_in_days']} 天後"))
            if data.get("next_billing"):
                rows.append(("下次計費", data["next_billing"]))

        if not rows:
            rows.append(("無資料", "", WIDGET_SUBTEXT))

        return rows

    def _browser_header(self, data: dict, rows: list):
        if data.get("updated_at"):
            rows.append(("更新時間", data["updated_at"], WIDGET_SUBTEXT))
        if data.get("stale_warning"):
            rows.append((data["stale_warning"], "", COLORS["warning"]))
