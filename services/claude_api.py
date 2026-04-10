import json
import os
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from .base import BaseService, ServiceResult

CLAUDE_PLANS = {
    "Pro": {"weekly_sonnet_hours": "40-80", "weekly_opus_hours": "N/A", "price": "$20/月"},
    "Max_100": {"weekly_sonnet_hours": "140-280", "weekly_opus_hours": "15-35", "price": "$100/月"},
    "Max_200": {"weekly_sonnet_hours": "240-480", "weekly_opus_hours": "24-40", "price": "$200/月"},
}

CLAUDE_DIR = Path.home() / ".claude"


def _read_json(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


class ClaudeCodeService(BaseService):
    name = "Claude Code 訂閱"

    def fetch(self, config: dict) -> ServiceResult:
        data = {}

        # --- 從 .credentials.json 取得訂閱資訊 ---
        creds = _read_json(CLAUDE_DIR / ".credentials.json")
        oauth = creds.get("claudeAiOauth", {})
        subscription_type = oauth.get("subscriptionType", "")
        expires_at_ms = oauth.get("expiresAt", 0)

        if subscription_type:
            data["subscription_type"] = subscription_type.upper()
        if expires_at_ms:
            exp_dt = datetime.fromtimestamp(expires_at_ms / 1000, tz=timezone.utc)
            data["token_expires"] = exp_dt.strftime("%Y-%m-%d %H:%M UTC")

        # --- 從 .claude.json 取得帳號資訊 ---
        claude_json = _read_json(CLAUDE_DIR / ".claude.json")
        account = claude_json.get("oauthAccount", {})
        if account.get("displayName"):
            data["display_name"] = account["displayName"]
        if account.get("emailAddress"):
            data["email"] = account["emailAddress"]
        data["extra_usage"] = account.get("hasExtraUsageEnabled", False)

        # --- 從 stats-cache.json 取得使用量統計 ---
        stats = _read_json(CLAUDE_DIR / "stats-cache.json")
        model_usage = stats.get("modelUsage", {})

        total_input = 0
        total_output = 0
        total_cache_read = 0
        total_cache_create = 0
        models_used = []

        for model_id, usage in model_usage.items():
            total_input += usage.get("inputTokens", 0)
            total_output += usage.get("outputTokens", 0)
            total_cache_read += usage.get("cacheReadInputTokens", 0)
            total_cache_create += usage.get("cacheCreationInputTokens", 0)
            short_name = model_id.split("/")[-1]  # strip org prefix if any
            # 取簡短名稱
            for keyword in ["opus", "sonnet", "haiku"]:
                if keyword in short_name.lower():
                    ver = short_name.split("-")[-1] if "-" in short_name else ""
                    models_used.append(f"{keyword.capitalize()} ({ver})" if ver else keyword.capitalize())
                    break

        data["total_input_tokens"] = total_input
        data["total_output_tokens"] = total_output
        data["total_cache_read_tokens"] = total_cache_read
        data["total_cache_create_tokens"] = total_cache_create
        data["total_sessions"] = stats.get("totalSessions", 0)
        data["total_messages"] = stats.get("totalMessages", 0)
        data["models_used"] = list(set(models_used))
        data["stats_date"] = stats.get("lastComputedDate", "")

        # --- 今日用量（從 dailyModelTokens）---
        today_str = datetime.now().strftime("%Y-%m-%d")
        daily_tokens = stats.get("dailyModelTokens", [])
        today_tokens = 0
        for day in daily_tokens:
            if day.get("date") == today_str:
                for model_tokens in day.get("tokensByModel", {}).values():
                    today_tokens += model_tokens
        data["today_tokens"] = today_tokens

        # 今日活動
        daily_activity = stats.get("dailyActivity", [])
        for day in daily_activity:
            if day.get("date") == today_str:
                data["today_messages"] = day.get("messageCount", 0)
                data["today_sessions"] = day.get("sessionCount", 0)
                break

        return ServiceResult(service_name=self.name, success=True, data=data)


class ClaudeAPIService(BaseService):
    name = "Claude API"

    def fetch(self, config: dict) -> ServiceResult:
        admin_key = config.get("admin_api_key", "").strip()

        if not admin_key:
            return self._not_configured()

        if not admin_key.startswith("sk-ant-admin"):
            return self._error("需要 Admin API Key（sk-ant-admin...）")

        headers = {
            "x-api-key": admin_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%dT00:00:00Z")

        try:
            r = requests.get(
                "https://api.anthropic.com/v1/organizations/usage_report/messages",
                headers=headers,
                params={
                    "starting_at": today,
                    "bucket_width": "1d"
                },
                timeout=15
            )

            if r.status_code == 401:
                return self._error("Admin API Key 無效")
            if r.status_code == 403:
                return self._error("無權限（需 Admin API Key）")
            if r.status_code != 200:
                return self._error(f"API 錯誤 {r.status_code}: {r.text[:200]}")

            result = r.json()
            buckets = result.get("data", [])

            total_input = 0
            total_output = 0
            total_cache_read = 0
            total_cache_create = 0

            for bucket in buckets:
                total_input += bucket.get("input_tokens", 0)
                total_output += bucket.get("output_tokens", 0)
                total_cache_read += bucket.get("cache_read_input_tokens", 0)
                total_cache_create += bucket.get("cache_creation_input_tokens", 0)

            data = {
                "today_input_tokens": total_input,
                "today_output_tokens": total_output,
                "today_cache_read_tokens": total_cache_read,
                "today_cache_create_tokens": total_cache_create,
                "today_total_tokens": total_input + total_output,
                "date": now.strftime("%Y-%m-%d")
            }

            # Also try to get cost report
            try:
                r2 = requests.get(
                    "https://api.anthropic.com/v1/organizations/cost_report",
                    headers=headers,
                    params={
                        "starting_at": today,
                        "bucket_width": "1d"
                    },
                    timeout=15
                )
                if r2.status_code == 200:
                    cost_data = r2.json()
                    cost_buckets = cost_data.get("data", [])
                    total_cost = sum(
                        float(b.get("cost", 0)) for b in cost_buckets
                    )
                    data["today_cost_usd"] = total_cost / 100  # cents to dollars
            except Exception:
                pass

            return ServiceResult(service_name=self.name, success=True, data=data)

        except requests.RequestException as e:
            return self._error(f"網路錯誤: {e}")
