# -*- coding: utf-8 -*-
"""商品评价分析看板 · 冒烟测试
验证：file:// 打开（1440px + 375px）→ 8 指标卡 / 6 图表 / 表格渲染 → 标签切换 → 无横向滚动 → 截图
用法：.venv/Scripts/python.exe scripts/reviews_smoke.py
"""
import pathlib
from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).resolve().parents[1]
FRONT = BASE / "reviews" / "frontend" / "index.html"
SHOT = BASE / "output" / "reviews_shot.png"
SHOT_MOBILE = BASE / "output" / "reviews_shot_mobile.png"


def run(viewport, shot_path):
    errors = []
    r = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport=viewport)
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append("PAGEERROR: " + str(e)))
        page.goto(FRONT.as_uri())
        page.wait_for_load_state("networkidle")
        page.wait_for_selector(".kpi-value", timeout=20000)
        page.wait_for_timeout(2500)

        r["title"] = page.locator("h1").first.inner_text()
        r["kpi_count"] = page.locator(".kpi-value").count()
        r["canvas_count"] = page.locator("canvas").count()
        r["tag_rows"] = page.locator("table").nth(0).locator("tbody tr").count()
        r["freq_rows"] = page.locator("table").nth(1).locator("tbody tr").count()
        r["prod_rows"] = page.locator("table").nth(2).locator("tbody tr").count() + page.locator("table").nth(3).locator("tbody tr").count()
        r["no_h_scroll"] = page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
        r["summary_text"] = page.locator("text=数据摘要").first.inner_text()
        # 标签排名切换：正面
        page.get_by_role("button", name="正面", exact=True).click()
        page.wait_for_timeout(400)
        r["tag_after_toggle"] = page.locator("table").nth(0).locator("tbody tr").count()
        page.get_by_role("button", name="整体", exact=True).click()
        page.wait_for_timeout(300)
        r["tag_after_all"] = page.locator("table").nth(0).locator("tbody tr").count()

        page.screenshot(path=str(shot_path), full_page=True)

        # 粘贴文本导入（spec：review-import）
        page.get_by_role("button", name="粘贴文本").click()
        page.wait_for_timeout(300)
        page.locator("textarea").fill("[1星] 物流太慢，等了一周\n[5星] 肤感很舒服，吸收快\n一般般，无功无过")
        page.get_by_role("button", name="导入分析").click()
        page.wait_for_timeout(800)
        r["paste_kpi_total"] = page.locator(".kpi-value").first.inner_text()
        r["paste_toast"] = page.locator("text=导入成功").first.is_visible()
        browser.close()
    return r, errors


results = {}
for name, viewport, shot in [
    ("desktop", {"width": 1440, "height": 900}, SHOT),
    ("mobile", {"width": 375, "height": 812}, SHOT_MOBILE),
]:
    r, errs = run(viewport, shot)
    results[name] = r
    print(f"[{name}] " + " | ".join(f"{k}={v}" for k, v in r.items()))
    print(f"[{name}] CONSOLE_ERRORS =", errs if errs else "none")

ok = all([
    results["desktop"]["kpi_count"] == 8,
    results["desktop"]["canvas_count"] == 6,
    results["desktop"]["tag_rows"] > 0,
    results["desktop"]["freq_rows"] > 0,
    results["desktop"]["prod_rows"] >= 20,
    results["desktop"]["no_h_scroll"],
    results["mobile"]["no_h_scroll"],
    results["mobile"]["kpi_count"] == 8,
    results["desktop"]["paste_kpi_total"] == "3",
    results["desktop"]["paste_toast"] is True,
])
print("REVIEWS_SMOKE_PASS =", ok)
