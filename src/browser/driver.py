import sys
import random
from pathlib import Path
from typing import Optional
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import HEADLESS, USER_AGENTS, VIEWPORT, PAGE_LOAD_TIMEOUT, SESSION_STATE_PATH
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page
class BrowserManager:
    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
    async def __aenter__(self) -> 'BrowserManager':
        await self.launch()
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
    async def launch(self) -> None:
        print('[BrowserManager]  Starting Playwright engine...')
        self._playwright = await async_playwright().start()
        print(f'[BrowserManager] 🌐 Launching Chromium (headless={HEADLESS})...')
        self._browser = await self._playwright.chromium.launch(headless=HEADLESS, args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-infobars', '--disable-extensions'])
        selected_user_agent: str = random.choice(USER_AGENTS)
        print(f'[BrowserManager] 🎭 Using user agent: {selected_user_agent[:60]}...')
        storage_state = None
        if SESSION_STATE_PATH.exists():
            print(f'[BrowserManager] 💾 Loading existing session state from {SESSION_STATE_PATH}...')
            storage_state = str(SESSION_STATE_PATH)
        self._context = await self._browser.new_context(user_agent=selected_user_agent, viewport=VIEWPORT, locale='en-IN', timezone_id='Asia/Kolkata', storage_state=storage_state)
        await self._context.add_init_script("\n            // Override the webdriver property to hide automation\n            // Real browsers have navigator.webdriver === undefined\n            // Automated browsers have navigator.webdriver === true\n            Object.defineProperty(navigator, 'webdriver', {\n                get: () => undefined,\n            });\n        ")
        print('[BrowserManager]  Browser launched successfully!')
    async def new_page(self) -> Page:
        if self._context is None:
            raise RuntimeError("Browser not launched! Call launch() first, or use 'async with BrowserManager() as mgr:' for automatic setup.")
        page: Page = await self._context.new_page()
        page.set_default_navigation_timeout(PAGE_LOAD_TIMEOUT)
        print('[BrowserManager]  New page created and ready')
        return page
    async def close(self) -> None:
        print('[BrowserManager]  Shutting down browser...')
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        print('[BrowserManager]  Browser closed cleanly')