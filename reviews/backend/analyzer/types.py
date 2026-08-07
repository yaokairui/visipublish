"""analyzer 公共类型。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ReviewResult:
    sentiment: str  # positive | negative | neutral
    score: float = 0.0  # 0-1，越高越正向
    confidence: float = 0.0
    source: str = "lexicon"  # 实际使用的分析实现
    labels: list[str] = field(default_factory=list)  # 维度标签（llm 模式）
