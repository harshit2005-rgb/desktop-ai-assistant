"""
Browser Manager

Responsible for:
- Starting Playwright
- Managing one browser
- Managing one browser context
- Managing the current page
"""

from __future__ import annotations

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)


class BrowserManager:

    def __init__(self) -> None:

        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def _ensure_browser(self) -> None:

        if self.browser is not None:
            return

        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=False,
        )

        self.context = self.browser.new_context()

    def get_page(self) -> Page:

        self._ensure_browser()

        if self.page is None:
            self.page = self.context.new_page()

        return self.page

    def new_tab(self) -> Page:

        self._ensure_browser()

        self.page = self.context.new_page()

        return self.page

    def close(self) -> None:

        if self.browser is not None:
            self.browser.close()

        if self.playwright is not None:
            self.playwright.stop()

        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None


browser_manager = BrowserManager()