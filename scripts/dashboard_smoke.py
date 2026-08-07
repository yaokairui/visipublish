# -*- coding: utf-8 -*-
"""全平台电商运营看板 · 冒烟测试
验证：file:// 打开 → KPI/图表/表格渲染 → 筛选联动 → Excel 导入 → 截图
用法：.venv/Scripts/python.exe scripts/dashboard_smoke.py
"""
import pathlib
import re
from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).resolve().parents[1]
DASH = BASE / "dashboard" / "index.html"
SHOT = BASE / "output" / "dashboard_shot.png"
SHOT_IMPORT = BASE / "output" / "dashboard_shot_import.png"
TEST_XLSX = BASE / "dashboard" / "_test_import.xlsx"

errors = []
all_console = []

def collect(msg):
    all_console.append(f"[{msg.type}] {msg.text}")
    if msg.type == "error":
        errors.append(msg.text)

r = {}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1000})
    page.on("console", collect)
    page.on("pageerror", lambda e: errors.append("PAGEERROR: " + str(e)))
    try:
        page.goto(DASH.as_uri())
        page.wait_for_load_state("networkidle")
        page.wait_for_selector(".kpi-card", timeout=20000)
        page.wait_for_timeout(2500)

        r["title"] = page.locator("h1").first.inner_text()
        r["kpi_cards"] = page.locator(".kpi-card").count()
        r["canvas_count"] = page.locator("canvas").count()
        r["store_rows"] = page.locator("table").nth(0).locator("tbody tr").count()
        r["product_rows"] = page.locator("table").nth(1).locator("tbody tr").count()
        r["store_warn_badges"] = page.locator("table").nth(0).locator(".badge-danger").count()
        r["chip_count"] = page.locator("button.chip").count()
        r["signal_seg_count"] = page.locator(".signal-seg").count()
        r["stats_line"] = page.locator("text=当前筛选").first.inner_text()
        r["clock_text"] = page.get_by_text(re.compile(r"^\d{2}:\d{2}:\d{2}$")).first.inner_text()
        roi = page.locator(".kpi-card").nth(5).inner_text()
        r["roi_has_value"] = bool(re.search(r"\d+(\.\d+)?x", roi))

        gmv_before = page.locator(".kpi-card").nth(0).locator(".font-mono").inner_text()
        page.locator("button.chip", has_text="京东").first.click()
        page.wait_for_timeout(900)
        gmv_after = page.locator(".kpi-card").nth(0).locator(".font-mono").inner_text()
        r["gmv_before"] = gmv_before
        r["gmv_after"] = gmv_after
        r["linkage_ok"] = gmv_before != gmv_after
        r["signal_seg_after"] = page.locator(".signal-seg").count()

        # 恢复示例数据 → 全量样本状态，截整页图
        page.get_by_role("button", name="恢复示例数据").click()
        page.wait_for_timeout(1200)
        r["restored_gmv"] = page.locator(".kpi-card").nth(0).locator(".font-mono").inner_text()
        page.screenshot(path=str(SHOT), full_page=True)
        r["screenshot"] = SHOT.name

        # Excel 导入（含 2 行非法数据应被跳过）
        if TEST_XLSX.exists():
            page.set_input_files("input[type=file]", str(TEST_XLSX))
            page.wait_for_timeout(1500)
            r["import_toast"] = page.locator("text=导入成功").first.is_visible()
            r["store_rows_after_import"] = page.locator("table").nth(0).locator("tbody tr").count()
            r["stats_after_import"] = page.locator("text=当前筛选").first.inner_text()
            page.screenshot(path=str(SHOT_IMPORT))
            r["screenshot_import"] = SHOT_IMPORT.name
    except Exception as e:
        r["EXCEPTION"] = str(e)
        r["body_text_snippet"] = page.inner_text("body")[:300].replace("\\n", " | ")
    finally:
        browser.close()

for k, v in r.items():
    print(f"RESULT {k} = {v}")
print("CONSOLE_ERRORS =", errors if errors else "none")
if errors:
    print("ALL_CONSOLE =")
    for line in all_console:
        print("  ", line)
print("SMOKE_PASS =", all([
    r.get("kpi_cards") == 8,
    r.get("canvas_count", 0) >= 7,
    r.get("store_rows", 0) >= 10,
    r.get("product_rows", 0) >= 15,
    r.get("linkage_ok") is True,
    r.get("roi_has_value") is True,
    r.get("signal_seg_count", 0) >= 6,
    not errors,
]))
