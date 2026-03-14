from __future__ import annotations

from pathlib import Path
from typing import Tuple


def capture_chart_page(url: str, output_path: str, timeframe: str = "4h") -> Tuple[bool, str]:
    """Capture a chart page screenshot with optional timeframe switching.

    Returns (ok, detail). detail is status message or reason.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return False, "playwright_not_installed"

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    tf_labels = []
    tf = (timeframe or "").strip().lower()
    if tf == "4h":
        tf_labels = ["4h", "4H", "4小时", "4 小时"]

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=90_000)
            page.wait_for_timeout(4000)

            switched = False
            for label in tf_labels:
                try:
                    page.get_by_text(label, exact=True).first.click(timeout=1200)
                    page.wait_for_timeout(1500)
                    switched = True
                    break
                except Exception:
                    continue

            page.screenshot(path=str(target), full_page=True)
            context.close()
            browser.close()
            return True, "timeframe_switched" if switched else "timeframe_switch_not_found"
    except Exception as exc:
        return False, f"capture_failed: {exc}"
