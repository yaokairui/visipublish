"""
运营规则库（Rules Engine）
=========================
面试演示版：把运营侧的「上架规则」沉淀为可配置的数据结构，
而不是写死在业务代码里。真实项目中，这份规则应来自后台配置中心 / 数据库。

规则要点：标题必须按「季节 + 品牌 + 商品名 + 核心卖点」拼装，
属性值做白名单归一化（AI 返回的值不在允许范围内时，回退到默认值）。
"""

SEASON_MAP = {
    1: "冬季", 2: "冬季", 3: "春季", 4: "春季", 5: "春季", 6: "夏季",
    7: "夏季", 8: "夏季", 9: "秋季", 10: "秋季", 11: "秋季", 12: "冬季",
}


def season_from_month(month: int) -> str:
    """按月份映射当前季节，用于标题前缀。"""
    return SEASON_MAP.get(month, "四季")


# 常见英文/变体颜色名 -> 简体中文（key 为去空格小写，供 normalize_color 匹配）
COLOR_ALIASES = {
    "white": "白色", "black": "黑色", "red": "红色", "blue": "蓝色",
    "green": "绿色", "yellow": "黄色", "orange": "橙色", "purple": "紫色",
    "pink": "粉色", "gray": "灰色", "grey": "灰色", "brown": "棕色",
    "beige": "米色", "cream": "米白", "ivory": "米白", "offwhite": "米白",
    "navy": "藏青", "navyblue": "藏青", "darkblue": "藏青",
    "skyblue": "天蓝", "lightblue": "浅蓝", "babyblue": "浅蓝",
    "lightgreen": "浅绿", "darkgreen": "墨绿", "olive": "橄榄绿",
    "burgundy": "酒红", "maroon": "酒红", "darkred": "酒红",
    "gold": "金色", "golden": "金色", "silver": "银色",
    "khaki": "卡其色", "camel": "驼色", "coffee": "咖啡色",
    "charcoal": "炭灰", "lightgray": "浅灰", "darkgray": "深灰",
    "multicolor": "多色", "colorful": "彩色",
}


def normalize_color(value) -> str:
    """把英文/变体颜色名归一化为简体中文；未命中时保留原值。

    匹配顺序：完全一致 -> 去空格一致（兼容 navy blue/navyblue）-> 单英文词
    别名以「完整词」出现（避免 whiteblack 被误判为白色）。
    """
    text = str(value or "").strip()
    if not text:
        return ""
    spaced = " ".join(text.lower().split())
    compact = spaced.replace(" ", "")
    if compact in COLOR_ALIASES:
        return COLOR_ALIASES[compact]
    if spaced in COLOR_ALIASES:
        return COLOR_ALIASES[spaced]
    words = set(spaced.split())
    for alias, cn in COLOR_ALIASES.items():
        if alias in words:  # 单英文词别名且以完整词出现
            return cn
    return text



