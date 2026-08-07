"""
端到端冒烟测试：启动模拟后台 -> 构造商品数据 -> MockChannel(Playwright RPA) 自动上架
-> 校验后台记录落盘 -> 幂等去重 -> 下架。
运行：.venv/Scripts/python scripts/smoke_test.py
"""
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.channels.mock_channel import (  # noqa: E402
    SELECTORS,
    MockChannel,
    check_backend_health,
)
from src.config import MOCK_BACKEND_URL  # noqa: E402
from src.listing_generator import listing_payload_for_rpa  # noqa: E402

BACKEND_DATA = BASE_DIR / "mock_backend" / "submissions.json"


def wait_health(url: str, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if check_backend_health(url):
            return True
        time.sleep(0.5)
    return False


def build_payload(idempotency_key: str) -> dict:
    payload = listing_payload_for_rpa(
        {
            "title": "夏季新款 CloudWear纯色T恤 透气舒适",
            "category": "T恤",
            "attributes": {"color": "白色", "material": "纯棉", "style": "基础款"},
            "prompts": ["prompt A", "prompt B", "prompt C"],
            "brand": "CloudWear",
            "season": "夏季",
            "selling_point": "透气舒适",
        }
    )
    payload["idempotency_key"] = idempotency_key
    return payload


def main() -> int:
    backend = subprocess.Popen(
        [sys.executable, "-m", "mock_backend.server"],
        cwd=str(BASE_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_health(MOCK_BACKEND_URL):
            print("FAIL: 模拟后台未在 15s 内启动")
            return 1
        print("PASS: 模拟后台已启动", MOCK_BACKEND_URL)

        # 契约校验：RPA 选择器必须与后台模板的 id 一致，防止改模板后 RPA 静默失效
        page_html = requests.get(MOCK_BACKEND_URL + "/", timeout=5).text
        form_selectors = [v for k, v in SELECTORS.items() if k != "success"]
        missing = [v for v in form_selectors if f'id="{v[1:]}"' not in page_html]
        if missing:
            print("FAIL: 后台页面缺少 RPA 选择器:", missing)
            return 1
        print("PASS: RPA 选择器与后台模板一致")

        before = (
            len(json.loads(BACKEND_DATA.read_text(encoding="utf-8")))
            if BACKEND_DATA.exists()
            else 0
        )

        channel = MockChannel(backend_url=MOCK_BACKEND_URL, headless=True)
        key = f"smoke-{uuid.uuid4().hex[:10]}"
        payload = build_payload(key)
        result = channel.publish(payload)
        for step in result.steps:
            print("  step:", step)
        if not result.success:
            print("FAIL: RPA 上架失败 ->", result.message)
            return 1
        print("PASS: RPA 上架成功 ->", result.message)
        if not result.screenshot or not Path(result.screenshot).exists():
            print("WARN: 截图未生成")
        else:
            print("PASS: 截图已生成", result.screenshot)

        records = json.loads(BACKEND_DATA.read_text(encoding="utf-8"))
        if len(records) != before + 1:
            print(f"FAIL: 后台记录数 {before} -> {len(records)}，应为 +1")
            return 1
        last = records[-1]
        ok = (
            last["title"] == payload["title"]
            and last["category"] == payload["category"]
            and "白色" in last["attributes"]
            and last.get("status") == "listed"
            and last.get("idempotency_key") == key
        )
        print("PASS: 后台记录已落盘（含 status/idempotency_key）" if ok else "FAIL: 后台记录内容不符", json.dumps(last, ensure_ascii=False))
        if not ok:
            return 1

        # 幂等：同键再发一次，不应新增记录
        dup = channel.publish(build_payload(key))
        if not dup.success:
            print("FAIL: 幂等重发失败 ->", dup.message)
            return 1
        records2 = json.loads(BACKEND_DATA.read_text(encoding="utf-8"))
        if len(records2) != before + 1:
            print(f"FAIL: 幂等重发后记录数变化 {len(records2)}，应仍为 {before + 1}")
            return 1
        print("PASS: 幂等重发未产生重复记录")

        # 下架
        backend_id = (result.extra or {}).get("record_id") or last["id"]
        off = channel.publish_off({"backend_id": backend_id})
        if not off.success:
            print("FAIL: 下架失败 ->", off.message)
            return 1
        records3 = json.loads(BACKEND_DATA.read_text(encoding="utf-8"))
        target = next((r for r in records3 if r["id"] == backend_id), None)
        if not target or target.get("status") != "delisted":
            print("FAIL: 下架后记录状态未更新")
            return 1
        print("PASS: 下架成功，记录状态 -> delisted")
        return 0
    finally:
        backend.terminate()
        backend.wait(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())