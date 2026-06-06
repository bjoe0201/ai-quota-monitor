"""
DesktopWidget — 桌面小工具主視窗

功能：
- 無邊框浮動視窗（wm_overrideredirect）
- 翻頁時鐘 (FlipClock) + 4 張精簡服務卡片
- 滑鼠左鍵拖拉移動，右鍵顯示選單
- 可選：Win32 HWND_BOTTOM 固定在桌面層
- 位置記憶（讀寫 config widget.x/y）
- 複用 services/ 與 local_server 資料流
"""
import ctypes
import queue
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk

from config.manager import ConfigManager
from services.browser_data import (
    BrowserOpenAIService,
    BrowserClaudeUsageService,
    BrowserClaudeBillingService,
    BrowserGitHubCopilotService,
    BrowserOpenRouterService,
)
from services import local_server
from services.base import ServiceResult
from services.webview_fetcher import WebviewFetcher

from desktop_widget.clock import DigitalClock
from desktop_widget.cards import CompactServiceCard
from desktop_widget.styles import (
    COLORS, WIDGET_WIDTH, WIDGET_LABEL, WIDGET_TEXT, UI_FONT,
)


# ── 服務清單（與 gui/app.py 相同）──────────────────────────────────────────
SERVICES = [
    ("browser_claude_usage",   BrowserClaudeUsageService()),
    ("browser_github_copilot", BrowserGitHubCopilotService()),
    ("browser_openai",         BrowserOpenAIService()),
    ("browser_claude_billing", BrowserClaudeBillingService()),
    ("browser_openrouter",     BrowserOpenRouterService()),
]

BROWSER_SERVICE_SOURCES = {
    "browser_openai":         "openai_billing",
    "browser_claude_usage":   "claude_usage",
    "browser_claude_billing": "claude_billing",
    "browser_github_copilot": "github_copilot",
    "browser_openrouter":     "openrouter",
}

SERVICE_NAMES = {
    "browser_openai":         "OpenAI 帳單 (瀏覽器)",
    "browser_claude_usage":   "Claude.ai 用量 (瀏覽器)",
    "browser_claude_billing": "Claude API 帳單 (瀏覽器)",
    "browser_github_copilot": "GitHub Copilot (瀏覽器)",
    "browser_openrouter":     "OpenRouter (瀏覽器)",
}

_WIDGET_VERSION = "v4.5.0"

_PAGE_URLS = [
    ("OpenAI 帳單",     "https://platform.openai.com/settings/organization/billing/overview?oclaw=1"),
    ("Claude.ai 用量",  "https://claude.ai/new?oclaw=1"),
    ("Claude API 帳單", "https://platform.claude.com/settings/billing?oclaw=1"),
    ("GitHub Copilot",  "https://github.com/settings/copilot/features?oclaw=1"),
    ("GitHub Budgets",  "https://github.com/settings/billing/budgets?oclaw=1"),
    ("OpenRouter 餘額", "https://openrouter.ai/settings/credits?oclaw=1"),
    ("OpenRouter 用量", "https://openrouter.ai/activity?oclaw=1"),
]

_PAGE_URLS_FF = [
    ("OpenAI 帳單",     "https://platform.openai.com/settings/organization/billing/overview?oflaw=1"),
    ("Claude.ai 用量",  "https://claude.ai/new?oflaw=1#settings/usage"),
    ("Claude API 帳單", "https://platform.claude.com/settings/billing?oflaw=1"),
    ("GitHub Copilot",  "https://github.com/settings/copilot/features?oflaw=1"),
    ("GitHub Budgets",  "https://github.com/settings/billing/budgets?oflaw=1"),
    ("OpenRouter 餘額", "https://openrouter.ai/settings/credits?oflaw=1"),
    ("OpenRouter 用量", "https://openrouter.ai/activity?oflaw=1"),
]

_oclaw_hwnds: set = set()  # 追蹤「一鍵全開」開啟的 Chrome 視窗 HWND
_oflaw_hwnds: set = set()  # 追蹤「一鍵全開」開啟的 Firefox 視窗 HWND

_CLAUDE_WARMUP_URL = "https://claude.ai/"
_CLAUDE_USAGE_DELAY = 1.5  # 秒，讓 SPA 完成初始載入後再開 Usage 頁


