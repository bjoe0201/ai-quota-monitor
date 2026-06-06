"""
WebView worker — 獨立子程序，負責執行 pywebview 事件迴圈。

架構：每個服務各自擁有獨立的 pywebview 視窗（hidden）。
- 背景刷新：各視窗並行 load_url，不輪流
- 登入：show_login(key) 只顯示該服務的視窗，其他服務完全不受影響
- login_done(key) 只關閉該服務視窗並重新建立 hidden 視窗

通訊協定（Parent → Worker，每行一個 JSON）：
  {"action": "refresh_all"}
  {"action": "refresh",     "key": "..."}
  {"action": "show_login",  "key": "..."}
  {"action": "login_done",  "key": "..."}
  {"action": "quit"}

Worker → Parent（stdout）：
  READY       — 所有視窗建立完成
  LOGIN_DONE  — login_done 後通知主程式可刷新
"""
import argparse
import json
import os
import sys
import threading
import time
import urllib.request
import urllib.error

if hasattr(sys, "_MEIPASS"):
    _BASE = sys._MEIPASS
else:
    _BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

_JS_PATH = os.path.join(_BASE, "assets", "ai-monitor-webview.js")

_DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)

WEBVIEW_SERVICES = {
    "openai_billing":           "https://platform.openai.com/settings/organization/billing/overview",
    "claude_usage":             "https://claude.ai/new?oclaw=1",
    "claude_billing":           "https://platform.claude.com/settings/billing",
    "github_copilot":           "https://github.com/settings/copilot/features",
    "github_copilot_budgets":   "https://github.com/settings/billing/budgets",
    "openrouter":               "https://openrouter.ai/settings/credits",
}

_SERVICE_LABELS = {
    "openai_billing":           "OpenAI 帳單",
    "claude_usage":             "Claude.ai 用量",
    "claude_billing":           "Claude API 帳單",
    "github_copilot":           "GitHub Copilot",
    "github_copilot_budgets":   "GitHub Copilot (Budgets)",
    "openrouter":               "OpenRouter",
}

# JS injected when Google SSO block is detected
_GOOGLE_BLOCKED_BANNER_JS = r"""
(function() {
    if (document.getElementById('__aimon_gsi_banner')) return;
    var bar = document.createElement('div');
    bar.id = '__aimon_gsi_banner';
    bar.style.cssText = [
        'position:fixed','top:0','left:0','right:0','z-index:999999',
        'background:#1a1a2e','color:#e2b96f','font-size:13px',
        'padding:10px 16px','display:flex','align-items:center','gap:12px',
        'box-shadow:0 2px 8px rgba(0,0,0,.5)','font-family:sans-serif'
    ].join(';');
    bar.innerHTML = '<span style="font-size:18px">⚠️</span>'
        + '<span><b>Google 登入在 WebView 中無法使用（Google 政策限制）</b><br>'
        + '<span style="font-size:11px;color:#aaa">請捲動頁面，改用 <b style="color:#e2b96f">Email 登入</b></span></span>';
    document.body.insertBefore(bar, document.body.firstChild);
})();
"""


def _load_js() -> str:
    try:
        with open(_JS_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        print(f"JS 讀取失敗: {e}", flush=True)
        return ""


class WorkerBridge:
    """Exposed to JS per-window. Forwards intercepted data to local_server."""

    def __init__(self, port: int):
        self._port = port

    def post_data(self, source: str, json_str: str) -> None:
        try:
            data = json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return
        SKIP_KEYS = {"source", "timestamp", "page_url", "received_at"}
        if not any(k not in SKIP_KEYS for k in data):
            return
        data["source"] = source
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            f"http://localhost:{self._port}/update",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=3):
                pass
        except urllib.error.URLError:
            pass


