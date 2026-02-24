import sys
import os

# Ensure the project root is in sys.path when running as a script or bundled app
if getattr(sys, "frozen", False):
    # PyInstaller bundle
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from gui.app import MainApp


def main():
    app = MainApp()
    app.mainloop()


if __name__ == "__main__":
    main()
