# 計劃：右鍵選單新增 Chrome / Firefox 分類子選單

## Context
使用者希望右鍵選單中的「單一網頁開啟」也能選擇用 Firefox 開啟，並將整體選單結構改為
Chrome 與 Firefox 兩個分類，各自有 4 個單頁 + 全部開啟 + 全部關閉。

目前選單（`desktop_widget/app.py` `_show_context_menu`）：
- 4 個單頁用 `webbrowser.open(url)` 開預設瀏覽器
- 一鍵開啟所有網頁 (Chrome) → `_open_all_in_new_window()`
- 一鍵關閉所有網頁 (Chrome) → `_close_oclaw_window()`
- 一鍵開啟所有網頁 (Firefox) → `_open_all_in_firefox()`
- 一鍵關閉所有網頁 (Firefox) → `_close_oflaw_window()`

## 採用方案
**分類子選單（cascading submenu）**：
```
Chrome ▶
  🌐 OpenAI 帳單
  🌐 Claude.ai 用量
  🌐 Claude API 帳單
  🌐 GitHub Copilot
  ─────
  🌐 一鍵開啟所有網頁
  ✕  一鍵關閉所有網頁
Firefox ▶
  🌐 OpenAI 帳單
  🌐 Claude.ai 用量
  🌐 Claude API 帳單
  🌐 GitHub Copilot
  ─────
  🔥 一鍵開啟所有網頁
  ✕  一鍵關閉所有網頁
```

## 關鍵檔案
- `desktop_widget/app.py` — 所有變更集中於此

## 實作步驟

### 1. 新增 Firefox 版 URL 列表（含 `?oflaw=1` 標記）
在 `_PAGE_URLS` 下方（約第 68 行）新增：
```python
_PAGE_URLS_FF = [
    ("OpenAI 帳單",     "https://platform.openai.com/settings/organization/billing/overview?oflaw=1"),
    ("Claude.ai 用量",  "https://claude.ai/settings/usage?oflaw=1"),
    ("Claude API 帳單", "https://platform.claude.com/settings/billing?oflaw=1"),
    ("GitHub Copilot",  "https://github.com/settings/billing/premium_requests_usage?oflaw=1"),
]
```
> 原 `_PAGE_URLS` 保留給 Chrome（`oclaw=1`），`_PAGE_URLS_FF` 給 Firefox（`oflaw=1`）。

### 2. 新增 `_open_in_chrome(url)` 輔助函式
在 `_find_firefox()` 之後新增：
```python
def _open_in_chrome(url: str):
    chrome = _find_chrome()
    if chrome:
        subprocess.Popen([chrome, url])
    else:
        webbrowser.open(url)


def _open_in_firefox(url: str):
    firefox = _find_firefox()
    if firefox:
        subprocess.Popen([firefox, url])
    else:
        webbrowser.open(url)
```

### 3. 修改 `_show_context_menu` — 改為子選單結構
將原本的 4 個單頁 + 4 個全開/關選項，替換為兩個 cascade 子選單：
```python
# 子選單樣式設定
sub_kw = dict(
    bg=COLORS["card_bg"], fg=COLORS["text"],
    activebackground=COLORS["info"], activeforeground=COLORS["bg"],
    font=("Segoe UI", 9), relief="flat", bd=0,
)

# Chrome 子選單
chrome_menu = tk.Menu(menu, tearoff=0, **sub_kw)
for label, url in _PAGE_URLS:
    chrome_menu.add_command(label=f"  🌐 {label}",
                            command=lambda u=url: _open_in_chrome(u))
chrome_menu.add_separator()
chrome_menu.add_command(label="  🌐 一鍵開啟所有網頁", command=_open_all_in_new_window)
chrome_menu.add_command(label="  ✕  一鍵關閉所有網頁", command=_close_oclaw_window)
menu.add_cascade(label="  Chrome ▶", menu=chrome_menu)

# Firefox 子選單
ff_menu = tk.Menu(menu, tearoff=0, **sub_kw)
for label, url in _PAGE_URLS_FF:
    ff_menu.add_command(label=f"  🌐 {label}",
                        command=lambda u=url: _open_in_firefox(u))
ff_menu.add_separator()
ff_menu.add_command(label="  🔥 一鍵開啟所有網頁", command=_open_all_in_firefox)
ff_menu.add_command(label="  ✕  一鍵關閉所有網頁", command=_close_oflaw_window)
menu.add_cascade(label="  Firefox ▶", menu=ff_menu)
```

### 4. 修改 `_open_all_in_firefox()` — 改用 `_PAGE_URLS_FF`
第 224 行：
```python
urls = [url for _, url in _PAGE_URLS_FF]  # 原本是 _PAGE_URLS
```

## 驗證
1. 執行 `py widget_main.py`
2. 右鍵點擊桌面小工具
3. 確認出現「Chrome ▶」和「Firefox ▶」子選單
4. 點擊 Chrome 子選單中的單一網頁 → 應以 Chrome 開啟
5. 點擊 Firefox 子選單中的單一網頁 → 應以 Firefox 開啟
6. 測試各自的全部開啟/關閉功能
