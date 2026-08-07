"""AI 商品标题生成（Title AI）
============================
根据「商品图片 + 识别结果 + 类目曝光关键词池」，调用 OpenAI 兼容的多模态 API
生成 N 条电商标题候选；未配置 API Key 或调用失败时返回空列表（由调用方回退规则模板标题）。

同时提供 resolve_title()：把审核界面选择的「标题来源」解析为最终标题，
支持：ai-1/ai-2/...（AI 候选）、rule（规则模板）、manual（手动输入）。
"""
import base64
import io
import json
import re

import requests

from src.config import (
    AI_TITLE_COUNT,
    TITLE_MAX_LEN,
    VISION_API_KEY,
    VISION_CHAT_COMPLETIONS_URL,
    VISION_MODEL,
)

_SYSTEM_PROMPT = (
    "你是资深电商运营标题专家。根据商品图片和 AI 识别信息，生成符合电商平台规则的商品标题。"
    "要求：\n"
    "1. 必须输出一个 JSON 数组，数组元素为标题字符串，禁止返回空数组；\n"
    "2. 标题需包含电商曝光关键词（如 新款、爆款、ins风、显瘦、透气、包邮 等，按类目搭配）；\n"
    "3. 图片信息不足时，基于识别信息（类目/颜色/材质/风格）合理扩写，不得编造具体功能承诺；\n"
    "4. 不使用绝对化用语（最、第一、100%、顶级 等）与平台违禁词；\n"
    "5. 只输出 JSON 数组，不要输出任何解释文字。"
)

_MIME_BY_FORMAT = {
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


def _detect_mime(image_bytes: bytes) -> str:
    try:
        from PIL import Image

        fmt = (Image.open(io.BytesIO(image_bytes)).format or "").lower()
        return _MIME_BY_FORMAT.get(fmt, "image/png")
    except Exception:
        return "image/png"


def _build_payload(
    image_bytes: bytes, vision: dict, rule: dict, count: int, max_len: int
) -> dict:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{_detect_mime(image_bytes)};base64,{b64}"
    keywords = "、".join(rule.get("exposure_keywords") or [])
    user_prompt = (
        f"请根据这张商品图片生成 {count} 条中文电商标题。\n"
        f"AI 识别信息：{json.dumps(vision, ensure_ascii=False)}\n"
        f"参考曝光关键词：{keywords or '（无，请自行搭配常用曝光词）'}\n"
        f"每条标题不超过 {max_len} 个字符。"
    )
    return {
        "model": VISION_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
        "temperature": 0.8,
    }


def parse_title_list(content: str) -> list[str]:
    """把模型输出解析为标题列表。

    兼容：JSON 数组、{"titles": [...]}、markdown 代码围栏、编号行文本；
    自动去重、去空白。
    """
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = text.rstrip("`").strip()
    data = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None

    if isinstance(data, list):
        raw = [str(x) for x in data]
    elif isinstance(data, dict):
        raw = [str(x) for x in (data.get("titles") or data.get("title") or [])]
    else:
        raw = []
        for line in text.splitlines():
            cleaned = re.sub(r"^\s*\d+[.、)]\s*", "", line).strip().strip('"')
            if cleaned and not cleaned.startswith("{") and "：" not in cleaned[:12]:
                raw.append(cleaned)

    seen, out = set(), []
    for item in raw:
        title = re.sub(r"\s+", " ", item).strip('" ')
        if title and title not in seen:
            seen.add(title)
            out.append(title)
    return out


def generate_ai_titles(
    image_bytes: bytes,
    vision: dict,
    rule: dict,
    count: int = AI_TITLE_COUNT,
    max_len: int = TITLE_MAX_LEN,
) -> list[str]:
    """调用真实 API 生成 count 条标题候选；未配置 Key / 调用失败返回空列表。"""
    if not VISION_API_KEY:
        return []
    try:
        payload = _build_payload(image_bytes, vision, rule, count, max_len)
        resp = requests.post(
            VISION_CHAT_COMPLETIONS_URL,
            headers={
                "Authorization": f"Bearer {VISION_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        titles = parse_title_list(content)
        return [t[:max_len] for t in titles[:count]]
    except Exception:
        return []


def resolve_title(
    source_key: str,
    ai_titles: list,
    rule_title: str,
    manual: str = "",
) -> str:
    """把审核界面的「标题来源」解析为最终标题。

    - ai-1 / ai-2 / ...：取对应 AI 候选（越界回退规则标题）
    - rule：规则模板标题
    - manual：手动输入（为空回退规则标题）
    """
    key = (source_key or "").strip().lower()
    if key.startswith("ai-"):
        parts = key.split("-")
        if len(parts) == 2 and parts[1].isdigit():
            idx = int(parts[1]) - 1
            if 0 <= idx < len(ai_titles or []):
                return (ai_titles or [])[idx]
        return rule_title
    if key == "manual":
        return (manual or "").strip() or rule_title
    return rule_title