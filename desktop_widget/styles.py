"""
桌面小工具樣式常數
重用主程式的 COLORS 並加入時鐘專用樣式
"""
from gui.widgets import COLORS, SERVICE_ACCENTS, format_tokens, ProgressBar

# COLORS 在此模組中保持不變，但 cards.py / app.py
# 應使用下方的 WIDGET_* 常數取代 COLORS["subtext"] 與 COLORS["text"]

# ── 翻頁時鐘磁貼樣式 ──────────────────────────────────────────────────────
TILE_W = 68           # 單個數字磁貼寬度
TILE_H = 90           # 單個數字磁貼高度
TILE_R = 10           # 圓角半徑
TILE_BG = "#e8e8f0"   # 磁貼背景（淺色）
TILE_TEXT = "#1e1e2e" # 數字顏色（深色）
TILE_DIM = "#b0b0c4"  # 分隔線顏色
TILE_SHADOW = "#a8a8bc"  # 翻頁陰影顏色

DIGIT_FONT = ("Consolas", 50, "bold")
LABEL_FONT = ("Segoe UI", 8)

# ── 小工具視窗設定 ────────────────────────────────────────────────────────
WIDGET_WIDTH = 380
WIDGET_MIN_HEIGHT = 400

# ── 小工具專用較亮文字顏色（覆蓋主程式的暗色調）──────────────────────────
WIDGET_LABEL   = "#a8b0d0"   # 標籤文字（比 subtext #6e738d 亮許多）
WIDGET_TEXT    = "#e2e8ff"   # 一般數值文字（比 text #cad3f5 更亮）
WIDGET_SUBTEXT = "#8890b8"   # 次要說明文字

# ── 服務卡片精簡版設定 ─────────────────────────────────────────────────────
COMPACT_CARD_PAD_X = 12
COMPACT_CARD_PAD_Y = 6

__all__ = [
    "COLORS", "SERVICE_ACCENTS", "format_tokens", "ProgressBar",
    "TILE_W", "TILE_H", "TILE_R", "TILE_BG", "TILE_TEXT",
    "TILE_DIM", "TILE_SHADOW", "DIGIT_FONT", "LABEL_FONT",
    "WIDGET_WIDTH", "WIDGET_MIN_HEIGHT",
    "COMPACT_CARD_PAD_X", "COMPACT_CARD_PAD_Y",
]