def _open_url(url: str):
    """開啟單一 URL，Claude.ai Usage 頁面需先暖機。"""
    if "claude.ai/new" in url and "settings/usage" in url:
        def _warmup():
            webbrowser.open(_CLAUDE_WARMUP_URL)
            time.sleep(_CLAUDE_USAGE_DELAY)
            webbrowser.open(url)
        threading.Thread(target=_warmup, daemon=True).start()
    else:
        webbrowser.open(url)


def _find_chrome() -> str | None:
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


def _find_firefox() -> str | None:
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


def _open_in_chrome(url: str):
    if "claude.ai/new" in url and "settings/usage" in url:
        def _warmup():
            chrome = _find_chrome()
            opener = (lambda u: subprocess.Popen([chrome, u])) if chrome else webbrowser.open
            opener(_CLAUDE_WARMUP_URL)
            time.sleep(_CLAUDE_USAGE_DELAY)
            opener(url)
        threading.Thread(target=_warmup, daemon=True).start()
        return
    chrome = _find_chrome()
    if chrome:
        subprocess.Popen([chrome, url])
    else:
        webbrowser.open(url)


def _open_in_firefox(url: str):
    if "claude.ai/new" in url and "settings/usage" in url:
        def _warmup():
            firefox = _find_firefox()
            opener = (lambda u: subprocess.Popen([firefox, u])) if firefox else webbrowser.open
            opener(_CLAUDE_WARMUP_URL)
            time.sleep(_CLAUDE_USAGE_DELAY)
            opener(url)
        threading.Thread(target=_warmup, daemon=True).start()
        return
    firefox = _find_firefox()
    if firefox:
        subprocess.Popen([firefox, url])
    else:
        webbrowser.open(url)


def _get_chrome_hwnds() -> set:
    """Return HWNDs of all visible Chrome windows (Windows only)."""
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


def _get_firefox_hwnds() -> set:
    """Return HWNDs of all visible Firefox windows (Windows only)."""
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


def _open_all_in_new_window():
    """Open all URLs in a new Chrome window. Claude.ai Usage needs a warmup tab first."""
    all_urls = [url for _, url in _PAGE_URLS]
    claude_url = next((u for u in all_urls if "claude.ai/new" in u and "settings/usage" in u), None)
    other_urls = [u for u in all_urls if u != claude_url]

    if sys.platform == "darwin":
        _close_oclaw_window()
        # macOS: AppleScript 開其他頁；Claude 用暖機流程
        tab_cmds = f'set URL of active tab to "{other_urls[0]}"\n'
        for u in other_urls[1:]:
            tab_cmds += f'        make new tab with properties {{URL:"{u}"}}\n'
        script = (
            'tell application "Google Chrome"\n'
            '    activate\n'
            '    make new window\n'
            '    tell front window\n'
            f'        {tab_cmds}'
            '    end tell\n'
            'end tell'
        )
        subprocess.Popen(["osascript", "-e", script])
        if claude_url:
            def _mac_claude():
                time.sleep(_CLAUDE_USAGE_DELAY)
                warmup_script = (
                    'tell application "Google Chrome"\n'
                    f'    tell front window\n'
                    f'        make new tab with properties {{URL:"{_CLAUDE_WARMUP_URL}"}}\n'
                    '    end tell\n'
                    'end tell'
                )
                subprocess.Popen(["osascript", "-e", warmup_script])
                time.sleep(_CLAUDE_USAGE_DELAY)
                usage_script = (
                    'tell application "Google Chrome"\n'
                    f'    tell front window\n'
                    f'        make new tab with properties {{URL:"{claude_url}"}}\n'
                    '    end tell\n'
                    'end tell'
                )
                subprocess.Popen(["osascript", "-e", usage_script])
            threading.Thread(target=_mac_claude, daemon=True).start()
        return

    chrome = _find_chrome()
    if not chrome:
        for url in all_urls:
            _open_url(url)
        return

    _close_oclaw_window()
    before = _get_chrome_hwnds()

    def _do_open():
        subprocess.Popen([chrome, "--new-window"] + other_urls)
        for _ in range(20):
            time.sleep(0.25)
            after = _get_chrome_hwnds()
            new = after - before
            if new:
                _oclaw_hwnds.update(new)
                break
        if claude_url:
            subprocess.Popen([chrome, _CLAUDE_WARMUP_URL])
            time.sleep(_CLAUDE_USAGE_DELAY)
            subprocess.Popen([chrome, claude_url])

    threading.Thread(target=_do_open, daemon=True).start()


