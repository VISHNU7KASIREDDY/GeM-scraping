from __future__ import annotations
import sys
import logging
from pathlib import Path
from typing import Optional
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from playwright.async_api import Page, ElementHandle
from config.settings import DEFAULT_TIMEOUT
from src.models.schemas import Bid
from src.browser.helpers import random_delay, safe_get_text, take_debug_screenshot, check_for_captcha
logger = logging.getLogger(__name__)
BID_CARDS_CONTAINER: str = '#bidCard .card'
CARD_BID_LINK: str = '.block_header a.bid_no_hover'
CARD_TITLE: str = '.card-body a[data-content]'
CARD_START_DATE: str = 'span.start_date'
CARD_END_DATE: str = 'span.end_date'
PAGINATION_CONTAINER: str = '.pagination2'
PAGINATION_ACTIVE: str = '.pagination2 span.current:not(.prev):not(.next)'
PAGINATION_ITEMS: str = '.pagination2 a.page-link'
PAGINATION_NEXT: str = '.pagination2 a.next'
PAGINATION_DISABLED_NEXT: str = '.pagination2 span.next'
async def extract_single_bid_card(card_element: ElementHandle, page: Page) -> Optional[Bid]:
    bid = Bid()
    try:
        bid_link: Optional[ElementHandle] = await card_element.query_selector(CARD_BID_LINK)
        if bid_link:
            bid_id_text: str = (await bid_link.inner_text()).strip()
            bid.bid_id = bid_id_text
            href: Optional[str] = await bid_link.get_attribute('href')
            if href:
                if href.startswith('/'):
                    bid.bid_url = f'https://bidplus.gem.gov.in{href}'
                elif href.startswith('http'):
                    bid.bid_url = href
                else:
                    bid.bid_url = f'https://bidplus.gem.gov.in/{href}'
    except Exception as exc:
        logger.debug('Could not extract bid_id/url: %s', exc)
    if not bid.bid_id:
        logger.warning('Skipping card with no bid_id (possibly an ad or empty card).')
        return None
    try:
        title_el: Optional[ElementHandle] = await card_element.query_selector(CARD_TITLE)
        if title_el:
            full_title: Optional[str] = await title_el.get_attribute('data-content')
            if full_title and full_title.strip():
                bid.title = full_title.strip()
            else:
                inner: str = (await title_el.inner_text()).strip()
                bid.title = inner
    except Exception as exc:
        logger.debug('Could not extract title for %s: %s', bid.bid_id, exc)
    try:
        quantity_val: Optional[str] = await card_element.evaluate('(el) => {\n                // Walk all <strong> tags in the card to find "Quantity:"\n                const strongs = el.querySelectorAll("strong");\n                for (let s of strongs) {\n                    if (s.textContent.includes("Quantity")) {\n                        // The text is in the nextSibling text node\n                        let node = s.nextSibling;\n                        while (node && node.nodeType !== Node.TEXT_NODE) {\n                            node = node.nextSibling;\n                        }\n                        return node ? node.textContent.trim() : "";\n                    }\n                }\n                return "";\n            }')
        bid.quantity = (quantity_val or '').strip()
    except Exception as exc:
        logger.debug('Could not extract quantity for %s: %s', bid.bid_id, exc)
    try:
        buyer_val: Optional[str] = await card_element.evaluate('(el) => {\n                const col = el.querySelector(".col-md-5");\n                if (!col) return "";\n                const text = col.innerText || col.textContent || "";\n                // Remove the "Department Name And Address:" prefix\n                return text.replace("Department Name And Address:", "").trim();\n            }')
        bid.buyer = (buyer_val or '').strip()
    except Exception as exc:
        logger.debug('Could not extract buyer for %s: %s', bid.bid_id, exc)
    try:
        start_text: str = await safe_get_text(card_element, CARD_START_DATE)
        bid.start_date = start_text.strip() if start_text else ''
    except Exception as exc:
        logger.debug('Could not extract start_date for %s: %s', bid.bid_id, exc)
    try:
        end_text: str = await safe_get_text(card_element, CARD_END_DATE)
        bid.end_date = end_text.strip() if end_text else ''
    except Exception as exc:
        logger.debug('Could not extract end_date for %s: %s', bid.bid_id, exc)
    try:
        if bid.bid_url:
            numeric_id: str = bid.bid_url.rstrip('/').split('/')[-1]
            if numeric_id.isdigit():
                bid.numeric_id = numeric_id
                bid.result_url = f'https://bidplus.gem.gov.in/bidding/bid/getBidResultView/{numeric_id}'
                logger.debug('  numeric_id = %s, result_url = %s', numeric_id, bid.result_url)
    except Exception as exc:
        logger.debug('Could not build result_url for %s: %s', bid.bid_id, exc)
    logger.info('   Extracted bid: %s  %s', bid.bid_id, bid.title[:60])
    return bid
