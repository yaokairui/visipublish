"""情感分析 analyzer 工厂（sentiment-analysis）。

契约：analyze(text) -> ReviewResult
实现：lexicon（默认，离线）｜ huggingface / llm（可选，v1.5 再落地）
"""

from __future__ import annotations

import os

from .lexicon import LexiconAnalyzer
from .types import ReviewResult

__all__ = ["ReviewResult", "LexiconAnalyzer", "create_analyzer"]


def create_analyzer(name: str | None = None) -> LexiconAnalyzer:
    """按 ANALYZER 环境变量（默认 lexicon）创建 analyzer。"""
    selected = (name or os.getenv("ANALYZER", "lexicon")).strip().lower()
    if selected == "lexicon":
        return LexiconAnalyzer()
    if selected in ("huggingface", "llm"):
        raise NotImplementedError(
            f"analyzer 实现「{selected}」为可选能力，v1 暂未落地；请使用默认 lexicon。"
        )
    raise ValueError(f"未知 analyzer：{selected}（可选：lexicon）")
