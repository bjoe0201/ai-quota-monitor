from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ServiceResult:
    service_name: str
    success: bool
    data: dict = field(default_factory=dict)
    error: Optional[str] = None


class BaseService(ABC):
    name: str = ""

    @abstractmethod
    def fetch(self, config: dict) -> ServiceResult:
        """Fetch quota/usage information from the service."""
        pass

    def _not_configured(self) -> ServiceResult:
        return ServiceResult(
            service_name=self.name,
            success=False,
            error="未設定 API Key"
        )

    def _error(self, msg: str) -> ServiceResult:
        return ServiceResult(
            service_name=self.name,
            success=False,
            error=msg
        )