def _close_oclaw_window():
    """Close tracked Chrome windows (Win32) or oclaw-tagged tabs (macOS)."""
    if sys.platform == "win32":
        if not _oclaw_hwnds:
            return
        import ctypes
        u32 = ctypes.windll.user32
        WM_CLOSE = 0x0010
        for hwnd in list(_oclaw_hwnds):
            u32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        _oclaw_hwnds.clear()
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


def _open_all_in_firefox():
    """Open all URLs in a new Firefox window. Claude.ai Usage needs a warmup tab first."""
    all_urls = [url for _, url in _PAGE_URLS_FF]
    claude_url = next((u for u in all_urls if "claude.ai/new" in u and "settings/usage" in u), None)
    other_urls = [u for u in all_urls if u != claude_url]

    firefox = _find_firefox()
    if not firefox:
        for url in all_urls:
            _open_url(url)
        return

    _close_oflaw_window()
    before = _get_firefox_hwnds()

    def _do_open():
        subprocess.Popen([firefox, "--new-window"] + other_urls)
        for _ in range(20):
            time.sleep(0.25)
            after = _get_firefox_hwnds()
            new = after - before
            if new:
                _oflaw_hwnds.update(new)
                break
        if claude_url:
            subprocess.Popen([firefox, _CLAUDE_WARMUP_URL])
            time.sleep(_CLAUDE_USAGE_DELAY)
            subprocess.Popen([firefox, claude_url])

    threading.Thread(target=_do_open, daemon=True).start()


def _close_oflaw_window():
    """Close tracked Firefox windows (Win32 only)."""
    if sys.platform == "win32":
        if not _oflaw_hwnds:
            return
        import ctypes
        u32 = ctypes.windll.user32
        WM_CLOSE = 0x0010
        for hwnd in list(_oflaw_hwnds):
            u32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        _oflaw_hwnds.clear()


