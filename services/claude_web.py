"""
Claude Web 額度服務 — 透過 claude.ai 的 sessionKey cookie 取得網頁上的額度資訊。

使用方式:
  1. 用瀏覽器登入 https://claude.ai
  2. 開啟 DevTools (F12) → Application → Cookies → claude.ai
  3. 複製 sessionKey 的值（格式: sk-ant-sid01-...）
  4. 貼到設定中的「Session Key」欄位
"""
import re
import requests
from .base import BaseService, ServiceResult

_CLAUDE_BASE = "https://claude.ai"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Content-Type": "application/json",
}


class ClaudeWebService(BaseService):
    name = "Claude Web 額度"

    def fetch(self, config: dict) -> ServiceResult:
        session_key = config.get("session_key", "").strip()
        if not session_key:
            return self._not_configured()

        cookies = {"sessionKey": session_key}

        # ------ Step 1: 取得組織資訊 ------
        try:
            r = requests.get(
                f"{_CLAUDE_BASE}/api/bootstrap",
                headers=_HEADERS,
                cookies=cookies,
                timeout=15,
            )
        except requests.RequestException as e:
            return self._error(f"網路錯誤: {e}")

        if r.status_code == 401 or r.status_code == 403:
            return self._error("Session Key 無效或已過期，請重新從瀏覽器取得")
        if r.status_code != 200:
            return self._error(f"Bootstrap API 錯誤 ({r.status_code})")

        try:
            bootstrap = r.json()
        except Exception:
            return self._error("無法解析 Bootstrap 回應")

        # 取得組織 UUID
        org_uuid = None
        account_info = {}

        # bootstrap 可能直接回傳 account 或 organization
        if isinstance(bootstrap, dict):
            # 嘗試多種可能的結構
            orgs = bootstrap.get("organizations", [])
            if orgs and isinstance(orgs, list):
                org_uuid = orgs[0].get("uuid") or orgs[0].get("id")
            # 嘗試直接取得 account
            account = bootstrap.get("account", {})
            if account:
                account_info["display_name"] = account.get("display_name", "")
                account_info["email"] = account.get("email_address", "") or account.get("email", "")

        if not org_uuid:
            # 嘗試從 /api/organizations 取得
            try:
                r2 = requests.get(
                    f"{_CLAUDE_BASE}/api/organizations",
                    headers=_HEADERS,
                    cookies=cookies,
                    timeout=15,
                )
                if r2.status_code == 200:
                    orgs_data = r2.json()
                    if isinstance(orgs_data, list) and orgs_data:
                        org_uuid = orgs_data[0].get("uuid") or orgs_data[0].get("id")
                    elif isinstance(orgs_data, dict):
                        org_list = orgs_data.get("data", orgs_data.get("organizations", []))
                        if org_list:
                            org_uuid = org_list[0].get("uuid") or org_list[0].get("id")
            except Exception:
                pass

        if not org_uuid:
            return self._error("無法取得組織 UUID，Session Key 可能無效")

        # ------ Step 2: 取得額度資料 ------
        data = {}
        if account_info.get("display_name"):
            data["display_name"] = account_info["display_name"]
        if account_info.get("email"):
            data["email"] = account_info["email"]

        # 嘗試取得使用量
        usage_fetched = False
        usage_endpoints = [
            f"/api/organizations/{org_uuid}/usage",
            f"/api/organizations/{org_uuid}/rate_limits",
            f"/api/organizations/{org_uuid}/settings/usage",
        ]

        for endpoint in usage_endpoints:
            try:
                r3 = requests.get(
                    f"{_CLAUDE_BASE}{endpoint}",
                    headers=_HEADERS,
                    cookies=cookies,
                    timeout=15,
                )
                if r3.status_code == 200:
                    usage_data = r3.json()
                    self._parse_usage(usage_data, data)
                    usage_fetched = True
                    break
            except Exception:
                continue

        # ------ Step 3: 嘗試取得帳號設定（訂閱方案等） ------
        try:
            r4 = requests.get(
                f"{_CLAUDE_BASE}/api/organizations/{org_uuid}/settings",
                headers=_HEADERS,
                cookies=cookies,
                timeout=15,
            )
            if r4.status_code == 200:
                settings = r4.json()
                self._parse_settings(settings, data)
        except Exception:
            pass

        # ------ Step 4: 嘗試直接取得使用量頁面 HTML（備援方案） ------
        if not usage_fetched:
            try:
                html_headers = {**_HEADERS, "Accept": "text/html"}
                r5 = requests.get(
                    f"{_CLAUDE_BASE}/settings/usage",
                    headers=html_headers,
                    cookies=cookies,
                    timeout=15,
                )
                if r5.status_code == 200:
                    self._parse_usage_html(r5.text, data)
                    usage_fetched = True
            except Exception:
                pass

        if not usage_fetched and not data.get("display_name"):
            return self._error("已連線但無法取得額度資料，API 端點可能已變更")

        data["org_uuid"] = org_uuid[:8] + "..."  # 只顯示前 8 字

        return ServiceResult(service_name=self.name, success=True, data=data)

    def _parse_usage(self, usage_data: dict, data: dict):
        """解析 Claude API 回傳的額度 JSON 資料。"""
        if not isinstance(usage_data, dict):
            return

        # --- Plan usage limits ---
        # 嘗試多種可能的 key 結構
        for key in ["plan_usage", "planUsage", "plan_usage_limits", "rate_limits"]:
            plan = usage_data.get(key)
            if plan:
                break
        else:
            plan = usage_data

        # Current session
        session = (
            plan.get("current_session")
            or plan.get("currentSession")
            or usage_data.get("current_session")
            or usage_data.get("currentSession")
        )
        if isinstance(session, dict):
            pct = session.get("percent_used") or session.get("percentUsed") or session.get("usage_percent")
            if pct is not None:
                data["session_percent"] = pct
            reset = session.get("resets_in") or session.get("resetsIn") or session.get("reset_time")
            if reset:
                data["session_reset"] = self._format_reset(reset)

        # Weekly limits
        weekly = (
            plan.get("weekly_limits")
            or plan.get("weeklyLimits")
            or usage_data.get("weekly_limits")
            or usage_data.get("weeklyLimits")
        )
        if isinstance(weekly, dict):
            all_models = weekly.get("all_models") or weekly.get("allModels") or weekly
            if isinstance(all_models, dict):
                pct = all_models.get("percent_used") or all_models.get("percentUsed") or all_models.get("usage_percent")
                if pct is not None:
                    data["weekly_percent"] = pct
                reset = all_models.get("resets_in") or all_models.get("resetsIn") or all_models.get("reset_time")
                if reset:
                    data["weekly_reset"] = self._format_reset(reset)

        # --- Extra usage ---
        extra = (
            usage_data.get("extra_usage")
            or usage_data.get("extraUsage")
            or plan.get("extra_usage")
            or plan.get("extraUsage")
        )
        if isinstance(extra, dict):
            data["extra_enabled"] = extra.get("enabled", extra.get("is_enabled", False))
            for k in ["spent", "amount_spent", "total_spent"]:
                if k in extra:
                    data["extra_spent"] = extra[k]
                    break
            for k in ["monthly_limit", "monthlyLimit", "spend_limit"]:
                if k in extra:
                    data["extra_limit"] = extra[k]
                    break
            for k in ["current_balance", "currentBalance", "balance"]:
                if k in extra:
                    data["extra_balance"] = extra[k]
                    break
            for k in ["resets", "resets_at", "reset_date"]:
                if k in extra:
                    data["extra_resets"] = extra[k]
                    break

        # --- 直接在頂層尋找百分比欄位 ---
        if "session_percent" not in data:
            for k in ["session_usage", "current_usage", "session_percent_used"]:
                if k in usage_data:
                    data["session_percent"] = usage_data[k]
                    break
        if "weekly_percent" not in data:
            for k in ["weekly_usage", "weekly_percent_used"]:
                if k in usage_data:
                    data["weekly_percent"] = usage_data[k]
                    break

    def _parse_settings(self, settings: dict, data: dict):
        """解析設定資料，取得訂閱方案相關資訊。"""
        if not isinstance(settings, dict):
            return

        plan_type = (
            settings.get("plan_type")
            or settings.get("planType")
            or settings.get("subscription_type")
            or settings.get("billing_type")
        )
        if plan_type:
            data["plan_type"] = str(plan_type).upper()

        # Look in nested structure
        billing = settings.get("billing", {})
        if isinstance(billing, dict):
            if not data.get("plan_type"):
                pt = billing.get("plan") or billing.get("type")
                if pt:
                    data["plan_type"] = str(pt).upper()

    def _parse_usage_html(self, html: str, data: dict):
        """從 HTML 頁面中解析額度資訊（備援方案）。"""
        # 嘗試找到 JSON 形式的內嵌資料
        import json
        # 找 <script> 中的 JSON 資料
        script_pattern = re.compile(r'<script[^>]*>\s*window\.__NEXT_DATA__\s*=\s*({.*?})\s*</script>', re.DOTALL)
        match = script_pattern.search(html)
        if match:
            try:
                next_data = json.loads(match.group(1))
                props = next_data.get("props", {}).get("pageProps", {})
                if props:
                    self._parse_usage(props, data)
                    return
            except Exception:
                pass

        # 正則匹配百分比
        pct_pattern = re.compile(r'(\d+)%\s*used')
        matches = pct_pattern.findall(html)
        if len(matches) >= 1:
            data["session_percent"] = int(matches[0])
        if len(matches) >= 2:
            data["weekly_percent"] = int(matches[1])

        # 正則匹配重置時間
        reset_pattern = re.compile(r'Resets?\s+in\s+([\d]+\s*hr?\s*[\d]*\s*min?)', re.IGNORECASE)
        resets = reset_pattern.findall(html)
        if len(resets) >= 1:
            data["session_reset"] = resets[0].strip()
        if len(resets) >= 2:
            data["weekly_reset"] = resets[1].strip()

        # 金額
        spent_pattern = re.compile(r'\$(\d+\.\d+)\s*spent')
        spent_match = spent_pattern.search(html)
        if spent_match:
            data["extra_spent"] = float(spent_match.group(1))

    @staticmethod
    def _format_reset(reset_value) -> str:
        """格式化重置時間。"""
        if isinstance(reset_value, str):
            return reset_value
        if isinstance(reset_value, (int, float)):
            # 假設是分鐘數
            minutes = int(reset_value)
            if minutes >= 60:
                h = minutes // 60
                m = minutes % 60
                return f"{h} 小時 {m} 分鐘"
            return f"{minutes} 分鐘"
        if isinstance(reset_value, dict):
            hours = reset_value.get("hours", 0)
            mins = reset_value.get("minutes", 0)
            parts = []
            if hours:
                parts.append(f"{hours} 小時")
            if mins:
                parts.append(f"{mins} 分鐘")
            return " ".join(parts) if parts else str(reset_value)
        return str(reset_value)
