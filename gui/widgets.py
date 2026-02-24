import tkinter as tk
from tkinter import ttk
from services.base import ServiceResult


COLORS = {
    "bg": "#1e1e2e",
    "card_bg": "#24273a",
    "card_border": "#363a4f",
    "success": "#a6e3a1",
    "error": "#f38ba8",
    "warning": "#f9e2af",
    "info": "#89b4fa",
    "text": "#cad3f5",
    "subtext": "#6e738d",
    "accent": "#89dceb",
    "title_bg": "#181926",
    "mauve": "#c6a0f6",
    "peach": "#f5a97f",
    "green": "#a6e3a1",
    "teal": "#8bd5ca",
    "row_alt": "#1e2030",
}

# Service accent colors for top border
SERVICE_ACCENTS = {
    "OpenAI 帳單 (瀏覽器)":    "#74c7ec",  # sapphire
    "Claude.ai 用量 (瀏覽器)": "#c6a0f6",  # mauve
    "Claude API 帳單 (瀏覽器)":"#cba6f7",  # lavender
    "GitHub Copilot (瀏覽器)": "#a6e3a1",  # green
}


def format_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


class ProgressBar(tk.Canvas):
    """Smooth rounded Canvas progress bar."""

    HEIGHT = 8

    def __init__(self, parent, percent: float = 0, color: str = COLORS["info"], **kwargs):
        kwargs.setdefault("height", self.HEIGHT)
        kwargs.setdefault("bg", COLORS["card_bg"])
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(parent, **kwargs)
        self._color = color
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
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1:
            return
        r = h // 2  # corner radius
        # Track
        self._round_rect(0, 0, w, h, r, fill=COLORS["card_border"], outline="")
        # Fill
        fw = max(0, int(w * self._percent / 100))
        if fw > 0:
            self._round_rect(0, 0, fw, h, r, fill=self._color, outline="")

    def _round_rect(self, x1, y1, x2, y2, r, **kwargs):
        r = min(r, (x2 - x1) // 2, (y2 - y1) // 2)
        self.create_oval(x1, y1, x1 + 2*r, y1 + 2*r, **kwargs)
        self.create_oval(x2 - 2*r, y1, x2, y1 + 2*r, **kwargs)
        self.create_oval(x1, y2 - 2*r, x1 + 2*r, y2, **kwargs)
        self.create_oval(x2 - 2*r, y2 - 2*r, x2, y2, **kwargs)
        self.create_rectangle(x1 + r, y1, x2 - r, y2, **kwargs)
        self.create_rectangle(x1, y1 + r, x2, y2 - r, **kwargs)


class ServiceCard(tk.Frame):
    def __init__(self, parent, service_name: str, **kwargs):
        kwargs.setdefault("bg", COLORS["card_bg"])
        kwargs.setdefault("relief", "flat")
        kwargs.setdefault("bd", 0)
        super().__init__(parent, **kwargs)
        self.service_name = service_name
        self._progress_bars: list[ProgressBar] = []
        self._build_ui()

    def _build_ui(self):
        accent_color = SERVICE_ACCENTS.get(self.service_name, COLORS["info"])

        # Top accent bar
        tk.Frame(self, bg=accent_color, height=3).pack(fill="x", side="top")

        # Header row
        header = tk.Frame(self, bg=COLORS["card_bg"], padx=14, pady=10)
        header.pack(fill="x")

        self.status_dot = tk.Label(
            header,
            text="●",
            fg=COLORS["subtext"],
            bg=COLORS["card_bg"],
            font=("Segoe UI", 9),
        )
        self.status_dot.pack(side="left")

        tk.Label(
            header,
            text=f"  {self.service_name}",
            fg=COLORS["text"],
            bg=COLORS["card_bg"],
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        # Divider
        tk.Frame(self, bg=COLORS["card_border"], height=1).pack(fill="x", padx=0)

        # Content area — rows added dynamically
        self.content_frame = tk.Frame(self, bg=COLORS["card_bg"], padx=14, pady=8)
        self.content_frame.pack(fill="both", expand=True)

        # Initial placeholder
        self._placeholder = tk.Label(
            self.content_frame,
            text="載入中...",
            fg=COLORS["subtext"],
            bg=COLORS["card_bg"],
            font=("Segoe UI", 9),
            anchor="w",
        )
        self._placeholder.pack(fill="x", pady=2)

        # Bottom padding
        tk.Frame(self, bg=COLORS["card_bg"], height=6).pack()

    # ── Public update methods ──────────────────────────────────────────────

    def update_result(self, result: ServiceResult):
        self._clear_content()

        if not result.success:
            if result.error and "等待瀏覽器" in result.error:
                self.status_dot.config(fg=COLORS["warning"])
                self._add_row(result.error, value_color=COLORS["subtext"])
            else:
                self.status_dot.config(fg=COLORS["error"])
                msg = result.error or "未知錯誤"
                self._add_row("錯誤", msg, value_color=COLORS["error"])
            return

        self.status_dot.config(fg=COLORS["success"])
        rows = self._format_data(result.service_name, result.data)
        self._render_rows(rows)

    def set_loading(self):
        self.status_dot.config(fg=COLORS["warning"])
        self._clear_content()
        self._add_row("更新中...", value_color=COLORS["warning"])

    # ── Internal rendering helpers ─────────────────────────────────────────

    def _clear_content(self):
        for w in self.content_frame.winfo_children():
            w.destroy()
        self._progress_bars.clear()
        if hasattr(self, "_placeholder"):
            self._placeholder = None

    def _render_rows(self, rows: list):
        """rows: list of (label, value, extra) tuples or special dicts."""
        for i, row in enumerate(rows):
            bg = COLORS["row_alt"] if i % 2 == 0 else COLORS["card_bg"]
            if isinstance(row, dict) and row.get("type") == "bar":
                self._add_progress_row(
                    row["label"], row["percent"],
                    row.get("detail", ""), row.get("color", COLORS["info"]),
                    bg=bg,
                )
            elif isinstance(row, dict) and row.get("type") == "divider":
                tk.Frame(self.content_frame, bg=COLORS["card_border"], height=1).pack(
                    fill="x", pady=(4, 2))
                tk.Label(
                    self.content_frame,
                    text=row["label"],
                    fg=COLORS["subtext"],
                    bg=COLORS["card_bg"],
                    font=("Segoe UI", 8),
                    anchor="w",
                ).pack(fill="x")
            else:
                label, value, *rest = row if isinstance(row, (list, tuple)) else (row, "", [])
                vc = rest[0] if rest else COLORS["text"]
                self._add_row(label, value, value_color=vc, bg=bg)

    def _add_row(self, label: str, value: str = "", value_color: str = None, bg: str = None):
        if bg is None:
            bg = COLORS["card_bg"]
        if value_color is None:
            value_color = COLORS["text"]
        row = tk.Frame(self.content_frame, bg=bg)
        row.pack(fill="x", pady=1)
        # inner padding
        inner = tk.Frame(row, bg=bg)
        inner.pack(fill="x", padx=2, pady=1)
        if value:
            tk.Label(
                inner, text=label, fg=COLORS["subtext"], bg=bg,
                font=("Segoe UI", 8), anchor="w", width=10,
            ).pack(side="left")
            tk.Label(
                inner, text=value, fg=value_color, bg=bg,
                font=("Segoe UI", 9, "bold"), anchor="w",
            ).pack(side="left", fill="x", expand=True)
        else:
            tk.Label(
                inner, text=label, fg=value_color, bg=bg,
                font=("Segoe UI", 9), anchor="w",
            ).pack(fill="x")

    def _add_progress_row(self, label: str, percent: float, detail: str = "",
                          color: str = None, bg: str = None):
        if bg is None:
            bg = COLORS["card_bg"]
        if color is None:
            color = self._pct_color(percent)

        row = tk.Frame(self.content_frame, bg=bg)
        row.pack(fill="x", pady=(3, 1))
        inner = tk.Frame(row, bg=bg, padx=2)
        inner.pack(fill="x")

        # Label row: name + pct
        top = tk.Frame(inner, bg=bg)
        top.pack(fill="x")
        tk.Label(top, text=label, fg=COLORS["subtext"], bg=bg,
                 font=("Segoe UI", 8), anchor="w").pack(side="left")
        tk.Label(top, text=f"{percent:.1f}%", fg=color, bg=bg,
                 font=("Segoe UI", 8, "bold"), anchor="e").pack(side="right")

        # Progress bar
        pb = ProgressBar(inner, percent=percent, color=color)
        pb.pack(fill="x", pady=(2, 1))
        self._progress_bars.append(pb)

        # Detail line
        if detail:
            tk.Label(inner, text=detail, fg=COLORS["subtext"], bg=bg,
                     font=("Segoe UI", 8), anchor="w").pack(fill="x")

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
                rows.append(("提示", data["plan_error"], COLORS["subtext"]))

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
                rows.append(("提示", data["note"], COLORS["subtext"]))

        elif service_name == "Claude Web 額度":
            if data.get("display_name"):
                rows.append(("帳號", data["display_name"]))
            if data.get("plan_type"):
                rows.append(("方案", data["plan_type"]))
            if data.get("session_percent") is not None:
                pct = data["session_percent"]
                reset = data.get("session_reset", "")
                rows.append({"type": "bar", "label": "本次工作階段", "percent": pct,
                             "detail": f"重置於: {reset}" if reset else "", "color": self._pct_color(pct)})
            if data.get("weekly_percent") is not None:
                pct = data["weekly_percent"]
                reset = data.get("weekly_reset", "")
                rows.append({"type": "bar", "label": "每週限額", "percent": pct,
                             "detail": f"重置於: {reset}" if reset else "", "color": self._pct_color(pct)})
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

        elif service_name == "OpenAI 帳單 (瀏覽器)":
            self._browser_header_rows(data, rows)
            if "balance_usd" in data:
                rows.append(("帳戶餘額", f"${data['balance_usd']:.2f}", COLORS["green"]))
            if "credits_used_usd" in data and "credits_total_usd" in data:
                used = data["credits_used_usd"]
                total = data["credits_total_usd"]
                pct = round(used / total * 100, 1) if total > 0 else 0
                rows.append({"type": "bar", "label": "Credits", "percent": pct,
                             "detail": f"${used:.2f} / ${total:.2f}", "color": self._pct_color(pct)})
            if "month_usage_usd" in data:
                rows.append(("本月用量", f"${data['month_usage_usd']:.4f}"))
            if "hard_limit_usd" in data:
                rows.append(("月上限", f"${data['hard_limit_usd']:.2f}"))
            if data.get("tier"):
                rows.append(("用量等級", data["tier"]))
            if data.get("auto_recharge"):
                rows.append(("自動儲值", "已啟用", COLORS["success"]))

        elif service_name == "Claude.ai 用量 (瀏覽器)":
            self._browser_header_rows(data, rows)
            if data.get("session_percent") is not None:
                pct = data["session_percent"]
                reset = data.get("session_reset", "")
                rows.append({"type": "bar", "label": "本次工作階段", "percent": pct,
                             "detail": f"重置於: {reset}" if reset else "", "color": self._pct_color(pct)})
            if data.get("weekly_percent") is not None:
                pct = data["weekly_percent"]
                reset = data.get("weekly_reset", "")
                rows.append({"type": "bar", "label": "每週限額", "percent": pct,
                             "detail": f"重置於: {reset}" if reset else "", "color": self._pct_color(pct)})
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
            self._browser_header_rows(data, rows)
            if data.get("plan"):
                rows.append(("方案", data["plan"]))
            pct = data.get("included_percent")
            if pct is not None:
                consumed = data.get("included_consumed")
                total = data.get("included_total")
                detail = f"{consumed:.1f} / {total:.0f} 次" if consumed is not None and total is not None else ""
                rows.append({"type": "bar", "label": "Premium Requests", "percent": pct,
                             "detail": detail, "color": self._pct_color(pct)})
            if data.get("billed_usd") and data["billed_usd"] > 0:
                rows.append(("已計費", f"${data['billed_usd']:.2f}", COLORS["peach"]))
            if data.get("resets_in_days") is not None:
                rows.append(("重置於", f"{data['resets_in_days']} 天後"))
            if data.get("next_billing"):
                rows.append(("下次計費", data["next_billing"]))

        if not rows:
            rows.append(("無資料", "", COLORS["subtext"]))

        return rows

    def _browser_header_rows(self, data: dict, rows: list):
        if data.get("updated_at"):
            rows.append(("更新時間", data["updated_at"], COLORS["subtext"]))
        if data.get("stale_warning"):
            rows.append((data["stale_warning"], "", COLORS["warning"]))
