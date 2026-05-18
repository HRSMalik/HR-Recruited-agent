import os
import re
import time
from pathlib import Path
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("recruitment-module")


@mcp.tool(title="Post to LinkedIn", description="post the job post on linkedin")
async def post_to_linkedin(
    content: str,
    *,
    email: str | None = None,
    password: str | None = None,
    headless: bool = False,
    storage_state_path: str = "linkedin_storage_state.json",
) -> None:
    """Log in to LinkedIn and publish a post.

    Notes:
    - Uses your own credentials (env vars LINKEDIN_EMAIL/LINKEDIN_PASSWORD or args).
    - If 2FA/challenge appears, it pauses so you can complete it manually.
    - Saves a Playwright storage state to reuse the session next time.
    """

    if not content or not content.strip():
        raise ValueError("content must be a non-empty string")

    email = email or os.getenv("LINKEDIN_EMAIL")
    password = password or os.getenv("LINKEDIN_PASSWORD")
    storage_state_file = Path(storage_state_path)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = None
        try:
            if storage_state_file.exists():
                context = await browser.new_context(storage_state=str(storage_state_file))
            else:
                context = await browser.new_context()

            page = await context.new_page()
            page.set_default_timeout(60000)
            page.set_default_navigation_timeout(60000)

            async def _fill_first(selectors: list[str], value: str, *, field_name: str) -> None:
                last_error: Exception | None = None
                for selector in selectors:
                    locator = page.locator(selector).first
                    try:
                        await locator.wait_for(state="visible", timeout=5000)
                        await locator.fill(value)
                        return
                    except PlaywrightTimeoutError as e:
                        last_error = e
                        continue

                # Fallback: try accessible-role based locators (can vary by locale/UI).
                try:
                    await page.get_by_role("textbox", name=re.compile(field_name, re.I)).fill(value, timeout=5000)
                    return
                except Exception as e:  # noqa: BLE001
                    last_error = e

                raise RuntimeError(f"Could not find {field_name} input on LinkedIn login page") from last_error

            async def _goto_feed() -> None:
                # Avoid waiting for "networkidle" on LinkedIn; it often keeps long-polling.
                await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")

                # If we're not authenticated, LinkedIn will redirect to /login or /checkpoint.
                if "/login" in page.url or "checkpoint" in page.url or "/challenge/" in page.url:
                    return

                # Wait for a stable UI element that exists on the feed.
                try:
                    await page.get_by_role(
                        "button", name=re.compile(r"^Start a post", re.I)
                    ).wait_for(timeout=45000)
                except PlaywrightTimeoutError:
                    await page.locator("header").wait_for(state="visible", timeout=45000)

            async def _wait_for_manual_login(max_seconds: int = 600) -> bool:
                deadline = time.monotonic() + max_seconds
                while time.monotonic() < deadline:
                    if "/login" not in page.url and "checkpoint" not in page.url and "/challenge/" not in page.url:
                        try:
                            await page.get_by_role(
                                "button", name=re.compile(r"^Start a post", re.I)
                            ).wait_for(timeout=2000)
                            return True
                        except PlaywrightTimeoutError:
                            pass
                    await page.wait_for_timeout(1000)
                return False

            # 1) Ensure we are logged in (or log in).
            await _goto_feed()
            if "/login" in page.url or "checkpoint" in page.url:
                if not email or not password:
                    raise RuntimeError(
                        "Not logged in and no credentials provided. "
                        "Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD env vars or pass email/password."
                    )

                await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

                await _fill_first(
                    [
                        "input#username",
                        "input[name='session_key']",
                        "input[autocomplete='username']",
                        "input[type='email']",
                        "input[autocomplete='email']",
                    ],
                    email,
                    field_name="email",
                )
                await _fill_first(
                    [
                        "input#password",
                        "input[name='session_password']",
                        "input[autocomplete='current-password']",
                        "input[type='password']",
                    ],
                    password,
                    field_name="password",
                )

                submitted = False
                for selector in [
                    "button[type='submit']",
                    "button:has-text('Sign in')",
                    "button:has-text('Continue')",
                ]:
                    try:
                        await page.locator(selector).first.click(timeout=15000)
                        submitted = True
                        break
                    except PlaywrightTimeoutError:
                        continue

                if not submitted:
                    try:
                        await page.get_by_role("button", name=re.compile(r"Sign\s*in", re.I)).click(timeout=15000)
                        submitted = True
                    except PlaywrightTimeoutError:
                        submitted = False

                if not submitted:
                    await page.locator(
                        "input#password, input[name='session_password'], input[type='password']"
                    ).first.focus()
                    await page.keyboard.press("Enter")

                await page.wait_for_load_state("domcontentloaded")
                if "checkpoint" in page.url or "/challenge/" in page.url:
                    # In an MCP/async server, we can't use blocking input() reliably.
                    # Keep the window open and wait for the user to complete verification.
                    sys.stderr.write("LinkedIn is asking for verification (2FA/challenge).\n")
                    sys.stderr.write("Complete it in the opened browser window.\n")
                    sys.stderr.flush()
                    ok = await _wait_for_manual_login(max_seconds=600)
                    if not ok:
                        raise RuntimeError(
                            "Timed out waiting for LinkedIn verification. "
                            "Re-run with headless=False and complete the challenge within 10 minutes."
                        )

                await _goto_feed()
                await context.storage_state(path=str(storage_state_file))

            # 2) Create a post.
            start_post_button = page.get_by_role("button", name=re.compile(r"^Start a post", re.I))
            await start_post_button.click(timeout=60000)

            textbox = page.locator("div[role='textbox'][contenteditable='true']").first
            await textbox.wait_for(state="visible", timeout=60000)
            await textbox.click()
            await textbox.fill(content)

            # 3) Publish.
            post_button = page.get_by_role("button", name=re.compile(r"^Post$", re.I))
            await post_button.wait_for(state="visible", timeout=60000)
            # await post_button.click(timeout=60000)

            try:
                await page.locator("div[role='dialog']").first.wait_for(state="hidden", timeout=30000)
            except PlaywrightTimeoutError:
                pass

            await page.wait_for_timeout(1500)
        finally:
            if context is not None:
                pass
            #     await context.close()
            pass
            # await browser.close()


if __name__ == "__main__":
    # IMPORTANT: MCP stdio transport uses stdout for the protocol.
    # Do not print to stdout from this process.
    mcp.run(transport="stdio")