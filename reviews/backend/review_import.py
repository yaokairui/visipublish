"""评价数据导入与标准化（review-import）。

支持：商家后台导出的 Excel/CSV、粘贴文本（每行一条，可选 [N星] 前缀）。
输出统一行结构：{content, rating, date, product, platform, shop}
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


# 列名别名（键为规范字段，值为可接受的中/英文列名）
COLUMN_ALIASES: dict[str, list[str]] = {
    "content": ["评价内容", "评论内容", "content", "comment", "text", "评价", "评论"],
    "rating": ["星级", "评分", "rating", "star", "stars", "score"],
    "date": ["日期", "评价时间", "date", "time", "created_at", "评论时间"],
    "product": ["商品", "商品名称", "product", "sku", "商品标题", "宝贝"],
    "platform": ["平台", "platform", "渠道", "channel"],
    "shop": ["店铺", "店名", "shop", "store"],
}

DEFAULT_VALUES = {"platform": "未知平台", "shop": "未知店铺", "product": "未命名商品"}


@dataclass
class ImportStats:
    raw_rows: int = 0
    valid_rows: int = 0
    skipped_rows: int = 0
    note: str = ""


@dataclass
class ReviewRow:
    content: str
    rating: int = 3
    date: str = ""
    product: str = ""
    platform: str = ""
    shop: str = ""

    def dedup_key(self) -> str:
        return f"{self.content}|{self.date}|{self.product}"


def normalize_star(value) -> int:
    """把各种星级形态归一为 1-5 整数，无法识别时按 3。"""
    if value is None or (isinstance(value, str) and not value.strip()):
        return 3
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return 3
        return max(1, min(5, int(round(value))))
    s = str(value).strip()
    if re.fullmatch(r"[★☆*]{1,5}", s) or re.fullmatch(r"[⭐]{1,5}", s):
        return max(1, min(5, s.count("★") or s.count("⭐")))
    m = re.search(r"(\d(?:\.\d)?)", s)
    if m:
        return max(1, min(5, int(round(float(m.group(1))))))
    if "好评" in s or "满意" in s:
        return 5
    if "中评" in s or "一般" in s:
        return 3
    if "差评" in s or "不满意" in s:
        return 1
    return 3


def _match_column(header: str) -> str | None:
    key = re.sub(r"[\s_\-（）()]", "", str(header)).lower()
    for field_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if key == re.sub(r"[\s_\-（）()]", "", alias).lower():
                return field_name
    return None


def _clean_str(value, default: str = "") -> str:
    """把单元格值安全转字符串：None / NaN / 'nan' / 'None' 都按默认值处理。"""
    if value is None:
        return default
    if isinstance(value, float) and pd.isna(value):
        return default
    s = str(value).strip()
    if s.lower() in ("nan", "none", "null"):
        return default
    return s


def _map_row(raw: dict) -> ReviewRow | None:
    content = _clean_str(raw.get("content"))
    if not content:
        return None
    return ReviewRow(
        content=content,
        rating=normalize_star(raw.get("rating")),
        date=_clean_str(raw.get("date")),
        product=_clean_str(raw.get("product"), DEFAULT_VALUES["product"]),
        platform=_clean_str(raw.get("platform"), DEFAULT_VALUES["platform"]),
        shop=_clean_str(raw.get("shop"), DEFAULT_VALUES["shop"]),
    )


def import_frame(df: pd.DataFrame) -> tuple[list[ReviewRow], ImportStats]:
    """把 pandas DataFrame（首行为表头）映射为 ReviewRow 列表。"""
    if df is None or df.empty:
        return [], ImportStats(note="表格为空")
    mapping = {}
    for col in df.columns:
        f = _match_column(str(col))
        if f and f not in mapping:
            mapping[f] = col
    if "content" not in mapping:
        return [], ImportStats(note="缺少必需列：未找到可识别的「评价内容」列")

    stats = ImportStats(raw_rows=len(df))
    rows: list[ReviewRow] = []
    seen: set[str] = set()
    for _, raw in df.iterrows():
        mapped = {f: raw[col] for f, col in mapping.items()}
        row = _map_row(mapped)
        if row is None:
            stats.skipped_rows += 1
            continue
        key = row.dedup_key()
        if key in seen:
            stats.skipped_rows += 1
            continue
        seen.add(key)
        rows.append(row)
    stats.valid_rows = len(rows)
    return rows, stats


def import_excel(path: str | Path) -> tuple[list[ReviewRow], ImportStats]:
    """读取 .xlsx（openpyxl）/.xls（xlrd，需 pip install xlrd）。"""
    try:
        df = pd.read_excel(path, engine="openpyxl", dtype=object)
    except Exception:
        try:
            df = pd.read_excel(path, engine="xlrd", dtype=object)
        except Exception as e:
            raise ValueError(
                "无法读取 Excel（仅支持 .xlsx；旧版 .xls 需安装 xlrd：pip install xlrd）"
            ) from e
    return import_frame(df)


def import_csv(path: str | Path) -> tuple[list[ReviewRow], ImportStats]:
    """读取 .csv（自动探测编码：utf-8-sig / gbk）。"""
    last_err: Exception | None = None
    for encoding in ("utf-8-sig", "gbk", "utf-8"):
        try:
            df = pd.read_csv(path, encoding=encoding, dtype=object)
            return import_frame(df)
        except (UnicodeDecodeError, csv.Error) as e:
            last_err = e
    raise last_err or ValueError("无法解析 CSV 文件")


LINE_PREFIX = re.compile(r"^\s*\[?\s*(\d+(?:\.\d+)?)\s*星?\]?\s*[:：]?\s*(.*)$")


def parse_pasted_text(text: str) -> tuple[list[ReviewRow], ImportStats]:
    """粘贴文本：每行一条评价，可选 [N星] / N星 / 星级：N 前缀。"""
    stats = ImportStats()
    rows: list[ReviewRow] = []
    seen: set[str] = set()
    for line in io.StringIO(text):
        line = line.strip()
        if not line:
            continue
        stats.raw_rows += 1
        rating = 3
        content = line
        m = LINE_PREFIX.match(line)
        if m:
            rating = max(1, min(5, int(round(float(m.group(1))))))
            content = m.group(2).strip()
        if not content:
            stats.skipped_rows += 1
            continue
        row = ReviewRow(content=content, rating=rating)
        key = row.dedup_key()
        if key in seen:
            stats.skipped_rows += 1
            continue
        seen.add(key)
        rows.append(row)
    stats.valid_rows = len(rows)
    return rows, stats
