"""
UI 全流程测试（React + FastAPI 新前端）：启动模拟后台 + Web 服务，
用 Playwright 模拟真实用户操作：批量上传 2 张图片 -> 开始生成
-> 审核队列出现 -> 批量上架 -> 校验后台记录 +2。
运行：.venv/Scripts/python scripts/ui_test.py
"""
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

WEB_PORT = 8502
WEB_URL = f"http://127.0.0.1:{WEB_PORT}"
BACKEND_DATA = BASE_DIR / "mock_backend" / "submissions.json"
BACKEND_URL = "http://127.0.0.1:8010"


def wait_url(url: str, timeout: float = 40.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(url, timeout=1).status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def make_test_image(color: tuple) -> bytes:
    img = Image.new("RGB", (600, 800), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def main() -> int:
    env = {**os.environ, "RPA_HEADLESS": "true"}
    backend = subprocess.Popen(
        [sys.executable, "-m", "mock_backend.server"],
        cwd=str(BASE_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env=env,
    )
    webapp = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "webapp.main:app", "--port", str(WEB_PORT)],
        cwd=str(BASE_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env=env,
    )
    try:
        if not wait_url(BACKEND_URL + "/health"):
            print("FAIL: 模拟后台未启动"); return 1
        if not wait_url(WEB_URL + "/api/config"):
            print("FAIL: Web 服务未启动"); return 1
        print("PASS: 模拟后台 + Web 服务均已启动")

        before = len(json.loads(BACKEND_DATA.read_text(encoding="utf-8"))) if BACKEND_DATA.exists() else 0

        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1500, "height": 1000})
            page.goto(WEB_URL, wait_until="domcontentloaded", timeout=30000)
            page.get_by_text("电商 AI 智能上架助手").first.wait_for(timeout=60000)
            print("PASS: 页面标题渲染")

            file_input = page.locator("input[type=file]").first
            file_input.set_input_files([
                {"name": "demo_red.png", "mimeType": "image/png", "buffer": make_test_image((200, 60, 60))},
                {"name": "demo_blue.png", "mimeType": "image/png", "buffer": make_test_image((60, 60, 200))},
            ])
            time.sleep(2)

            page.get_by_role("button", name="开始生成").click(timeout=15000)
            page.get_by_text("批量审核队列").first.wait_for(timeout=300000)
            page.get_by_text("已勾选").first.wait_for(timeout=30000)
            time.sleep(2)
            print("PASS: 点击【开始生成】后展示批量审核队列（默认勾选）")

            page.get_by_role("button", name="确认无误，批量上架").click(timeout=15000)
            page.get_by_text("批量上架成功").first.wait_for(timeout=300000)
            print("PASS: 批量上架成功，页面展示成功信息")

            page.screenshot(path=str(BASE_DIR / "output" / "ui_webapp.png"), full_page=True)
            browser.close()

        after = len(json.loads(BACKEND_DATA.read_text(encoding="utf-8")))
        if after != before + 2:
            print(f"FAIL: 后台记录数 {before} -> {after}，应为 +2"); return 1
        print("PASS: 后台新增两条上架记录")
        return 0
    finally:
        webapp.terminate()
        backend.terminate()
        try:
            webapp.wait(timeout=10)
            backend.wait(timeout=10)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
