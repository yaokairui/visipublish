"""MockChannel：把人工审核后的商品数据，通过 Playwright RPA 自动填进
本地模拟电商后台的表单并提交。

要点（自旧 src/rpa.py 迁移）：
- 每个关键步骤带重试（元素未加载 / 网络抖动时可自动恢复）
- 填写后做回读校验，防止「填错位置」这种静默失败
- 成功 / 失败都截图，方便面试演示与排查
- publish 携带 idempotency_key 实现幂等；publish_off 调用后台 /delist
"""
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import requests

from src.channels.base import BaseChannel, ChannelResult
from src.channels.rpa_channel import RpaChannel, retry_action, serialize_attributes
from src.config import MOCK_BACKEND_URL, OUTPUT_DIR, RPA_HEADLESS

# 模拟后台表单的稳定选择器（与 mock_backend/templates/index.html 保持一致）
SELECTORS = {
    "title": "#title",
    "category": "#category",
    "attributes": "#attributes",
    "idempotency_key": "#idempotency_key",
    "submit": "#submit-btn",
    "success": "#success-banner",
}


def check_backend_health(url: str, timeout: float = 2.0) -> bool:
    """提交前先探活，给用户更友好的提示。"""
    try:
        resp = requests.get(url.rstrip("/") + "/health", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


def _select_category(page, category: str) -> str:
    """按文案选择类目；找不到时回退到第一个真实选项并告警。"""
    options = [o.strip() for o in page.locator("#category option").all_inner_texts()]
    real_options = [o for o in options if o and "请选择" not in o]
    if category in real_options:
        page.select_option("#category", label=category)
        return category
    if real_options:
        page.select_option("#category", label=real_options[0])
        return real_options[0]
    raise RuntimeError("模拟后台类目下拉菜单为空，无法选择")


def _fill_hidden(page, selector: str, value: str) -> None:
    """隐藏输入框不满足 Playwright 可操作性校验，改用 evaluate 直接赋值。"""
    page.locator(selector).evaluate(
        "(el, v) => { el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })); }",
        value,
    )


class MockChannel(RpaChannel):
    """本地模拟后台渠道：Playwright RPA 填表 + 幂等提交 + /delist 下架。"""

    name = "mock"

    def __init__(
        self,
        backend_url: str = MOCK_BACKEND_URL,
        headless: bool = RPA_HEADLESS,
        screenshot_dir=None,
        max_attempts: int = 3,
    ):
        super().__init__(headless=headless, screenshot_dir=screenshot_dir, max_attempts=max_attempts)
        self.backend_url = backend_url.rstrip("/")

    @classmethod
    def create(cls) -> "MockChannel":
        """工厂：按全局配置构造默认实例。"""
        return cls(backend_url=MOCK_BACKEND_URL, headless=RPA_HEADLESS)

    # ---------- 契约实现 ----------

    def check_ready(self) -> tuple[bool, str]:
        ok = check_backend_health(self.backend_url)
        return (
            (True, "模拟后台可访问")
            if ok
            else (False, f"模拟后台不可访问：{self.backend_url}")
        )

    def publish(self, item: dict) -> ChannelResult:
        from playwright.sync_api import sync_playwright  # 延迟导入，未装 playwright 时不影响其他功能

        payload = item or {}
        title = payload.get("title", "")
        category = payload.get("category", "")
        attributes = serialize_attributes(payload.get("attributes", {}))
        idempotency_key = str(payload.get("idempotency_key") or "")
        result = ChannelResult(
            success=False,
            message="",
            url=self.backend_url,
            extra={"idempotency_key": idempotency_key},
        )
        shot_name = f"rpa_{idempotency_key or datetime.now().strftime('%H%M%S')}.png"
        screenshot_path = self._screenshot_path(shot_name)

        if not title.strip():
            result.message = "商品标题为空，已取消上架"
            return result

        try:
            with sync_playwright() as p:
                browser, page = self._launch_page(p)

                # 1. 打开模拟后台
                self._open(page, self.backend_url)
                result.steps.append("打开模拟后台页面")

                # 2. 填写标题
                retry_action(
                    lambda: page.locator(SELECTORS["title"]).fill(title),
                    self.max_attempts,
                    desc="填写标题",
                )
                result.steps.append("填写标题")

                # 3. 选择类目
                chosen = retry_action(
                    lambda: _select_category(page, category),
                    self.max_attempts,
                    desc="选择类目",
                )
                result.steps.append(
                    f"选择类目「{chosen}」"
                    if chosen == category
                    else f"类目未匹配，回退为「{chosen}」"
                )

                # 4. 填写属性
                retry_action(
                    lambda: page.locator(SELECTORS["attributes"]).fill(attributes),
                    self.max_attempts,
                    desc="填写属性",
                )
                result.steps.append("填写属性")

                # 5. 写入幂等键（隐藏输入框，供后台去重）
                if idempotency_key:
                    _fill_hidden(page, SELECTORS["idempotency_key"], idempotency_key)
                    result.steps.append("写入幂等键")

                # 6. 回读校验（防止静默填错）
                filled_title = page.locator(SELECTORS["title"]).input_value()
                filled_attrs = page.locator(SELECTORS["attributes"]).input_value()
                if filled_title != title:
                    raise RuntimeError(f"标题回读校验失败：期望「{title}」，实际「{filled_title}」")
                if filled_attrs != attributes:
                    raise RuntimeError(f"属性回读校验失败：期望「{attributes}」，实际「{filled_attrs}」")
                result.steps.append("回读校验通过（标题/属性一致）")

                # 7. 点击提交
                retry_action(
                    lambda: page.locator(SELECTORS["submit"]).click(),
                    self.max_attempts,
                    desc="点击提交按钮",
                )
                result.steps.append("点击【提交上架】")

                # 8. 等待成功标识
                retry_action(
                    lambda: page.locator(SELECTORS["success"]).wait_for(
                        state="visible", timeout=10000
                    ),
                    self.max_attempts,
                    desc="等待上架成功",
                )
                result.steps.append("后端返回上架成功")

                page.screenshot(path=str(screenshot_path), full_page=True)
                result.screenshot = str(screenshot_path)
                result.success = True
                result.message = f"上架成功：{title}"
                result.url = page.url
                # 成功页 URL 形如 /success?sid=<record_id>，作为下架标识
                sid = parse_qs(urlparse(page.url).query).get("sid", [None])[0]
                result.extra["record_id"] = sid
                browser.close()

        except Exception as exc:  # 统一收口，失败也尝试截图
            result.message = f"RPA 执行失败：{exc}"
            result.steps.append(f"失败：{exc}")
            if not result.screenshot:
                try:
                    from playwright.sync_api import sync_playwright as _sp

                    with _sp() as p:
                        browser = p.chromium.launch(headless=self.headless)
                        page = browser.new_page()
                        page.goto(self.backend_url, timeout=5000)
                        page.screenshot(path=str(screenshot_path), full_page=True)
                        browser.close()
                    result.screenshot = str(screenshot_path)
                except Exception:
                    pass
            if "Executable doesn't exist" in str(exc):
                result.message = (
                    "未安装 Playwright 浏览器内核。请在虚拟环境中执行："
                    "playwright install chromium"
                )
        return result

    def publish_off(self, item: dict) -> ChannelResult:
        backend_id = (item or {}).get("backend_id") or (item or {}).get("record_id")
        result = ChannelResult(success=False, message="")
        if not backend_id:
            result.message = "缺少后端记录 ID，无法下架"
            return result
        try:
            resp = requests.post(
                self.backend_url + "/delist",
                data={"item_id": backend_id},
                timeout=10,
            )
            if resp.status_code != 200 or not resp.json().get("ok"):
                result.message = f"下架失败：HTTP {resp.status_code}，{resp.text[:120]}"
                return result
        except Exception as exc:
            result.message = f"下架失败：{exc}"
            return result
        result.success = True
        result.message = f"已下架记录 {backend_id}"
        result.steps = ["调用模拟后台 /delist", f"记录 {backend_id} -> delisted"]
        result.extra["backend_id"] = backend_id
        return result