# -*- coding: utf-8 -*-
"""临时脚本：端到端验证导航页主题 → 项目继承。"""
import pathlib
from playwright.sync_api import sync_playwright

base = pathlib.Path(r"C:\Users\86135\Desktop\VisiPublish_Agent")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # 导航页切到亮色
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto((base / "site" / "index.html").as_uri(), wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    page.locator("#themeToggle").click()
    page.wait_for_timeout(500)

    # 评价看板
    page.click('a[data-theme-link][href*="reviews"]')
    page.wait_for_timeout(2500)
    print("reviews theme:", page.evaluate("document.documentElement.dataset.theme"))
    page.go_back()
    page.wait_for_timeout(1200)

    # 运营看板
    page.click('a[data-theme-link][href*="dashboard"]')
    page.wait_for_timeout(3000)
    print("dashboard theme:", page.evaluate("document.documentElement.dataset.theme"))
    page.go_back()
    page.wait_for_timeout(1200)

    # 上架助手（http）
    page.click('a[data-theme-link][href*="127.0.0.1:8502"]')
    page.wait_for_timeout(3000)
    print("listing theme:", page.evaluate("document.documentElement.dataset.theme"))
    page.close()
    browser.close()
