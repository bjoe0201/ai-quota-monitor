import requests
from .base import BaseService, ServiceResult

# Free tier quotas for reference
FREE_TIER_LIMITS = {
    "gemini-2.0-flash": {"rpm": 15, "tpm": 1_000_000, "rpd": 1500},
    "gemini-1.5-flash": {"rpm": 15, "tpm": 1_000_000, "rpd": 1500},
    "gemini-1.5-pro": {"rpm": 2, "tpm": 32_000, "rpd": 50},
}


class GoogleGeminiService(BaseService):
    name = "Google Gemini"

    def fetch(self, config: dict) -> ServiceResult:
        api_key = config.get("api_key", "").strip()
        project_id = config.get("project_id", "").strip()

        if not api_key:
            return self._not_configured()

        data = {}

        # Verify API key by listing available models
        try:
            r = requests.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                params={"key": api_key},
                timeout=10
            )
            if r.status_code == 400:
                return self._error("API Key 無效")
            if r.status_code == 403:
                return self._error("API Key 被拒絕或無權限")
            if r.status_code == 200:
                models_data = r.json()
                models = models_data.get("models", [])
                data["available_models_count"] = len(models)
                data["key_valid"] = True
        except requests.RequestException as e:
            return self._error(f"網路錯誤: {e}")

        # Gemini API does not expose quota usage via REST API directly
        # Show static free tier limits as reference
        data["note"] = "Gemini API 配額需在 Google AI Studio 查看"
        data["free_tier_limits"] = FREE_TIER_LIMITS

        # If project_id provided, try Google Cloud Quotas API
        if project_id:
            try:
                r = requests.get(
                    f"https://cloudquotas.googleapis.com/v1/projects/{project_id}/quotaInfos",
                    params={"key": api_key},
                    timeout=10
                )
                if r.status_code == 200:
                    quota_data = r.json()
                    infos = quota_data.get("quotaInfos", [])
                    data["cloud_quotas"] = [
                        {
                            "name": q.get("quotaDisplayName", ""),
                            "metric": q.get("metric", ""),
                            "limit": q.get("quotaBuckets", [{}])[0].get("effectiveLimit", "N/A")
                            if q.get("quotaBuckets") else "N/A"
                        }
                        for q in infos[:10]  # Limit to first 10
                    ]
                    data["project_id"] = project_id
            except requests.RequestException:
                pass

        return ServiceResult(service_name=self.name, success=True, data=data)
