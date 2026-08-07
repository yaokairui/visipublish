"""
单元回归检查（无第三方测试框架，纯断言）
运行：.venv\\Scripts\\python scripts\\unit_checks.py
覆盖 code-review 修复：四字段 schema 校验、平衡花括号解析、MIME 推断、
颜色归一化防误伤、颜色归一化仅作用于 color 属性、端点解析；
以及渠道适配器契约（registry / ApiChannel 骨架 / publish_batch 批量逻辑）。
"""
import io
import sys
from pathlib import Path

from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src import config  # noqa: E402
from src.batch import publish_batch  # noqa: E402
from src.channels import get_channel  # noqa: E402
from src.channels.registry import available_channels  # noqa: E402
from src.channels.base import BaseChannel, ChannelResult  # noqa: E402
from src.config import resolve_chat_completions_url  # noqa: E402
from src.rules import normalize_color, resolve_attributes  # noqa: E402
from src.title_ai import parse_title_list, resolve_title  # noqa: E402
from src.vision_client import OpenAIVisionClient  # noqa: E402


def check(name, cond):
    assert cond, f"FAIL: {name}"
    print(f"PASS: {name}")


# 1. 端点解析
check("base=/v1 自动补全", resolve_chat_completions_url("https://x.com/v1") == "https://x.com/v1/chat/completions")
check("完整端点原样", resolve_chat_completions_url("https://x.com/v1/chat/completions") == "https://x.com/v1/chat/completions")
check("带尾斜杠", resolve_chat_completions_url("https://x.com/v1/") == "https://x.com/v1/chat/completions")

# 2. 四字段 schema 校验
check("四字段齐全有效", OpenAIVisionClient._is_valid_listing({"category": "T恤", "color": "红", "material": "棉", "style": "款"}))
check("缺 material 无效", not OpenAIVisionClient._is_valid_listing({"category": "T恤", "color": "红", "style": "款"}))
check("只含 category 无效", not OpenAIVisionClient._is_valid_listing({"category": "T恤"}))
check("非 dict 无效", not OpenAIVisionClient._is_valid_listing("x"))

# 3. 平衡花括号解析（夹带解释文字 + 假花括号）
parsed = OpenAIVisionClient._parse_json(
    '说明：错误码 {code=1}。结果：{"category": "T恤", "color": "红色", "material": "纯棉", "style": "基础款"}'
)
check("假花括号前有 JSON 仍可提取", parsed["category"] == "T恤")
parsed2 = OpenAIVisionClient._parse_json('```json\n{"category": "T恤", "color": "白色"}\n```')
check("代码围栏解析", parsed2["color"] == "白色")

# 4. MIME 推断
png = io.BytesIO(); Image.new("RGB", (10, 10), (255, 0, 0)).save(png, format="PNG")
jpeg = io.BytesIO(); Image.new("RGB", (10, 10), (255, 0, 0)).save(jpeg, format="JPEG")
check("PNG MIME", OpenAIVisionClient._detect_mime(png.getvalue()) == "image/png")
check("JPEG MIME", OpenAIVisionClient._detect_mime(jpeg.getvalue()) == "image/jpeg")

# 5. 颜色归一化
check("Red->红色", normalize_color("Red") == "红色")
check("navy blue->藏青", normalize_color("navy blue") == "藏青")
check("Light Gray->浅灰", normalize_color("Light Gray") == "浅灰")
check("复合词 whiteblack 不误伤", normalize_color("whiteblack") == "whiteblack")
check("中文原样", normalize_color("白色") == "白色")
check("空值", normalize_color("") == "")

# 6. 归一化只作用于 color 属性
rule = {"attribute_spec": {"color": {"type": "text", "default": "白色"}, "pattern": {"type": "text", "default": ""}}}
attrs = resolve_attributes(rule, {"color": "Red", "pattern": "Stripes"})
check("color 归一化", attrs["color"] == "红色")
check("非 color 文本原样", attrs["pattern"] == "Stripes")

