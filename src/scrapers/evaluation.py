from __future__ import annotations
import sys
import logging
from pathlib import Path
from typing import Optional
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from playwright.async_api import Page
from bs4 import BeautifulSoup
from config.settings import DEFAULT_TIMEOUT
from src.models.schemas import Bid, VendorEvaluation
from src.browser.helpers import random_delay, safe_get_text, wait_and_click, take_debug_screenshot, check_for_captcha, handle_login_if_needed
logger = logging.getLogger(__name__)
async def find_evaluation_section(page: Page) -> bool:
    logger.info('Looking for evaluation section...')
    try:
        toggles = await page.query_selector_all(".panel-heading a, [data-toggle='collapse']")
        for toggle in toggles:
            text = (await toggle.inner_text()).lower()
            if 'evaluation' in text or 'technical' in text:
                await toggle.click()
                await page.wait_for_timeout(500)
    except Exception as exc:
        logger.debug('Could not click collapse toggles: %s', exc)
    try:
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        for panel_id in ['collapseThree', 'collapseTwo', 'collapseOne']:
            panel = soup.find(id=panel_id)
            if panel and panel.find('table'):
                logger.info('   Evaluation section found inside panel #%s', panel_id)
                return True
        for t in soup.find_all('table'):
            headers = [th.get_text(strip=True).lower() for th in t.find_all('th')]
            if any(('seller' in h or 'vendor' in h for h in headers)):
                logger.info('   Evaluation section found using fallback header search')
                return True
    except Exception as exc:
        logger.debug('Error checking section visibility: %s', exc)
    return False
async def extract_vendor_table(page: Page, bid_id: str) -> list[VendorEvaluation]:
    logger.info('Extracting vendor evaluation table for bid %s...', bid_id)
    vendors: list[VendorEvaluation] = []
    try:
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        table = None
        for panel_id in ['collapseThree', 'collapseTwo', 'collapseOne']:
            panel = soup.find(id=panel_id)
            if panel:
                table = panel.find('table')
                if table:
                    logger.info('   Found table inside panel #%s', panel_id)
                    break
        if not table:
            for t in soup.find_all('table'):
                headers = [th.get_text(strip=True).lower() for th in t.find_all('th')]
                if any(('seller' in h or 'vendor' in h for h in headers)):
                    table = t
                    logger.info('   Found table using fallback header search')
                    break
        if table:
            headers = [th.get_text(strip=True) for th in table.find_all('th')]
            logger.info('   Table headers: %s', headers)
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
                    vendor = VendorEvaluation(bid_id=bid_id, vendor_name=vendor_name)
                    if price_idx is not None and price_idx < len(cells):
                        price_cell = cells[price_idx]
                        bid_price_span = price_cell.find('span', class_='bid_price')
                        if bid_price_span:
                            vendor.vendor_price = bid_price_span.get_text(strip=True)
                        else:
                            vendor.vendor_price = price_cell.get_text(strip=True)
                    if rank_idx is not None and rank_idx < len(cells):
                        vendor.vendor_rank = cells[rank_idx].get_text(strip=True)
                    if status_idx is not None and status_idx < len(cells):
                        vendor.status_flag = cells[status_idx].get_text(strip=True)
                    vendors.append(vendor)
                    logger.info('     Vendor #%d: Rank=%s, Name=%s, Price=%s, Status=%s', row_idx, vendor.vendor_rank or 'N/A', vendor.vendor_name[:30], vendor.vendor_price or 'N/A', vendor.status_flag or 'N/A')
    except Exception as e:
        logger.error('Error parsing vendor evaluation table for %s: %s', bid_id, e)
    return vendors
