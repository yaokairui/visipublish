"""
视觉识别模块（Vision Client）
============================
统一入口 analyze_image()：
- 配置了 VISION_API_KEY  -> 调用 OpenAI 兼容的 Vision API，把图片转成结构化 JSON
- 未配置/调用失败       -> 自动回退 MockVisionClient（用 Pillow 提取图像主色，
                            离线也能跑通整条演示链路）

兼容性设计：
- VISION_API_BASE 支持「/v1 根地址」与「完整 chat/completions 端点」两种写法（config 层归一化）
- response_format 自适应：优先 json_object，返回不满足目标 schema 或请求失败时，
  自动降级为不带 response_format 的普通请求重试（适配 agnes 等网关）
- 目标 schema = 四字段齐全（category/color/material/style），见 spec vision-recognition
- 系统提示词约束类目枚举与简体中文输出；规则层再兜底归一化
"""
import base64
import io
import json
import re

import requests
from PIL import Image

from src.config import VISION_API_KEY, VISION_CHAT_COMPLETIONS_URL, VISION_MODEL

# Mock 识别可输出的颜色名（用于标题/属性展示，真实数据来自像素分析）
_COLOR_THRESHOLDS = [
    # (颜色名, 判断函数)
    ("黑色", lambda r, g, b: max(r, g, b) < 70),
    ("白色", lambda r, g, b: min(r, g, b) > 190 and max(r, g, b) - min(r, g, b) < 35),
    ("灰色", lambda r, g, b: abs(r - g) < 25 and abs(g - b) < 25 and 70 <= max(r, g, b) <= 190),
    ("红色", lambda r, g, b: r > 140 and g < 110 and b < 110),
    ("橙色", lambda r, g, b: r > 170 and 90 < g < 180 and b < 90),
    ("黄色", lambda r, g, b: r > 170 and g > 150 and b < 110),
    ("粉色", lambda r, g, b: r > 170 and 90 < g < 160 and 110 < b < 180),
    ("蓝色", lambda r, g, b: b > 140 and b > r + 30),
    ("紫色", lambda r, g, b: r > 110 and b > 130 and g < 110),
    ("绿色", lambda r, g, b: g > 130 and g > r + 20 and g > b + 20),
    ("棕色", lambda r, g, b: 100 < r < 190 and 60 < g < 140 and b < 90),
]

# 目标 schema：识别结果必须包含这四个字段才算有效
_TARGET_KEYS = ("category", "color", "material", "style")

# 系统提示词：类目枚举 + 简体中文约束，降低脏数据概率（规则层仍会二次兜底）
_SYSTEM_PROMPT = (
    "你是电商运营智能助手，负责把商品图片识别成标准化的上架数据。"
    "严格只输出一个 JSON 对象，不要输出 markdown 代码块，不要输出任何解释文字。"
    "JSON 必须包含以下字符串字段：category、color、material、style。"
    "category 只能是以下之一：T恤、连衣裙、牛仔裤、卫衣、运动鞋。"
    "color、material、style 使用简体中文描述。"
    "若无法判断，category 填 T恤，其余字段填最常见值。"
)

