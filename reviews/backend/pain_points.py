"""差评痛点挖掘（pain-point-mining）。

jieba 分词 + 停用词 → 好评/差评分组 TF-IDF 对比 → 痛点词 TopN + 例句。
纯 Python 实现，不依赖 sklearn。
"""

from __future__ import annotations

import math
import random
from collections import Counter

import jieba

from .analyzer import ReviewResult

# 通用停用词 + 电商常用噪音词
STOPWORDS = {
    "的", "了", "是", "在", "我", "也", "都", "就", "很", "太", "有", "和", "与",
    "这", "那", "个", "不", "没", "还", "又", "再", "就", "但", "而", "却", "被",
    "把", "让", "给", "对", "比", "从", "到", "于", "及", "或", "等", "啊", "呢",
    "吧", "吗", "哦", "哈", "呀", "啦", "么", "东西", "商品", "产品", "这个", "那个",
    "一下", "感觉", "觉得", "有点", "真的", "其实", "总之", "整体", "比较", "非常",
    "特别", "已经", "还是", "而且", "然后", "因为", "所以", "不过", "但是", "虽然",
    "今天", "昨天", "现在", "时候", "我们", "你们", "他们", "人家", "自己", "什么",
    "怎么", "为什么", "是不是", "有没有", "一个", "一次", "一件", "一样", "可以",
    "应该", "需要", "要求", "建议", "希望", "结果", "情况", "问题", "一", "用", "图片", "照片",
    "卖家", "商家", "店铺", "下单", "收到", "买了", "用了",
    "就是", "一般", "没有", "也是", "还是", "竟然", "居然",
}


def _tokenize(content: str) -> list[str]:
    words = []
    for w in jieba.lcut(content):
        w = w.strip()
        # 不按长度过滤：保留「慢」「贵」等单字痛点词，噪音由 STOPWORDS 控制
        if w in STOPWORDS or not w.isalnum():
            continue
        words.append(w)
    return words


def extract_pain_points(
    reviews: list[dict],
    top_n: int = 20,
    min_docs: int = 2,
    seed: int = 42,
) -> list[dict]:
    """reviews: [{"content": str, "sentiment": str, "product": str, "platform": str, ...}]
    返回按权重降序的痛点词列表：[{"word", "weight", "neg_docs", "examples": [...]}]。
    """
    neg_docs: list[set[str]] = []  # 每条差评的词集合
    neg_tokens: list[str] = []
    pos_docs: list[set[str]] = []
    pos_tokens: list[str] = []

    for r in reviews:
        words = _tokenize(str(r.get("content", "")))
        if not words:
            continue
        if r.get("sentiment") == "negative":
            neg_docs.append(set(words))
            neg_tokens.extend(words)
        elif r.get("sentiment") == "positive":
            pos_docs.append(set(words))
            pos_tokens.extend(words)

    if not neg_docs or not pos_docs:
        return []

    total_neg_tokens = max(1, len(neg_tokens))
    total_pos_docs = max(1, len(pos_docs))
    neg_count = Counter(neg_tokens)
    pos_doc_count = Counter(w for doc in pos_docs for w in doc)

    rng = random.Random(seed)
    pain = []
    for word, tf in neg_count.items():
        neg_doc_freq = sum(1 for doc in neg_docs if word in doc)
        if neg_doc_freq < min_docs:
            continue
        tf_score = tf / total_neg_tokens
        # 在好评中越罕见、权重越高 → 差评特有的痛点
        idf_score = math.log1p(total_pos_docs / (1 + pos_doc_count.get(word, 0)))
        weight = tf_score * idf_score
        examples = [r["content"] for r in reviews
                    if r.get("sentiment") == "negative" and word in str(r.get("content", ""))]
        pain.append({
            "word": word,
            "weight": round(weight, 6),
            "neg_docs": neg_doc_freq,
            "examples": rng.sample(examples, min(3, len(examples))),
        })

    pain.sort(key=lambda x: x["weight"], reverse=True)
    return pain[:top_n]


def dimension_stats(reviews: list[dict]) -> list[dict]:
    """llm 维度标签聚合（v1.5）：labels 字段统计。"""
    counter: Counter = Counter()
    total = 0
    for r in reviews:
        for label in r.get("labels") or []:
            counter[label] += 1
            total += 1
    return [
        {"dimension": dim, "count": cnt, "pct": round(cnt / total * 100, 1) if total else 0}
        for dim, cnt in counter.most_common()
    ]


def sentiment_summary(reviews: list[dict]) -> dict:
    """全局摘要：总条数 / 好评率 / 差评率 / 平均星级。"""
    total = len(reviews)
    if not total:
        return {"total": 0, "positive": 0, "negative": 0, "neutral": 0,
                "positive_rate": 0, "negative_rate": 0, "avg_rating": 0}
    c = Counter(r.get("sentiment") for r in reviews)
    avg_rating = sum(float(r.get("rating") or 0) for r in reviews) / total
    return {
        "total": total,
        "positive": c.get("positive", 0),
        "negative": c.get("negative", 0),
        "neutral": c.get("neutral", 0),
        "positive_rate": round(c.get("positive", 0) / total * 100, 1),
        "negative_rate": round(c.get("negative", 0) / total * 100, 1),
        "avg_rating": round(avg_rating, 2),
    }
