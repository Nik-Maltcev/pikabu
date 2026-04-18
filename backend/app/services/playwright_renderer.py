"""PlaywrightRenderer — async context manager for headless Chromium rendering."""

import logging

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class PlaywrightRenderer:
    """Manages a headless Chromium browser for rendering JS-heavy pages."""

    def __init__(self) -> None:
        self._playwright = None
        self._browser = None

    async def __aenter__(self) -> "PlaywrightRenderer":
        """Launch browser on context entry."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close browser on context exit (even on exception)."""
        try:
            if self._browser:
                await self._browser.close()
        except Exception:
            logger.warning("Error closing browser", exc_info=True)
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            logger.warning("Error stopping playwright", exc_info=True)

    async def render_page(
        self, url: str, wait_selector: str, timeout: int = 30000
    ) -> str:
        """Navigate to URL, wait for selector, return rendered HTML.

        Returns empty string on timeout or error.
        """
        page = await self._browser.new_page()
        try:
            await page.goto(url, timeout=timeout)
            await page.wait_for_selector(wait_selector, timeout=timeout)
            return await page.content()
        except Exception:
            logger.warning("PlaywrightRenderer failed for %s", url, exc_info=True)
            return ""
        finally:
            await page.close()
