"""FastAPI 后端：为 React 前端提供电商 AI 上架 API。

契约见 docs/web_api_contract.md。复用 src/ 全部业务逻辑：
识别 -> 规则生成 -> AI 标题 -> 批量审核 -> 渠道发布（后台线程 job）。

启动：python -m uvicorn webapp.main:app --port 8502
"""
import sys
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src import config  # noqa: E402
from src.batch import publish_batch  # noqa: E402
from src.channels import get_channel  # noqa: E402
from src.listing_generator import generate_listing, listing_payload_for_rpa  # noqa: E402
from src.placeholder import make_placeholder  # noqa: E402
from src.rules import (  # noqa: E402
    ATTR_LABELS,
    CATEGORY_OPTIONS,
    CATEGORY_RULES,
    get_rule,
    get_rule_by_name,
    resolve_attributes,
)
from src.title_ai import generate_ai_titles, resolve_title  # noqa: E402
from src.vision_client import analyze_image  # noqa: E402

app = FastAPI(title="VisiPublish Agent API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- 内存存储（单用户演示） ----------------
_SESSIONS: dict[str, dict] = {}  # session_id -> {"items": [Item]}
_JOBS: dict[str, dict] = {}      # job_id -> 发布任务状态
_CHANNEL = get_channel()

# ---------------- 工具 ----------------
def _make_placeholder_urls(item_id: str, prompts: list) -> list:
    for i, prompt in enumerate(prompts, start=1):
        out_dir = config.OUTPUT_DIR / "placeholders" / item_id
        make_placeholder(prompt, i, out_dir)
    return [f"/api/placeholders/{item_id}/{i}" for i in range(1, len(prompts) + 1)]


def _build_item(name: str, image_bytes: bytes, vision: dict) -> dict:
    listing = generate_listing(vision, 0)
    item_id = uuid.uuid4().hex[:12]
    item = {
        "id": item_id,
        "name": name or "未命名商品图",
        "status": "pending",
        "error": "",
        "selected": True,
        "category_key": listing["category_key"],
        "category": listing["category"],
        "attributes": listing["attributes"],
        "prompts": listing["prompts"],
        "ai_titles": [],
        "rule_title": listing["title"],
        "title_source": "rule",
        "manual_title": "",
        "title": listing["title"],
        "vision": vision,
        "placeholders": _make_placeholder_urls(item_id, listing["prompts"]),
        "rpa_result": None,
        "backend_id": None,
        "seed": 0,
        "season": listing["season"],
        "selling_point": listing["selling_point"],
        "listing": listing,
    }
    return item


def _skipped_item(name: str, error: str) -> dict:
    return {
        "id": uuid.uuid4().hex[:12],
        "name": name or "未命名商品图",
        "status": "skipped",
        "error": error,
        "selected": False,
        "category_key": None,
        "category": "",
        "attributes": {},
        "prompts": [],
        "ai_titles": [],
        "rule_title": "",
        "title_source": "rule",
        "manual_title": "",
        "title": "",
        "vision": None,
        "placeholders": [],
        "rpa_result": None,
        "backend_id": None,
        "seed": 0,
        "season": "",
        "selling_point": "",
        "listing": None,
    }


def _refresh_title(item: dict) -> None:
    item["title"] = resolve_title(
        item.get("title_source", "rule"),
        item.get("ai_titles") or [],
        item.get("rule_title", ""),
        item.get("manual_title", ""),
    )


def _build_payload(item: dict) -> dict:
    """从审核后的 item 构造渠道 payload（复用规则库契约，避免重复）。"""
    listing = dict(item.get("listing") or {})
    rule = get_rule_by_name(item["category"])
    listing.update(
        {
            "title": item.get("title", ""),
            "category": item["category"],
            "attributes": item.get("attributes") or {},
            "prompts": item.get("prompts") or [],
            "brand": rule["brand"],
            "season": item.get("season", listing.get("season", "")),
            "selling_point": item.get("selling_point", listing.get("selling_point", "")),
        }
    )
    return listing_payload_for_rpa(listing)


def _get_session(header: str) -> dict:
    if not header:
        raise HTTPException(status_code=400, detail="缺少 X-Session-Id 请求头")
    sess = _SESSIONS.get(header)
    if sess is None:
        raise HTTPException(status_code=404, detail="会话不存在，请刷新页面重新创建")
    return sess


def _find_item(sess: dict, item_id: str) -> dict:
    item = next((it for it in sess["items"] if it["id"] == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="商品条目不存在")
    return item


# ---------------- 会话 ----------------
@app.post("/api/session")
def create_session():
    sid = uuid.uuid4().hex
    _SESSIONS[sid] = {"items": []}
    return {"session_id": sid}


@app.delete("/api/session")
def clear_session(x_session_id: str = Header(default="", alias="X-Session-Id")):
    _SESSIONS.pop(x_session_id, None)
    return {"ok": True}


# ---------------- 配置 ----------------
@app.get("/api/config")
def get_config():
    return {
        "vision_configured": bool(config.VISION_API_KEY),
        "vision_model": config.VISION_MODEL,
        "channel": _CHANNEL.name,
        "mock_backend_url": config.MOCK_BACKEND_URL,
        "rpa_headless": config.RPA_HEADLESS,
        "batch_limit": config.BATCH_IMAGE_LIMIT,
        "ai_title_count": config.AI_TITLE_COUNT,
        "title_max_len": config.TITLE_MAX_LEN,
        "categories": CATEGORY_OPTIONS,
        "category_rules": [
            {"name": rule["name"], "attribute_spec": rule["attribute_spec"]}
            for rule in CATEGORY_RULES.values()
        ],
        "attribute_labels": ATTR_LABELS,
    }


# ---------------- 商品条目 ----------------
@app.get("/api/items")
def list_items(x_session_id: str = Header(default="", alias="X-Session-Id")):
    sess = _get_session(x_session_id)
    return {"items": sess["items"]}


@app.post("/api/generate")
async def generate_items(
    files: list[UploadFile] = File(...),
    x_session_id: str = Header(default="", alias="X-Session-Id"),
):
    sess = _get_session(x_session_id)
    picked = files[: config.BATCH_IMAGE_LIMIT]
    items = []
    for f in picked:
        data = await f.read()
        try:
            vision = analyze_image(data)
            item = _build_item(f.filename, data, vision)
            if config.VISION_API_KEY and item.get("listing"):
                rule = get_rule(item["category_key"])
                item["ai_titles"] = generate_ai_titles(data, vision, rule)
            item["title_source"] = "ai-1" if item["ai_titles"] else "rule"
            _refresh_title(item)
        except Exception as exc:  # 单张失败不中断整批
            item = _skipped_item(f.filename, str(exc))
        items.append(item)
    sess["items"] = items
    return {"items": items}


class ReviewBody(BaseModel):
    title_source: str = "rule"
    manual_title: str = ""
    category: str = ""
    attributes: dict = {}
    prompts: list[str] = []
    selected: bool = True


@app.post("/api/items/{item_id}/review")
def review_item(
    item_id: str,
    body: ReviewBody,
    x_session_id: str = Header(default="", alias="X-Session-Id"),
):
    sess = _get_session(x_session_id)
    item = _find_item(sess, item_id)
    if item.get("status") == "skipped" or not item.get("listing"):
        raise HTTPException(status_code=400, detail="该条目生成失败，无法编辑")

    category = body.category or item["category"]
    rule = get_rule_by_name(category)
    item["category_key"] = rule["name"] if rule["name"] == category else item["category_key"]
    item["category"] = rule["name"]
    item["attributes"] = resolve_attributes(rule, body.attributes or item["attributes"])
    item["prompts"] = body.prompts or item["prompts"]
    item["title_source"] = (
        body.title_source
        if body.title_source in ("ai-1", "ai-2", "ai-3", "rule", "manual")
        else "rule"
    )
    item["manual_title"] = body.manual_title or ""
    item["selected"] = bool(body.selected)
    _refresh_title(item)
    return {"item": item}


@app.post("/api/items/{item_id}/regen")
def regen_item(
    item_id: str,
    x_session_id: str = Header(default="", alias="X-Session-Id"),
):
    sess = _get_session(x_session_id)
    item = _find_item(sess, item_id)
    if item.get("status") == "skipped" or not item.get("listing"):
        raise HTTPException(status_code=400, detail="该条目生成失败，无法重新生成")
    item["seed"] = item.get("seed", 0) + 1
    listing = generate_listing(item["vision"], item["seed"])
    item["rule_title"] = listing["title"]
    item["season"] = listing["season"]
    item["selling_point"] = listing["selling_point"]
    item["listing"] = listing
    item["status"] = "pending"
    item["error"] = ""
    _refresh_title(item)
    return {"item": item}


@app.post("/api/items/{item_id}/delist")
def delist_item(
    item_id: str,
    x_session_id: str = Header(default="", alias="X-Session-Id"),
):
    sess = _get_session(x_session_id)
    item = _find_item(sess, item_id)
    res = _CHANNEL.publish_off({"backend_id": item.get("backend_id")})
    if res.success:
        item["status"] = "delisted"
    return {"ok": res.success, "message": res.message}


@app.get("/api/placeholders/{item_id}/{index}")
def placeholder_image(item_id: str, index: int):
    path = config.OUTPUT_DIR / "placeholders" / item_id / f"placeholder_{index}.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail="占位图不存在")
    return FileResponse(path, media_type="image/png")


@app.get("/api/rpa_screenshot/{filename}")
def rpa_screenshot(filename: str):
    safe = Path(filename).name
    path = config.OUTPUT_DIR / "screenshots" / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="截图不存在")
    return FileResponse(path, media_type="image/png")


# ---------------- 批量发布（后台线程 + 轮询） ----------------
class PublishBody(BaseModel):
    item_ids: list[str] = []


@app.post("/api/publish")
def publish_items(
    body: PublishBody,
    x_session_id: str = Header(default="", alias="X-Session-Id"),
):
    sess = _get_session(x_session_id)
    ready, message = _CHANNEL.check_ready()
    if not ready:
        raise HTTPException(status_code=400, detail=f"渠道不可用：{message}")

    targets = [
        it
        for it in sess["items"]
        if it["id"] in body.item_ids
        and it["status"] not in ("success", "delisted", "skipped")
    ]
    if not targets:
        raise HTTPException(status_code=400, detail="没有可上架的勾选项")

    for it in targets:
        it["payload"] = _build_payload(it)

    job_id = uuid.uuid4().hex[:12]
    job = {
        "running": True,
        "total": len(targets),
        "success": 0,
        "failed": 0,
        "error": "",
        "items": targets,
    }
    _JOBS[job_id] = job

    def _run():
        try:
            summary = publish_batch(_CHANNEL, targets)
            job["success"] = summary["success"]
            job["failed"] = summary["failed"]
        except Exception as exc:  # 整体兜底，避免线程静默死亡
            job["error"] = str(exc)
            job["failed"] = len(targets) - job.get("success", 0)
        finally:
            job["running"] = False

    threading.Thread(target=_run, daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/publish/{job_id}")
def publish_status(job_id: str):
    job = _JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {
        "running": job["running"],
        "total": job["total"],
        "success": job["success"],
        "failed": job["failed"],
        "error": job.get("error", ""),
        "items": [
            {
                "id": it["id"],
                "status": it["status"],
                "error": it.get("error", ""),
                "message": (it.get("rpa_result") or {}).get("message", "")
                or it.get("error", ""),
                "title": it.get("title", ""),
            }
            for it in job["items"]
        ],
    }


# ---------------- 静态托管（前端构建产物） ----------------
_DIST = BASE_DIR / "frontend" / "dist"
if (_DIST / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="frontend")


@app.get("/")
def root():
    return {"app": "VisiPublish Agent API", "docs": "/docs", "contract": "docs/web_api_contract.md"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("webapp.main:app", host=config.WEB_HOST, port=config.WEB_PORT, reload=False)
