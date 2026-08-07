"""
本地模拟电商后台（供 Playwright RPA 测试用）
============================================
一个极简 Flask 应用：
- GET  /            商品上架表单（标题 / 类目下拉 / 属性 / 提交按钮）
- POST /submit      接收表单并落盘到 submissions.json
- POST /delist      按 item_id 下架记录（status -> delisted）
- GET  /success     上架成功页（含 #success-banner 供 RPA 断言）
- GET  /submissions 已上架记录列表（演示 RPA 成果）
- GET  /health      探活接口

启动：python -m mock_backend.server
"""
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for

# 保证从仓库根目录运行也能导入 src 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import MOCK_BACKEND_HOST, MOCK_BACKEND_PORT  # noqa: E402
from src.rules import CATEGORY_OPTIONS  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "submissions.json"

app = Flask(__name__)


def load_submissions() -> list:
    if not DATA_FILE.exists():
        return []
    try:
        records = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    # 旧记录无 status 字段时，按 "listed"（已上架）兼容
    for record in records:
        record.setdefault("status", "listed")
    return records


def write_submissions(records: list) -> None:
    """把整份记录列表写回 submissions.json（沿用现有 JSON 落盘方式）。"""
    DATA_FILE.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def save_submission(record: dict) -> dict:
    records = load_submissions()
    record["id"] = uuid.uuid4().hex[:12]
    record["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    record.setdefault("status", "listed")
    records.append(record)
    write_submissions(records)
    return record


@app.route("/")
def index():
    return render_template("index.html", categories=CATEGORY_OPTIONS)


@app.route("/submit", methods=["POST"])
def submit():
    title = (request.form.get("title") or "").strip()
    category = (request.form.get("category") or "").strip()
    attributes = (request.form.get("attributes") or "").strip()
    sku = (request.form.get("sku") or "").strip()
    idempotency_key = (request.form.get("idempotency_key") or "").strip()
    if not title or not category:
        return render_template(
            "index.html",
            categories=CATEGORY_OPTIONS,
            error="标题和类目为必填项",
        ), 400
    # 幂等：同一 idempotency_key 已存在时，不重复落盘，直接跳转到既有记录
    if idempotency_key:
        existing = next(
            (
                r
                for r in load_submissions()
                if r.get("idempotency_key") == idempotency_key
            ),
            None,
        )
        if existing:
            return redirect(url_for("success", sid=existing["id"]))
    record_data = {
        "title": title,
        "category": category,
        "attributes": attributes,
        "sku": sku,
    }
    if idempotency_key:
        record_data["idempotency_key"] = idempotency_key
    record = save_submission(record_data)
    return redirect(url_for("success", sid=record["id"]))


@app.route("/delist", methods=["POST"])
def delist():
    item_id = (request.form.get("item_id") or "").strip()
    records = load_submissions()
    record = next((r for r in records if r["id"] == item_id), None)
    if not record:
        return {"ok": False}, 404
    record["status"] = "delisted"
    write_submissions(records)
    return {"ok": True, "status": "delisted", "id": item_id}


@app.route("/success")
def success():
    sid = request.args.get("sid", "")
    record = next((r for r in load_submissions() if r["id"] == sid), None)
    if not record:
        return "记录不存在", 404
    return render_template("success.html", record=record)


@app.route("/submissions")
def submissions():
    return render_template("submissions.html", records=reversed(load_submissions()))


@app.route("/health")
def health():
    return {"ok": True, "app": "mock-ecommerce-backend"}


if __name__ == "__main__":
    print(f"模拟电商后台已启动：http://{MOCK_BACKEND_HOST}:{MOCK_BACKEND_PORT}")
    app.run(host=MOCK_BACKEND_HOST, port=MOCK_BACKEND_PORT, debug=False)
