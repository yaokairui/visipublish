"""
Pillow 占位图生成：不调用生图 API，用颜色方块 + 提示词摘要模拟「AI 生图结果」。
颜色由提示词内容 hash 决定，同一提示词每次生成的颜色稳定。
"""
import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = (768, 768)

_CJK_FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/msyh.ttc"),      # 微软雅黑
    Path("C:/Windows/Fonts/msyhbd.ttc"),
    Path("C:/Windows/Fonts/simhei.ttf"),     # 黑体
    Path("C:/Windows/Fonts/simsun.ttc"),     # 宋体
    Path("/System/Library/Fonts/PingFang.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
]


def _load_font(size: int):
    for path in _CJK_FONT_CANDIDATES:
        try:
            if path.exists():
                return ImageFont.truetype(str(path), size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _palette_from_seed(seed_text: str) -> tuple:
    digest = hashlib.sha256(seed_text.encode("utf-8")).digest()
    hue = digest[0] / 255.0
    sat = 0.35 + (digest[1] / 255.0) * 0.45
    light = 0.45 + (digest[2] / 255.0) * 0.30
    from colorsys import hls_to_rgb

    r, g, b = hls_to_rgb(hue, light, sat)
    return (int(r * 255), int(g * 255), int(b * 255))


def _wrap_text(draw, text, font, max_width):
    lines, current = [], ""
    for char in text:
        if draw.textlength(current + char, font=font) <= max_width:
            current += char
        else:
            lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines


def make_placeholder(
    prompt_text: str,
    index: int,
    out_dir: Path,
    size: tuple = SIZE,
    label: str = "AI 生图占位图",
) -> Path:
    """生成一张渐变色占位图，图上叠加提示词摘要，返回图片路径。"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    width, height = size
    base_color = _palette_from_seed(prompt_text)
    lighter = tuple(min(255, c + 40) for c in base_color)
    darker = tuple(max(0, c - 60) for c in base_color)

    img = Image.new("RGB", (width, height), base_color)
    draw = ImageDraw.Draw(img)
    # 上下渐变色块，让「占位图」看起来更有设计感
    for y in range(height):
        t = y / height
        color = tuple(int(darker[i] + (lighter[i] - darker[i]) * t) for i in range(3))
        draw.line([(0, y), (width, y)], fill=color)

    # 中央白色信息卡
    card = Image.new("RGBA", (width - 160, height - 160), (255, 255, 255, 230))
    img.paste(card, (80, 80), card)

    title_font = _load_font(44)
    body_font = _load_font(30)
    small_font = _load_font(26)

    text_x = 120
    text_y = 130
    draw.text((text_x, text_y), f"{label} #{index}", font=title_font, fill=(40, 40, 40))
    text_y += 90

    max_width = width - 240
    for line in _wrap_text(draw, prompt_text, body_font, max_width):
        draw.text((text_x, text_y), line, font=body_font, fill=(70, 70, 70))
        text_y += 48
        if text_y > height - 120:
            break

    draw.text(
        (text_x, height - 110),
        "提示词摘要（未调用生图 API）",
        font=small_font,
        fill=(120, 120, 120),
    )

    path = out_dir / f"placeholder_{index}.png"
    img.save(path, "PNG")
    return path