class DesktopWidget(tk.Tk):
    """桌面小工具主視窗。"""

    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.config_data = self.config_manager.load()
        self._result_queue: queue.Queue = queue.Queue()
        self._last_browser_ts: dict[str, str] = {}
        self._visible = True
        self._drag_x = 0
        self._drag_y = 0
        self._desktop_level: bool = self.config_data.get("widget", {}).get(
            "desktop_level", True
        )

        # 啟動本地 HTTP 伺服器
        port = self.config_data.get("server_port", 7890)
        local_server.start(port)

        # WebView fetcher（僅在 webview/both 模式下啟動）
        self._webview_fetcher: WebviewFetcher | None = None
        self._init_webview_if_needed()

        self._setup_window()
        self._build_ui()
        self._position_window()
        self.protocol("WM_DELETE_WINDOW", self.quit_app)

        # 初始化卡片狀態
        self.after(300, self._init_browser_cards)
        self.after(100, self._poll_queue)
        self.after(1500, self._poll_browser_live)

        # 若設定桌面層則套用 Win32
        if self._desktop_level:
            self.after(500, self._sink_to_bottom)

    # ── 視窗設定 ──────────────────────────────────────────────────────────

    def _setup_window(self):
        self.title("AI 額度監控")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)

        # 無邊框
        self.wm_overrideredirect(True)

        # 不出現在工作列（Windows 限定）
        if sys.platform == "win32":
            self.wm_attributes("-toolwindow", True)

        # 微透明
        opacity = self.config_data.get("widget", {}).get("opacity", 0.95)
        self.wm_attributes("-alpha", opacity)

    def _position_window(self):
        self.update_idletasks()
        w  = WIDGET_WIDTH
        h  = self.winfo_reqheight()

        # 虛擬桌面範圍（涵蓋所有螢幕，含多螢幕負座標情況）
        try:
            u32 = ctypes.windll.user32
            vx = u32.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN
            vy = u32.GetSystemMetrics(77)   # SM_YVIRTUALSCREEN
            vw = u32.GetSystemMetrics(78)   # SM_CXVIRTUALSCREEN
            vh = u32.GetSystemMetrics(79)   # SM_CYVIRTUALSCREEN
        except Exception:
            vx, vy = 0, 0
            vw = self.winfo_screenwidth()
            vh = self.winfo_screenheight()

        wc = self.config_data.get("widget", {})
        sx = wc.get("x", -32768)   # 不能用 -1，因為多螢幕時可能有合法負座標
        sy = wc.get("y", -32768)

        # 驗證：左上角至少保留 20px 在虛擬桌面內
        in_bounds = (
            vx <= sx <= vx + vw - 20 and
            vy <= sy <= vy + vh - 20
        )

        if not in_bounds:
            # 超出所有螢幕或初次啟動 → 主螢幕右下角
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            sx = sw - w - 20
            sy = sh - h - 60
        self.geometry(f"{w}x{h}+{sx}+{sy}")

    # ── UI 建構 ───────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── 翻頁時鐘（可拖拉）─────────────────────────────────────────────
        self.clock = DigitalClock(self)
        self.clock.pack(fill="x")
        self._setup_drag(self.clock)
        self._setup_drag(self)

        # ── 全部展開 / 全部收合（疊在時鐘左下角）─────────────────────────
        expand_btn = tk.Label(
            self.clock, text="▾▾",
            fg=WIDGET_TEXT, bg=COLORS["card_bg"],
            font=(UI_FONT, 11, "bold"), cursor="hand2",
        )
        expand_btn.place(relx=0.0, rely=1.0, x=10, y=-6, anchor="sw")
        expand_btn.bind("<Button-1>", lambda e: self._set_all_collapsed(False))

        collapse_btn = tk.Label(
            self.clock, text="▸▸",
            fg=WIDGET_LABEL, bg=COLORS["card_bg"],
            font=(UI_FONT, 11, "bold"), cursor="hand2",
        )
        collapse_btn.place(relx=0.0, rely=1.0, x=38, y=-6, anchor="sw")
        collapse_btn.bind("<Button-1>", lambda e: self._set_all_collapsed(True))

        # 分隔線
        tk.Frame(self, bg=COLORS["card_border"], height=1).pack(fill="x")

        # ── 服務卡片區（可捲動）───────────────────────────────────────────
        cards_outer = tk.Frame(self, bg=COLORS["bg"])
        cards_outer.pack(fill="both", expand=True)

        collapsed_cfg = self.config_data.get("widget", {}).get(
            "collapsed_cards", {}
        )
        self.cards: dict[str, CompactServiceCard] = {}
        for key, _ in SERVICES:
            card = CompactServiceCard(cards_outer, SERVICE_NAMES[key])
            card.pack(fill="x", padx=0, pady=0)
            tk.Frame(cards_outer, bg=COLORS["card_border"], height=1).pack(fill="x")
            self.cards[key] = card
            self._setup_drag(card)
            # Restore previous collapse state
            if collapsed_cfg.get(key, False):
                card.toggle_collapsed()
            card.bind(
                "<<CardToggled>>",
                lambda e, k=key: self._on_card_toggled(k),
            )

        # ── 狀態列 ────────────────────────────────────────────────────────
        status_bar = tk.Frame(self, bg=COLORS["title_bg"], pady=4)
        status_bar.pack(fill="x")
        self._setup_drag(status_bar)

        self.status_dot = tk.Label(
            status_bar, text="●",
            fg=WIDGET_LABEL, bg=COLORS["title_bg"],
            font=("Segoe UI", 8), padx=8,
        )
        self.status_dot.pack(side="left")

        self.status_label = tk.Label(
            status_bar, text="就緒",
            fg=WIDGET_LABEL, bg=COLORS["title_bg"],
            font=("Segoe UI", 7),
        )
        self.status_label.pack(side="left")

        # 版號（右側）
        tk.Label(
            status_bar, text=_WIDGET_VERSION,
            fg=COLORS["subtext"], bg=COLORS["title_bg"],
            font=("Segoe UI", 7),
        ).pack(side="right", padx=(0, 4))

        # 重新整理按鈕（小）
        self.refresh_btn = tk.Label(
            status_bar, text="⟳",
            fg=COLORS["accent"], bg=COLORS["title_bg"],
            font=("Segoe UI", 10), padx=8,
            cursor="hand2",
        )
        self.refresh_btn.pack(side="right")
        self.refresh_btn.bind("<Button-1>", lambda e: self.refresh_all())

        # 右鍵選單綁定（整個視窗）
        self.bind_all("<Button-3>", self._show_context_menu)

    # ── 拖拉移動 ──────────────────────────────────────────────────────────

    def _setup_drag(self, widget: tk.Widget):
        widget.bind("<ButtonPress-1>", self._drag_start, add="+")
        widget.bind("<B1-Motion>", self._drag_motion, add="+")
        widget.bind("<ButtonRelease-1>", self._drag_end, add="+")

    def _drag_start(self, event):
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def _drag_motion(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.geometry(f"+{x}+{y}")

    def _drag_end(self, event):
        self._save_position()
        if self._desktop_level:
            self.after(100, self._sink_to_bottom)

    # ── Win32 桌面層 ──────────────────────────────────────────────────────

    def _sink_to_bottom(self):
        """將視窗置於所有視窗底層（桌面層級）。"""
        try:
            hwnd = self.winfo_id()
            HWND_BOTTOM = 1
            SWP_NOSIZE   = 0x0001
            SWP_NOMOVE   = 0x0002
            SWP_NOACTIVATE = 0x0010
            ctypes.windll.user32.SetWindowPos(
                hwnd, HWND_BOTTOM, 0, 0, 0, 0,
                SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE,
            )
        except Exception:
            pass

    def _float_to_top(self):
        """浮動至最上層（暫時，用於互動後復位）。"""
        try:
            hwnd = self.winfo_id()
            HWND_TOP = 0
            ctypes.windll.user32.SetWindowPos(
                hwnd, HWND_TOP, 0, 0, 0, 0, 0x0001 | 0x0002,
            )
        except Exception:
            pass

    def _toggle_desktop_level(self):
        self._desktop_level = not self._desktop_level
        wc = self.config_data.setdefault("widget", {})
        wc["desktop_level"] = self._desktop_level
        self.config_manager.save()
        if self._desktop_level:
            self._sink_to_bottom()
        else:
            self._float_to_top()

    # ── 位置儲存 ──────────────────────────────────────────────────────────

    def _save_position(self):
        wc = self.config_data.setdefault("widget", {})
        wc["x"] = self.winfo_x()
        wc["y"] = self.winfo_y()
        self.config_manager.save()

    # ── 右鍵選單 ──────────────────────────────────────────────────────────

    def _show_context_menu(self, event):
        menu = tk.Menu(
            self, tearoff=0,
            bg=COLORS["card_bg"], fg=COLORS["text"],
            activebackground=COLORS["info"], activeforeground=COLORS["bg"],
            font=("Segoe UI", 9), relief="flat", bd=0,
        )
        menu.add_command(label="⟳  重新整理", command=self.refresh_all)
        menu.add_separator()

        level_label = (
            "✓ 固定在桌面層" if self._desktop_level
            else "  固定在桌面層"
        )
        menu.add_command(label=level_label, command=self._toggle_desktop_level)

        menu.add_separator()
        sub_kw = dict(
            bg=COLORS["card_bg"], fg=COLORS["text"],
            activebackground=COLORS["info"], activeforeground=COLORS["bg"],
            font=("Segoe UI", 9), relief="flat", bd=0,
        )
        chrome_menu = tk.Menu(menu, tearoff=0, **sub_kw)
        for label, url in _PAGE_URLS:
            chrome_menu.add_command(label=f"  🌐 {label}",
                                    command=lambda u=url: _open_in_chrome(u))
        chrome_menu.add_separator()
        chrome_menu.add_command(label="  🌐 一鍵開啟所有網頁",
                                command=_open_all_in_new_window)
        chrome_menu.add_command(label="  ✕  一鍵關閉所有網頁",
                                command=_close_oclaw_window)
        menu.add_cascade(label="  Chrome ▶", menu=chrome_menu)

        ff_menu = tk.Menu(menu, tearoff=0, **sub_kw)
        for label, url in _PAGE_URLS_FF:
            ff_menu.add_command(label=f"  🌐 {label}",
                                command=lambda u=url: _open_in_firefox(u))
        ff_menu.add_separator()
        ff_menu.add_command(label="  🔥 一鍵開啟所有網頁",
                            command=_open_all_in_firefox)
        ff_menu.add_command(label="  ✕  一鍵關閉所有網頁",
                            command=_close_oflaw_window)
        menu.add_cascade(label="  Firefox ▶", menu=ff_menu)
        # WebView 模式快捷
        mode = self.config_data.get("browser", {}).get("mode", "system")
        if mode in ("webview", "both"):
            menu.add_separator()
            menu.add_command(label="  🔲 WebView 立即刷新", command=self._webview_refresh_all)
            from services.webview_fetcher import WEBVIEW_SERVICES
            wv_label_map = {
                "openai_billing":  "OpenAI 帳單",
                "claude_usage":    "Claude.ai 用量",
                "claude_billing":  "Claude API 帳單",
                "github_copilot":  "GitHub Copilot",
                "openrouter":      "OpenRouter",
            }
            wv_menu = tk.Menu(menu, tearoff=0, **sub_kw)
            for key in WEBVIEW_SERVICES:
                label = wv_label_map.get(key, key)
                svc_menu = tk.Menu(wv_menu, tearoff=0, **sub_kw)
                svc_menu.add_command(
                    label=f"  🔑 開啟登入視窗",
                    command=lambda k=key: self._webview_show_login(k),
                )
                svc_menu.add_command(
                    label=f"  ✓ 完成登入（隱藏視窗）",
                    command=lambda k=key: self._webview_login_done(k),
                )
                wv_menu.add_cascade(label=f"  {label} ▶", menu=svc_menu)
            menu.add_cascade(label="  🔲 WebView 登入 ▶", menu=wv_menu)

        menu.add_separator()
        menu.add_command(label="  🖥 開啟主視窗", command=self._open_main_window)
        menu.add_command(label="  ⚙ 透明度設定", command=self._opacity_dialog)
        menu.add_command(label="  ⚙ 模式設定", command=self._mode_dialog)
        menu.add_separator()
        menu.add_command(label="  ✕ 離開", command=self.quit_app)

        try:
            # macOS + wm_overrideredirect 的已知問題：需暫時恢復邊框才能讓選單項目可點
            if sys.platform == "darwin":
                self.wm_overrideredirect(False)
                self.update()
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
            if sys.platform == "darwin":
                self.wm_overrideredirect(True)

    def _init_webview_if_needed(self) -> None:
        mode = self.config_data.get("browser", {}).get("mode", "system")
        if mode not in ("webview", "both"):
            return
        if self._webview_fetcher and self._webview_fetcher.is_running:
            return
        port = self.config_data.get("server_port", 7890)
        fetcher = WebviewFetcher()
        fetcher.start(port=port)
        self._webview_fetcher = fetcher
        refresh_mins = self.config_data.get("browser", {}).get("webview_auto_refresh_minutes", 5)
        def _delayed_start():
            if fetcher.wait_ready(timeout=30):
                fetcher.refresh_all()
                fetcher.set_auto_refresh(refresh_mins)
        threading.Thread(target=_delayed_start, daemon=True, name="webview-init").start()

    def _stop_webview(self) -> None:
        if self._webview_fetcher:
            self._webview_fetcher.stop()
            self._webview_fetcher = None

    def _open_all_pages(self):
        _open_all_in_new_window()

    def _open_main_window(self):
        main_py = Path(sys.argv[0]).parent / "main.py"
        try:
            subprocess.Popen(
                [sys.executable, str(main_py)],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        except Exception:
            pass

    def _opacity_dialog(self):
        OpacityDialog(self, self.config_manager, self.config_data)

    def _mode_dialog(self):
        ModeDialog(self, self.config_manager, self.config_data)

    def _webview_refresh_all(self) -> None:
        if self._webview_fetcher:
            self._webview_fetcher.refresh_all()

    def _webview_show_login(self, key: str) -> None:
        if self._webview_fetcher:
            self._webview_fetcher.show_login(key)

    def _webview_login_done(self, key: str = "") -> None:
        if self._webview_fetcher:
            self._webview_fetcher.login_done(key)

    # ── 資料輪詢（複用 gui/app.py 的邏輯）───────────────────────────────

    def refresh_all(self):
        self.status_label.config(text="更新中...", fg=COLORS["warning"])
        self.status_dot.config(fg=COLORS["warning"])
        local_server.request_refresh()
        config = self.config_manager.get()
        browser_keys = set(BROWSER_SERVICE_SOURCES.keys())
        for key, service in SERVICES:
            if key not in browser_keys:
                svc_config = config["services"].get(key, {})
                if svc_config.get("enabled", True):
                    self.cards[key].set_loading()
                    t = threading.Thread(
                        target=self._fetch_service,
                        args=(key, service, svc_config),
                        daemon=True,
                    )
                    t.start()
        self.after(1500, self._restore_status)

    def _init_browser_cards(self):
        config = self.config_manager.get()
        for svc_key in BROWSER_SERVICE_SOURCES:
            svc_obj = next((s for k, s in SERVICES if k == svc_key), None)
            if svc_obj and svc_key in self.cards:
                svc_config = config["services"].get(svc_key, {})
                t = threading.Thread(
                    target=self._fetch_service,
                    args=(svc_key, svc_obj, svc_config),
                    daemon=True,
                )
                t.start()

    def _poll_browser_live(self):
        config = self.config_manager.get()
        for svc_key, src_key in BROWSER_SERVICE_SOURCES.items():
            entry = local_server.DATA_STORE.get(src_key)
            if entry is None:
                continue
            new_ts = entry.get("received_at", "")
            if new_ts != self._last_browser_ts.get(src_key, ""):
                self._last_browser_ts[src_key] = new_ts
                svc_obj = next((s for k, s in SERVICES if k == svc_key), None)
                if svc_obj and svc_key in self.cards:
                    svc_config = config["services"].get(svc_key, {})
                    t = threading.Thread(
                        target=self._fetch_service,
                        args=(svc_key, svc_obj, svc_config),
                        daemon=True,
                    )
                    t.start()
        self.after(1500, self._poll_browser_live)

    def _fetch_service(self, key: str, service, config: dict):
        try:
            result = service.fetch(config)
        except Exception as e:
            result = ServiceResult(
                service_name=service.name,
                success=False,
                error=str(e),
            )
        self._result_queue.put((key, result))

    def _poll_queue(self):
        updated = False
        while not self._result_queue.empty():
            try:
                key, result = self._result_queue.get_nowait()
                if key in self.cards:
                    self.cards[key].update_result(result)
                    updated = True
            except queue.Empty:
                break
        self._update_status_from_cards()
        if updated:
            self.after(30, self._auto_resize)
        self.after(200, self._poll_queue)

    def _auto_resize(self):
        """依內容自動調整視窗高度，固定左上角位置，僅向下延伸。"""
        self.update_idletasks()
        h = self.winfo_reqheight()
        x = self.winfo_x()
        y = self.winfo_y()
        self.geometry(f"{WIDGET_WIDTH}x{h}+{x}+{y}")
        if self._desktop_level:
            self._sink_to_bottom()

    def _set_all_collapsed(self, collapsed: bool):
        for card in self.cards.values():
            if card._collapsed != collapsed:
                card.toggle_collapsed()
        # toggle_collapsed will fire <<CardToggled>> per card → save handled there
        self.after(30, self._auto_resize)

    def _on_card_toggled(self, key: str):
        wc = self.config_data.setdefault("widget", {})
        states = wc.setdefault("collapsed_cards", {})
        states[key] = self.cards[key]._collapsed
        self.config_manager.save()
        self.after(20, self._auto_resize)

    def _update_status_from_cards(self):
        any_warn = any(
            c.status_dot.cget("fg") == COLORS["warning"]
            for c in self.cards.values()
        )
        any_ok = any(
            c.status_dot.cget("fg") == COLORS["success"]
            for c in self.cards.values()
        )
        if any_warn:
            pass  # 保持更新中狀態
        elif any_ok:
            now = datetime.now().strftime("%H:%M:%S")
            self.status_label.config(text=f"更新: {now}", fg=COLORS["subtext"])
            self.status_dot.config(fg=COLORS["success"])

    def _restore_status(self):
        now = datetime.now().strftime("%H:%M:%S")
        self.status_label.config(text=f"更新: {now}", fg=COLORS["subtext"])
        self.status_dot.config(fg=COLORS["success"])

    # ── 顯示控制 ──────────────────────────────────────────────────────────

    def toggle_visibility(self):
        if self._visible:
            self.withdraw()
            self._visible = False
        else:
            self.deiconify()
            self._visible = True
            if self._desktop_level:
                self.after(100, self._sink_to_bottom)

    def quit_app(self):
        _close_oclaw_window()
        _close_oflaw_window()
        self._stop_webview()
        self._save_position()
        local_server.stop()
        self.destroy()


# ── 透明度設定對話框 ────────────────────────────────────────────────────────

class OpacityDialog(tk.Toplevel):
    def __init__(self, parent: DesktopWidget, config_manager, config_data):
        super().__init__(parent)
        self._parent = parent
        self._cm = config_manager
        self._data = config_data

        self.title("透明度設定")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.wm_attributes("-topmost", True)
        self.grab_set()

        self.update_idletasks()
        px, py = parent.winfo_x(), parent.winfo_y()
        self.geometry(f"280x120+{px + 40}+{py + 40}")

        self._build()

    def _build(self):
        tk.Label(
            self, text="視窗透明度",
            fg=COLORS["text"], bg=COLORS["bg"],
            font=("Segoe UI", 9, "bold"), pady=8,
        ).pack()

        cur = self._data.get("widget", {}).get("opacity", 0.95)
        self._var = tk.DoubleVar(value=cur)

        scale = tk.Scale(
            self, from_=0.3, to=1.0,
            resolution=0.05, orient="horizontal",
            variable=self._var,
            command=self._preview,
            bg=COLORS["bg"], fg=COLORS["text"],
            troughcolor=COLORS["card_border"],
            highlightthickness=0, length=220,
        )
        scale.pack(pady=4)

        btn_row = tk.Frame(self, bg=COLORS["bg"])
        btn_row.pack(pady=4)
        tk.Button(
            btn_row, text="確定", command=self._apply,
            bg=COLORS["success"], fg=COLORS["bg"],
            relief="flat", padx=16, pady=4,
        ).pack(side="left", padx=4)
        tk.Button(
            btn_row, text="取消", command=self.destroy,
            bg=COLORS["card_border"], fg=COLORS["text"],
            relief="flat", padx=16, pady=4,
        ).pack(side="left", padx=4)

    def _preview(self, val):
        self._parent.wm_attributes("-alpha", float(val))

    def _apply(self):
        v = self._var.get()
        wc = self._data.setdefault("widget", {})
        wc["opacity"] = v
        self._cm.save()
        self.destroy()


# ── 模式設定對話框 ──────────────────────────────────────────────────────────────

class ModeDialog(tk.Toplevel):
    """資料來源模式設定：system / webview / both。"""

    def __init__(self, parent: DesktopWidget, config_manager, config_data):
        super().__init__(parent)
        self._parent = parent
        self._cm = config_manager
        self._data = config_data

        self.title("模式設定")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.wm_attributes("-topmost", True)
        self.grab_set()

        self.update_idletasks()
        px, py = parent.winfo_x(), parent.winfo_y()
        self.geometry(f"340x240+{px + 30}+{py + 30}")

        self._build()

    def _build(self):
        tk.Label(
            self, text="資料來源模式",
            fg=COLORS["text"], bg=COLORS["bg"],
            font=("Segoe UI", 9, "bold"), pady=8,
        ).pack()

        browser_cfg = self._data.get("browser", {})
        self._mode_var = tk.StringVar(value=browser_cfg.get("mode", "system"))
        self._refresh_var = tk.IntVar(value=browser_cfg.get("webview_auto_refresh_minutes", 5))

        mode_frame = tk.Frame(self, bg=COLORS["bg"], padx=16)
        mode_frame.pack(fill="x")
        for val, label in [
            ("system",  "系統瀏覽器 Chrome/Firefox（需 Tampermonkey）"),
            ("webview", "內嵌 WebView（背景靜默，無需 Tampermonkey）"),
            ("both",    "兩者同時執行"),
        ]:
            tk.Radiobutton(
                mode_frame, text=label,
                variable=self._mode_var, value=val,
                fg=COLORS["text"], bg=COLORS["bg"],
                selectcolor=COLORS["card_bg"],
                activebackground=COLORS["bg"], activeforeground=COLORS["text"],
                font=("Segoe UI", 8),
            ).pack(anchor="w")

        tk.Label(
            self, text="WebView 自動刷新（分鐘）",
            fg=COLORS["subtext"], bg=COLORS["bg"],
            font=("Segoe UI", 8), pady=(4,),
        ).pack(anchor="w", padx=16)

        rf_row = tk.Frame(self, bg=COLORS["bg"], padx=16)
        rf_row.pack(anchor="w")
        for mins in [3, 5, 10, 30]:
            tk.Radiobutton(
                rf_row, text=f"{mins}分",
                variable=self._refresh_var, value=mins,
                fg=COLORS["text"], bg=COLORS["bg"],
                selectcolor=COLORS["card_bg"],
                activebackground=COLORS["bg"], activeforeground=COLORS["text"],
                font=("Segoe UI", 8),
            ).pack(side="left", padx=3)

        btn_row = tk.Frame(self, bg=COLORS["bg"])
        btn_row.pack(pady=10)
        tk.Button(
            btn_row, text="確定", command=self._apply,
            bg=COLORS["success"], fg=COLORS["bg"],
            relief="flat", padx=16, pady=4,
        ).pack(side="left", padx=4)
        tk.Button(
            btn_row, text="取消", command=self.destroy,
            bg=COLORS["card_border"], fg=COLORS["text"],
            relief="flat", padx=16, pady=4,
        ).pack(side="left", padx=4)

    def _apply(self):
        cfg = self._data.setdefault("browser", {})
        new_mode = self._mode_var.get()
        cfg["mode"] = new_mode
        cfg["webview_auto_refresh_minutes"] = self._refresh_var.get()
        self._cm.save()
        self.destroy()

        # Restart/stop webview fetcher on parent
        if new_mode in ("webview", "both"):
            self._parent._stop_webview()
            self._parent._init_webview_if_needed()
        else:
            self._parent._stop_webview()
