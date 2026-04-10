import json
import os
import requests
from datetime import datetime, timedelta
from pathlib import Path
from .base import BaseService, ServiceResult

# Local Copilot OAuth token path (Windows & macOS/Linux)
_APPS_JSON_PATHS = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "github-copilot" / "apps.json",
    Path.home() / ".config" / "github-copilot" / "apps.json",
]


def _read_local_token() -> str:
    """Read OAuth token from GitHub Copilot's local apps.json."""
    for path in _APPS_JSON_PATHS:
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                for entry in data.values():
                    token = entry.get("oauth_token", "")
                    if token:
                        return token
            except Exception:
                pass
    return ""


class GitHubCopilotService(BaseService):
    name = "GitHub Copilot"

    def fetch(self, config: dict) -> ServiceResult:
        token = config.get("token", "").strip()
        org = config.get("org", "").strip()

        # 優先使用本地自動讀取的 token
        local_token = _read_local_token()
        token_source = "manual"
        if not token and local_token:
            token = local_token
            token_source = "local"
        elif not token:
            return self._not_configured()

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        data = {"token_source": token_source}

        # Check user info to verify token
        try:
            r = requests.get("https://api.github.com/user", headers=headers, timeout=10)
            if r.status_code == 401:
                # If local token expired, fall back to manual if provided
                if token_source == "local" and config.get("token", "").strip():
                    token = config["token"].strip()
                    headers["Authorization"] = f"Bearer {token}"
                    data["token_source"] = "manual"
                    r = requests.get("https://api.github.com/user", headers=headers, timeout=10)
                    if r.status_code == 401:
                        return self._error("Token 無效或已過期")
                else:
                    return self._error("Token 無效或已過期（本地 token 可能已過期）")
            if r.status_code == 200:
                user_data = r.json()
                data["username"] = user_data.get("login", "")
        except requests.RequestException as e:
            return self._error(f"網路錯誤: {e}")

        # Personal Copilot subscription status
        try:
            r = requests.get(
                "https://api.github.com/user/copilot",
                headers=headers,
                timeout=10
            )
            if r.status_code == 200:
                copilot_info = r.json()
                plan = copilot_info.get("plan", {})
                data["plan"] = plan.get("type", "Unknown")
                data["enabled"] = True
                # Additional subscription details
                if copilot_info.get("public_code_suggestions"):
                    data["public_code"] = copilot_info["public_code_suggestions"]
                if copilot_info.get("next_billing_date"):
                    data["next_billing"] = copilot_info["next_billing_date"][:10]
            elif r.status_code == 404:
                data["enabled"] = False
                data["plan"] = "無訂閱"
            elif r.status_code == 403:
                data["enabled"] = None
                data["plan"] = "需要 copilot 範圍權限"
        except requests.RequestException as e:
            data["plan_error"] = str(e)

        # Try organization metrics if org is provided
        if org:
            try:
                today = datetime.utcnow()
                since = (today - timedelta(days=28)).strftime("%Y-%m-%d")
                url = f"https://api.github.com/orgs/{org}/copilot/metrics"
                r = requests.get(
                    url,
                    headers=headers,
                    params={"since": since},
                    timeout=10
                )
                if r.status_code == 200:
                    metrics = r.json()
                    if metrics:
                        total_active = sum(
                            day.get("total_active_users", 0)
                            for day in metrics
                        )
                        data["org"] = org
                        data["days_with_data"] = len(metrics)
                        data["total_active_users_sum"] = total_active
                        data["latest_active_users"] = metrics[-1].get("total_active_users", 0)
                elif r.status_code == 404:
                    data["org_error"] = f"找不到組織 '{org}' 或無 Copilot 授權"
                elif r.status_code == 403:
                    data["org_error"] = "無權限存取組織 Copilot 資料"
            except requests.RequestException as e:
                data["org_error"] = f"組織資料錯誤: {e}"

        return ServiceResult(service_name=self.name, success=True, data=data)
