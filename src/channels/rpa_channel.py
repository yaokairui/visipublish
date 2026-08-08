"""RPA 渠道基类：把 Playwright 浏览器自动化的公共能力沉淀到这里。

从旧 src/rpa.py 迁移的公共能力：
- 浏览器启动 / 页面打开（含重试）
- 关键步骤 _retry 重试
- 填写后回读校验
- 成功 / 失败截图留档

真实 RPA 渠道（闲鱼 / 千牛等）可继承本类，只需提供目标页面 URL、
选择器与登录态处理，无需重写浏览器骨架。
"""
import time
from pathlib import Path

from src.channels.base import BaseChannel
from src.config import OUTPUT_DIR, RPA_BROWSER


class RPAError(RuntimeError):
    """RPA 执行失败。"""


def retry_action(action, attempts: int = 3, delay: float = 1.5, desc: str = "操作"):
    """对关键步骤做重试：元素未加载 / 网络抖动时可自动恢复。"""
    last_error = None
    for i in range(attempts):
        try:
            return action()
        except Exception as exc:
            last_error = exc
            if i < attempts - 1:
                time.sleep(delay)
    raise RPAError(f"{desc} 重试 {attempts} 次仍失败：{last_error}") from last_error


def serialize_attributes(attributes: dict) -> str:
    """属性 dict -> 表单文本（与模拟后台「；」分隔约定一致）。"""
    return "；".join(f"{k}：{v}" for k, v in (attributes or {}).items())


class RpaChannel(BaseChannel):
    """浏览器自动化渠道基类：负责浏览器生命周期与公共工具方法。"""

    def __init__(
        self,
        headless: bool = True,
        screenshot_dir: Path | None = None,
        max_attempts: int = 3,
        browser_name: str = RPA_BROWSER,
    ):
        self.headless = headless
        self.screenshot_dir = Path(screenshot_dir) if screenshot_dir else OUTPUT_DIR / "screenshots"
        self.max_attempts = max_attempts
        self.browser_name = browser_name

    def _screenshot_path(self, name: str) -> Path:
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        return self.screenshot_dir / name

    def _launch_page(self, playwright):
        """启动浏览器并返回 (browser, page)，统一视口便于截图演示。"""
        browser_type = getattr(playwright, self.browser_name, None)
        if browser_type is None:
            raise RPAError(
                f"不支持的浏览器类型：{self.browser_name}（可用 chromium / firefox / webkit）"
            )
        browser = browser_type.launch(headless=self.headless)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        return browser, page

    def _open(self, page, url: str) -> None:
        """打开目标页面（带重试）。"""

        def goto():
            page.goto(url, wait_until="domcontentloaded", timeout=15000)

        retry_action(goto, self.max_attempts, desc="打开目标页面")
