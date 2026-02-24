"""
瀏覽器資料服務 — 從 local_server.DATA_STORE 讀取
Tampermonkey 注入的頁面資料。

四個服務類別分別對應四個被監控的頁面：
  - BrowserOpenAIService      → openai_billing
  - BrowserClaudeUsageService → claude_usage
  - BrowserClaudeBillingService → claude_billing
  - BrowserGitHubCopilotService → github_copilot
"""
from datetime import datetime
from . import local_server
from .base import BaseService, ServiceResult

# 若資料超過此秒數未更新，顯示警告
STALE_THRESHOLD_SEC = 600  # 10 分鐘


def _stale_warning(received_at: str) -> str | None:
    """Return stale warning string if data is old, else None."""
    try:
        dt = datetime.fromisoformat(received_at)
        age = (datetime.now() - dt).total_seconds()
        if age > STALE_THRESHOLD_SEC:
            mins = int(age // 60)
            return f"（資料已 {mins} 分鐘未更新，請確認瀏覽器頁面仍開啟）"
    except Exception:
        pass
    return None


def _ts_display(received_at: str) -> str:
    try:
        dt = datetime.fromisoformat(received_at)
        return dt.strftime("%H:%M:%S")
    except Exception:
        return received_at


def _base_not_connected(name: str) -> ServiceResult:
    if not local_server.is_running():
        return ServiceResult(
            service_name=name,
            success=False,
            error="本地伺服器未啟動"
        )
    return ServiceResult(
        service_name=name,
        success=False,
        error="等待瀏覽器連線...\n請在瀏覽器開啟對應頁面（已安裝 Tampermonkey 腳本）"
    )


# ─────────────────────────────────────────────────────
#  OpenAI 帳單
# ─────────────────────────────────────────────────────
class BrowserOpenAIService(BaseService):
    name = "OpenAI 帳單 (瀏覽器)"
    source_key = "openai_billing"

    def fetch(self, config: dict) -> ServiceResult:
        raw = local_server.get_data(self.source_key)
        if not raw:
            return _base_not_connected(self.name)

        data = dict(raw)
        recv = data.get("received_at", "")
        data["updated_at"] = _ts_display(recv)
        warn = _stale_warning(recv)
        if warn:
            data["stale_warning"] = warn

        return ServiceResult(service_name=self.name, success=True, data=data)


# ─────────────────────────────────────────────────────
#  Claude.ai 用量
# ─────────────────────────────────────────────────────
class BrowserClaudeUsageService(BaseService):
    name = "Claude.ai 用量 (瀏覽器)"
    source_key = "claude_usage"

    def fetch(self, config: dict) -> ServiceResult:
        raw = local_server.get_data(self.source_key)
        if not raw:
            return _base_not_connected(self.name)

        data = dict(raw)
        recv = data.get("received_at", "")
        data["updated_at"] = _ts_display(recv)
        warn = _stale_warning(recv)
        if warn:
            data["stale_warning"] = warn

        return ServiceResult(service_name=self.name, success=True, data=data)


# ─────────────────────────────────────────────────────
#  Claude API 帳單 (platform.claude.com)
# ─────────────────────────────────────────────────────
class BrowserClaudeBillingService(BaseService):
    name = "Claude API 帳單 (瀏覽器)"
    source_key = "claude_billing"

    def fetch(self, config: dict) -> ServiceResult:
        raw = local_server.get_data(self.source_key)
        if not raw:
            return _base_not_connected(self.name)

        data = dict(raw)
        recv = data.get("received_at", "")
        data["updated_at"] = _ts_display(recv)
        warn = _stale_warning(recv)
        if warn:
            data["stale_warning"] = warn

        return ServiceResult(service_name=self.name, success=True, data=data)


# ─────────────────────────────────────────────────────
#  GitHub Copilot (網頁)
# ─────────────────────────────────────────────────────
class BrowserGitHubCopilotService(BaseService):
    name = "GitHub Copilot (瀏覽器)"
    source_key = "github_copilot"

    def fetch(self, config: dict) -> ServiceResult:
        raw = local_server.get_data(self.source_key)
        if not raw:
            return _base_not_connected(self.name)

        data = dict(raw)
        recv = data.get("received_at", "")
        data["updated_at"] = _ts_display(recv)
        warn = _stale_warning(recv)
        if warn:
            data["stale_warning"] = warn

        return ServiceResult(service_name=self.name, success=True, data=data)
