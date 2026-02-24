"""
本地 HTTP 伺服器 — 接收 Tampermonkey JS 傳來的瀏覽器頁面資料。

- 監聽 http://localhost:7890
- POST /update  → 接收 JSON 並更新 DATA_STORE
- GET  /status  → 回傳所有暫存資料
- 支援 CORS (讓 Tampermonkey GM_xmlhttpRequest 能順利傳送)
- 在背景執行緒中運行，不阻擋主程式
"""
import json
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

# ─────────────────────────────────────────────────────────────────
#  共用資料儲存（由伺服器寫入、由服務類別讀取）
# ─────────────────────────────────────────────────────────────────
DATA_STORE: dict[str, dict] = {}
_store_lock = threading.Lock()

# ─────────────────────────────────────────────────────────────────
#  Refresh command flag — GUI sets this to trigger JS re-fetch
# ─────────────────────────────────────────────────────────────────
_refresh_seq: int = 0          # monotonically increasing sequence
_refresh_lock = threading.Lock()


def request_refresh():
    """Called by GUI to tell all JS clients to re-fetch immediately."""
    global _refresh_seq
    with _refresh_lock:
        _refresh_seq += 1


def get_refresh_seq() -> int:
    with _refresh_lock:
        return _refresh_seq

DEFAULT_PORT = 7890
_server_instance: Optional[ThreadingHTTPServer] = None
_server_thread: Optional[threading.Thread] = None


def get_data(key: str) -> Optional[dict]:
    with _store_lock:
        return DATA_STORE.get(key)


def get_all_data() -> dict:
    with _store_lock:
        return dict(DATA_STORE)


def is_running() -> bool:
    return _server_instance is not None


# ─────────────────────────────────────────────────────────────────
#  HTTP Handler
# ─────────────────────────────────────────────────────────────────
class _Handler(BaseHTTPRequestHandler):

    # CORS headers for all responses
    _CORS = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-AI-Monitor-Client",
    }

    def _send(self, status: int, body: bytes, content_type: str = "application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for k, v in self._CORS.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        for k, v in self._CORS.items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        if self.path == "/status" or self.path == "/":
            payload = json.dumps(get_all_data(), ensure_ascii=False).encode()
            self._send(200, payload)
        elif self.path == "/health":
            self._send(200, b'{"ok":true}')
        elif self.path.startswith("/poll"):
            # JS polls with ?seq=N; if server seq > N, tell JS to refresh
            import urllib.parse as _up
            qs = _up.parse_qs(_up.urlparse(self.path).query)
            try:
                client_seq = int(qs.get("seq", ["0"])[0])
            except (ValueError, IndexError):
                client_seq = 0
            server_seq = get_refresh_seq()
            payload = json.dumps({
                "seq": server_seq,
                "refresh": server_seq > client_seq,
            }).encode()
            self._send(200, payload)
        else:
            self._send(404, b'{"error":"not found"}')

    def do_POST(self):
        if self.path != "/update":
            self._send(404, b'{"error":"not found"}')
            return

        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            self._send(400, b'{"error":"empty body"}')
            return

        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as e:
            self._send(400, json.dumps({"error": str(e)}).encode())
            return

        source = data.get("source")
        if not source:
            self._send(400, b'{"error":"missing source field"}')
            return

        # Reject empty payloads (only meta keys, no real data values)
        SKIP_KEYS = {"source", "timestamp", "page_url", "received_at"}
        real_keys = [k for k in data if k not in SKIP_KEYS]
        if not real_keys:
            self._send(200, json.dumps({"ok": False, "reason": "empty payload, ignored"}).encode())
            return

        # Stamp with received time
        data["received_at"] = datetime.now().isoformat()

        with _store_lock:
            DATA_STORE[source] = data

        self._send(200, json.dumps({"ok": True, "source": source}).encode())

    def log_message(self, fmt, *args):
        # Suppress default console output to keep the app clean
        pass


# ─────────────────────────────────────────────────────────────────
#  Server lifecycle
# ─────────────────────────────────────────────────────────────────
def start(port: int = DEFAULT_PORT):
    """Start the local HTTP server in a background daemon thread."""
    global _server_instance, _server_thread

    if _server_instance is not None:
        return  # Already running

    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
        _server_instance = server

        def _run():
            server.serve_forever()

        t = threading.Thread(target=_run, daemon=True, name="ai-monitor-server")
        t.start()
        _server_thread = t
        print(f"[AI Monitor 伺服器] 已在 http://localhost:{port} 啟動")
    except OSError as e:
        print(f"[AI Monitor 伺服器] 無法啟動 (port {port}): {e}")
        _server_instance = None


def stop():
    """Stop the server gracefully."""
    global _server_instance, _server_thread
    if _server_instance:
        _server_instance.shutdown()
        _server_instance = None
        _server_thread = None
        print("[AI Monitor 伺服器] 已停止")
