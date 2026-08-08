# -*- coding: utf-8 -*-
"""临时脚本：截取评价看板「负面评价观点趋势」面板与放大视图。"""
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
    page.goto((base / "reviews" / "frontend" / "index.html").as_uri(), wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    panel = page.locator(".chart-zoom").filter(has_text="负面评价观点趋势")
    panel.scroll_into_view_if_needed()
    page.wait_for_timeout(400)
    panel.screenshot(path=str(out / "reviews_negtrend_fixed.png"))
    panel.click()
    page.wait_for_timeout(800)
    page.screenshot(path=str(out / "reviews_negtrend_zoom.png"))
    print("neg trend panel shot done; errors:", errs if errs else "none")
    page.close()
    browser.close()
