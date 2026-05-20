from __future__ import annotations
import sys
import logging
from pathlib import Path
from typing import Optional
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from playwright.async_api import Page
from bs4 import BeautifulSoup
from config.settings import DEFAULT_TIMEOUT
from src.models.schemas import Bid, BidResult
from src.browser.helpers import random_delay, safe_get_text, wait_and_click, take_debug_screenshot, check_for_captcha, handle_login_if_needed
logger = logging.getLogger(__name__)
DETAIL_PAGE_CONTENT: str = 'table, h4, label'

async def navigate_and_capture(page: Page, bid: Bid) -> tuple[bool, str]:
    target_url: str = bid.result_url or bid.bid_url
    if not target_url:
        logger.warning('Bid %s has no detail URL — cannot navigate.', bid.bid_id)
        return (False, '')
    logger.info('Navigating to detail page for bid %s → %s', bid.bid_id, target_url)
    try:
        await page.goto(target_url, wait_until='load', timeout=DEFAULT_TIMEOUT)
        await page.wait_for_timeout(1500)
    except Exception as exc:
        logger.error('Failed to navigate to %s: %s', target_url, exc)
        return (False, '')
    current_url = page.url
    is_sso = 'sso.gem.gov.in' in current_url
    is_homepage = 'gem.gov.in' in current_url and 'bidplus' not in current_url
    if is_sso or is_homepage:
        logger.info('SSO/redirect detected for %s, handling login...', bid.bid_id)
        try:
            await handle_login_if_needed(page, target_url)
            await page.goto(target_url, wait_until='load', timeout=DEFAULT_TIMEOUT)
            await page.wait_for_timeout(1500)
        except Exception as exc:
            logger.error('Login handling failed for %s: %s', bid.bid_id, exc)
            return (False, '')
    captured_html = ''
    try:
        captured_html = await page.content()
    except Exception as exc:
        logger.warning('Could not capture page content for %s: %s', bid.bid_id, exc)
    html_lower = captured_html.lower()
    has_bid_content = any((marker in html_lower for marker in ['collapseone', 'collapsetwo', 'collapsethree', 'seller', 'vendor', 'bidder', 'financial evaluation', 'technical evaluation', 'bid_price', 'bid-result']))
    if has_bid_content:
        logger.info('  ✓ Captured %d bytes of bid content for %s', len(captured_html), bid.bid_id)
        return (True, captured_html)
    else:
        logger.warning('  → Captured HTML for %s does not contain bid result markers (may be empty/redirect page)', bid.bid_id)
        return (False, captured_html)

