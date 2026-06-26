"""
Browser Manager

Responsible for:
- Starting Playwright
- Keeping one browser instance alive
- Returning the browser instance
"""

from __future__ import annotations

from playwright.sync_api import Browser, Playwright, sync_playwright


class BrowserManager:
    """
    Singleton-style browser manager.

    Only one browser should exist during the application's lifetime.
    """

    def __init__(self) -> None:
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None

    def get_browser(self) -> Browser:
        """
        Return an existing browser.
        Launch one if it doesn't exist.
        """

        if self.browser is not None:
            return self.browser

        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=False,
        )

        return self.browser

    def close(self) -> None:
        """
        Close browser and Playwright.
        """

        if self.browser is not None:
            self.browser.close()
            self.browser = None

        if self.playwright is not None:
            self.playwright.stop()
            self.playwright = None


browser_manager = BrowserManager()