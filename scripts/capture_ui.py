# -*- coding: utf-8 -*-
"""Capture current UI state of all projects for visual inspection.

Usage: .venv/Scripts/python.exe scripts/capture_ui.py
"""
import pathlib
from playwright.sync_api import sync_playwright

BASE = pathlib.Path(__file__).resolve().parents[1]
OUT = BASE / "output"
OUT.mkdir(exist_ok=True)

TARGETS = [
    ("site", (BASE / "site" / "index.html").as_uri(), OUT / "current_site.png"),
    ("reviews", (BASE / "reviews" / "frontend" / "index.html").as_uri(), OUT / "current_reviews.png"),
    ("reviews_mobile", (BASE / "reviews" / "frontend" / "index.html").as_uri(), OUT / "current_reviews_mobile.png"),
    ("dashboard", (BASE / "dashboard" / "index.html").as_uri(), OUT / "current_dashboard.png"),
    ("listing", "http://127.0.0.1:8502/", OUT / "current_listing.png"),
]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for name, url, shot in TARGETS:
            viewport = {"width": 375, "height": 812} if name == "reviews_mobile" else {"width": 1500, "height": 950}
            page = browser.new_page(viewport=viewport)
            errors = []
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append("PAGEERROR: " + str(e)))
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                pass
            page.wait_for_timeout(2500)
            page.screenshot(path=str(shot), full_page=False)
            print(f"{name}: saved {shot.name} | console_errors={errors if errors else 'none'}")
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