# 每个类目一条规则：
#   aliases          识别结果匹配用别名（用于把 AI 返回的类目名归一化）
#   brand / product  标题模板的「品牌」与「商品名」
#   title_template   标题拼装模板（季节+品牌+商品名+核心卖点）
#   selling_points   核心卖点池（「重新生成」时轮换）
#   attribute_spec   属性白名单：choice=下拉枚举，text=自由文本
#   prompt_templates AI 生图提示词模板（演示只生成文本，不调用生图 API）
CATEGORY_RULES = {
    "tshirt": {
        "name": "T恤",
        "aliases": ["t恤", "t恤衫", "tee", "短袖", "t-shirt", "tshirt", "t 恤"],
        "brand": "CloudWear",
        "product": "纯色T恤",
        "exposure_keywords": ["2026新款", "纯棉", "透气", "ins风", "男女同款"],
        "title_template": "{season}新款 {brand}{product} {selling_point}",
        "selling_points": ["透气舒适", "简约百搭", "亲肤不闷汗"],
        "attribute_spec": {
            "color": {"type": "text", "default": "白色"},
            "material": {
                "type": "choice",
                "options": ["纯棉", "棉涤混纺", "莫代尔"],
                "default": "纯棉",
            },
            "style": {
                "type": "choice",
                "options": ["基础款", "修身款", "oversize"],
                "default": "基础款",
            },
        },
        "prompt_templates": [
            "电商主图：{color}{material}{product}，{selling_point}，纯色背景，柔和棚拍灯光，"
            "商品居中构图，细节清晰，无文字无水印",
            "模特场景图：{color}{product}，{style}版型，{selling_point}，户外自然光，"
            "真实质感，高清商品摄影，留出文案排版空间",
            "细节特写：{material}面料纹理与领口走线，{color}，浅灰背景，微距摄影，高清",
        ],
    },
    "dress": {
        "name": "连衣裙",
        "aliases": ["连衣裙", "裙子", "dress", "one piece", "one-piece"],
        "brand": "Claudia",
        "product": "法式连衣裙",
        "title_template": "{season}新款 {brand}{product} {selling_point}",
        "selling_points": ["显瘦收腰", "垂坠感强", "通勤约会两穿"],
        "attribute_spec": {
            "color": {"type": "text", "default": "米白"},
            "material": {
                "type": "choice",
                "options": ["雪纺", "棉麻", "聚酯纤维"],
                "default": "雪纺",
            },
            "length": {
                "type": "choice",
                "options": ["短款", "中长款", "长款"],
                "default": "中长款",
            },
        },
        "prompt_templates": [
            "电商主图：{color}{material}{product}，{selling_point}，奶油色背景，柔光棚拍，"
            "商品居中，无文字无水印",
            "模特场景图：{color}{product}，{length}，{selling_point}，都市街景，自然光，高清",
            "细节特写：{material}裙摆与腰线剪裁，{color}，浅色背景，微距摄影，高清",
        ],
    },
    "jeans": {
        "name": "牛仔裤",
        "aliases": ["牛仔裤", "牛仔", "jeans", "denim"],
        "brand": "DenimLab",
        "product": "直筒牛仔裤",
        "title_template": "{season}新款 {brand}{product} {selling_point}",
        "selling_points": ["高腰显瘦", "弹力不勒", "百搭直筒"],
        "attribute_spec": {
            "color": {"type": "text", "default": "经典蓝"},
            "material": {
                "type": "choice",
                "options": ["丹宁", "弹力牛仔", "重磅牛仔"],
                "default": "丹宁",
            },
            "fit": {
                "type": "choice",
                "options": ["直筒", "小脚", "阔腿"],
                "default": "直筒",
            },
        },
        "prompt_templates": [
            "电商主图：{color}{material}{product}，{selling_point}，浅灰背景，棚拍，"
            "商品居中，无文字无水印",
            "模特场景图：{color}{product}，{fit}版型，{selling_point}，街头风格，自然光，高清",
            "细节特写：{material}纹理与车线工艺，{color}，微距摄影，高清",
        ],
    },
    "hoodie": {
        "name": "卫衣",
        "aliases": ["卫衣", "hoodie", "sweatshirt", "连帽衫"],
        "brand": "CozyUp",
        "product": "宽松卫衣",
        "title_template": "{season}新款 {brand}{product} {selling_point}",
        "selling_points": ["加绒保暖", "慵懒风", "男女同款"],
        "attribute_spec": {
            "color": {"type": "text", "default": "燕麦色"},
            "material": {
                "type": "choice",
                "options": ["毛圈棉", "抓绒", "棉涤"],
                "default": "毛圈棉",
            },
            "style": {
                "type": "choice",
                "options": ["连帽", "圆领", "立领"],
                "default": "连帽",
            },
        },
        "prompt_templates": [
            "电商主图：{color}{material}{product}，{selling_point}，暖色背景，棚拍，"
            "商品居中，无文字无水印",
            "模特场景图：{color}{product}，{style}款，{selling_point}，休闲街拍，自然光，高清",
            "细节特写：{material}绒面质感与袖口螺纹，{color}，微距摄影，高清",
        ],
    },
    "sneaker": {
        "name": "运动鞋",
        "aliases": ["运动鞋", "球鞋", "跑鞋", "sneaker", "running shoes"],
        "brand": "StrideX",
        "product": "轻量运动鞋",
        "title_template": "{season}新款 {brand}{product} {selling_point}",
        "selling_points": ["轻若无物", "缓震回弹", "透气不闷脚"],
        "attribute_spec": {
            "color": {"type": "text", "default": "白灰"},
            "material": {
                "type": "choice",
                "options": ["飞织", "网布", "合成革"],
                "default": "飞织",
            },
            "use_case": {
                "type": "choice",
                "options": ["跑步", "通勤", "休闲"],
                "default": "跑步",
            },
        },
        "prompt_templates": [
            "电商主图：{color}{material}{product}，{selling_point}，浅灰背景，棚拍，"
            "45度侧视，无文字无水印",
            "模特场景图：{color}{product}，{use_case}场景，{selling_point}，动态抓拍，高清",
            "细节特写：{material}鞋面纹理与鞋底缓震结构，{color}，微距摄影，高清",
        ],
    },
}

