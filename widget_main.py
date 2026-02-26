"""
桌面小工具入口點

執行方式：
    python widget_main.py

打包後執行：
    dist/AI額度監控-桌面小工具.exe
"""
import sys
import os

# ── PyInstaller 路徑修正 ──────────────────────────────────────────────────
if hasattr(sys, "_MEIPASS"):
    # 執行 bundle 時，sys._MEIPASS 是解壓縮的暫存目錄
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

os.chdir(base_dir)
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

# ── 啟動桌面小工具 ────────────────────────────────────────────────────────
from desktop_widget.app import DesktopWidget
from desktop_widget.tray import SystemTray, is_available as tray_available


def main():
    app = DesktopWidget()

    # 系統匣圖示（若 pystray + Pillow 已安裝）
    tray = SystemTray(app)
    if tray_available():
        tray.start()
    else:
        # 未安裝 pystray 時，在標題列區域提示
        print("[Widget] pystray 未安裝，系統匣圖示不可用。\n"
              "可執行: pip install pystray Pillow")

    try:
        app.mainloop()
    finally:
        tray.stop()


if __name__ == "__main__":
    main()
