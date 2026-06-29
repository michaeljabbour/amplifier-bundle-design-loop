"""Async render helper: converts a URL to a full-page PNG via headless Chromium."""

from __future__ import annotations

from pathlib import Path

from playwright.async_api import async_playwright

_VIEWPORT = {"width": 1280, "height": 800}


async def render_to_png(url: str, out_path: Path) -> Path:
    """Render *url* to a full-page PNG saved at *out_path*.

    Parameters
    ----------
    url:
        Any URL that Chromium can navigate to (``http://``, ``https://``,
        ``file://``).
    out_path:
        Destination path for the PNG file (parent directory must exist).

    Returns
    -------
    Path
        The *out_path* passed in, so callers can chain.

    Raises
    ------
    RuntimeError
        If the navigation returned a non-OK HTTP response.
    RuntimeError
        If the output file is missing or empty after the screenshot.
    Exception
        Any Playwright-level error (e.g. page not found for a ``file://`` URL).
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            page = await browser.new_page(viewport=_VIEWPORT)
            response = await page.goto(url, wait_until="load")
            if response is not None and not response.ok:
                raise RuntimeError(
                    f"Navigation to {url!r} failed with status {response.status}"
                )
            await page.screenshot(path=str(out_path), full_page=True)
        finally:
            await browser.close()

    out_path = Path(out_path)
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError(
            f"Screenshot was not written (or is empty) at {out_path}"
        )
    return out_path
