"""渠道适配器基类：统一「登录 / 上架 / 下架 / 状态检查」契约。

调用方（app.py / batch.py）只依赖 BaseChannel，不感知平台差异：
- MockChannel  -> 本地模拟后台（Playwright RPA 填表）
- ApiChannel   -> 官方开放平台 API 骨架（拼多多 / 1688 等，尚未实现）
- RpaChannel   -> 浏览器自动化渠道基类（登录态 / 选择器由各实现提供）

未来接入真实平台 = 新增一个 Channel 模块，不改动调用方。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ChannelResult:
    """渠道发布 / 下架的结构化结果，供界面展示与批量汇总。"""

    success: bool
    message: str
    steps: list[str] = field(default_factory=list)
    screenshot: str | None = None
    url: str = ""
    submitted_at: str = field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "message": self.message,
            "steps": self.steps,
            "screenshot": self.screenshot,
            "url": self.url,
            "submitted_at": self.submitted_at,
            "extra": self.extra,
        }


class BaseChannel(ABC):
    """渠道契约。name 为渠道标识，item 为已审核的 listing payload。"""

    name: str = "base"

    @abstractmethod
    def check_ready(self) -> tuple[bool, str]:
        """渠道是否可用（服务可达 / 已登录 / 已配置凭证）。返回 (ok, message)。"""

    @abstractmethod
    def publish(self, item: dict) -> ChannelResult:
        """上架一条商品记录。item 含 title / category / attributes 等，可含 idempotency_key。"""

    @abstractmethod
    def publish_off(self, item: dict) -> ChannelResult:
        """下架一条商品记录。item 至少含后端记录标识（backend_id / record_id）。"""

    def check_status(self, item: dict) -> str:
        """查询记录状态；默认实现返回 unknown，各渠道按需覆写。"""
        return "unknown"