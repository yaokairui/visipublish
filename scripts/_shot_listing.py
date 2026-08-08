# -*- coding: utf-8 -*-
"""临时脚本：为上架助手卡片生成带识别结果的全页截图。"""
import pathlib
from playwright.sync_api import sync_playwright

base = pathlib.Path(r"C:\Users\86135\Desktop\VisiPublish_Agent")
out = base / "output"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errs = []
    page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errs.append("PAGEERROR: " + str(e)))
    api_resp = {}
    page.on("response", lambda r: api_resp.update({r.url: r.status}) if "/api/" in r.url else None)
    page.goto("http://127.0.0.1:8502/?theme=dark", wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    page.locator("#file-input").set_input_files(str(base / "output" / "placeholder_1.png"))
    page.wait_for_timeout(800)
    previews = page.locator(".grid img").count()
    print("preview imgs:", previews)
    with page.expect_response(lambda r: "/api/generate" in r.url and r.request.method == "POST", timeout=90000) as resp_info:
        page.locator("section button.btn-primary").click()
    resp = resp_info.value
    body = resp.json()
    print("generate status:", resp.status, "items:", len(body.get("items", [])),
          "statuses:", [it.get("status") for it in body.get("items", [])])
    rows = 0
    for _ in range(30):
        page.wait_for_timeout(2000)
        rows = page.locator("section").filter(has_text="批量审核队列").locator(".space-y-3 > div").count()
        if rows > 0:
            break
    print("listing rows:", rows)
    page.wait_for_timeout(1200)
    page.screenshot(path=str(out / "listing_card.png"), full_page=True)
    print("errors:", errs if errs else "none")
    page.close()
    browser.close()