async def scrape_all_evaluations(page: Page, bids: list[Bid]) -> dict[str, list[VendorEvaluation]]:
    total: int = len(bids)
    evaluations: dict[str, list[VendorEvaluation]] = {}
    logger.info(' Starting evaluation extraction for %d bids ', total)
    for index, bid in enumerate(bids, start=1):
        logger.info(' Processing evaluation %d/%d: %s ', index, total, bid.bid_id)
        try:
            target_url: str = bid.result_url or bid.bid_url
            if not target_url:
                logger.warning('Skipping bid %s  no detail URL available.', bid.bid_id)
                continue
            logger.info('  Navigating to detail page: %s', target_url)
            try:
                await page.goto(target_url, wait_until='load', timeout=DEFAULT_TIMEOUT)
                await page.wait_for_timeout(1500)
            except Exception as nav_exc:
                logger.error('  Failed to load detail page for %s: %s', bid.bid_id, nav_exc)
                await take_debug_screenshot(page, f'eval_nav_fail_{bid.bid_id}')
                continue
            try:
                await handle_login_if_needed(page, target_url)
            except Exception as login_exc:
                logger.error('  Login handling failed for %s: %s', bid.bid_id, login_exc)
                continue
            try:
                await check_for_captcha(page)
            except Exception as captcha_exc:
                logger.error('  CAPTCHA detected for bid %s: %s', bid.bid_id, captcha_exc)
                continue
            final_url = page.url
            def is_valid_detail_url(url: str) -> bool:
                if 'bidplus.gem.gov.in' not in url:
                    return False
                path = url.split('bidplus.gem.gov.in')[-1].strip('/')
                if not path or path == 'dashboard' or path == 'home':
                    return False
                valid_keywords = ['getBidResultView', 'getSinglePacketResultView', 'showbidDocument', 'evaluation', 'bidding/bid', 'buyer-bid']
                return any((kw in url for kw in valid_keywords))
            if not is_valid_detail_url(final_url):
                logger.warning('Still not on a valid bidplus detail page for %s after login/navigation attempt (URL: %s)', bid.bid_id, final_url)
                if bid.result_url and 'getBidResultView' in bid.result_url:
                    alt_url = bid.result_url.replace('getBidResultView', 'getSinglePacketResultView')
                    logger.info('Retrying with alternate URL pattern for bid %s evaluation: %s', bid.bid_id, alt_url)
                    bid.result_url = alt_url
                    target_url = alt_url
                    try:
                        await page.goto(target_url, wait_until='load', timeout=DEFAULT_TIMEOUT)
                        await page.wait_for_timeout(1500)
                        await handle_login_if_needed(page, target_url)
                        await check_for_captcha(page)
                        final_url = page.url
                        if not is_valid_detail_url(final_url):
                            logger.warning('Still failed to reach detail page on retry for %s: %s', bid.bid_id, final_url)
                            continue
                    except Exception as retry_exc:
                        logger.error('Retry failed for %s: %s', bid.bid_id, retry_exc)
                        continue
                else:
                    continue
            await random_delay()
            section_found: bool = await find_evaluation_section(page)
            if not section_found:
                logger.info('   No evaluation section for bid %s.  Storing empty list.', bid.bid_id)
                evaluations[bid.bid_id] = []
                continue
            vendor_list: list[VendorEvaluation] = await extract_vendor_table(page, bid.bid_id)
            evaluations[bid.bid_id] = vendor_list
            logger.info('   Extracted %d vendor evaluation(s) for %s.', len(vendor_list), bid.bid_id)
        except Exception as exc:
            logger.error('Unexpected error processing evaluation for bid %s: %s', bid.bid_id, exc, exc_info=True)
            await take_debug_screenshot(page, f'eval_error_{bid.bid_id}')
        await random_delay()
    bids_with_data: int = sum((1 for v in evaluations.values() if v))
    bids_without_data: int = sum((1 for v in evaluations.values() if not v))
    bids_failed: int = total - len(evaluations)
    logger.info(' Evaluation extraction complete \n  Bids with evaluation data : %d\n  Bids with empty evaluation: %d\n  Bids failed/skipped       : %d\n  Total                     : %d', bids_with_data, bids_without_data, bids_failed, total)
    return evaluations