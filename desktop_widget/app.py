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
)
from services import local_server
from services.base import ServiceResult

from desktop_widget.clock import FlipClock
from desktop_widget.cards import CompactServiceCard
from desktop_widget.styles import COLORS, WIDGET_WIDTH, WIDGET_LABEL, WIDGET_TEXT


# ── 服務清單（與 gui/app.py 相同）──────────────────────────────────────────
SERVICES = [
    ("browser_claude_usage",   BrowserClaudeUsageService()),
    ("browser_github_copilot", BrowserGitHubCopilotService()),
    ("browser_openai",         BrowserOpenAIService()),
    ("browser_claude_billing", BrowserClaudeBillingService()),
]

BROWSER_SERVICE_SOURCES = {
    "browser_openai":         "openai_billing",
    "browser_claude_usage":   "claude_usage",
    "browser_claude_billing": "claude_billing",
    "browser_github_copilot": "github_copilot",
}

SERVICE_NAMES = {
    "browser_openai":         "OpenAI 帳單 (瀏覽器)",
    "browser_claude_usage":   "Claude.ai 用量 (瀏覽器)",
    "browser_claude_billing": "Claude API 帳單 (瀏覽器)",
    "browser_github_copilot": "GitHub Copilot (瀏覽器)",
}

_WIDGET_VERSION = "v1.8.0"

_PAGE_URLS = [
    ("OpenAI 帳單",     "https://platform.openai.com/settings/organization/billing/overview"),
    ("Claude.ai 用量",  "https://claude.ai/settings/usage"),
    ("Claude API 帳單", "https://platform.claude.com/settings/billing"),
    ("GitHub Copilot",  "https://github.com/settings/billing/premium_requests_usage"),
]


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

        self._setup_window()
        self._build_ui()
        self._position_window()

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

        # 不出現在工作列
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
        self.clock = FlipClock(self)
        self.clock.pack(fill="x")
        self._setup_drag(self.clock)
        self._setup_drag(self)

        # 分隔線
        tk.Frame(self, bg=COLORS["card_border"], height=1).pack(fill="x")

        # ── 服務卡片區（可捲動）───────────────────────────────────────────
        cards_outer = tk.Frame(self, bg=COLORS["bg"])
        cards_outer.pack(fill="both", expand=True)

        self.cards: dict[str, CompactServiceCard] = {}
        for key, _ in SERVICES:
            card = CompactServiceCard(cards_outer, SERVICE_NAMES[key])
            card.pack(fill="x", padx=0, pady=0)
            tk.Frame(cards_outer, bg=COLORS["card_border"], height=1).pack(fill="x")
            self.cards[key] = card
            self._setup_drag(card)

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
            fg=COLORS["card_border"], bg=COLORS["title_bg"],
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
        for label, url in _PAGE_URLS:
            menu.add_command(label=f"  🌐 {label}",
                             command=lambda u=url: webbrowser.open(u))
        menu.add_command(label="  🌐 一鍵開啟所有網頁",
                         command=self._open_all_pages)
        menu.add_separator()
        menu.add_command(label="  🖥 開啟主視窗", command=self._open_main_window)
        menu.add_command(label="  ⚙ 透明度設定", command=self._opacity_dialog)
        menu.add_separator()
        menu.add_command(label="  ✕ 離開", command=self.quit_app)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _open_all_pages(self):
        for _, url in _PAGE_URLS:
            webbrowser.open(url)

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
        """依內容自動調整視窗高度，並確保不超出螢幕底部。"""
        self.update_idletasks()
        h = self.winfo_reqheight()
        x = self.winfo_x()
        y = self.winfo_y()
        sh = self.winfo_screenheight()
        # 避免超出螢幕底部（保留 48px 給工作列）
        if y + h > sh - 48:
            y = max(0, sh - h - 48)
        self.geometry(f"{WIDGET_WIDTH}x{h}+{x}+{y}")
        if self._desktop_level:
            self._sink_to_bottom()

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
