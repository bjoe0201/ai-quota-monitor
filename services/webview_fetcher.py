"""
WebviewFetcher — manages a subprocess that runs pywebview as a separate process.

Why subprocess:
  On Windows, pywebview (WebView2/Edge) requires webview.start() to be called
  on the main thread of its own process. Since our app's main thread is owned by
  tkinter, we cannot call webview.start() on it or in any background thread.

  Solution: spawn a child process (webview_worker.py) that owns its own main
  thread for the WebView event loop. The worker injects ai-monitor-webview.js
  which calls window.pywebview.api.post_data() → the worker forwards the data
  via HTTP POST to localhost:7890/update (the same local_server already running).

Data flow:
  WebviewFetcher.refresh_all()
    → child process loads service URLs
    → JS intercepts API responses
    → JS calls pywebview.api.post_data(source, json)
    → worker posts to http://localhost:7890/update
    → existing _poll_browser_live() picks up new DATA_STORE entries
    → UI updates as normal
"""
import os
import sys
import subprocess
import threading
import json
from typing import Optional

# Service key → URL to navigate for data collection
WEBVIEW_SERVICES = {
    "openai_billing":           "https://platform.openai.com/settings/organization/billing/overview",
    "claude_usage":             "https://claude.ai/new?oclaw=1",
    "claude_billing":           "https://platform.claude.com/settings/billing",
    "github_copilot":           "https://github.com/settings/copilot/features",
    "github_copilot_budgets":   "https://github.com/settings/billing/budgets",
    "openrouter":               "https://openrouter.ai/settings/credits",
}

_WORKER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "services",
    "webview_worker.py",
)


class WebviewFetcher:
    """
    Manages a subprocess that runs pywebview for background data collection.
    """

    def __init__(self, bridge=None):  # noqa: ARG002 (bridge unused; subprocess handles POST)
        self._proc: Optional[subprocess.Popen[str]] = None
        self._stop_event = threading.Event()
        self._auto_refresh_minutes: int = 5
        self._auto_refresh_job: Optional[threading.Timer] = None
        self._port: int = 7890
        self._ready = threading.Event()

    def start(self, port: int = 7890) -> None:
        """Start the webview worker subprocess."""
        if self._proc and self._proc.poll() is None:
            return  # already running
        self._port = port
        self._stop_event.clear()
        self._ready.clear()
        self._launch_worker()

    def _launch_worker(self) -> None:
        python = sys.executable
        try:
            self._proc = subprocess.Popen(
                [python, _WORKER_PATH, "--port", str(self._port)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            # Monitor stdout in background thread to detect readiness
            threading.Thread(
                target=self._monitor_stdout, daemon=True, name="webview-monitor"
            ).start()
        except Exception as e:
            print(f"[WebviewFetcher] 子程序啟動失敗: {e}")

    def _monitor_stdout(self) -> None:
        if not self._proc or not self._proc.stdout:
            return
        for line in self._proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            if "READY" in line:
                self._ready.set()
            elif "LOGIN_DONE" in line:
                # Worker confirmed login done — schedule a refresh after short delay
                import threading as _t
                def _post_login_refresh():
                    import time
                    time.sleep(1.5)
                    self.refresh_all()
                _t.Thread(target=_post_login_refresh, daemon=True).start()
            else:
                print(f"[WebviewWorker] {line}")

    def wait_ready(self, timeout: float = 20.0) -> bool:
        """Block until the worker reports ready. Returns True on success."""
        return self._ready.wait(timeout)

    def _send_cmd(self, cmd: dict) -> None:
        """Write a JSON command to the worker via stdin."""
        if not self._proc or self._proc.poll() is not None or not self._proc.stdin:
            return
        try:
            self._proc.stdin.write(json.dumps(cmd) + "\n")
            self._proc.stdin.flush()
        except Exception:
            pass

    def load_service(self, key: str) -> None:
        """Navigate the worker WebView to the service URL."""
        url = WEBVIEW_SERVICES.get(key)
        if url:
            self._send_cmd({"action": "load", "key": key, "url": url})

    def refresh_all(self) -> None:
        """Navigate through all service URLs sequentially."""
        if not self._ready.is_set():
            return
        self._send_cmd({"action": "refresh_all"})

    def show_login(self, key: str) -> None:
        """Show the independent window for this service (others unaffected)."""
        self._send_cmd({"action": "show_login", "key": key})

    def login_done(self, key: str = "") -> None:
        """Hide this service window and trigger a refresh for it."""
        self._send_cmd({"action": "login_done", "key": key})

    def hide(self) -> None:
        self._send_cmd({"action": "hide"})

    def set_auto_refresh(self, minutes: int) -> None:
        self._auto_refresh_minutes = minutes
        self._cancel_auto_refresh()
        if minutes > 0:
            self._schedule_auto_refresh()

    def _schedule_auto_refresh(self) -> None:
        if self._stop_event.is_set():
            return
        interval = self._auto_refresh_minutes * 60
        self._auto_refresh_job = threading.Timer(interval, self._auto_refresh_tick)
        self._auto_refresh_job.daemon = True
        self._auto_refresh_job.start()

    def _auto_refresh_tick(self) -> None:
        self.refresh_all()
        self._schedule_auto_refresh()

    def _cancel_auto_refresh(self) -> None:
        if self._auto_refresh_job:
            self._auto_refresh_job.cancel()
            self._auto_refresh_job = None

    def stop(self) -> None:
        """Stop the worker subprocess."""
        self._stop_event.set()
        self._cancel_auto_refresh()
        if self._proc and self._proc.poll() is None:
            try:
                self._send_cmd({"action": "quit"})
                self._proc.wait(timeout=3)
            except Exception:
                pass
            try:
                self._proc.terminate()
            except Exception:
                pass
        self._proc = None

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None
