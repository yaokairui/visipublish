# -*- coding: utf-8 -*-
"""Verify reviews dashboard: theme toggle, chart zoom modal, neg-trend overlap."""
import pathlib
from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).resolve().parents[1]
URL = (BASE / "reviews" / "frontend" / "index.html").as_uri()


def main():
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page(viewport={"width": 1440, "height": 900})
        errs = []
        page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errs.append("PAGEERROR: " + str(e)))
        page.goto(URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_selector(".kpi-value", timeout=20000)
        page.wait_for_timeout(2500)
        out["default_theme"] = page.evaluate("document.documentElement.dataset.theme")
        out["toggle_btn"] = page.locator("button.theme-toggle").count()
        out["chart_boxes"] = page.locator(".chart-zoom").count()
        page.screenshot(path=str(BASE / "output" / "reviews_after_dark.png"), full_page=False)

        # zoom modal on trend chart (second chart box in section 4)
        boxes = page.locator(".chart-zoom")
        boxes.nth(2).click()
        page.wait_for_timeout(900)
        out["zoom_dialog"] = page.locator("[role=dialog]").count()
        out["canvas_while_zoom"] = page.locator("canvas").count()
        out["zoom_title"] = page.locator("[role=dialog] h2").first.inner_text() if out["zoom_dialog"] else ""
        page.keyboard.press("Escape")
        page.wait_for_timeout(700)
        out["canvas_after_esc"] = page.locator("canvas").count()

        # toggle theme
        page.locator("button.theme-toggle").click()
        page.wait_for_timeout(1000)
        out["after_toggle"] = page.evaluate("document.documentElement.dataset.theme")
        out["ls"] = page.evaluate("localStorage.getItem('visipublish-theme')")
        out["no_h_scroll"] = page.evaluate(
            "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
        )
        out["chart_boxes_light"] = page.locator(".chart-zoom").count()
        page.screenshot(path=str(BASE / "output" / "reviews_after_light.png"), full_page=False)

        # direct ?theme=light
        p2 = b.new_page(viewport={"width": 1440, "height": 900})
        p2.goto(URL + "?theme=light")
        p2.wait_for_load_state("networkidle")
        p2.wait_for_timeout(1800)
        out["direct_light"] = p2.evaluate("document.documentElement.dataset.theme")
        p2.close()
        out["errors"] = errs
        b.close()

    for k, v in out.items():
        print(f"{k} = {v}")
    ok = (
        out["default_theme"] == "dark"
        and out["toggle_btn"] == 1
        and out["chart_boxes"] == 6
        and out["zoom_dialog"] == 1
        and out["canvas_while_zoom"] == 7
        and out["canvas_after_esc"] == 6
        and out["after_toggle"] == "light"
        and out["ls"] == "light"
        and out["no_h_scroll"]
        and out["direct_light"] == "light"
        and not out["errors"]
    )
    print("VERIFY_PASS =", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
