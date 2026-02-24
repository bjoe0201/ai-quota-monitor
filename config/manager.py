import json
import os
import base64
from pathlib import Path


CONFIG_DIR = Path.home() / ".config" / "ai-quota-monitor"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "auto_refresh_minutes": 30,
    "server_port": 7890,
    "services": {
        "github_copilot": {
            "enabled": True,
            "token": "",
            "org": ""
        },
        "claude_code": {
            "enabled": True,
            "plan": "Pro",
            "note": "Claude Code 訂閱額度需在 claude.ai 查看"
        },
        "claude_api": {
            "enabled": True,
            "admin_api_key": ""
        },
        "openai": {
            "enabled": True,
            "api_key": ""
        },
        "google_gemini": {
            "enabled": True,
            "api_key": "",
            "project_id": ""
        },
        "claude_web": {
            "enabled": True,
            "session_key": ""
        },
        "github_copilot_web": {
            "enabled": True,
            "session_cookie": "",
            "customer_id": ""
        },
        "browser_openai": {
            "enabled": True
        },
        "browser_claude_usage": {
            "enabled": True
        },
        "browser_claude_billing": {
            "enabled": True
        },
        "browser_github_copilot": {
            "enabled": True
        }
    }
}


def _encode(text: str) -> str:
    if not text:
        return ""
    return base64.b64encode(text.encode()).decode()


def _decode(text: str) -> str:
    if not text:
        return ""
    try:
        return base64.b64decode(text.encode()).decode()
    except Exception:
        return text


class ConfigManager:
    def __init__(self):
        self._config = None
        self._ensure_dir()

    def _ensure_dir(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        if not CONFIG_FILE.exists():
            self._config = DEFAULT_CONFIG.copy()
            self.save()
            return self._config

        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Merge with defaults to handle new keys
        config = DEFAULT_CONFIG.copy()
        config["auto_refresh_minutes"] = data.get("auto_refresh_minutes", 30)
        config["server_port"] = data.get("server_port", 7890)
        for svc_key in DEFAULT_CONFIG["services"]:
            if svc_key in data.get("services", {}):
                config["services"][svc_key].update(data["services"][svc_key])

        # Decode sensitive fields
        services = config["services"]
        if services["github_copilot"]["token"]:
            services["github_copilot"]["token"] = _decode(services["github_copilot"]["token"])
        if services["claude_api"]["admin_api_key"]:
            services["claude_api"]["admin_api_key"] = _decode(services["claude_api"]["admin_api_key"])
        if services["openai"]["api_key"]:
            services["openai"]["api_key"] = _decode(services["openai"]["api_key"])
        if services["google_gemini"]["api_key"]:
            services["google_gemini"]["api_key"] = _decode(services["google_gemini"]["api_key"])
        if services["claude_web"]["session_key"]:
            services["claude_web"]["session_key"] = _decode(services["claude_web"]["session_key"])
        if services["github_copilot_web"]["session_cookie"]:
            services["github_copilot_web"]["session_cookie"] = _decode(services["github_copilot_web"]["session_cookie"])

        self._config = config
        return self._config

    def save(self):
        if self._config is None:
            return

        # Deep copy and encode sensitive fields
        data = json.loads(json.dumps(self._config))
        services = data["services"]
        if services["github_copilot"]["token"]:
            services["github_copilot"]["token"] = _encode(services["github_copilot"]["token"])
        if services["claude_api"]["admin_api_key"]:
            services["claude_api"]["admin_api_key"] = _encode(services["claude_api"]["admin_api_key"])
        if services["openai"]["api_key"]:
            services["openai"]["api_key"] = _encode(services["openai"]["api_key"])
        if services["google_gemini"]["api_key"]:
            services["google_gemini"]["api_key"] = _encode(services["google_gemini"]["api_key"])
        if services["claude_web"]["session_key"]:
            services["claude_web"]["session_key"] = _encode(services["claude_web"]["session_key"])
        if services["github_copilot_web"]["session_cookie"]:
            services["github_copilot_web"]["session_cookie"] = _encode(services["github_copilot_web"]["session_cookie"])

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get(self) -> dict:
        if self._config is None:
            self.load()
        return self._config

    def update_service(self, service_key: str, values: dict):
        if self._config is None:
            self.load()
        self._config["services"][service_key].update(values)

    def set_auto_refresh(self, minutes: int):
        if self._config is None:
            self.load()
        self._config["auto_refresh_minutes"] = minutes

    def set_server_port(self, port: int):
        if self._config is None:
            self.load()
        self._config["server_port"] = port
