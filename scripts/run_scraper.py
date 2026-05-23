from __future__ import annotations
import asyncio
import json
import sys
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import RAW_JSON_PATH, RAW_DIR, PROCESSED_DIR, INSIGHTS_DIR, SCREENSHOTS_DIR, OUTPUT_DIR, GEM_BASE_URL, DEFAULT_TIMEOUT, TARGET_BID_COUNT
from src.browser.driver import BrowserManager
from src.scrapers.filter import apply_filters, navigate_to_bids_page
from src.scrapers.listing import scrape_all_listings
from src.scrapers.bid_result import scrape_all_bid_results
from src.scrapers.evaluation import scrape_all_evaluations
from src.models.schemas import ScrapedBid
def ensure_directories() -> None:
    directories = [OUTPUT_DIR, RAW_DIR, PROCESSED_DIR, INSIGHTS_DIR, SCREENSHOTS_DIR]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f'  📁 {directory}')
async def run_pipeline() -> None:
    print('=' * 60)
    print('  GeM SCRAPER  Starting Pipeline')
    print('=' * 60)
    print('\n Ensuring output directories exist ')
    ensure_directories()
    async with BrowserManager() as browser_manager:
        page = await browser_manager.new_page()
        print('\n' + '' * 60)
        print('  STEP 0.5  Navigating to GeM portal')
        print('' * 60)
        await navigate_to_bids_page(page)
        print('\n' + '' * 60)
        print('  STEP 1 / 4  Applying search filters')
        print('' * 60)
        try:
            await apply_filters(page)
            print(' Filters applied successfully')
        except Exception as e:
            print(f'⚠ Filter application failed: {e}')
            print('  Continuing without filters ')
        print('\n' + '' * 60)
        print('  STEP 2 / 4  Scraping bid listings')
        print('' * 60)
        bids = await scrape_all_listings(page, target_count=TARGET_BID_COUNT)
        if not bids:
            print(' No bids found! Check filters or page structure.')
            print('  Taking a screenshot for debugging ')
            from src.browser.helpers import take_debug_screenshot
            await take_debug_screenshot(page, 'no_bids_found')
            return
        print(f'✅ Found {len(bids)} bid(s)')
        print('\n' + '' * 60)
        print('  STEP 2.5  Authenticating with GeM SSO')
        print('' * 60)
        login_url = None
        for bid in bids:
            if bid.result_url:
                login_url = bid.result_url
                break
        if login_url:
            print(f'🔑 Navigating to {login_url} to trigger SSO login...')
            try:
                await page.goto(login_url, wait_until='load', timeout=DEFAULT_TIMEOUT)
                await page.wait_for_timeout(2500)
                from src.browser.helpers import handle_login_if_needed
                await handle_login_if_needed(page, login_url)
                print(' Authentication complete')
            except Exception as e:
                print(f'⚠️ SSO Login flow encountered an error: {e}')
        else:
            print(' No bid result URLs found to trigger login.')
        if page.is_closed():
            print(' Browser page was closed. Re-opening a new page to resume...')
            page = await browser_manager.new_page()
        async def block_redirects(route):
            url = route.request.url
            resource_type = route.request.resource_type
            if resource_type == 'document':
                if 'auth/logout' in url or ('gem.gov.in' in url and 'bidplus' not in url and 'fulfilment' not in url and ('sso' not in url)):
                    print(f'  🛡️ Blocked redirect/logout navigation: {url}')
                    await route.fulfill(status=204, content_type='text/html', body='<html><body>blocked</body></html>')
                    return
            await route.continue_()
        try:
            await page.route('**', block_redirects)
        except Exception as e:
            print(f'⚠️ Could not register redirect protection (page might be closed): {e}')
        print('\n' + '' * 60)
        print('  STEP 3 / 4  Scraping bid results')
        print('' * 60)
        results = await scrape_all_bid_results(page, bids)
        print(f'✅ Got results for {len(results)} bid(s)')
        print('\n' + '' * 60)
        print('  STEP 4 / 4  Scraping vendor evaluations')
        print('' * 60)
        evaluations = await scrape_all_evaluations(page, bids)
        print(f'✅ Got evaluations for {len(evaluations)} bid(s)')
    print('\n Combining data into ScrapedBid objects ')
    scraped_bids: list[ScrapedBid] = []
    for bid in bids:
        scraped = ScrapedBid(bid=bid, result=results.get(bid.bid_id), evaluations=evaluations.get(bid.bid_id, []))
        scraped_bids.append(scraped)
    print(f'\n💾 Saving raw data to {RAW_JSON_PATH} …')
    raw_data = [sb.to_dict() for sb in scraped_bids]
    with open(RAW_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(raw_data, f, indent=2, ensure_ascii=False)
    print('\n' + '=' * 60)
    print(f'  ✅ Scraped {len(scraped_bids)} bids, saved to {RAW_JSON_PATH}')
    print('=' * 60)
if __name__ == '__main__':
    try:
        asyncio.run(run_pipeline())
    except KeyboardInterrupt:
        print('\n\n Scraping interrupted by user (Ctrl+C)')
        print('   Partial data may have been saved. Check output/raw/')
        sys.exit(0)
    except Exception as e:
        print('\n' + '=' * 60)
        print('   SCRAPER FAILED')
        print('=' * 60)
        print(f'  Error: {e}')
        print(f'\n  Full traceback:')
        traceback.print_exc()
        print(f'\n  💡 Tips:')
        print(f'     • Check your internet connection')
        print(f'     • Make sure Playwright is installed: playwright install chromium')
        print(f"     • Try running with HEADLESS=False to see what's happening")
        sys.exit(1)