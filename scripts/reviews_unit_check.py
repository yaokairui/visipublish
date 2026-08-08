# -*- coding: utf-8 -*-
"""评价分析后端核心 · 单元检查
用法：.venv/Scripts/python.exe scripts/reviews_unit_check.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from reviews.backend.analyzer import create_analyzer
from reviews.backend.demo_data import generate_demo_reviews
from reviews.backend.pain_points import extract_pain_points, sentiment_summary
from reviews.backend.review_import import (
    import_excel,
    normalize_star,
    parse_pasted_text,
)

FAIL = []


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")
    if not cond:
        FAIL.append(name)


# 1. 星级归一
check("normalize_star 数字", normalize_star(5) == 5)
check("normalize_star 星号串", normalize_star("★★★★☆") == 4)
check("normalize_star emoji", normalize_star("⭐⭐⭐⭐") == 4)
check("normalize_star 文本", normalize_star("差评") == 1)
check("normalize_star 空", normalize_star("") == 3)
check("normalize_star 半值向上", normalize_star(4.5) == 5)
check("normalize_star 中文数字", normalize_star("五星") == 5)

# 2. 粘贴文本解析
rows, stats = parse_pasted_text("[1星] 物流太慢了\n[5星] 很好用\n一般般\n\n[2星] 色差严重")
check("粘贴解析条数", stats.valid_rows == 4, f"valid={stats.valid_rows}")
check("粘贴解析星级", rows[0].rating == 1 and rows[1].rating == 5 and rows[2].rating == 3)

# 3. Excel 导入（混合星级格式 + 空行 + 重复行）
excel_path = Path(__file__).resolve().parents[1] / "output" / "_review_test.xlsx"
pd.DataFrame([
    {"评价内容": "面料舒服，很满意", "星级": 5, "日期": "2026/7/1", "商品": "T恤"},
    {"评价内容": "物流太慢了，等了一周", "星级": 1, "日期": "2026/7/2", "商品": "T恤"},
    {"评价内容": "物流太慢了，等了一周", "星级": "★★", "日期": "2026/7/2", "商品": "T恤"},  # 重复
    {"评价内容": "", "星级": 3, "日期": "2026/7/3", "商品": "耳机"},  # 空内容
    {"评价内容": "有色差，偏小", "星级": "差评", "日期": "2026/7/4", "商品": "T恤"},
]).to_excel(excel_path, index=False)
rows2, stats2 = import_excel(excel_path)
check("Excel 导入有效行", stats2.valid_rows == 3, f"valid={stats2.valid_rows}, skipped={stats2.skipped_rows}")
check("Excel 星级归一", rows2[2].rating == 1, f"rows={[r.rating for r in rows2]}")

# 4. 情感分析（lexicon）
analyzer = create_analyzer("lexicon")
demo = generate_demo_reviews(160)
analyzed = []
for r in demo:
    res = analyzer.analyze(r["content"])
    analyzed.append({**r, "sentiment": res.sentiment, "score": res.score,
                     "confidence": res.confidence, "source": res.source})
summary = sentiment_summary(analyzed)
check("情感分析有结果", summary["total"] == 160, f"total={summary['total']}")
check("情感分布合理", summary["positive"] > 60 and summary["negative"] > 30,
      f"pos={summary['positive']}, neg={summary['negative']}")
check("情感中性样例", any(r["sentiment"] == "neutral" for r in analyzed))
check("差评判定样例", analyzer.analyze("物流太慢了，等了一周").sentiment == "negative")
check("好评判定样例", analyzer.analyze("面料很舒服，很满意，会回购").sentiment == "positive")
check("质量不好判负", analyzer.analyze("质量不好").sentiment == "negative")
check("尺寸太小判负", analyzer.analyze("衣服太小").sentiment == "negative")
check("没效果判负", analyzer.analyze("用了几次没效果").sentiment == "negative")
check("不油腻判正", analyzer.analyze("一点都不油腻").sentiment == "positive")

# 5. 痛点挖掘
pain = extract_pain_points(analyzed, top_n=10)
top_words = [p["word"] for p in pain]
print("    痛点词 Top10:", top_words)
check("痛点词非空", len(pain) > 0)
check("痛点含关键词", any(w in ("物流", "快递", "客服", "色差", "破损", "退货", "贵") for w in top_words))
check("痛点例句非空", all(p["examples"] for p in pain[:3]))

# 5b. spec 验收场景：物流类差评集中 → 快递/发货/慢 成为高权重痛点词
neg_logistics = [{"content": "快递太慢，发货也慢", "sentiment": "negative"} for _ in range(30)]
pos_normal = [{"content": "质量很好，面料舒服", "sentiment": "positive"} for _ in range(30)]
pain2 = extract_pain_points(neg_logistics + pos_normal, top_n=10)
top2 = [p["word"] for p in pain2]
print("    物流场景痛点 Top10:", top2)
check("物流场景含快递", "快递" in top2)
check("物流场景含发货", "发货" in top2)
check("物流场景含慢", ("慢" in top2) or ("太慢" in top2))

print("\n" + ("ALL CHECKS PASSED" if not FAIL else f"FAILED: {FAIL}"))
sys.exit(1 if FAIL else 0)
