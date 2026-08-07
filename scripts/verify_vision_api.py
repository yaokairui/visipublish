"""
Vision API 实测验证（当前 .env 配置为 agnes-2.5-flash）
运行：.venv\\Scripts\\python scripts\\verify_vision_api.py
"""
import io
import sys
from pathlib import Path

from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import VISION_API_KEY, VISION_MODEL  # noqa: E402
from src.listing_generator import generate_listing  # noqa: E402
from src.rules import CATEGORY_OPTIONS, normalize_color  # noqa: E402
from src.vision_client import analyze_image  # noqa: E402


def main() -> int:
    if not VISION_API_KEY:
        print("VISION_API_KEY 未配置：本脚本用于真实网关实测，跳过。")
        return 0

    # 生成一张纯色测试图（红色）
    img = Image.new("RGB", (600, 800), (220, 40, 40))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    print(f"调用真实 Vision API（model={VISION_MODEL}）...")
    vision = analyze_image(buf.getvalue())
    print("识别结果:", vision)

    assert set(("category", "color", "material", "style")) <= set(vision), (
        "返回缺少目标字段"
    )
    assert vision["source"] == "api", f"应走真实 API，实际 {vision['source']}"

    listing = generate_listing(vision, seed=0)
    print("规则命中类目:", listing["category"])
    print("生成标题:", listing["title"])
    print("属性:", listing["attributes"])

    # 类目必须归一化到规则库枚举；英文颜色必须归一化为中文
    assert listing["category"] in CATEGORY_OPTIONS, listing["category"]
    assert normalize_color(vision["color"]) == listing["attributes"]["color"], (
        "颜色未归一化"
    )

    # AI 标题生成实测（含类目曝光关键词）
    from src.rules import get_rule  # noqa: E402
    from src.title_ai import generate_ai_titles  # noqa: E402

    rule = get_rule(listing["category_key"])
    ai_titles = generate_ai_titles(buf.getvalue(), vision, rule)
    print("AI 标题候选:", ai_titles)
    assert ai_titles, "AI 标题生成应返回候选（可能 API 失败，请检查网络/Key）"
    assert all(len(t) <= 60 for t in ai_titles), "存在超长标题"
    print("PASS: agnes-2.5-flash 实测通过（识别 + AI 标题），输出可被规则库安全消费")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())