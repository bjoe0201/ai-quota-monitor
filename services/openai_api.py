import requests
from datetime import datetime, timedelta, timezone
from .base import BaseService, ServiceResult


class OpenAIService(BaseService):
    name = "OpenAI API"

    def fetch(self, config: dict) -> ServiceResult:
        api_key = config.get("api_key", "").strip()

        if not api_key:
            return self._not_configured()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        data = {}
        now = datetime.now(timezone.utc)

        # Get credit grants / remaining balance
        try:
            r = requests.get(
                "https://api.openai.com/v1/dashboard/billing/credit_grants",
                headers=headers,
                timeout=10
            )
            if r.status_code == 401:
                return self._error("API Key 無效")
            if r.status_code == 200:
                grants = r.json()
                data["total_granted"] = grants.get("total_granted", 0)
                data["total_used"] = grants.get("total_used", 0)
                data["total_available"] = grants.get("total_available", 0)
                data["has_credits"] = True
            elif r.status_code == 404:
                # No credit grants, might be pay-as-you-go
                data["has_credits"] = False
        except requests.RequestException as e:
            data["credits_error"] = str(e)

        # Get subscription info
        try:
            r = requests.get(
                "https://api.openai.com/v1/dashboard/billing/subscription",
                headers=headers,
                timeout=10
            )
            if r.status_code == 200:
                sub = r.json()
                data["plan"] = sub.get("plan", {}).get("title", "Unknown")
                data["has_payment_method"] = sub.get("has_payment_method", False)
                # Hard limit in cents -> dollars
                hard_limit = sub.get("hard_limit_usd")
                soft_limit = sub.get("soft_limit_usd")
                if hard_limit is not None:
                    data["hard_limit_usd"] = float(hard_limit)
                if soft_limit is not None:
                    data["soft_limit_usd"] = float(soft_limit)
        except requests.RequestException as e:
            data["subscription_error"] = str(e)

        # Get usage for current month
        try:
            start_date = now.strftime("%Y-%m-01")
            end_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
            r = requests.get(
                "https://api.openai.com/v1/dashboard/billing/usage",
                headers=headers,
                params={"start_date": start_date, "end_date": end_date},
                timeout=10
            )
            if r.status_code == 200:
                usage = r.json()
                # total_usage is in cents
                total_cents = usage.get("total_usage", 0)
                data["month_usage_usd"] = total_cents / 100.0
                data["month_start"] = start_date
        except requests.RequestException as e:
            data["usage_error"] = str(e)

        if not data:
            return self._error("無法取得任何資料")

        return ServiceResult(service_name=self.name, success=True, data=data)
