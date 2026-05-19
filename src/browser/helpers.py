import sys
import asyncio
import random
import functools
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Any
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import MIN_DELAY, MAX_DELAY, SCREENSHOT_DIR, ELEMENT_TIMEOUT, SELECTORS, SESSION_STATE_PATH
from playwright.async_api import Page

async def random_delay(min_sec: float=MIN_DELAY, max_sec: float=MAX_DELAY) -> None:
    delay: float = random.uniform(min_sec, max_sec)
    print(f'  ⏳ Waiting {delay:.1f}s (rate limiting)...')
    await asyncio.sleep(delay)

async def wait_and_click(page: Page, selector: str, timeout: int=ELEMENT_TIMEOUT) -> bool:
    try:
        await page.wait_for_selector(selector, timeout=timeout, state='visible')
        await page.click(selector)
        print(f'  ✅ Clicked: {selector}')
        return True
    except Exception as e:
        print(f"  ❌ Failed to click '{selector}': {e}")
        return False

async def safe_get_text(page: Page, selector: str, default: str='') -> str:
    try:
        element = await page.query_selector(selector)
        if element:
            text: Optional[str] = await element.text_content()
            return text.strip() if text else default
        return default
    except Exception as e:
        print(f"  ⚠️  Could not extract text for '{selector}': {e}")
        return default

async def safe_get_attribute(page: Page, selector: str, attribute: str, default: str='') -> str:
    try:
        element = await page.query_selector(selector)
        if element:
            value: Optional[str] = await element.get_attribute(attribute)
            return value.strip() if value else default
        return default
    except Exception as e:
        print(f"  ⚠️  Could not extract attribute '{attribute}' for '{selector}': {e}")
        return default

async def take_debug_screenshot(page: Page, name: str) -> Optional[str]:
    try:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp: str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filepath: Path = SCREENSHOT_DIR / f'{timestamp}_{name}.png'
        await page.screenshot(path=str(filepath), full_page=True)
        print(f'  📸 Screenshot saved: {filepath}')
        return str(filepath)
    except Exception as e:
        print(f"  ⚠️  Failed to take screenshot '{name}': {e}")
        return None

async def check_for_captcha(page: Page) -> bool:
    try:
        captcha_element = await page.query_selector(SELECTORS['captcha_frame'])
        if captcha_element:
            print('\n  🛑 CAPTCHA DETECTED!')
            print('  ────────────────────────────────────────')
            print('  A CAPTCHA challenge is blocking the scraper.')
            print('  If running in headed mode (HEADLESS=false),')
            print('  please solve it manually in the browser window.')
            print('  ────────────────────────────────────────\n')
            await take_debug_screenshot(page, 'captcha_detected')
            print('  ⏳ Waiting up to 5 minutes for CAPTCHA resolution...')
            try:
                await page.wait_for_selector(SELECTORS['captcha_frame'], state='detached', timeout=300000)
                print('  ✅ CAPTCHA resolved! Continuing...')
            except Exception:
                print('  ⚠️  CAPTCHA wait timed out after 5 minutes')
            return True
        return False
    except Exception as e:
        print(f'  ⚠️  Error checking for CAPTCHA: {e}')
        return False

def retry_on_failure(max_retries: int=3, delay: float=2.0) -> Callable:

    def decorator(func: Callable) -> Callable:

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Optional[Exception] = None
            for attempt in range(1, max_retries + 2):
                try:
                    result = await func(*args, **kwargs)
                    if attempt > 1:
                        print(f'  ✅ {func.__name__} succeeded on attempt {attempt}')
                    return result
                except Exception as e:
                    last_exception = e
                    if attempt <= max_retries:
                        print(f'  ⚠️  {func.__name__} failed (attempt {attempt}/{max_retries + 1}): {e}')
                        print(f'  ⏳ Retrying in {delay}s...')
                        await asyncio.sleep(delay)
                    else:
                        print(f'  ❌ {func.__name__} failed after {max_retries + 1} attempts: {e}')
            raise last_exception
        return wrapper
    return decorator

