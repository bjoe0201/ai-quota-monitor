import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import webbrowser
import subprocess
import sys
from datetime import datetime

from config.manager import ConfigManager
from services.browser_data import (
    BrowserOpenAIService,
    BrowserClaudeUsageService,
    BrowserClaudeBillingService,
    BrowserGitHubCopilotService,
)
from services import local_server
from gui.widgets import ServiceCard, COLORS


SERVICES = [
    ("browser_openai",         BrowserOpenAIService()),
    ("browser_claude_usage",   BrowserClaudeUsageService()),
    ("browser_claude_billing", BrowserClaudeBillingService()),
    ("browser_github_copilot", BrowserGitHubCopilotService()),
]

# Mapping: service key → DATA_STORE source key (for live browser polling)
BROWSER_SERVICE_SOURCES = {
    "browser_openai":         "openai_billing",
    "browser_claude_usage":   "claude_usage",
    "browser_claude_billing": "claude_billing",
    "browser_github_copilot": "github_copilot",
}


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.config_data = self.config_manager.load()
        self._result_queue = queue.Queue()
        self._refresh_job = None
        self._last_browser_ts: dict[str, str] = {}  # source_key → received_at

        # Start local HTTP server for Tampermonkey browser data
        port = self.config_data.get("server_port", 7890)
        local_server.start(port)

        self.title("AI 額度監控")
        self.configure(bg=COLORS["bg"])
        self.resizable(True, True)
        self.minsize(680, 560)

        self._build_ui()
        self._position_window()

        # Start initial fetch
        self.after(200, self.refresh_all)

        # Initialize browser cards with proper "waiting" state (run once)
        self.after(250, self._init_browser_cards)

        # Poll for results from background threads
        self.after(100, self._poll_queue)

        # Poll for live browser data changes (every 1.5s)
        self.after(1500, self._poll_browser_live)

    def _position_window(self):
        self.update_idletasks()
        w, h = 760, 680
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        # ── Title bar ──────────────────────────────────────────────────────
        title_bar = tk.Frame(self, bg=COLORS["title_bg"])
        title_bar.pack(fill="x")

        # Left: icon + title
        left = tk.Frame(title_bar, bg=COLORS["title_bg"])
        left.pack(side="left", padx=16, pady=12)

        tk.Label(
            left, text="📊", bg=COLORS["title_bg"],
            font=("Segoe UI Emoji", 16),
        ).pack(side="left")

        title_text = tk.Frame(left, bg=COLORS["title_bg"])
        title_text.pack(side="left", padx=(8, 0))

        tk.Label(
            title_text, text="AI 額度監控",
            fg=COLORS["accent"], bg=COLORS["title_bg"],
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")

        tk.Label(
            title_text, text="AI Quota Monitor  ·  v1.8.3",
            fg=COLORS["subtext"], bg=COLORS["title_bg"],
            font=("Segoe UI", 8),
        ).pack(anchor="w")

        # Right: buttons
        btn_frame = tk.Frame(title_bar, bg=COLORS["title_bg"])
        btn_frame.pack(side="right", padx=14)

        self.refresh_btn = tk.Button(
            btn_frame, text="⟳  重新整理",
            command=self.refresh_all,
            bg=COLORS["info"], fg=COLORS["bg"],
            font=("Segoe UI", 9, "bold"),
            relief="flat", padx=12, pady=5, cursor="hand2",
            activebackground=COLORS["accent"], activeforeground=COLORS["bg"],
        )
        self.refresh_btn.pack(side="left", padx=(0, 6))

        tk.Button(
            btn_frame, text="🌐  開啟網頁",
            command=self._show_open_menu,
            bg=COLORS["card_border"], fg=COLORS["text"],
            font=("Segoe UI", 9),
            relief="flat", padx=12, pady=5, cursor="hand2",
            activebackground=COLORS["card_bg"], activeforeground=COLORS["text"],
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            btn_frame, text="⚙  設定",
            command=self.open_settings,
            bg=COLORS["card_border"], fg=COLORS["text"],
            font=("Segoe UI", 9),
            relief="flat", padx=12, pady=5, cursor="hand2",
            activebackground=COLORS["card_bg"], activeforeground=COLORS["text"],
        ).pack(side="left")

        # Thin separator
        tk.Frame(self, bg=COLORS["card_border"], height=1).pack(fill="x")

        # ── Status bar (must be packed before scroll area to reserve space) ──
        tk.Frame(self, bg=COLORS["card_border"], height=1).pack(fill="x", side="bottom")
        status_bar = tk.Frame(self, bg=COLORS["title_bg"], pady=5)
        status_bar.pack(fill="x", side="bottom")

        # ── Scrollable content ─────────────────────────────────────────────
        scroll_container = tk.Frame(self, bg=COLORS["bg"])
        scroll_container.pack(fill="both", expand=True)
        scroll_container.grid_rowconfigure(0, weight=1)
        scroll_container.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(scroll_container, bg=COLORS["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg=COLORS["bg"])

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        self._canvas_window = canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Keep scroll_frame width in sync with canvas width
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(
            self._canvas_window, width=e.width))

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # Cards grid
        self.cards = {}
        self._build_cards()

        self.status_dot_lbl = tk.Label(
            status_bar, text="●", fg=COLORS["subtext"],
            bg=COLORS["title_bg"], font=("Segoe UI", 9), padx=12,
        )
        self.status_dot_lbl.pack(side="left")

        self.status_label = tk.Label(
            status_bar, text="就緒",
            fg=COLORS["subtext"], bg=COLORS["title_bg"],
            font=("Segoe UI", 8),
        )
        self.status_label.pack(side="left")

    def _build_cards(self):
        pad = 14
        service_names = {
            "browser_openai":         "OpenAI 帳單 (瀏覽器)",
            "browser_claude_usage":   "Claude.ai 用量 (瀏覽器)",
            "browser_claude_billing": "Claude API 帳單 (瀏覽器)",
            "browser_github_copilot": "GitHub Copilot (瀏覽器)",
        }

        row_frame = None
        for i, (key, _) in enumerate(SERVICES):
            if i % 2 == 0:
                row_frame = tk.Frame(self.scroll_frame, bg=COLORS["bg"])
                row_frame.pack(fill="x", padx=pad, pady=(pad if i == 0 else pad // 2, 0))

            card = ServiceCard(row_frame, service_names[key])
            gap = pad // 2
            card.pack(side="left", fill="both", expand=True,
                      padx=(0, gap) if i % 2 == 0 else (0, 0))
            self.cards[key] = card

        tk.Frame(self.scroll_frame, bg=COLORS["bg"], height=pad).pack()

    def refresh_all(self):
        self.refresh_btn.config(state="disabled", text="⏳ 更新中...")
        self.status_label.config(text="更新中...", fg=COLORS["warning"])
        self.status_dot_lbl.config(fg=COLORS["warning"])
        # Notify all JS clients to re-fetch immediately
        local_server.request_refresh()
        config = self.config_manager.get()

        # browser_* services are driven by _poll_browser_live, skip here
        browser_keys = set(BROWSER_SERVICE_SOURCES.keys())

        for key, service in SERVICES:
            if key in browser_keys:
                continue  # 不干擾瀏覽器服務卡片
            svc_config = config["services"].get(key, {})
            if svc_config.get("enabled", True):
                self.cards[key].set_loading()
                t = threading.Thread(
                    target=self._fetch_service,
                    args=(key, service, svc_config),
                    daemon=True
                )
                t.start()

        # Schedule auto-refresh (minimum 1 minute to avoid tight loop)
        minutes = max(1, config.get("auto_refresh_minutes", 30))
        if self._refresh_job:
            self.after_cancel(self._refresh_job)
        self._refresh_job = self.after(minutes * 60 * 1000, self.refresh_all)

        # All cards are browser-driven; restore button after brief delay
        browser_keys = set(BROWSER_SERVICE_SOURCES.keys())
        all_browser = all(k in browser_keys for k, _ in SERVICES)
        if all_browser:
            self.after(1500, self._restore_refresh_btn)

    def _init_browser_cards(self):
        """Run once at startup: fetch each browser service to show proper initial state."""
        config = self.config_manager.get()
        for svc_key in BROWSER_SERVICE_SOURCES:
            svc_obj = next((s for k, s in SERVICES if k == svc_key), None)
            if svc_obj and svc_key in self.cards:
                svc_config = config["services"].get(svc_key, {})
                t = threading.Thread(
                    target=self._fetch_service,
                    args=(svc_key, svc_obj, svc_config),
                    daemon=True
                )
                t.start()

    def _poll_browser_live(self):
        """Check DATA_STORE every 1.5s; if a browser source has new data, refresh that card."""
        config = self.config_manager.get()
        for svc_key, src_key in BROWSER_SERVICE_SOURCES.items():
            entry = local_server.DATA_STORE.get(src_key)
            if entry is None:
                continue
            new_ts = entry.get("received_at", "")
            if new_ts != self._last_browser_ts.get(src_key, ""):
                self._last_browser_ts[src_key] = new_ts
                # Find the matching service object
                svc_obj = next((s for k, s in SERVICES if k == svc_key), None)
                if svc_obj and svc_key in self.cards:
                    svc_config = config["services"].get(svc_key, {})
                    t = threading.Thread(
                        target=self._fetch_service,
                        args=(svc_key, svc_obj, svc_config),
                        daemon=True
                    )
                    t.start()
        self.after(1500, self._poll_browser_live)

    def _fetch_service(self, key: str, service, config: dict):
        try:
            result = service.fetch(config)
        except Exception as e:
            from services.base import ServiceResult
            result = ServiceResult(
                service_name=service.name,
                success=False,
                error=str(e)
            )
        self._result_queue.put((key, result))

    def _poll_queue(self):
        completed = []
        while not self._result_queue.empty():
            try:
                key, result = self._result_queue.get_nowait()
                self.cards[key].update_result(result)
                completed.append(key)
            except queue.Empty:
                break

        if completed:
            browser_keys = set(BROWSER_SERVICE_SOURCES.keys())
            non_browser_cards = [k for k in self.cards if k not in browser_keys]
            all_done = all(
                self.cards[k].status_dot.cget("fg") != COLORS["warning"]
                for k in non_browser_cards
            ) if non_browser_cards else True
            if all_done:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.status_label.config(text=f"最後更新: {now}", fg=COLORS["subtext"])
                self.status_dot_lbl.config(fg=COLORS["success"])
                self.refresh_btn.config(state="normal", text="⟳  重新整理")

        self.after(200, self._poll_queue)

    def _restore_refresh_btn(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_label.config(text=f"最後更新: {now}", fg=COLORS["subtext"])
        self.status_dot_lbl.config(fg=COLORS["success"])
        self.refresh_btn.config(state="normal", text="⟳  重新整理")

    _PAGE_URLS = [
        ("OpenAI 帳單",     "https://platform.openai.com/settings/organization/billing/overview?oclaw=1"),
        ("Claude.ai 用量",  "https://claude.ai/settings/usage?oclaw=1"),
        ("Claude API 帳單", "https://platform.claude.com/settings/billing?oclaw=1"),
        ("GitHub Copilot",  "https://github.com/settings/billing/premium_requests_usage?oclaw=1"),
    ]

    _oclaw_hwnds: set = set()  # 追蹤「一鍵全開」開啟的 Chrome 視窗 HWND
    _oflaw_hwnds: set = set()  # 追蹤「一鍵全開」開啟的 Firefox 視窗 HWND

    def _find_chrome(self) -> str | None:
        import shutil, os
        if sys.platform == "win32":
            candidates = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ]
        elif sys.platform == "darwin":
            candidates = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
        else:
            candidates = ["google-chrome", "chromium-browser", "chromium"]
        for c in candidates:
            if os.path.isfile(c) or shutil.which(c):
                return c
        return None

    def _find_firefox(self) -> str | None:
        import shutil, os
        if sys.platform == "win32":
            candidates = [
                r"C:\Program Files\Mozilla Firefox\firefox.exe",
                r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
            ]
        elif sys.platform == "darwin":
            candidates = ["/Applications/Firefox.app/Contents/MacOS/firefox"]
        else:
            candidates = ["firefox"]
        for c in candidates:
            if os.path.isfile(c) or shutil.which(c):
                return c
        return None

    def _get_chrome_hwnds(self) -> set:
        if sys.platform != "win32":
            return set()
        import ctypes, ctypes.wintypes
        u32 = ctypes.windll.user32
        hwnds = []
        buf = ctypes.create_unicode_buffer(512)
        def cb(hwnd, _):
            u32.GetClassNameW(hwnd, buf, 512)
            if buf.value == "Chrome_WidgetWin_1" and u32.IsWindowVisible(hwnd):
                u32.GetWindowTextW(hwnd, buf, 512)
                if buf.value:
                    hwnds.append(hwnd)
            return True
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        u32.EnumWindows(WNDENUMPROC(cb), 0)
        return set(hwnds)

    def _get_firefox_hwnds(self) -> set:
        if sys.platform != "win32":
            return set()
        import ctypes, ctypes.wintypes
        u32 = ctypes.windll.user32
        hwnds = []
        buf = ctypes.create_unicode_buffer(512)
        def cb(hwnd, _):
            u32.GetClassNameW(hwnd, buf, 512)
            if buf.value == "MozillaWindowClass" and u32.IsWindowVisible(hwnd):
                u32.GetWindowTextW(hwnd, buf, 512)
                if buf.value:
                    hwnds.append(hwnd)
            return True
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        u32.EnumWindows(WNDENUMPROC(cb), 0)
        return set(hwnds)

    def _open_all_in_new_window(self):
        """Open all four URLs in a single new Chrome window, track new HWNDs."""
        urls = [url for _, url in self._PAGE_URLS]
        chrome = self._find_chrome()
        if not chrome:
            for url in urls:
                webbrowser.open(url)
            return
        self._close_oclaw_window()
        before = self._get_chrome_hwnds()
        subprocess.Popen([chrome, "--new-window"] + urls)
        def track():
            import time
            for _ in range(20):  # up to 5s
                time.sleep(0.25)
                after = self._get_chrome_hwnds()
                new = after - before
                if new:
                    MainApp._oclaw_hwnds.update(new)
                    return
        threading.Thread(target=track, daemon=True).start()

    def _close_oclaw_window(self):
        """Close tracked Chrome windows (Win32) or oclaw-tagged tabs (macOS)."""
        if sys.platform == "win32":
            if not MainApp._oclaw_hwnds:
                return
            import ctypes
            u32 = ctypes.windll.user32
            WM_CLOSE = 0x0010
            for hwnd in list(MainApp._oclaw_hwnds):
                u32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            MainApp._oclaw_hwnds.clear()
        elif sys.platform == "darwin":
            script = (
                'tell application "Google Chrome"\n'
                '    set windowsToClose to {}\n'
                '    repeat with w in every window\n'
                '        repeat with t in every tab of w\n'
                '            if URL of t contains "oclaw=1" then\n'
                '                set end of windowsToClose to w\n'
                '                exit repeat\n'
                '            end if\n'
                '        end repeat\n'
                '    end repeat\n'
                '    repeat with w in windowsToClose\n'
                '        close w\n'
                '    end repeat\n'
                'end tell'
            )
            subprocess.run(["osascript", "-e", script])

    def _open_all_in_firefox(self):
        """Open all four URLs in a single new Firefox window, track new HWNDs."""
        urls = [url for _, url in self._PAGE_URLS]
        firefox = self._find_firefox()
        if not firefox:
            for url in urls:
                webbrowser.open(url)
            return
        self._close_oflaw_window()
        before = self._get_firefox_hwnds()
        subprocess.Popen([firefox, "--new-window"] + urls)
        def track():
            import time
            for _ in range(20):  # up to 5s
                time.sleep(0.25)
                after = self._get_firefox_hwnds()
                new = after - before
                if new:
                    MainApp._oflaw_hwnds.update(new)
                    return
        threading.Thread(target=track, daemon=True).start()

    def _close_oflaw_window(self):
        """Close tracked Firefox windows (Win32 only)."""
        if sys.platform == "win32":
            if not MainApp._oflaw_hwnds:
                return
            import ctypes
            u32 = ctypes.windll.user32
            WM_CLOSE = 0x0010
            for hwnd in list(MainApp._oflaw_hwnds):
                u32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            MainApp._oflaw_hwnds.clear()

    def _show_open_menu(self):
        menu = tk.Menu(self, tearoff=0,
                       bg=COLORS["card_bg"], fg=COLORS["text"],
                       activebackground=COLORS["info"], activeforeground=COLORS["bg"],
                       font=("Segoe UI", 9), relief="flat", bd=0)
        for label, url in self._PAGE_URLS:
            menu.add_command(label=f"  {label}",
                             command=lambda u=url: webbrowser.open(u))
        menu.add_separator()
        menu.add_command(label="  🌐 一鍵全開 (Chrome)",
                         command=self._open_all_in_new_window)
        menu.add_command(label="  ✕ 一鍵關閉所有網頁 (Chrome)",
                         command=self._close_oclaw_window)
        menu.add_command(label="  🔥 一鍵全開 (Firefox)",
                         command=self._open_all_in_firefox)
        menu.add_command(label="  ✕ 一鍵關閉所有網頁 (Firefox)",
                         command=self._close_oflaw_window)
        # Pop up below the button
        try:
            x = self.winfo_rootx() + self.winfo_width() - 220
            y = self.winfo_rooty() + 56
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _open_all_pages(self):
        self._open_all_in_new_window()

    def open_settings(self):
        SettingsDialog(self, self.config_manager)


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent: MainApp, config_manager: ConfigManager):
        super().__init__(parent)
        self.parent = parent
        self.config_manager = config_manager
        self.config_data = config_manager.get()

        self.title("設定")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.grab_set()

        self._build_ui()
        self._position()

    def _position(self):
        self.update_idletasks()
        w, h = 580, 580
        px = self.parent.winfo_x()
        py = self.parent.winfo_y()
        pw = self.parent.winfo_width()
        ph = self.parent.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        tk.Label(
            self,
            text="服務設定",
            fg=COLORS["accent"],
            bg=COLORS["bg"],
            font=("Helvetica", 13, "bold"),
            pady=12
        ).pack()

        # Notebook tabs
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Dark.TNotebook",
            background=COLORS["bg"],
            borderwidth=0
        )
        style.configure(
            "Dark.TNotebook.Tab",
            background=COLORS["card_bg"],
            foreground=COLORS["text"],
            padding=[6, 4],
            font=("Helvetica", 8)
        )
        style.map(
            "Dark.TNotebook.Tab",
            background=[("selected", COLORS["info"])],
            foreground=[("selected", COLORS["bg"])]
        )

        nb = ttk.Notebook(self, style="Dark.TNotebook")
        nb.pack(fill="both", expand=True, padx=16, pady=8)

        self.entries = {}
        self._add_browser_tab(nb)
        self._add_general_tab(nb)

        # Buttons
        btn_frame = tk.Frame(self, bg=COLORS["bg"], pady=12)
        btn_frame.pack()

        tk.Button(
            btn_frame,
            text="儲存",
            command=self.save,
            bg=COLORS["success"],
            fg=COLORS["bg"],
            font=("Helvetica", 10, "bold"),
            relief="flat",
            padx=20,
            pady=6,
            cursor="hand2"
        ).pack(side="left", padx=6)

        tk.Button(
            btn_frame,
            text="取消",
            command=self.destroy,
            bg=COLORS["card_border"],
            fg=COLORS["text"],
            font=("Helvetica", 10),
            relief="flat",
            padx=20,
            pady=6,
            cursor="hand2"
        ).pack(side="left", padx=6)

    def _make_tab(self, nb, title):
        frame = tk.Frame(nb, bg=COLORS["card_bg"], padx=16, pady=12)
        nb.add(frame, text=title)
        return frame

    def _add_field(self, frame, label, key, secret=False, default="", hint=""):
        row = tk.Frame(frame, bg=COLORS["card_bg"])
        row.pack(fill="x", pady=6)

        tk.Label(
            row,
            text=label,
            fg=COLORS["subtext"],
            bg=COLORS["card_bg"],
            font=("Helvetica", 9),
            width=18,
            anchor="w"
        ).pack(side="left")

        show = "*" if secret else ""
        var = tk.StringVar(value=default)
        entry = tk.Entry(
            row,
            textvariable=var,
            show=show,
            bg=COLORS["bg"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            font=("Helvetica", 9),
            width=30
        )
        entry.pack(side="left", ipady=4, padx=4)
        self.entries[key] = var

        if hint:
            tk.Label(
                frame,
                text=hint,
                fg=COLORS["subtext"],
                bg=COLORS["card_bg"],
                font=("Helvetica", 8),
                anchor="w"
            ).pack(fill="x", padx=2)

        return var

    def _add_browser_tab(self, nb):
        frame = self._make_tab(nb, "🌐 瀏覽器")

        tk.Label(
            frame,
            text="Tampermonkey 瀏覽器擷取",
            fg=COLORS["text"],
            bg=COLORS["card_bg"],
            font=("Helvetica", 9, "bold"),
        ).pack(anchor="w", pady=(0, 4))

        tk.Label(
            frame,
            text=(
                "安裝 Tampermonkey 後，將 ai-monitor-client.js 複製\n"
                "到 Tampermonkey 新增腳本。\n"
                "開啟以下之一頁面即可自動擷取：\n\n"
                "  • platform.openai.com/…/billing/overview\n"
                "  • claude.ai/settings/usage\n"
                "  • platform.claude.com/settings/billing\n"
                "  • github.com/settings/copilot/features\n\n"
                "腳本將資料傳到下方設定的本地伺服器 Port。"
            ),
            fg=COLORS["subtext"],
            bg=COLORS["card_bg"],
            font=("Helvetica", 8),
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        # Server status indicator
        from services import local_server as _ls
        _srv_on = "已啟動 ✓"
        _srv_off = "未啟動"
        status_text = f"本地伺服器: {_srv_on if _ls.is_running() else _srv_off}"
        self._browser_status_lbl = tk.Label(
            frame,
            text=status_text,
            fg=COLORS["success"] if _ls.is_running() else COLORS["error"],
            bg=COLORS["card_bg"],
            font=("Helvetica", 9),
        )
        self._browser_status_lbl.pack(anchor="w", pady=(0, 4))

        tk.Label(
            frame,
            text="\n可在 Tampermonkey 腳本中調整各頁面的擷取間隔。\n頁面展示 ICON 可直接在瀏覽器中操作。",
            fg=COLORS["subtext"],
            bg=COLORS["card_bg"],
            font=("Helvetica", 8),
            justify="left",
        ).pack(anchor="w")

    def _add_general_tab(self, nb):
        frame = self._make_tab(nb, "一般")

        tk.Label(frame, text="自動更新間隔:", fg=COLORS["subtext"],
                 bg=COLORS["card_bg"], font=("Helvetica", 9)).pack(anchor="w", pady=(0, 4))

        refresh_var = tk.IntVar(value=self.config_data.get("auto_refresh_minutes", 30))
        self.entries["auto_refresh"] = refresh_var

        row = tk.Frame(frame, bg=COLORS["card_bg"])
        row.pack(anchor="w")
        for minutes in [5, 15, 30, 60]:
            tk.Radiobutton(
                row,
                text=f"{minutes} 分鐘",
                variable=refresh_var,
                value=minutes,
                fg=COLORS["text"],
                bg=COLORS["card_bg"],
                selectcolor=COLORS["bg"],
                activebackground=COLORS["card_bg"],
                activeforeground=COLORS["text"],
                font=("Helvetica", 9)
            ).pack(side="left", padx=4)

        tk.Label(frame, text="\n本地伺服器 Port (瀏覽器腳本用):",
                 fg=COLORS["subtext"], bg=COLORS["card_bg"],
                 font=("Helvetica", 9)).pack(anchor="w", pady=(8, 4))

        port_row = tk.Frame(frame, bg=COLORS["card_bg"])
        port_row.pack(anchor="w")
        tk.Label(port_row, text="Port:", fg=COLORS["subtext"],
                 bg=COLORS["card_bg"], font=("Helvetica", 9)).pack(side="left")
        port_var = tk.IntVar(value=self.config_data.get("server_port", 7890))
        self.entries["server_port"] = port_var
        tk.Entry(port_row, textvariable=port_var, bg=COLORS["bg"], fg=COLORS["text"],
                 insertbackground=COLORS["text"], relief="flat",
                 font=("Helvetica", 9), width=8).pack(side="left", ipady=4, padx=8)
        tk.Label(port_row, text="(Tampermonkey JS 預設: 7890)",
                 fg=COLORS["subtext"], bg=COLORS["card_bg"],
                 font=("Helvetica", 8)).pack(side="left")

    def save(self):
        config_manager = self.config_manager

        # General
        config_manager.set_auto_refresh(self.entries["auto_refresh"].get())
        config_manager.set_server_port(int(self.entries["server_port"].get()))

        config_manager.save()
        self.destroy()

        # Trigger refresh
        self.parent.config_data = config_manager.get()
        self.parent.refresh_all()