# 属性字段中文名（供前端渲染属性编辑器）
ATTR_LABELS = {
    "color": "颜色",
    "material": "材质",
    "style": "版型",
    "fit": "版型",
    "length": "裙长",
    "use_case": "用途",
    "pattern": "图案",
    "fabric": "面料",
    "sleeve": "袖长",
    "rise": "腰型",
}

# 模拟后台下拉菜单与 Streamlit 类目选择共用，保证 RPA 可选到同一枚举
CATEGORY_OPTIONS = [rule["name"] for rule in CATEGORY_RULES.values()]

DEFAULT_CATEGORY_KEY = "tshirt"


def _norm(value: str) -> str:
    return (value or "").strip().lower().replace(" ", "")


def match_category(vision_category) -> str:
    """把 AI 返回的类目名归一化到规则库 key；匹配不到时回退默认类目。"""
    if vision_category:
        target = _norm(vision_category)
        for key, rule in CATEGORY_RULES.items():
            if target == _norm(rule["name"]) or any(
                target == _norm(alias) for alias in rule["aliases"]
            ):
                return key
    return DEFAULT_CATEGORY_KEY


def get_rule(category_key: str) -> dict:
    return CATEGORY_RULES.get(category_key, CATEGORY_RULES[DEFAULT_CATEGORY_KEY])


def get_rule_by_name(category_name: str) -> dict:
    for rule in CATEGORY_RULES.values():
        if rule["name"] == category_name:
            return rule
    return CATEGORY_RULES[DEFAULT_CATEGORY_KEY]


def resolve_attributes(rule: dict, vision_attrs: dict) -> dict:
    """属性白名单归一化：AI 值合法则采用，否则回退默认值。"""
    resolved = {}
    spec = rule["attribute_spec"]
    vision_attrs = vision_attrs or {}
    for key, meta in spec.items():
        value = vision_attrs.get(key)
        if meta["type"] == "choice":
            options = meta["options"]
            matched = next(
                (opt for opt in options if _norm(opt) == _norm(str(value or ""))), None
            )
            resolved[key] = matched or meta.get("default")
        else:
            raw = str(value).strip() if value else ""
            if raw:
                # 仅对 color 类自由文本做颜色归一化，避免语义错位
                resolved[key] = normalize_color(raw) if key == "color" else raw
            else:
                resolved[key] = meta.get("default", "")
    return resolved


def _safe_format(template: str, **kwargs) -> str:
    """宽松格式化：缺失占位符保持原样，避免单个字段异常拖垮整条流水线。"""
    result = template
    for key, value in kwargs.items():
        result = result.replace("{" + key + "}", str(value))
    return result


def build_title(rule: dict, season: str, attrs: dict, selling_point: str) -> str:
    return _safe_format(
        rule["title_template"],
        season=season,
        brand=rule["brand"],
        product=rule["product"],
        selling_point=selling_point,
    )


def build_prompts(rule: dict, attrs: dict, selling_point: str) -> list:
    prompts = []
    for template in rule["prompt_templates"]:
        prompts.append(
            _safe_format(
                template,
                product=rule["product"],
                selling_point=selling_point,
                **attrs,
            )
        )
    return prompts