async def autofill_login_credentials(page: Page, username: str, password: str) -> None:
    try:
        if 'sso.gem.gov.in' not in page.url:
            return
        username_selectors = ['#loginid', "input[name='loginid']", "input[name='username']", "input[type='text']"]
        for sel in username_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await page.fill(sel, username)
                    print(f'  ✓ Auto-filled username using selector: {sel}')
                    break
            except Exception:
                continue
        password_selectors = ['#password', "input[name='password']", "input[type='password']"]
        for sel in password_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await page.fill(sel, password)
                    print(f'  ✓ Auto-filled password using selector: {sel}')
                    break
            except Exception:
                continue
    except Exception as e:
        print(f'  ⚠️  Failed to auto-fill credentials: {e}')

async def handle_login_if_needed(page: Page, target_url: Optional[str]=None) -> bool:
    await page.wait_for_timeout(1500)
    current_url = page.url
    is_sso = 'sso.gem.gov.in' in current_url
    is_homepage_redirect = 'gem.gov.in' in current_url and 'bidplus' not in current_url
    if not is_sso and (not is_homepage_redirect):
        return True
    print('\n' + '=' * 80)
    print('🔒 SSO LOGIN REQUIRED!')
    print(f'Current URL: {current_url}')
    print('=' * 80)
    if is_homepage_redirect:
        print('  → Redirected to portal landing page. Navigating to SSO Login Page...')
        try:
            await page.goto('https://sso.gem.gov.in/ARXSSO/oauth/login', wait_until='domcontentloaded', timeout=30000)
            current_url = page.url
        except Exception as e:
            print(f'  ⚠️  Failed to navigate to SSO login page: {e}')
    from config.settings import HEADLESS
    if HEADLESS:
        print('\n' + 'X' * 80)
        print('❌ ERROR: GeM SSO LOGIN REQUIRED BUT SCRAPER IS RUNNING IN HEADLESS MODE!')
        print('X' * 80)
        print('To solve this:')
        print('1. Edit your .env file and set HEADLESS=false')
        print('2. Run python scripts/run_scraper.py again')
        print('3. Enter your credentials and solve the CAPTCHA in the visible browser window')
        print('4. Once you log in, your session will be saved automatically, and you can')
        print('   switch back to HEADLESS=true if desired.')
        print('X' * 80 + '\n')
        raise RuntimeError('GeM SSO Login required but scraper is running in headless mode. Set HEADLESS=false to log in.')
    from config.settings import GEM_USERNAME, GEM_PASSWORD
    username = GEM_USERNAME
    password = GEM_PASSWORD
    if username and password:
        print('  Attempting to auto-fill credentials...')
        await autofill_login_credentials(page, username, password)
        print('\n🔑 Credentials auto-filled! Please solve the CAPTCHA and click Login.\n')
    else:
        print('\n🔑 Please enter your GeM Login Details and solve the CAPTCHA in the browser window.\n')
    print('=' * 80)
    print('⏳ WAITING FOR USER TO COMPLETE LOGIN...')
    print('Once you complete the login, the browser will redirect back to GeM.')
    print('We will automatically detect this and resume scraping.')
    print('=' * 80)
    max_wait_seconds = 300
    wait_interval = 2.0
    elapsed = 0.0
    while elapsed < max_wait_seconds:
        current_url = page.url
        if 'bidplus.gem.gov.in' in current_url:
            print(f'\n🎉 Login detected! Redirected to: {current_url}')
            try:
                SESSION_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
                await page.context.storage_state(path=str(SESSION_STATE_PATH))
                print(f'💾 Session successfully saved to {SESSION_STATE_PATH}\n')
            except Exception as e:
                print(f'  ⚠️  Could not save session state: {e}')
            if target_url:
                print(f'🔄 Re-navigating to target URL: {target_url}...')
                try:
                    await page.goto(target_url, wait_until='domcontentloaded', timeout=30000)
                except Exception as e:
                    print(f'  ⚠️  Failed to navigate back to target URL: {e}')
            return True
        await asyncio.sleep(wait_interval)
        elapsed += wait_interval
    raise TimeoutError('SSO login timed out. Please try running the scraper again.')