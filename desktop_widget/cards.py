"""
精簡版服務卡片元件 (CompactServiceCard)
資料欄位與主視窗 gui/widgets.py 的 ServiceCard 完全一致。
Linear / Raycast 風格 — Hero + 28-segment bar + KV 底線分隔
"""
import tkinter as tk
from services.base import ServiceResult
from desktop_widget.styles import (
    COLORS, SERVICE_ACCENTS, format_tokens, ProgressBar,
    UI_FONT, MONO_FONT,
    COMPACT_CARD_PAD_X, COMPACT_CARD_PAD_Y,
    WIDGET_LABEL, WIDGET_TEXT, WIDGET_SUBTEXT,
    COMPACT_FONT_TITLE, COMPACT_FONT_HERO, COMPACT_FONT_HERO_UNIT,
    COMPACT_FONT_HERO_LABEL, COMPACT_FONT_KV_LABEL, COMPACT_FONT_KV_VALUE,
    COMPACT_FONT_BAR_LABEL, COMPACT_FONT_BAR_PCT, COMPACT_FONT_BAR_DETAIL,
    COMPACT_FONT_RESET_PILL, COMPACT_FONT_BADGE, COMPACT_FONT_TIMESTAMP,
)


class CompactServiceCard(tk.Frame):
    """桌面小工具用服務卡片。Hero + bar + KV 底線分隔。"""

    def __init__(self, parent, service_name: str, **kw):
        kw.setdefault("bg", COLORS["card_bg"])
        kw.setdefault("relief", "flat")
        kw.setdefault("bd", 0)
        super().__init__(parent, **kw)
        self.service_name = service_name
        self._pbars: list[ProgressBar] = []
        self._build_ui()

    # ── Header helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _glyph_for(service_name: str) -> str:
        return {
            "OpenAI 帳單 (瀏覽器)":     "OA",
            "Claude.ai 用量 (瀏覽器)":  "C",
            "Claude API 帳單 (瀏覽器)": "API",
            "GitHub Copilot (瀏覽器)":  "GH",
            "OpenRouter (瀏覽器)":      "OR",
        }.get(service_name, "·")

    @staticmethod
    def _short_name(service_name: str) -> str:
        return {
            "OpenAI 帳單 (瀏覽器)":     "OpenAI",
            "Claude.ai 用量 (瀏覽器)":  "Claude.ai",
            "Claude API 帳單 (瀏覽器)": "Claude API",
            "GitHub Copilot (瀏覽器)":  "Copilot",
            "OpenRouter (瀏覽器)":      "OpenRouter",
        }.get(service_name, service_name)

    def _build_ui(self):
        accent = SERVICE_ACCENTS.get(self.service_name, COLORS["info"])

        # Header
        header = tk.Frame(self, bg=COLORS["card_bg"],
                          padx=COMPACT_CARD_PAD_X, pady=6)
        header.pack(fill="x")

        # 18x18 glyph icon (smaller than main window)
        glyph_text = self._glyph_for(self.service_name)
        glyph = tk.Frame(header, bg=accent, width=18, height=18)
        glyph.pack(side="left")
        glyph.pack_propagate(False)
        tk.Label(glyph, text=glyph_text, bg=accent, fg=COLORS["bg"],
                 font=(MONO_FONT, 7, "bold")).pack(expand=True)

        # Short name
        tk.Label(
            header,
            text=f"  {self._short_name(self.service_name)}",
            fg=WIDGET_TEXT, bg=COLORS["card_bg"],
            font=COMPACT_FONT_TITLE,
        ).pack(side="left")

        # Timestamp
        self.time_label = tk.Label(
            header, text="",
            fg=WIDGET_SUBTEXT, bg=COLORS["card_bg"],
            font=COMPACT_FONT_TIMESTAMP,
        )
        self.time_label.pack(side="right")

        # Status dot
        self.status_dot = tk.Label(
            header, text="●",
            fg=WIDGET_LABEL, bg=COLORS["card_bg"],
            font=(UI_FONT, 5),
        )
        self.status_dot.pack(side="right", padx=(0, 3))

        # Content area
        self.content = tk.Frame(
            self, bg=COLORS["card_bg"],
            padx=COMPACT_CARD_PAD_X, pady=COMPACT_CARD_PAD_Y,
        )
        self.content.pack(fill="both", expand=True)

        self._show_placeholder("載入中...")

    # ── Public ─────────────────────────────────────────────────────────────

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

    # ── Internal rendering ─────────────────────────────────────────────────

    def _clear(self):
        for w in self.content.winfo_children():
            w.destroy()
        self._pbars.clear()

    def _show_placeholder(self, text: str, color: str = None):
        tk.Label(
            self.content, text=text,
            fg=color or WIDGET_LABEL, bg=COLORS["card_bg"],
            font=COMPACT_FONT_KV_LABEL, anchor="w",
        ).pack(fill="x", pady=1)

    def _render(self, rows: list):
        # Find last KV/pair row index
        last_kv_idx = -1
        for i in range(len(rows) - 1, -1, -1):
            r = rows[i]
            if isinstance(r, dict) and r.get("type") in ("hero", "bar", "divider"):
                continue
            last_kv_idx = i
            break

        for i, row in enumerate(rows):
            is_last = (i == last_kv_idx)
            if isinstance(row, dict):
                rtype = row.get("type")
                if rtype == "hero":
                    self._add_hero(
                        row["label"], row["value"],
                        color=row.get("color"),
                        value_unit=row.get("unit"),
                        badge=row.get("badge"),
                    )
                elif rtype == "bar":
                    self._add_bar_row(
                        row["label"], row["percent"],
                        row.get("detail", ""), row.get("color", COLORS["info"]),
                        reset_text=row.get("reset_text"),
                        reset_urgent=row.get("reset_urgent", False),
                    )
                elif rtype == "divider":
                    tk.Frame(self.content, bg=COLORS["border"],
                             height=1).pack(fill="x", pady=(6, 3))
                    tk.Label(
                        self.content, text=row["label"],
                        fg=WIDGET_SUBTEXT, bg=COLORS["card_bg"],
                        font=COMPACT_FONT_HERO_LABEL, anchor="w",
                    ).pack(fill="x")
                elif rtype == "pair":
                    self._add_pair_row(
                        row.get("left_label", ""), row.get("left_value", ""),
                        row.get("right_label", ""), row.get("right_value", ""),
                        last=is_last,
                    )
            else:
                label, value, *rest = row if isinstance(row, (list, tuple)) else (row, "", [])
                vc = rest[0] if rest else WIDGET_TEXT
                self._add_row(label, value, vc, last=is_last)

    def _add_hero(self, label: str, value: str, color: str = None,
                  value_unit: str = None, badge: str = None):
        color = color or COLORS["text"]
        bg = COLORS["card_bg"]
        block = tk.Frame(self.content, bg=bg)
        block.pack(fill="x", pady=(0, 8))

        # Label row
        top = tk.Frame(block, bg=bg)
        top.pack(fill="x")
        tk.Label(top, text=label.upper(), fg=COLORS["text_dim"], bg=bg,
                 font=COMPACT_FONT_HERO_LABEL, anchor="w").pack(side="left")
        if badge:
            b = tk.Frame(top, bg=bg,
                         highlightthickness=1, highlightbackground=COLORS["border"])
            b.pack(side="right", padx=2)
            tk.Label(b, text=f" {badge} ", fg=COLORS["text_muted"], bg=bg,
                     font=COMPACT_FONT_BADGE).pack()

        # Main value
        valrow = tk.Frame(block, bg=bg)
        valrow.pack(fill="x", anchor="w", pady=(1, 0))
        tk.Label(valrow, text=str(value), fg=color, bg=bg,
                 font=COMPACT_FONT_HERO).pack(side="left", anchor="s")
        if value_unit:
            tk.Label(valrow, text=value_unit, fg=COLORS["text_muted"], bg=bg,
                     font=COMPACT_FONT_HERO_UNIT).pack(side="left", anchor="s", padx=(2, 0))

        # Separator
        tk.Frame(self.content, bg=COLORS["border"], height=1).pack(fill="x")

    def _add_row(self, label: str, value: str = "",
                 value_color: str = None, last: bool = False):
        bg = COLORS["card_bg"]
        vc = value_color or WIDGET_TEXT
        row = tk.Frame(self.content, bg=bg)
        row.pack(fill="x")
        inner = tk.Frame(row, bg=bg)
        inner.pack(fill="x", padx=0, pady=4)
        if value:
            tk.Label(inner, text=label, fg=WIDGET_LABEL, bg=bg,
                     font=COMPACT_FONT_KV_LABEL, anchor="w").pack(side="left")
            tk.Label(inner, text=value, fg=vc, bg=bg,
                     font=COMPACT_FONT_KV_VALUE, anchor="e").pack(side="right")
        else:
            tk.Label(inner, text=label, fg=vc, bg=bg,
                     font=COMPACT_FONT_KV_LABEL, anchor="w").pack(fill="x")
        if not last:
            tk.Frame(self.content, bg=COLORS["border"], height=1).pack(fill="x")

    def _add_pair_row(self, left_label: str, left_value: str = "",
                       right_label: str = "", right_value: str = "",
                       last: bool = False):
        bg = COLORS["card_bg"]
        row = tk.Frame(self.content, bg=bg)
        row.pack(fill="x")
        inner = tk.Frame(row, bg=bg)
        inner.pack(fill="x", padx=0, pady=4)

        left_f = tk.Frame(inner, bg=bg)
        left_f.pack(side="left", fill="x", expand=True)
        tk.Label(left_f, text=left_label, fg=WIDGET_LABEL, bg=bg,
                 font=COMPACT_FONT_KV_LABEL, anchor="w").pack(side="left", padx=(0, 4))
        tk.Label(left_f, text=left_value, fg=WIDGET_TEXT, bg=bg,
                 font=COMPACT_FONT_KV_VALUE, anchor="w").pack(side="left")

        right_f = tk.Frame(inner, bg=bg)
        right_f.pack(side="left", fill="x", expand=True)
        tk.Label(right_f, text=right_label, fg=WIDGET_LABEL, bg=bg,
                 font=COMPACT_FONT_KV_LABEL, anchor="w").pack(side="left", padx=(0, 4))
        tk.Label(right_f, text=right_value, fg=WIDGET_TEXT, bg=bg,
                 font=COMPACT_FONT_KV_VALUE, anchor="w").pack(side="left")

        if not last:
            tk.Frame(self.content, bg=COLORS["border"], height=1).pack(fill="x")

    def _add_bar_row(self, label: str, percent: float,
                     detail: str = "", color: str = None,
                     reset_text: str = None, reset_urgent: bool = False):
        bg = COLORS["card_bg"]
        color = color or self._pct_color(percent)
        row = tk.Frame(self.content, bg=bg)
        row.pack(fill="x", pady=(4, 2))
        inner = tk.Frame(row, bg=bg)
        inner.pack(fill="x")

        top = tk.Frame(inner, bg=bg)
        top.pack(fill="x")
        tk.Label(top, text=label, fg=WIDGET_LABEL, bg=bg,
                 font=COMPACT_FONT_BAR_LABEL, anchor="w").pack(side="left")
        tk.Label(top, text=f"{percent:.1f}%", fg=color, bg=bg,
                 font=COMPACT_FONT_BAR_PCT, anchor="e").pack(side="right")
        if reset_text:
            pill_color = COLORS["warning"] if reset_urgent else COLORS["violet"]
            pill = tk.Frame(top, bg=bg,
                            highlightthickness=1, highlightbackground=pill_color)
            pill.pack(side="left", padx=4)
            tk.Label(pill, text=f" \u21bb {reset_text} ", fg=pill_color, bg=bg,
                     font=COMPACT_FONT_RESET_PILL).pack()

        pb = ProgressBar(inner, percent=percent, color=color, height=6)
        pb.pack(fill="x", pady=(1, 0))
        self._pbars.append(pb)

        if detail:
            detail_row = tk.Frame(inner, bg=bg)
            detail_row.pack(fill="x")
            tk.Label(detail_row, text=detail, fg=WIDGET_SUBTEXT, bg=bg,
                     font=COMPACT_FONT_BAR_DETAIL, anchor="w").pack(side="left")

    @staticmethod
    def _pct_color(pct: float) -> str:
        if pct >= 85:
            return COLORS["error"]
        elif pct >= 60:
            return COLORS["warning"]
        return COLORS["info"]

    # ── Data formatting (mirrors gui/widgets.py _format_data) ──────────────

    def _format_data(self, service_name: str, data: dict) -> list:
        rows = []

        if service_name == "OpenAI 帳單 (瀏覽器)":
            self._browser_header(data, rows)
            if "balance_usd" in data:
                rows.append({
                    "type": "hero",
                    "label": "帳戶餘額",
                    "value": f"${data['balance_usd']:.2f}",
                    "color": COLORS["success"],
                })
            if "credits_used_usd" in data and "credits_total_usd" in data:
                used = data["credits_used_usd"]
                total = data["credits_total_usd"]
                pct = round(used / total * 100, 1) if total > 0 else 0
                rows.append({
                    "type": "bar", "label": "Credits 用量", "percent": pct,
                    "detail": f"${used:.2f} / ${total:.2f}",
                    "color": self._pct_color(pct),
                })
            month_val = f"${data['month_usage_usd']:.4f}" if "month_usage_usd" in data else ""
            limit_val = f"${data['hard_limit_usd']:.0f}" if "hard_limit_usd" in data else ""
            if month_val or limit_val:
                rows.append({
                    "type": "pair",
                    "left_label": "本月用量", "left_value": month_val,
                    "right_label": "月上限", "right_value": limit_val,
                })
            tier_val = str(data["tier"]) if data.get("tier") else ""
            auto_val = "已啟用" if data.get("auto_recharge") else ""
            if tier_val or auto_val:
                rows.append({
                    "type": "pair",
                    "left_label": "用量等級", "left_value": tier_val,
                    "right_label": "自動儲值", "right_value": auto_val,
                })

        elif service_name == "Claude.ai 用量 (瀏覽器)":
            self._browser_header(data, rows)
            if data.get("session_percent") is not None:
                pct = data["session_percent"]
                reset = data.get("session_reset", "")
                rows.append({
                    "type": "bar", "label": "本次工作階段", "percent": pct,
                    "color": self._pct_color(pct),
                    "reset_text": reset if reset else None,
                    "reset_urgent": True,
                })
            if data.get("weekly_percent") is not None:
                pct = data["weekly_percent"]
                reset = data.get("weekly_reset", "")
                rows.append({
                    "type": "bar", "label": "每週限額", "percent": pct,
                    "color": self._pct_color(pct),
                    "reset_text": reset if reset else None,
                })
            if data.get("extra_enabled") or "extra_spent" in data or "extra_balance" in data:
                pct   = data.get("extra_percent", 0)
                reset = data.get("extra_resets", "")
                spent = data.get("extra_spent")
                limit = data.get("extra_limit")
                bal   = data.get("extra_balance")
                rows.append({
                    "type": "bar", "label": "額外用量", "percent": pct,
                    "color": self._pct_color(pct),
                    "reset_text": reset if reset else None,
                })
                parts = []
                if spent is not None and limit is not None:
                    parts.append(f"${spent:.2f} / ${limit:.0f}")
                elif spent is not None:
                    parts.append(f"已花費 ${spent:.2f}")
                if bal is not None:
                    parts.append(f"餘額 ${bal:.2f}")
                if "auto_reload" in data:
                    parts.append("自動儲值" if data["auto_reload"] else "儲值:關")
                if parts:
                    rows.append(("", "  \u00b7  ".join(parts), COLORS["green"]))

        elif service_name == "Claude API 帳單 (瀏覽器)":
            self._browser_header(data, rows)
            if "balance_usd" in data:
                rows.append({
                    "type": "hero",
                    "label": "帳戶餘額",
                    "value": f"${data['balance_usd']:.2f}",
                    "color": COLORS["success"],
                    "badge": str(data["plan"]) if data.get("plan") else None,
                })
            month_val = f"${data['this_month_usd']:.4f}" if "this_month_usd" in data else ""
            next_val = data["next_billing"] if data.get("next_billing") else ""
            if month_val or next_val:
                rows.append({
                    "type": "pair",
                    "left_label": "本月用量", "left_value": month_val,
                    "right_label": "下次計費", "right_value": next_val,
                })
            monthly_val = f"${data['monthly_usd']:.2f}" if "monthly_usd" in data else ""
            limit_val = f"${data['spend_limit_usd']:.2f}" if "spend_limit_usd" in data else ""
            if monthly_val or limit_val:
                rows.append({
                    "type": "pair",
                    "left_label": "月費", "left_value": monthly_val,
                    "right_label": "消費上限", "right_value": limit_val,
                })

        elif service_name == "GitHub Copilot (瀏覽器)":
            self._browser_header(data, rows)
            consumed = data.get("included_consumed")
            total = data.get("included_total")
            pct = data.get("included_percent")
            if consumed is not None and total is not None:
                remaining = total - consumed
                hero_color = self._pct_color(pct) if pct is not None else COLORS["info"]
                rows.append({
                    "type": "hero",
                    "label": "PREMIUM REQUESTS 剩餘",
                    "value": f"{remaining:.0f}",
                    "unit": f"/{total:.0f}",
                    "color": hero_color,
                    "badge": data.get("plan"),
                })
            if pct is not None:
                detail = f"{consumed:.1f} / {total:.0f} 次" if consumed is not None and total is not None else ""
                reset_days = data.get("resets_in_days")
                rows.append({
                    "type": "bar", "label": "Premium Requests", "percent": pct,
                    "detail": detail, "color": self._pct_color(pct),
                    "reset_text": f"{reset_days} 天後" if reset_days is not None else None,
                    "reset_urgent": (reset_days or 99) <= 3,
                })
            if data.get("billed_usd") and data["billed_usd"] > 0:
                rows.append(("已計費", f"${data['billed_usd']:.2f}", COLORS["peach"]))
            if data.get("next_billing"):
                rows.append(("下次計費", data["next_billing"], COLORS["violet"]))

        elif service_name == "OpenRouter (瀏覽器)":
            self._browser_header(data, rows)
            if data.get("parse_error"):
                rows.append(("解析失敗", str(data["parse_error"]), COLORS["error"]))
            if "balance_usd" in data:
                rows.append({
                    "type": "hero",
                    "label": "帳戶餘額",
                    "value": f"${data['balance_usd']:.2f}",
                    "color": COLORS["success"],
                })
            spend_val = f"${data['month_spend_usd']:.4f}" if data.get("month_spend_usd") is not None else ""
            req_val = f"{data['month_requests']:,} 次" if data.get("month_requests") is not None else ""
            if spend_val or req_val:
                rows.append({
                    "type": "pair",
                    "left_label": "本月花費", "left_value": spend_val,
                    "right_label": "請求次數", "right_value": req_val,
                })
            tokens_val = format_tokens(int(data["month_tokens"])) if data.get("month_tokens") is not None else ""
            model_val = str(data["top_model"])[:20] if data.get("top_model") else ""
            if tokens_val or model_val:
                rows.append({
                    "type": "pair",
                    "left_label": "Tokens", "left_value": tokens_val,
                    "right_label": "常用模型", "right_value": model_val,
                })

        if not rows:
            rows.append(("無資料", "", WIDGET_SUBTEXT))

        return rows

    def _browser_header(self, data: dict, rows: list):
        if data.get("updated_at"):
            self.time_label.config(text=data["updated_at"])
        if data.get("stale_warning"):
            rows.append((data["stale_warning"], "", COLORS["warning"]))