_MIME_BY_FORMAT = {
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


class VisionError(RuntimeError):
    """视觉识别失败（API 或解析异常）。"""


class MockVisionClient:
    """离线回退识别：主色来自真实像素分析，类目/材质/风格使用内置演示默认值。"""

    def analyze(self, image_bytes: bytes) -> dict:
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            color_name = self._dominant_color_name(img)
        except Exception as exc:  # 图片损坏等
            raise VisionError(f"图片解析失败：{exc}") from exc
        return {
            "category": "T恤",  # 演示：Mock 模式固定默认类目；真实模式由大模型判断
            "color": color_name,
            "material": "纯棉",
            "style": "基础款",
            "source": "mock",
            "note": "未配置 API Key，已使用内置 Mock 识别（主色来自真实像素分析）",
        }

    @staticmethod
    def _dominant_color_name(img: Image.Image) -> str:
        small = img.resize((64, 64))
        small = small.quantize(colors=4, method=Image.Quantize.MEDIANCUT).convert("RGB")
        pixels = list(small.getdata())
        counts: dict = {}
        for rgb in pixels:
            key = (rgb[0] // 16, rgb[1] // 16, rgb[2] // 16)
            counts[key] = counts.get(key, 0) + 1
        (r16, g16, b16), _ = max(counts.items(), key=lambda kv: kv[1])
        r, g, b = r16 * 16 + 8, g16 * 16 + 8, b16 * 16 + 8
        for name, check in _COLOR_THRESHOLDS:
            if check(r, g, b):
                return name
        return "白色"


class OpenAIVisionClient:
    """OpenAI 兼容 Vision API：图片 -> 结构化 JSON（自适应 response_format）。"""

    def __init__(
        self,
        api_key: str = VISION_API_KEY,
        base_url: str = VISION_CHAT_COMPLETIONS_URL,
        model: str = VISION_MODEL,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def _build_payload(self, data_url: str, use_json_object: bool) -> dict:
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请识别这张商品图片并返回 JSON"},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
        }
        if use_json_object:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def _request(self, payload: dict) -> str:
        """POST 请求并返回 message.content，网络/HTTP 错误统一抛 VisionError。"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(self.base_url, headers=headers, json=payload, timeout=90)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            raise VisionError(f"Vision API 调用失败：{exc}") from exc

    def analyze(self, image_bytes: bytes) -> dict:
        if not self.api_key:
            raise VisionError("VISION_API_KEY 未配置")

        b64 = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{self._detect_mime(image_bytes)};base64,{b64}"

        # 第一轮：带 response_format=json_object（OpenAI 官方最优路径）
        # 失败或返回 schema 不符时，第二轮降级为普通请求重试（适配 agnes 等网关）
        last_error = None
        for use_json_object in (True, False):
            try:
                content = self._request(self._build_payload(data_url, use_json_object))
                data = self._parse_json(content)
                if self._is_valid_listing(data):
                    data["source"] = "api"  # 覆盖模型自带 source，保证来源标识一致
                    return data
                last_error = VisionError(
                    f"返回 JSON 缺少目标字段 {_TARGET_KEYS}，已降级重试"
                    if use_json_object
                    else f"返回 JSON 缺少目标字段 {_TARGET_KEYS}"
                )
            except VisionError as exc:
                last_error = exc
                if not use_json_object:
                    break
        raise last_error

    @staticmethod
    def _detect_mime(image_bytes: bytes) -> str:
        """按实际图片格式推断 MIME，避免 data URL 与实际内容不符。"""
        try:
            fmt = (Image.open(io.BytesIO(image_bytes)).format or "").lower()
            return _MIME_BY_FORMAT.get(fmt, "image/png")
        except Exception:
            return "image/png"

    @staticmethod
    def _is_valid_listing(data: dict) -> bool:
        """目标 schema 校验：category/color/material/style 四字段齐全才算有效。"""
        return isinstance(data, dict) and all(key in data for key in _TARGET_KEYS)

    @staticmethod
    def _parse_json(content: str) -> dict:
        """健壮解析：容忍代码围栏、前后空白、夹带解释文字等异常输出。"""
        text = (content or "").strip()
        if text.startswith("```"):  # 兼容模型输出 markdown 代码围栏
            text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
            text = text.rstrip("`").strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # 模型夹带解释文字时，按平衡花括号提取（避免贪婪匹配误抓）
            data = OpenAIVisionClient._extract_json_object(text)
            if data is None:
                raise VisionError(f"模型返回不是合法 JSON：{content[:200]}")
        if not isinstance(data, dict):
            raise VisionError("模型返回的 JSON 不是对象")
        return data

    @staticmethod
    def _extract_json_object(text: str):
        """从夹带文字的响应中提取第一个可解析为对象的平衡 JSON 块。"""
        start = 0
        while True:
            start = text.find("{", start)
            if start == -1:
                return None
            depth = 0
            in_string = False
            escape = False
            for i in range(start, len(text)):
                ch = text[i]
                if in_string:
                    if escape:
                        escape = False
                    elif ch == "\\":
                        escape = True
                    elif ch == '"':
                        in_string = False
                else:
                    if ch == '"':
                        in_string = True
                    elif ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            candidate = text[start : i + 1]
                            try:
                                return json.loads(candidate)
                            except json.JSONDecodeError:
                                break  # 该起点不是合法 JSON，尝试下一个 {
            start += 1


def create_vision_client():
    """工厂：按配置返回真实 API 客户端或 Mock 客户端。"""
    if VISION_API_KEY:
        return OpenAIVisionClient()
    return MockVisionClient()


def analyze_image(image_bytes: bytes) -> dict:
    """统一入口：优先真实 API，失败自动回退 Mock，保证演示不中断。"""
    if VISION_API_KEY:
        try:
            return create_vision_client().analyze(image_bytes)
        except VisionError:
            fallback = MockVisionClient().analyze(image_bytes)
            fallback["note"] = "真实 API 调用失败，已自动回退到 Mock 识别"
            return fallback
    return create_vision_client().analyze(image_bytes)
