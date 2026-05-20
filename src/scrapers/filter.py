from __future__ import annotations
import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from playwright.async_api import Page
from config.settings import GEM_BASE_URL, DEFAULT_TIMEOUT
from src.browser.helpers import random_delay, wait_and_click, safe_get_text, check_for_captcha, take_debug_screenshot
logger = logging.getLogger(__name__)
STATUS_TOGGLE_CHECKBOX: str = 'input#bidrastatus'
AWARDED_STATUS_CHECKBOX: str = 'input#bid_awarded'
BID_CARD_SELECTOR: str = '#bidCard div.card'

async def navigate_to_bids_page(page: Page) -> None:
    logger.info('Navigating to GeM All-Bids page: %s', GEM_BASE_URL)
    await page.goto(GEM_BASE_URL, wait_until='networkidle', timeout=DEFAULT_TIMEOUT)
    logger.info('Page loaded successfully.')
    await check_for_captcha(page)
    await random_delay()
    logger.info('GeM All-Bids page is ready for interaction.')

async def apply_filters(page: Page) -> None:
    logger.info('Applying filters — target status: Awarded')
    try:
        logger.info("Step 1/3: Clicking 'Bid/RA Status' filter toggle...")
        await page.wait_for_selector(STATUS_TOGGLE_CHECKBOX, state='attached', timeout=15000)
        toggle = await page.query_selector(STATUS_TOGGLE_CHECKBOX)
        if toggle:
            is_checked = await toggle.is_checked()
            if not is_checked:
                await toggle.click()
                logger.info("  → 'Bid/RA Status' toggled.")
                await page.wait_for_timeout(2000)
            else:
                logger.info("  → 'Bid/RA Status' was already toggled.")
    except Exception as exc:
        logger.error("Could not click 'Bid/RA Status' toggle: %s", exc)
        await take_debug_screenshot(page, 'filter_toggle_fail')
        raise
    try:
        logger.info("Step 2/3: Checking 'Bid/RA Awarded' status...")
        await page.wait_for_selector(AWARDED_STATUS_CHECKBOX, state='attached', timeout=10000)
        checkbox = await page.query_selector(AWARDED_STATUS_CHECKBOX)
        if checkbox:
            is_checked = await checkbox.is_checked()
            if not is_checked:
                await checkbox.click()
                logger.info("  → 'Bid/RA Awarded' checkbox checked.")
                await page.wait_for_timeout(3000)
            else:
                logger.info("  → 'Bid/RA Awarded' checkbox was already checked.")
    except Exception as exc:
        logger.error("Error selecting 'Awarded' checkbox: %s", exc)
        await take_debug_screenshot(page, 'filter_awarded_fail')
        raise
    try:
        logger.info('Step 3/3: Waiting for filtered results to load...')
        await page.wait_for_selector(BID_CARD_SELECTOR, state='visible', timeout=DEFAULT_TIMEOUT)
        logger.info('Filtered results loaded successfully.')
    except Exception as exc:
        logger.warning('No bid cards appeared after applying filters: %s', exc)
        await take_debug_screenshot(page, 'filter_no_results')
        raise
    bid_cards = await page.query_selector_all(BID_CARD_SELECTOR)
    result_count: int = len(bid_cards)
    logger.info('Filter application complete.  %d bid cards visible on the first page.', result_count)

async def verify_filters_applied(page: Page) -> bool:
    logger.info("Verifying that 'Awarded' filter is active...")
    bid_cards = await page.query_selector_all(BID_CARD_SELECTOR)
    if not bid_cards:
        logger.warning('Verification FAILED: No bid cards found on the page.')
        await take_debug_screenshot(page, 'verify_no_cards')
        return False
    logger.info('  → Found %d bid card(s) on the page.', len(bid_cards))
    try:
        page_text: str = await page.inner_text('body')
        if 'awarded' in page_text.lower():
            logger.info("  → Page text contains 'Awarded'.  Filter appears active.")
            return True
        else:
            logger.warning("  → Page text does NOT contain 'Awarded'.  Filter may not be applied correctly.")
            await take_debug_screenshot(page, 'verify_no_awarded_text')
            return False
    except Exception as exc:
        logger.error('Error during filter verification: %s', exc)
        await take_debug_screenshot(page, 'verify_error')
        return False