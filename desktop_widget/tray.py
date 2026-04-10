"""
系統匣圖示 (SystemTray)
使用 pystray 建立系統匣圖示與右鍵選單。
若 pystray 或 Pillow 未安裝則靜默略過（小工具仍可正常使用）。
"""
from __future__ import annotations
import threading
import subprocess
import sys
from pathlib import Path

_TRAY_AVAILABLE = False
try:
    import pystray
    from PIL import Image, ImageDraw
    _TRAY_AVAILABLE = True
except ImportError:
    pass


def _make_icon() -> "Image.Image | None":
    """動態產生 64×64 系統匣圖示。"""
    if not _TRAY_AVAILABLE:
        return None
    img = Image.new("RGB", (64, 64), color="#1e1e2e")
    draw = ImageDraw.Draw(img)
    # 外框
    draw.rounded_rectangle([2, 2, 61, 61], radius=10, outline="#89dceb", width=2)
    # "AI" 文字
    draw.text((10, 8), "AI", fill="#89dceb")
    # 小圓點（進度指示）
    for i, color in enumerate(["#a6e3a1", "#cba6f7", "#74c7ec", "#f9e2af"]):
        x = 10 + i * 12
        draw.ellipse([x, 42, x + 8, 50], fill=color)
    return img


class SystemTray:
    """
    系統匣圖示管理。
    在背景執行緒運行 pystray，提供 show/hide/open/quit 選項。
    """

    def __init__(self, widget_app):
        self._app = widget_app
        self._icon = None
        self._thread = None

    def start(self):
        """啟動系統匣（在背景執行緒中）。"""
        if not _TRAY_AVAILABLE:
            return
        img = _make_icon()
        if img is None:
            return

        menu = pystray.Menu(
            pystray.MenuItem("顯示 / 隱藏", self._on_toggle, default=True),
            pystray.MenuItem("⟳ 重新整理", self._on_refresh),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🖥 開啟主視窗", self._on_open_main),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("✕ 離開", self._on_quit),
        )
        self._icon = pystray.Icon(
            "ai-quota-widget",
            img,
            "AI 額度監控 桌面小工具",
            menu,
        )
        self._icon.run_detached()

    def stop(self):
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass

    # ── 選單回呼 ──────────────────────────────────────────────────────────

    def _on_toggle(self, icon, item):
        """顯示 / 隱藏視窗。"""
        app = self._app
        app.after(0, app.toggle_visibility)

    def _on_refresh(self, icon, item):
        app = self._app
        app.after(0, app.refresh_all)

    def _on_open_main(self, icon, item):
        """啟動主視窗 (main.py)。"""
        main_py = Path(sys.argv[0]).parent / "main.py"
        try:
            subprocess.Popen([sys.executable, str(main_py)],
                             creationflags=0x00000008)  # DETACHED_PROCESS
        except Exception:
            pass

    def _on_quit(self, icon, item):
        app = self._app
        app.after(0, app.quit_app)


def is_available() -> bool:
    return _TRAY_AVAILABLE
