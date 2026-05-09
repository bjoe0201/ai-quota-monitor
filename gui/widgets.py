import platform
import tkinter as tk
from tkinter import ttk
from services.base import ServiceResult


# ── Platform fonts ─────────────────────────────────────────────────────────
if platform.system() == "Darwin":
    UI_FONT = "SF Pro Text"
    MONO_FONT = "SF Mono"
else:
    UI_FONT = "Segoe UI Variable"
    MONO_FONT = "Cascadia Mono"


# ── Colors (Linear / Raycast style) ───────────────────────────────────────
COLORS = {
    # Backgrounds
    "bg":            "#0a0a0c",
    "card_bg":       "#111114",
    "card_bg_hover": "#16161a",
    "title_bg":      "#0a0a0c",
    "row_alt":       "#111114",

    # Borders
    "border":        "#1f1f24",
    "border_strong": "#2a2a32",
    "card_border":   "#1f1f24",

    # Text
    "text":          "#fafafa",
    "text_muted":    "#a1a1aa",
    "text_dim":      "#71717a",
    "text_faint":    "#52525b",
    "subtext":       "#71717a",

    # Semantic
    "success":       "#34d399",
    "warning":       "#fbbf24",
    "error":         "#f87171",
    "info":          "#60a5fa",
    "violet":        "#a78bfa",
    "peach":         "#fbbf24",

    # Legacy aliases
    "green":         "#34d399",
    "accent":        "#60a5fa",
    "mauve":         "#a78bfa",
    "teal":          "#34d399",
}

SERVICE_ACCENTS = {
    "OpenAI 帳單 (瀏覽器)":     "#60a5fa",
    "Claude.ai 用量 (瀏覽器)":  "#a78bfa",
    "Claude API 帳單 (瀏覽器)": "#c084fc",
    "GitHub Copilot (瀏覽器)":  "#34d399",
    "OpenRouter (瀏覽器)":      "#818cf8",
}


# ── Font tokens ────────────────────────────────────────────────────────────
FONT_TITLE      = (UI_FONT, 11, "bold")
FONT_HERO       = (MONO_FONT, 28, "bold")
FONT_HERO_UNIT  = (MONO_FONT, 14)
FONT_HERO_LABEL = (UI_FONT, 8, "bold")
FONT_KV_LABEL   = (UI_FONT, 9)
FONT_KV_VALUE   = (MONO_FONT, 10, "bold")
FONT_BAR_LABEL  = (UI_FONT, 9)
FONT_BAR_PCT    = (MONO_FONT, 9, "bold")
FONT_BAR_DETAIL = (MONO_FONT, 8)
FONT_RESET_PILL = (MONO_FONT, 8, "bold")
FONT_BADGE      = (UI_FONT, 8)
FONT_TIMESTAMP  = (MONO_FONT, 8)


def format_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


# ── 28-segment progress bar ───────────────────────────────────────────────

class ProgressBar(tk.Canvas):
    HEIGHT = 8
    SEGMENTS = 28
    SEG_GAP = 2

    def __init__(self, parent, percent: float = 0, color: str = None, **kw):
        kw.setdefault("height", self.HEIGHT)
        kw.setdefault("bg", COLORS["card_bg"])
        kw.setdefault("highlightthickness", 0)
        super().__init__(parent, **kw)
        self._color = color or COLORS["info"]
        self._percent = percent
        self.bind("<Configure>", lambda e: self._draw())
        self._draw()

    def set(self, percent: float, color: str = None):
        self._percent = max(0.0, min(100.0, percent))
        if color:
            self._color = color
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1:
            return
        seg_total_gap = self.SEG_GAP * (self.SEGMENTS - 1)
        seg_w = (w - seg_total_gap) / self.SEGMENTS
        filled = round((self._percent / 100) * self.SEGMENTS)
        for i in range(self.SEGMENTS):
            x1 = i * (seg_w + self.SEG_GAP)
            x2 = x1 + seg_w
            color = self._color if i < filled else COLORS["border"]
            self.create_rectangle(x1, 0, x2, h, fill=color, outline="", width=0)