class ServiceWindow:
    """
    One pywebview window per service.
    Each window is independent — login/refresh on one does not affect others.

    Android pattern: destroy + recreate the window on each show_login call,
    because window.hide() + window.show() is unreliable in WebView2.
    """

    def __init__(self, key: str, url: str, webview, bridge: WorkerBridge, js_code: str):
        self._key = key
        self._url = url
        self._webview = webview
        self._bridge = bridge
        self._js_code = js_code
        self._login_mode = False
        self._lock = threading.Lock()
        self._window = None
        self._create_window(hidden=True)

    def _create_window(self, hidden: bool = True):
        """Create (or recreate) the pywebview window for this service."""
        label = _SERVICE_LABELS.get(self._key, self._key)
        self._window = self._webview.create_window(
            title=f"AI Monitor — {label}",
            url="about:blank",
            width=1100,
            height=800,
            hidden=hidden,
            resizable=True,
            js_api=self._bridge,
        )
        self._window.events.loaded += self._on_page_loaded

    @property
    def window(self):
        return self._window

    def _on_page_loaded(self) -> None:
        if not self._window:
            return
        try:
            current_url = self._window.evaluate_js("location.href") or ""
        except Exception:
            current_url = ""

        with self._lock:
            in_login = self._login_mode

        if in_login:
            # Detect Google GSI block
            if "accounts.google.com/gsi/" in current_url:
                try:
                    self._window.evaluate_js(_GOOGLE_BLOCKED_BANNER_JS)
                except Exception:
                    pass
                # Bounce back to login page
                service_url = self._url
                def _go_back():
                    time.sleep(0.8)
                    try:
                        self._window.load_url(service_url)
                    except Exception:
                        pass
                threading.Thread(target=_go_back, daemon=True).start()
            # Do not inject monitoring JS while user is logging in
            return

        # Background mode — inject monitoring JS
        if self._js_code:
            try:
                self._window.evaluate_js(self._js_code)
            except Exception as e:
                print(f"[{self._key}] JS 注入失敗: {e}", flush=True)

    def refresh(self) -> None:
        """Load the service URL in background (hidden window)."""
        with self._lock:
            if self._login_mode:
                return
        if not self._window:
            return
        try:
            self._window.load_url(self._url)
        except Exception as e:
            print(f"[{self._key}] refresh 失敗: {e}", flush=True)

    def show_login(self) -> None:
        """
        Enter login mode: destroy any existing window, create a fresh one,
        then navigate to the service URL and show it.

        Following Android's createLoginWebView() pattern — never reuse a hidden window,
        because window.hide() + window.show() is unreliable in WebView2.
        """
        # Destroy the old window first (Android pattern: always fresh)
        if self._window:
            try:
                self._webview.destroy_window(self._window)
            except Exception:
                pass
            self._window = None
        time.sleep(0.1)

        with self._lock:
            self._login_mode = True

        # Create a brand-new window (visible)
        self._create_window(hidden=False)
        try:
            self._window.load_url(self._url)
        except Exception as e:
            print(f"[{self._key}] show_login load_url 失敗: {e}", flush=True)

    def login_done(self) -> None:
        """
        Exit login mode: destroy the login window and create a fresh hidden window
        ready for the next background refresh.
        """
        with self._lock:
            self._login_mode = False

        if self._window:
            try:
                self._webview.destroy_window(self._window)
            except Exception:
                pass
            self._window = None
        time.sleep(0.1)

        # Recreate a clean hidden window for future refreshes
        self._create_window(hidden=True)


class WebviewWorker:
    def __init__(self, port: int):
        self._port = port
        self._js_code = _load_js()
        self._bridge = WorkerBridge(port)
        self._service_windows: dict[str, ServiceWindow] = {}
        self._webview = None

    def run(self) -> None:
        import webview
        self._webview = webview

        # Create one independent window per service
        for key, url in WEBVIEW_SERVICES.items():
            sw = ServiceWindow(key, url, webview, self._bridge, self._js_code)
            self._service_windows[key] = sw

        threading.Thread(target=self._read_commands, daemon=True, name="cmd-reader").start()

        def _on_start():
            # expose() is called inside _create_window() for each ServiceWindow.
            # Nothing more to do here — just signal readiness.
            print("READY", flush=True)

        webview.start(func=_on_start, private_mode=False, user_agent=_DESKTOP_UA)

    def _read_commands(self) -> None:
        for raw in sys.stdin:
            raw = raw.strip()
            if not raw:
                continue
            try:
                cmd = json.loads(raw)
            except json.JSONDecodeError:
                continue
            action = cmd.get("action", "")
            key = cmd.get("key", "")

            if action == "refresh_all":
                # Each service window refreshes independently in its own thread
                for k, sw in self._service_windows.items():
                    threading.Thread(
                        target=sw.refresh,
                        daemon=True,
                        name=f"refresh-{k}",
                    ).start()

            elif action == "refresh":
                sw = self._service_windows.get(key)
                if sw:
                    threading.Thread(target=sw.refresh, daemon=True).start()

            elif action == "show_login":
                sw = self._service_windows.get(key)
                if sw:
                    threading.Thread(
                        target=sw.show_login,
                        daemon=True,
                        name=f"login-{key}",
                    ).start()

            elif action == "login_done":
                sw = self._service_windows.get(key)
                if sw:
                    sw.login_done()
                print("LOGIN_DONE", flush=True)

            elif action == "quit":
                self._do_quit()
                break

    def _do_quit(self) -> None:
        if self._webview:
            for sw in self._service_windows.values():
                if sw.window:
                    try:
                        self._webview.destroy_window(sw.window)
                    except Exception:
                        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7890)
    args, _ = parser.parse_known_args()  # ignore --webview-worker and other flags
    worker = WebviewWorker(args.port)
    worker.run()


if __name__ == "__main__":
    main()
