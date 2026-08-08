# -*- coding: utf-8 -*-
"""VisiPublish 展示站 · 冒烟测试
验证：file:// 打开（桌面 1440px + 手机 375px）→ 渲染 → 无横向滚动 → 链接正确 → 截图
用法：.venv/Scripts/python.exe scripts/site_smoke.py
"""
import pathlib
from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).resolve().parents[1]
SITE = BASE / "site" / "index.html"
SHOT_DESKTOP = BASE / "output" / "site_shot.png"
SHOT_MOBILE = BASE / "output" / "site_shot_mobile.png"


def run(viewport, shot_path):
    errors = []
    r = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=viewport)
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append("PAGEERROR: " + str(e)))
        page.goto(SITE.as_uri())
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1200)

        r["h1"] = page.locator("h1").first.inner_text().replace("\n", " ")
        r["cards"] = page.locator("article.project-card").count()
        r["badges"] = [page.locator("article.project-card").nth(i).locator("span[class^='badge-']").inner_text() for i in range(3)]
        r["status_dots"] = page.locator(".dot").count()
        r["nav_links"] = page.locator("header nav a").count()
        r["no_h_scroll"] = page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
        # 滚动到底，确认 reveal 内容可见
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(700)
        last_card = page.locator("article.project-card").last
        r["last_card_visible"] = last_card.evaluate("el => getComputedStyle(el).opacity === '1'")
        # 链接正确性
        r["dash_link"] = page.locator('a[href="../dashboard/index.html"]').count()
        r["readme_link"] = page.locator('a[href="../README.md"]').count()
        r["reviews_link"] = page.locator('a[href="../reviews/frontend/index.html"]').count()
        page.screenshot(path=str(shot_path), full_page=True)
        browser.close()
    return r, errors


results = {}
for name, viewport, shot in [
    ("desktop", {"width": 1440, "height": 900}, SHOT_DESKTOP),
    ("mobile", {"width": 375, "height": 812}, SHOT_MOBILE),
]:
    r, errs = run(viewport, shot)
    results[name] = r
    print(f"[{name}] " + " | ".join(f"{k}={v}" for k, v in r.items()))
    print(f"[{name}] CONSOLE_ERRORS =", errs if errs else "none")

ok = all([
    results["desktop"]["cards"] == 3,
    results["desktop"]["no_h_scroll"],
    results["desktop"]["last_card_visible"],
    results["desktop"]["dash_link"] >= 1,
    results["desktop"]["readme_link"] >= 1,
    results["desktop"]["reviews_link"] >= 1,
    results["mobile"]["no_h_scroll"],
    results["mobile"]["cards"] == 3,
])
print("SITE_SMOKE_PASS =", ok)
