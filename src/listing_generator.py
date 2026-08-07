"""
Listing 生成器：把「视觉识别结果 + 运营规则库」组装成一条可上架的商品记录。
"""
from datetime import datetime

from src import rules
from src.rules import (
    build_prompts,
    build_title,
    get_rule,
    match_category,
    resolve_attributes,
    season_from_month,
)


def generate_listing(vision_data: dict, seed: int = 0) -> dict:
    """根据视觉 JSON + 规则库生成 listing。

    seed 用于「重新生成」：轮换核心卖点，从而让标题/提示词产生变化。
    """
    vision_data = vision_data or {}
    rule_key = match_category(vision_data.get("category"))
    rule = get_rule(rule_key)

    attributes = resolve_attributes(rule, vision_data)
    season = season_from_month(datetime.now().month)
    selling_point = rule["selling_points"][seed % len(rule["selling_points"])]
    title = build_title(rule, season, attributes, selling_point)
    prompts = build_prompts(rule, attributes, selling_point)

    return {
        "category": rule["name"],
        "category_key": rule_key,
        "attributes": attributes,
        "title": title,
        "season": season,
        "brand": rule["brand"],
        "selling_point": selling_point,
        "prompts": prompts,
        "vision_raw": vision_data,
        "seed": seed,
        "source": vision_data.get("source", "unknown"),
        "note": vision_data.get("note", ""),
    }


def listing_payload_for_rpa(listing: dict) -> dict:
    """RPA 提交用的精简 payload（模拟后台表单字段）。"""
    return {
        "title": listing["title"],
        "category": listing["category"],
        "attributes": listing["attributes"],
        "prompts": listing["prompts"],
        "brand": listing["brand"],
        "season": listing["season"],
        "selling_point": listing["selling_point"],
    }