# 7. 渠道注册表
mock_ch = get_channel("mock")
check("get_channel('mock') 实例化", mock_ch.name == "mock")
check("默认渠道为 mock", get_channel(None).name == "mock")
api_ch = get_channel("api")
check("get_channel('api') 实例化", api_ch.name == "api")
api_ok, api_msg = api_ch.check_ready()
check("ApiChannel.check_ready 提示未实现", api_ok is False and "未实现" in api_msg)
try:
    api_ch.publish({})
    check("ApiChannel.publish 抛 NotImplementedError", False)
except NotImplementedError:
    check("ApiChannel.publish 抛 NotImplementedError", True)
try:
    get_channel("nope")
    check("未知渠道抛 ValueError", False)
except ValueError:
    check("未知渠道抛 ValueError", True)
check("可用渠道清单含 mock/api", available_channels() == ["api", "mock"])


# 8. publish_batch：勾选过滤 + 幂等键注入 + 失败隔离 + 状态机
class _FakeChannel(BaseChannel):
    """桩渠道：记录调用，按标题前缀模拟失败。"""

    name = "fake"

    def __init__(self):
        self.calls = []

    def check_ready(self):
        return True, "ok"

    def publish(self, item):
        self.calls.append(item)
        if str(item.get("title", "")).startswith("BAD"):
            return ChannelResult(success=False, message="模拟渠道失败")
        return ChannelResult(success=True, message="ok", extra={"record_id": "rec-1"})

    def publish_off(self, item):
        return ChannelResult(success=True, message="delisted")


def make_item(title, selected=True, status="pending"):
    return {
        "id": "id-" + title[:4],
        "title": title,
        "name": title,
        "selected": selected,
        "status": status,
        "payload": {"title": title, "category": "T恤", "attributes": {}},
    }


items = [
    make_item("GOOD-A", selected=True),
    make_item("BAD-B", selected=True),
    make_item("SKIP-C", selected=False),
]
fake = _FakeChannel()
summary = publish_batch(fake, items)

check("仅发布勾选项（2 条）", summary["total"] == 2)
check("成功 1 条", summary["success"] == 1)
check("失败 1 条", summary["failed"] == 1)
check("未勾选条目状态不变", items[2]["status"] == "pending")
check("成功条目 status=success", items[0]["status"] == "success")
check("失败条目 status=failed 且记录错误", items[1]["status"] == "failed" and "模拟渠道失败" in items[1]["error"])
check("成功条目回填 backend_id", items[0]["backend_id"] == "rec-1")
check("幂等键注入（item.id）", fake.calls[0]["idempotency_key"] == "id-GOOD" and fake.calls[1]["idempotency_key"] == "id-BAD-")


# 9. publish_batch 异常隔离（渠道抛异常）
class _BoomChannel(_FakeChannel):
    def publish(self, item):
        raise RuntimeError("boom")


boom_items = [make_item("A"), make_item("B")]
boom = _BoomChannel()
boom_summary = publish_batch(boom, boom_items)
check("渠道抛异常被隔离为失败", boom_summary["failed"] == 2)
check("异常条目保留错误信息", "boom" in boom_items[0]["error"])

# 10. AI 标题解析与来源解析
check("JSON 数组解析", parse_title_list('["标题A", "标题B"]') == ["标题A", "标题B"])
check("代码围栏 JSON 解析", parse_title_list('```json\n["A", "B"]\n```') == ["A", "B"])
check("dict titles 解析", parse_title_list('{"titles": ["A", "B"]}') == ["A", "B"])
check("编号行文本兜底", parse_title_list("1. 标题一\n2. 标题二") == ["标题一", "标题二"])
check("去重", parse_title_list('["A", "A", "B"]') == ["A", "B"])
check("resolve ai-1", resolve_title("ai-1", ["A", "B"], "R") == "A")
check("resolve ai-2", resolve_title("ai-2", ["A", "B"], "R") == "B")
check("resolve ai 越界回退", resolve_title("ai-9", ["A", "B"], "R") == "R")
check("resolve rule", resolve_title("rule", ["A", "B"], "R") == "R")
check("resolve manual", resolve_title("manual", [], "R", "M") == "M")
check("resolve manual 空回退", resolve_title("manual", [], "R", "  ") == "R")
check("resolve 未知回退", resolve_title("", ["A"], "R") == "R")

print("ALL UNIT CHECKS PASSED")