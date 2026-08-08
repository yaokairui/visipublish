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
        page.goto(SITE.as_uri(), wait_until="load")
        page.wait_for_timeout(1800)

        r["h1"] = page.locator("h1").first.inner_text().replace("\n", " ")
        r["cards"] = page.locator("article.project-card").count()
        r["badges"] = [page.locator("article.project-card").nth(i).locator("span[class^='badge-']").inner_text() for i in range(3)]
        r["status_dots"] = page.locator(".dot").count()
        r["brand"] = page.locator("header nav a").first.inner_text().replace("\n", "")
        r["status_labels"] = [page.locator("span[role='listitem']").nth(i).inner_text() for i in range(page.locator("span[role='listitem']").count())]
        r["probe_label"] = page.locator("#probeListing").inner_text()
        r["probe_dot"] = page.locator("#probeListing .dot").get_attribute("class")
        r["nav_links"] = page.locator("header nav a").count()
        r["no_h_scroll"] = page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
        # 滚动到底，确认 reveal 内容可见
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(700)
        last_card = page.locator("article.project-card").last
        r["last_card_visible"] = last_card.evaluate("el => getComputedStyle(el).opacity === '1'")
        # 链接正确性
        r["dash_link"] = page.locator('a[href*="../dashboard/index.html"]').count()
        r["app_link"] = page.locator('a[href*="http://127.0.0.1:8502/"]').count()
        r["reviews_link"] = page.locator('a[href*="../reviews/frontend/index.html"]').count()
        r["theme_toggle"] = page.locator("#themeToggle").count()
        r["theme_links_ok"] = page.evaluate(
            "document.querySelectorAll('a[data-theme-link]').length > 0 && "
            "Array.from(document.querySelectorAll('a[data-theme-link]')).every(a => /[?&]theme=(dark|light)/.test(a.href))"
        )
        r["default_theme"] = page.evaluate("document.documentElement.dataset.theme")
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
    results["desktop"]["theme_toggle"] == 1,
    results["desktop"]["theme_links_ok"],
    results["desktop"]["default_theme"] == "dark",
    results["desktop"]["dash_link"] >= 1,
    results["desktop"]["app_link"] >= 1,
    results["desktop"]["reviews_link"] >= 1,
    results["desktop"]["brand"] == "YaoKr电商工具箱",
    results["desktop"]["probe_dot"] in ("dot on", "dot off"),
    all(lbl in results["desktop"]["status_labels"] for lbl in ["运营看板 · 离线可用", "评价分析 · 离线可用"]),
    results["mobile"]["no_h_scroll"],
    results["mobile"]["cards"] == 3,
])
print("SITE_SMOKE_PASS =", ok)