async def extract_all_bids_on_page(page: Page) -> list[Bid]:
    logger.info('Extracting all bid cards from the current page...')
    card_elements: list[ElementHandle] = await page.query_selector_all(BID_CARDS_CONTAINER)
    logger.info('Found %d bid card elements on this page.', len(card_elements))
    bids: list[Bid] = []
    for index, card in enumerate(card_elements, start=1):
        logger.debug('Parsing card %d/%d ...', index, len(card_elements))
        bid: Optional[Bid] = await extract_single_bid_card(card, page)
        if bid is not None:
            bids.append(bid)
    logger.info('Extracted %d bids from this page.', len(bids))
    return bids
async def get_pagination_info(page: Page) -> dict:
    pagination = await page.query_selector(PAGINATION_CONTAINER)
    if not pagination:
        logger.info('No pagination found  results fit on a single page.')
        return {'current_page': 1, 'total_pages': 1, 'has_next': False}
    current_page: int = 1
    try:
        active_link = await page.query_selector(PAGINATION_ACTIVE)
        if active_link:
            active_text: str = (await active_link.inner_text()).strip()
            current_page = int(active_text)
    except (ValueError, TypeError):
        logger.debug('Could not parse active page number; defaulting to 1.')
    all_links: list[ElementHandle] = await page.query_selector_all(PAGINATION_ITEMS)
    total_pages: int = 0
    for link in all_links:
        text: str = (await link.inner_text()).strip()
        if text.isdigit():
            page_num: int = int(text)
            if page_num > total_pages:
                total_pages = page_num
    total_pages = max(total_pages, 1)
    disabled_next = await page.query_selector(PAGINATION_DISABLED_NEXT)
    has_next: bool = disabled_next is None
    info: dict = {'current_page': current_page, 'total_pages': total_pages, 'has_next': has_next}
    logger.info('Pagination info: %s', info)
    return info
async def navigate_to_next_page(page: Page) -> bool:
    pagination_info: dict = await get_pagination_info(page)
    if not pagination_info['has_next']:
        logger.info('No next page available (currently on page %d of %d).', pagination_info['current_page'], pagination_info['total_pages'])
        return False
    logger.info('Navigating from page %d to page %d...', pagination_info['current_page'], pagination_info['current_page'] + 1)
    await random_delay()
    try:
        next_button = await page.query_selector(PAGINATION_NEXT)
        if next_button:
            await next_button.click()
        else:
            logger.warning("'Next' button element not found.")
            return False
    except Exception as exc:
        logger.error("Error clicking 'Next' button: %s", exc)
        await take_debug_screenshot(page, 'pagination_next_fail')
        return False
    try:
        await page.wait_for_selector(BID_CARDS_CONTAINER, timeout=DEFAULT_TIMEOUT)
    except Exception as exc:
        logger.error('Bid cards did not load after clicking Next: %s', exc)
        await take_debug_screenshot(page, 'pagination_load_fail')
        return False
    await check_for_captcha(page)
    await random_delay()
    logger.info('Successfully navigated to the next page.')
    return True
async def scrape_all_listings(page: Page, target_count: int=30) -> list[Bid]:
    all_bids: list[Bid] = []
    page_number: int = 1
    logger.info(' Starting listing extraction (target: %d bids) ', target_count)
    while len(all_bids) < target_count:
        logger.info(' Page %d  collected %d/%d bids so far ', page_number, len(all_bids), target_count)
        page_bids: list[Bid] = await extract_all_bids_on_page(page)
        if not page_bids:
            logger.warning('No bids extracted from page %d.  Stopping.', page_number)
            break
        all_bids.extend(page_bids)
        logger.info('Collected %d/%d bids so far (added %d from page %d).', len(all_bids), target_count, len(page_bids), page_number)
        if len(all_bids) >= target_count:
            logger.info('Reached target count (%d).  Stopping pagination.', target_count)
            break
        moved: bool = await navigate_to_next_page(page)
        if not moved:
            logger.info('No more pages available.  Stopping pagination.')
            break
        page_number += 1
    if len(all_bids) > target_count:
        all_bids = all_bids[:target_count]
        logger.info('Trimmed result list to exactly %d bids.', target_count)
    logger.info(' Listing extraction complete: %d bids collected across %d pages ', len(all_bids), page_number)
    return all_bids