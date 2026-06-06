"""
WebviewBridge — exposed to JS via pywebview.expose().

JS calls: window.pywebview.api.post_data(source, jsonStr)
Python receives the call and writes to local_server.DATA_STORE.
"""
import json
import time
import threading

from services import local_server


class WebviewBridge:
    """Python-side JS bridge. All methods are callable from injected JS."""

    def post_data(self, source: str, json_str: str) -> None:
        """Receive data from injected JS and merge into DATA_STORE."""
        try:
            data = json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return

        SKIP_KEYS = {"source", "timestamp", "page_url", "received_at"}
        if not any(k not in SKIP_KEYS for k in data):
            return

        data["received_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        data["source"] = source

        with local_server._store_lock:
            existing = local_server.DATA_STORE.get(source, {})
            merged = {**existing, **data}
            if "parse_error" not in data:
                merged.pop("parse_error", None)
            local_server.DATA_STORE[source] = merged
