# -*- coding: utf-8 -*-
"""临时脚本：验证导航页明暗切换与项目链接主题参数同步。"""
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
    page.goto((base / "site" / "index.html").as_uri(), wait_until="domcontentloaded")
    page.wait_for_timeout(1800)
    print("default theme:", page.evaluate("document.documentElement.dataset.theme"))
    themes_before = page.evaluate(
        "[...document.querySelectorAll('a[data-theme-link]')].map(a => new URL(a.href).searchParams.get('theme'))"
    )
    print("link themes before:", set(themes_before))
    page.locator("#themeToggle").click()
    page.wait_for_timeout(600)
    print("theme after toggle:", page.evaluate("document.documentElement.dataset.theme"))
    themes_after = page.evaluate(
        "[...document.querySelectorAll('a[data-theme-link]')].map(a => new URL(a.href).searchParams.get('theme'))"
    )
    print("link themes after:", set(themes_after))
    body_bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
    print("body_bg:", body_bg)
    page.screenshot(path=str(out / "site_light_check.png"), full_page=False)
    print("errors:", errs if errs else "none")
    page.close()
    browser.close()
