import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / os.getenv('OUTPUT_DIR', 'output')
SESSION_STATE_PATH = PROJECT_ROOT / 'config' / 'session_state.json'
RAW_OUTPUT_DIR = OUTPUT_DIR / 'raw'
PROCESSED_OUTPUT_DIR = OUTPUT_DIR / 'processed'
INSIGHTS_OUTPUT_DIR = OUTPUT_DIR / 'insights'
SCREENSHOT_DIR = OUTPUT_DIR / 'screenshots'
RAW_JSON_PATH = RAW_OUTPUT_DIR / 'bids_raw.json'
PROCESSED_CSV_PATH = PROCESSED_OUTPUT_DIR / 'bids_processed.csv'
INSIGHTS_JSON_PATH = INSIGHTS_OUTPUT_DIR / 'summary_report.json'
BASE_URL = 'https://bidplus.gem.gov.in'
ALL_BIDS_URL = f'{BASE_URL}/all-bids'
BID_RESULT_URL_TEMPLATE = f'{BASE_URL}/showbidDocument/{ bid_id} '
GEM_USERNAME = os.getenv('GEM_USERNAME', '')
GEM_PASSWORD = os.getenv('GEM_PASSWORD', '')
HEADLESS = os.getenv('HEADLESS', 'true').lower() == 'true'
USER_AGENTS = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36']
VIEWPORT = {'width': 1920, 'height': 1080}
MIN_DELAY = float(os.getenv('MIN_DELAY', '2'))
MAX_DELAY = float(os.getenv('MAX_DELAY', '5'))
PAGE_LOAD_TIMEOUT = 60000
ELEMENT_TIMEOUT = 30000
TARGET_BID_COUNT = int(os.getenv('TARGET_BID_COUNT', '30'))
SELECTORS = {'search_box': '#searchBid', 'search_button': '#searchBidRA', 'bid_card': '.bid-info-card, .border.p-3.mb-3', 'bid_number': ".bid_no, [id^='bidNo']", 'bid_end_date': '.bid_end_date, .end-date', 'department': '.department, .org-name', 'item_description': '.item-desc, .bid-title', 'quantity': '.qty, .quantity', 'bid_value': '.est-value, .bid-value', 'view_bid_link': "a[href*='showbidDocument'], a[href*='bidDocument']", 'pagination_container': '.pagination', 'next_page': ".pagination .next a, a[aria-label='Next']", 'page_links': '.pagination li a', 'active_page': '.pagination .active', 'result_table': 'table.table, .bid-result-table', 'winner_row': 'tr.winner, tr:has(.L1)', 'vendor_rows': 'table tbody tr', 'evaluation_tab': "a[href*='evaluation'], .eval-tab", 'captcha_frame': "iframe[src*='captcha'], iframe[src*='turnstile'], #challenge-running"}
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
GEM_BASE_URL = ALL_BIDS_URL
DEFAULT_TIMEOUT = PAGE_LOAD_TIMEOUT
RAW_DIR = RAW_OUTPUT_DIR
PROCESSED_DIR = PROCESSED_OUTPUT_DIR
INSIGHTS_DIR = INSIGHTS_OUTPUT_DIR
SCREENSHOTS_DIR = SCREENSHOT_DIR