async def extract_bid_result(page: Page, bid_id: str, captured_html: str='') -> Optional[BidResult]:
    logger.info('Extracting bid result for %s ...', bid_id)
    result = BidResult(bid_id=bid_id)
    html = captured_html
    if not html:
        try:
            html = await page.content()
        except Exception:
            logger.warning('Could not get page content for %s', bid_id)
            return result
    try:
        soup = BeautifulSoup(html, 'html.parser')
        for selector in ['div.result_date', 'span.result_date']:
            date_el = soup.select_one(selector)
            if date_el:
                result.result_date = date_el.get_text(strip=True)
                break
        table = None
        for panel_id in ['collapseThree', 'collapseTwo', 'collapseOne']:
            panel = soup.find(id=panel_id)
            if panel:
                table = panel.find('table')
                if table:
                    logger.info('  → Found table inside panel #%s', panel_id)
                    break
        if not table:
            for t in soup.find_all('table'):
                headers = [th.get_text(strip=True).lower() for th in t.find_all('th')]
                if any(('seller' in h or 'vendor' in h for h in headers)):
                    table = t
                    logger.info('  → Found table using fallback header search')
                    break
        if table:
            headers = [th.get_text(strip=True) for th in table.find_all('th')]
            logger.info('  → Table headers: %s', headers)
            name_idx = None
            price_idx = None
            rank_idx = None
            status_idx = None
            for i, h in enumerate(headers):
                h_lower = h.lower()
                if 'seller' in h_lower or 'vendor' in h_lower or 'bidder' in h_lower:
                    name_idx = i
                elif 'price' in h_lower or 'value' in h_lower or 'quote' in h_lower:
                    price_idx = i
                elif 'rank' in h_lower:
                    rank_idx = i
                elif 'status' in h_lower:
                    status_idx = i
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
                participant_count = 0
                for row_idx, r in enumerate(rows, 1):
                    cells = r.find_all('td')
                    if len(cells) < 2:
                        continue
                    vendor_name = ''
                    if name_idx is not None and name_idx < len(cells):
                        name_cell = cells[name_idx]
                        cid_span = name_cell.find('span', class_='cid')
                        if cid_span:
                            vendor_name = cid_span.get_text(strip=True)
                        else:
                            span = name_cell.find('span')
                            if span:
                                contents = span.contents
                                if contents and isinstance(contents[0], str):
                                    vendor_name = contents[0].strip()
                                else:
                                    vendor_name = span.get_text(strip=True)
                            else:
                                vendor_name = name_cell.get_text(strip=True)
                        if '(' in vendor_name:
                            vendor_name = vendor_name.split('(')[0]
                        vendor_name = vendor_name.split('\n')[0].split('\r')[0].strip()
                    if not vendor_name:
                        continue
                    participant_count += 1
                    price = ''
                    if price_idx is not None and price_idx < len(cells):
                        price_cell = cells[price_idx]
                        bid_price_span = price_cell.find('span', class_='bid_price')
                        if bid_price_span:
                            price = bid_price_span.get_text(strip=True)
                        else:
                            price = price_cell.get_text(strip=True)
                    rank = ''
                    if rank_idx is not None and rank_idx < len(cells):
                        rank = cells[rank_idx].get_text(strip=True)
                    if rank.upper() == 'L1':
                        result.winner_name = vendor_name
                        result.winner_price = price
                result.total_participants = participant_count
                result.num_bidders = participant_count
                logger.info('  ✓ Extracted %d participants, winner: %s', participant_count, result.winner_name or 'N/A')
                return result
    except Exception as e:
        logger.error('Error parsing result table for %s: %s', bid_id, e)
    return result

async def scrape_all_bid_results(page: Page, bids: list[Bid]) -> dict[str, BidResult]:
    total: int = len(bids)
    results: dict[str, BidResult] = {}
    logger.info('═══ Starting bid result extraction for %d bids ═══', total)
    for index, bid in enumerate(bids, start=1):
        logger.info('── Processing bid %d/%d: %s ──', index, total, bid.bid_id)
        try:
            nav_success, captured_html = await navigate_and_capture(page, bid)
            if not nav_success and bid.result_url and ('getBidResultView' in bid.result_url):
                alt_url = bid.result_url.replace('getBidResultView', 'getSinglePacketResultView')
                logger.info('Retrying with alternate URL pattern for bid %s: %s', bid.bid_id, alt_url)
                bid.result_url = alt_url
                nav_success, captured_html = await navigate_and_capture(page, bid)
            if not nav_success and (not captured_html):
                logger.warning('Skipping bid %s — no content captured.', bid.bid_id)
                continue
            bid_result: Optional[BidResult] = await extract_bid_result(page, bid.bid_id, captured_html)
            if bid_result is not None:
                results[bid.bid_id] = bid_result
                logger.info('  ✓ Result saved for %s (winner: %s)', bid.bid_id, bid_result.winner_name or 'N/A')
            else:
                logger.info('  → No result data available for %s.', bid.bid_id)
        except Exception as exc:
            logger.error('Unexpected error processing bid %s: %s', bid.bid_id, exc, exc_info=True)
        await random_delay()
    success_count: int = len(results)
    fail_count: int = total - success_count
    logger.info('═══ Bid result extraction complete: %d/%d successful, %d skipped ═══', success_count, total, fail_count)
    return results