# ── ServiceCard ────────────────────────────────────────────────────────────

class ServiceCard(tk.Frame):
    def __init__(self, parent, service_name: str, **kwargs):
        kwargs.setdefault("bg", COLORS["card_bg"])
        kwargs.setdefault("relief", "flat")
        kwargs.setdefault("bd", 0)
        super().__init__(parent, **kwargs)
        self.service_name = service_name
        self._progress_bars: list[ProgressBar] = []
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
        header = tk.Frame(self, bg=COLORS["card_bg"], padx=16, pady=14)
        header.pack(fill="x")

        # 22x22 glyph icon
        glyph_text = self._glyph_for(self.service_name)
        glyph = tk.Frame(header, bg=accent, width=22, height=22)
        glyph.pack(side="left")
        glyph.pack_propagate(False)
        tk.Label(glyph, text=glyph_text, bg=accent, fg=COLORS["bg"],
                 font=(MONO_FONT, 8, "bold")).pack(expand=True)

        # Short name
        tk.Label(header, text=f"  {self._short_name(self.service_name)}",
                 fg=COLORS["text"], bg=COLORS["card_bg"],
                 font=FONT_TITLE).pack(side="left")

        # Timestamp (right side)
        self.time_label = tk.Label(header, text="",
                                   fg=COLORS["text_faint"], bg=COLORS["card_bg"],
                                   font=FONT_TIMESTAMP)
        self.time_label.pack(side="right")

        # Status dot (right side, before timestamp)
        self.status_dot = tk.Label(header, text="●",
                                   fg=COLORS["text_dim"], bg=COLORS["card_bg"],
                                   font=(UI_FONT, 6))
        self.status_dot.pack(side="right", padx=(0, 4))

        # Content area
        self.content_frame = tk.Frame(self, bg=COLORS["card_bg"], padx=16, pady=0)
        self.content_frame.pack(fill="both", expand=True, pady=(0, 14))

        # Placeholder
        self._placeholder = tk.Label(
            self.content_frame, text="載入中...",
            fg=COLORS["text_dim"], bg=COLORS["card_bg"],
            font=FONT_KV_LABEL, anchor="w",
        )
        self._placeholder.pack(fill="x", pady=2)

    # ── Public update methods ──────────────────────────────────────────────

    def update_result(self, result: ServiceResult):
        self._clear_content()

        if not result.success:
            if result.error and "等待瀏覽器" in result.error:
                self.status_dot.config(fg=COLORS["warning"])
                self._add_row(result.error, value_color=COLORS["text_dim"], last=True)
            else:
                self.status_dot.config(fg=COLORS["error"])
                msg = result.error or "未知錯誤"
                self._add_row("錯誤", msg, value_color=COLORS["error"], last=True)
            return

        self.status_dot.config(fg=COLORS["success"])
        rows = self._format_data(result.service_name, result.data)
        self._render_rows(rows)

    def set_loading(self):
        self.status_dot.config(fg=COLORS["warning"])
        self._clear_content()
        self._add_row("更新中...", value_color=COLORS["warning"], last=True)

    # ── Internal rendering helpers ─────────────────────────────────────────

    def _clear_content(self):
        for w in self.content_frame.winfo_children():
            w.destroy()
        self._progress_bars.clear()
        if hasattr(self, "_placeholder"):
            self._placeholder = None

    def _render_rows(self, rows: list):
        # Find last KV/pair row index (for omitting trailing separator)
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
                    self._add_progress_row(
                        row["label"], row["percent"],
                        row.get("detail", ""), row.get("color", COLORS["info"]),
                        reset_text=row.get("reset_text"),
                        reset_urgent=row.get("reset_urgent", False),
                    )
                elif rtype == "divider":
                    tk.Frame(self.content_frame, bg=COLORS["border"],
                             height=1).pack(fill="x", pady=(8, 4))
                    tk.Label(
                        self.content_frame, text=row["label"],
                        fg=COLORS["text_dim"], bg=COLORS["card_bg"],
                        font=FONT_HERO_LABEL, anchor="w",
                    ).pack(fill="x")
                elif rtype == "pair":
                    self._add_pair_row(
                        row.get("left_label", ""), row.get("left_value", ""),
                        row.get("right_label", ""), row.get("right_value", ""),
                        last=is_last,
                    )
            else:
                label, value, *rest = row if isinstance(row, (list, tuple)) else (row, "", [])
                vc = rest[0] if rest else COLORS["text"]
                self._add_row(label, value, value_color=vc, last=is_last)

    def _add_hero(self, label: str, value: str, color: str = None,
                  value_unit: str = None, badge: str = None):
        color = color or COLORS["text"]
        bg = COLORS["card_bg"]
        block = tk.Frame(self.content_frame, bg=bg)
        block.pack(fill="x", pady=(2, 14))

        # Label row (with optional badge)
        top = tk.Frame(block, bg=bg)
        top.pack(fill="x")
        tk.Label(top, text=label.upper(), fg=COLORS["text_dim"], bg=bg,
                 font=FONT_HERO_LABEL, anchor="w").pack(side="left")
        if badge:
            b = tk.Frame(top, bg=bg,
                         highlightthickness=1, highlightbackground=COLORS["border"])
            b.pack(side="right", padx=4)
            tk.Label(b, text=f" {badge} ", fg=COLORS["text_muted"], bg=bg,
                     font=FONT_BADGE).pack()

        # Main value
        valrow = tk.Frame(block, bg=bg)
        valrow.pack(fill="x", anchor="w", pady=(2, 0))
        tk.Label(valrow, text=str(value), fg=color, bg=bg,
                 font=FONT_HERO).pack(side="left", anchor="s")
        if value_unit:
            tk.Label(valrow, text=value_unit, fg=COLORS["text_muted"], bg=bg,
                     font=FONT_HERO_UNIT).pack(side="left", anchor="s", padx=(2, 0))

        # Separator after hero
        tk.Frame(self.content_frame, bg=COLORS["border"], height=1).pack(fill="x")

    def _add_row(self, label: str, value: str = "", value_color: str = None,
                 last: bool = False):
        bg = COLORS["card_bg"]
        vc = value_color or COLORS["text"]
        row = tk.Frame(self.content_frame, bg=bg)
        row.pack(fill="x")
        inner = tk.Frame(row, bg=bg)
        inner.pack(fill="x", padx=0, pady=6)

        if value:
            tk.Label(inner, text=label, fg=COLORS["text_dim"], bg=bg,
                     font=FONT_KV_LABEL, anchor="w").pack(side="left")
            tk.Label(inner, text=value, fg=vc, bg=bg,
                     font=FONT_KV_VALUE, anchor="e").pack(side="right")
        else:
            tk.Label(inner, text=label, fg=vc, bg=bg,
                     font=FONT_KV_LABEL, anchor="w").pack(fill="x")

        if not last:
            tk.Frame(self.content_frame, bg=COLORS["border"], height=1).pack(fill="x")

    def _add_pair_row(self, left_label: str, left_value: str = "",
                       right_label: str = "", right_value: str = "",
                       last: bool = False):
        bg = COLORS["card_bg"]
        row = tk.Frame(self.content_frame, bg=bg)
        row.pack(fill="x")
        inner = tk.Frame(row, bg=bg)
        inner.pack(fill="x", padx=0, pady=6)

        left_f = tk.Frame(inner, bg=bg)
        left_f.pack(side="left", fill="x", expand=True)
        tk.Label(left_f, text=left_label, fg=COLORS["text_dim"], bg=bg,
                 font=FONT_KV_LABEL, anchor="w").pack(side="left", padx=(0, 6))
        tk.Label(left_f, text=left_value, fg=COLORS["text"], bg=bg,
                 font=FONT_KV_VALUE, anchor="w").pack(side="left")

        right_f = tk.Frame(inner, bg=bg)
        right_f.pack(side="left", fill="x", expand=True)
        tk.Label(right_f, text=right_label, fg=COLORS["text_dim"], bg=bg,
                 font=FONT_KV_LABEL, anchor="w").pack(side="left", padx=(0, 6))
        tk.Label(right_f, text=right_value, fg=COLORS["text"], bg=bg,
                 font=FONT_KV_VALUE, anchor="w").pack(side="left")

        if not last:
            tk.Frame(self.content_frame, bg=COLORS["border"], height=1).pack(fill="x")

    def _add_progress_row(self, label: str, percent: float, detail: str = "",
                          color: str = None, reset_text: str = None,
                          reset_urgent: bool = False):
        bg = COLORS["card_bg"]
        if color is None:
            color = self._pct_color(percent)

        row = tk.Frame(self.content_frame, bg=bg)
        row.pack(fill="x", pady=(6, 4))
        inner = tk.Frame(row, bg=bg)
        inner.pack(fill="x")

        # Label + reset pill (next to label) + percentage
        top = tk.Frame(inner, bg=bg)
        top.pack(fill="x")
        tk.Label(top, text=label, fg=COLORS["text_dim"], bg=bg,
                 font=FONT_BAR_LABEL, anchor="w").pack(side="left")
        tk.Label(top, text=f"{percent:.1f}%", fg=color, bg=bg,
                 font=FONT_BAR_PCT, anchor="e").pack(side="right")
        if reset_text:
            self._add_reset_pill(top, reset_text, urgent=reset_urgent,
                                 side="left")

        # Progress bar
        pb = ProgressBar(inner, percent=percent, color=color)
        pb.pack(fill="x", pady=(2, 1))
        self._progress_bars.append(pb)

        # Detail line
        if detail:
            detail_row = tk.Frame(inner, bg=bg)
            detail_row.pack(fill="x")
            tk.Label(detail_row, text=detail, fg=COLORS["text_dim"], bg=bg,
                     font=FONT_BAR_DETAIL, anchor="w").pack(side="left")

    def _add_reset_pill(self, parent, text: str, urgent: bool = False,
                        side: str = "right"):
        color = COLORS["warning"] if urgent else COLORS["violet"]
        bg = COLORS["card_bg"]
        pill = tk.Frame(parent, bg=bg,
                        highlightthickness=1, highlightbackground=color)
        pill.pack(side=side, padx=4)
        tk.Label(pill, text=f" \u21bb {text} ", fg=color, bg=bg,
                 font=FONT_RESET_PILL).pack()

    @staticmethod
    def _pct_color(pct: float) -> str:
        if pct >= 85:
            return COLORS["error"]
        elif pct >= 60:
            return COLORS["warning"]
        return COLORS["info"]

    # ── Data formatters ────────────────────────────────────────────────────

    def _format_data(self, service_name: str, data: dict) -> list:
        rows = []

        if service_name == "GitHub Copilot":
            src = "自動" if data.get("token_source") == "local" else "手動"
            if data.get("username"):
                rows.append(("帳號", f"{data['username']}  [{src}登入]"))
            if data.get("plan"):
                rows.append(("方案", data["plan"]))
            if data.get("enabled") is False:
                rows.append(("狀態", "未訂閱 Copilot", COLORS["error"]))
            elif data.get("enabled") is True:
                rows.append(("狀態", "已啟用", COLORS["success"]))
            if data.get("next_billing"):
                rows.append(("下次計費", data["next_billing"]))
            if data.get("org"):
                rows.append(("組織", data["org"]))
                rows.append(("活躍天數", f"{data.get('days_with_data', 0)} 天"))
                rows.append(("活躍用戶", str(data.get("latest_active_users", 0))))
            if data.get("org_error"):
                rows.append(("組織", data["org_error"], COLORS["warning"]))
            if data.get("plan_error"):
                rows.append(("提示", data["plan_error"], COLORS["text_dim"]))

        elif service_name == "Claude Code 訂閱":
            if data.get("display_name"):
                rows.append(("帳號", data["display_name"]))
            if data.get("subscription_type"):
                rows.append(("訂閱", data["subscription_type"]))
            if data.get("extra_usage"):
                rows.append(("擴充用量", "已啟用", COLORS["success"]))
            if data.get("today_tokens", 0) > 0:
                rows.append(("今日 Token", format_tokens(data["today_tokens"])))
            if data.get("today_messages") is not None:
                rows.append(("今日訊息", f"{data.get('today_messages', 0)} 則 / {data.get('today_sessions', 0)} 工作階段"))
            if data.get("total_sessions", 0) > 0:
                rows.append(("累計", f"{data['total_messages']} 則 / {data['total_sessions']} 次"))
            if data.get("models_used"):
                rows.append(("模型", ", ".join(data["models_used"])))
            if data.get("stats_date"):
                rows.append(("統計截至", data["stats_date"]))

        elif service_name == "Claude API":
            if data.get("date"):
                rows.append(("日期", data["date"]))
            input_t = data.get("today_input_tokens", 0)
            output_t = data.get("today_output_tokens", 0)
            rows.append(("輸入", format_tokens(input_t)))
            rows.append(("輸出", format_tokens(output_t)))
            cache_r = data.get("today_cache_read_tokens", 0)
            if cache_r > 0:
                rows.append(("快取讀取", format_tokens(cache_r)))
            if "today_cost_usd" in data:
                rows.append(("今日費用", f"${data['today_cost_usd']:.4f}", COLORS["peach"]))

        elif service_name == "OpenAI API":
            if data.get("plan"):
                rows.append(("方案", data["plan"]))
            if data.get("has_credits"):
                rows.append(("剩餘點數", f"${data.get('total_available', 0):.2f}", COLORS["green"]))
                rows.append(("已使用", f"${data.get('total_used', 0):.2f}"))
            if "month_usage_usd" in data:
                rows.append(("本月用量", f"${data['month_usage_usd']:.4f}"))
            if "hard_limit_usd" in data:
                rows.append(("月上限", f"${data['hard_limit_usd']:.2f}"))
            if data.get("credits_error"):
                rows.append(("點數", data["credits_error"], COLORS["warning"]))
            if data.get("usage_error"):
                rows.append(("用量", data["usage_error"], COLORS["warning"]))

        elif service_name == "Google Gemini":
            if data.get("key_valid"):
                rows.append(("API Key", "有效", COLORS["success"]))
                rows.append(("可用模型", f"{data.get('available_models_count', 0)} 個"))
            if data.get("project_id"):
                rows.append(("專案", data["project_id"]))
                quotas = data.get("cloud_quotas", [])
                for q in quotas[:3]:
                    rows.append((q["name"], str(q["limit"])))
            limits = data.get("free_tier_limits", {})
            if limits:
                fl = limits.get("gemini-2.0-flash", {})
                rows.append({"type": "divider", "label": "免費配額（gemini-2.0-flash）"})
                rows.append(("RPM / RPD", f"{fl.get('rpm','N/A')} / {fl.get('rpd','N/A')}"))
                rows.append(("TPM", format_tokens(fl.get("tpm", 0))))
            if data.get("note"):
                rows.append(("提示", data["note"], COLORS["text_dim"]))

        elif service_name == "Claude Web 額度":
            if data.get("display_name"):
                rows.append(("帳號", data["display_name"]))
            if data.get("plan_type"):
                rows.append(("方案", data["plan_type"]))
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

        elif service_name == "GitHub Copilot 額度":
            if data.get("copilot_plan"):
                rows.append(("方案", data["copilot_plan"]))
            if data.get("included_consumed") is not None:
                consumed = data["included_consumed"]
                total = data.get("included_total", 0)
                pct = data.get("included_percent", 0)
                detail = f"{consumed:.1f} / {total:.0f} 次"
                rows.append({"type": "bar", "label": "Premium Requests", "percent": pct,
                             "detail": detail, "color": self._pct_color(pct)})
            if data.get("billed_amount") is not None:
                rows.append(("已計費", f"${data['billed_amount']:.2f}", COLORS["peach"]))
            if data.get("resets_in_days") is not None:
                rows.append(("重置於", f"{data['resets_in_days']} 天後"))
            models = data.get("models", [])
            if models:
                rows.append({"type": "divider", "label": "模型使用量"})
                for m in models[:5]:
                    rows.append((m.get("name", "?")[:20],
                                 f"{m.get('included_requests', 0):.0f} 次  (${m.get('gross_amount', 0):.2f})"))
                if len(models) > 5:
                    rows.append((f"...共 {len(models)} 個模型", ""))

        # ── Browser services (with Hero) ───────────────────────────────────

        elif service_name == "OpenAI 帳單 (瀏覽器)":
            self._browser_header_rows(data, rows)
            # Hero: balance
            if "balance_usd" in data:
                rows.append({
                    "type": "hero",
                    "label": "帳戶餘額",
                    "value": f"${data['balance_usd']:.2f}",
                    "color": COLORS["success"],
                })
            # Bar: Credits
            if "credits_used_usd" in data and "credits_total_usd" in data:
                used = data["credits_used_usd"]
                total = data["credits_total_usd"]
                pct = round(used / total * 100, 1) if total > 0 else 0
                rows.append({
                    "type": "bar", "label": "Credits 用量", "percent": pct,
                    "detail": f"${used:.2f} / ${total:.2f}",
                    "color": self._pct_color(pct),
                })
            # KV pairs — 2x2 layout
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
            self._browser_header_rows(data, rows)
            # Bars
            if data.get("session_percent") is not None:
                pct = data["session_percent"]
                reset = data.get("session_reset", "")
                rows.append({
                    "type": "bar", "label": "本次工作階段", "percent": pct,
                    "color": self._pct_color(pct),
                    "reset_text": reset if reset else None,
                    "reset_urgent": True,  # session resets are usually urgent
                })
            if data.get("weekly_percent") is not None:
                pct = data["weekly_percent"]
                reset = data.get("weekly_reset", "")
                rows.append({
                    "type": "bar", "label": "每週限額", "percent": pct,
                    "color": self._pct_color(pct),
                    "reset_text": reset if reset else None,
                })
            # Extra usage
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
            self._browser_header_rows(data, rows)
            # Hero: balance
            if "balance_usd" in data:
                rows.append({
                    "type": "hero",
                    "label": "帳戶餘額",
                    "value": f"${data['balance_usd']:.2f}",
                    "color": COLORS["success"],
                    "badge": str(data["plan"]) if data.get("plan") else None,
                })
            # KV pairs — 2x2 layout
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
            self._browser_header_rows(data, rows)
            # Hero: remaining requests
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
            # Bar: usage
            if pct is not None:
                detail = f"{consumed:.1f} / {total:.0f} 次" if consumed is not None and total is not None else ""
                reset_days = data.get("resets_in_days")
                rows.append({
                    "type": "bar", "label": "Premium Requests", "percent": pct,
                    "detail": detail, "color": self._pct_color(pct),
                    "reset_text": f"{reset_days} 天後" if reset_days is not None else None,
                    "reset_urgent": (reset_days or 99) <= 3,
                })
            # KV pairs
            if data.get("billed_usd") and data["billed_usd"] > 0:
                rows.append(("已計費", f"${data['billed_usd']:.2f}", COLORS["peach"]))
            if data.get("next_billing"):
                rows.append(("下次計費", data["next_billing"], COLORS["violet"]))

        elif service_name == "OpenRouter (瀏覽器)":
            self._browser_header_rows(data, rows)
            if data.get("parse_error"):
                rows.append(("解析失敗", str(data["parse_error"]), COLORS["error"]))
            # Hero: balance
            if "balance_usd" in data:
                rows.append({
                    "type": "hero",
                    "label": "帳戶餘額",
                    "value": f"${data['balance_usd']:.2f}",
                    "color": COLORS["success"],
                })
            # KV pairs — 2x2 layout
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
            rows.append(("無資料", "", COLORS["text_dim"]))

        return rows

    def _browser_header_rows(self, data: dict, rows: list):
        if data.get("updated_at"):
            self.time_label.config(text=data["updated_at"])
        if data.get("stale_warning"):
            rows.append((data["stale_warning"], "", COLORS["warning"]))
