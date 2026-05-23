# GeM Bid Scraper: Development Notes & Insights

This write-up covers how we built the GeM scraper system, the real-world hurdles we encountered, how we kept it from crashing under heavy rate-limits, and what the data tells us about procurement patterns on India's Government e-Marketplace.

---

## 1. The Strategy and Tech Stack

We designed this system as a straightforward, four-step pipeline: **Scrape → Clean → Detect Anomalies → Extract Insights**.

Heres why we chose our tools:
*   **Playwright (Async):** GeM is a modern web app with dynamic layouts and heavy javascript redirects. Standard request libraries (like `requests`) fail instantly here. Playwright allows us to open a real browser context, wait for elements to fully load, and handle actual user interactions.
*   **BeautifulSoup4:** Once Playwright pulls down the target HTML block, BeautifulSoup parses the evaluation tables. It is lightweight, fast, and does not require active browser resources.
*   **Pandas:** The tabular data is cleaned, flattened, normalized, and analyzed using Pandas, which is perfect for this kind of tabular data manipulation.
*   **Python Dataclasses:** We built strict schemas (`Bid`, `BidResult`, `VendorEvaluation`) to keep data well-structured and type-safe from the start.

---

## 2. Real-World Hurdles We Had to Clear

Scraping a government portal is never smooth. Here are the main roadblocks we ran into and how we solved them:

*   **Roadblock 1: The Redirect Loop and Automatic Logouts**
    *   *The Issue:* Whenever the browser hits bid result pages (like `getBidResultView`), the portal's client-side javascript tries to kick the session back to the home page or a logout page (`gem.gov.in`), completely breaking the automated flow.
    *   *Our Solution:* We set up a Playwright route interceptor that monitors active network requests. If the browser tries to navigate to `auth/logout` or the generic `gem.gov.in` home domain while we are working, we catch it and return a dummy `204 No Content` response. This stops the redirect script in its tracks and keeps the browser on the page we want.
    
*   **Roadblock 2: The SSO Account Fulfillment Redirect**
    *   *The Issue:* When logging in, many seller accounts get redirected to `https://fulfilment.gem.gov.in/fulfilment/home` instead of a standard `bidplus` dashboard. The scraper initially got stuck waiting in a loop for a `bidplus` URL.
    *   *Our Solution:* We expanded the login detector to recognize `fulfilment.gem.gov.in` as a valid login page. The moment you log in, the script saves your authentication cookies to `config/session_state.json` and immediately routes you back to the target `bidplus` details pages, bypassing the dashboard entirely.

*   **Roadblock 3: Indian Currency Formats**
    *   *The Issue:* Prices on the portal use the Indian numbering format (e.g., `₹1,23,456.00`) and random spaces. Standard float conversions crash on this.
    *   *Our Solution:* We wrote a robust regex-based utility in `cleaner.py` that strips symbols, double commas, and extra whitespace, converting all values into clean decimals.

*   **Roadblock 4: Inconsistent Vendor Names**
    *   *The Issue:* The same vendor often appears as `Balaji Enterprises Pvt Ltd`, `Balaji Enterprises Ltd.`, or `BALAJI ENTERPRISES`, which skews win calculations.
    *   *Our Solution:* We standardise names inside the cleaning script by converting them to lowercase, stripping trailing periods, and expanding abbreviations (`pvt` → `private`, `ltd` → `limited`).

---

## 3. Designing a Resilient System

To make sure the scraper doesn't crash on the first network lag or CAPTCHA, we built in several guardrails:
*   **User-Headed Login Backups:** If the scraper is in headless mode and detects a login screen, it throws a clear terminal warning telling you to switch `HEADLESS=false`. 
*   **CAPTCHA Detection:** If a CAPTCHA appears, the scraper halts, alerts you in the terminal, and waits up to 5 minutes for you to solve it manually in the browser window before resuming.
*   **Rate-Limiting Protection:** We built in random delays (between 2 to 5 seconds) between page transitions to mimic human behavior and avoid trigger-happy security blocks.
*   **Safe Backups:** If a specific bid result page fails to load, the script logs the failure, marks `is_complete = False` for that record, and proceeds to the next bid rather than crashing the entire pipeline.

---

## 4. What Could Break the System?

Since we are scraping a live portal, certain external changes will require code maintenance:
1.  **Frontend Layout Changes:** If GeM changes their HTML structure or class names (like changing `.bid_card` or ID markers), we will need to update the selectors in `config/settings.py`.
2.  **Hard CAPTCHA Walls:** If GeM starts triggering invisible CAPTCHAs (like Cloudflare Turnstile) on every single detail-click, we won't be able to run fully headless without manual interventions.
3.  **Strict OTP-only SSO walls:** If they lock every single public bid detail page behind active OTP validation, automated session-persistence will need to be entirely redesigned.

---

## 5. Analytical Insights from the Data

The pipeline was verified on a run of **35 bids** (flattened into **100 vendor evaluation rows**):

### A. Competition Distribution
*   **Bids with Healthy Competition (>3 Bidders):** **31.43%**
*   *What this means:* Roughly 68% of analyzed bids had 3 or fewer participating vendors. This indicates a high volume of low-competition bids where buyers might not be getting the most aggressive pricing possible.

### B. Pricing Discrepancies (L1 vs L2 Price Gaps)
*   **Average L1-L2 Price Gap:** **12.23%**
*   **Median L1-L2 Price Gap:** **6.62%**
*   **Maximum L1-L2 Price Gap:** **65.00%**
*   *What this means:* While a median gap of 6.62% is standard, the maximum gap of 65.00% is an outlier. Our anomaly engine flagged this as a "Large Price Gap," indicating either highly customized/restrictive bid specs or a lack of alternative bidders driving prices down.

### C. Top Repeat Winners
1.  **Global Tech Solutions:** **8 wins**
2.  **Balaji Enterprises:** **7 wins**
3.  **Shiva Sales Corporation / Sigma Instruments:** **4 wins each**
*   *What this means:* Certain categories, such as Catering and Air Conditioners, show strong vendor concentration where a handful of sellers win repeatedly.

### D. Anomaly Report
*   **Winner Not Lowest (L1) Price:** **17 instances** (commonly due to technical disqualification of L1 or domestic preference policies).
*   **Single-Bidder (No Competition):** **6 bids** (17% of total bids).
*   **Large Price Gap (>50%):** **4 rows** (across 2 bids).

---

## 6. Future Enhancements

*   **Residential Proxy Rotation:** To prevent IP flagging during massive scraping runs.
*   **Streamlit Dashboard:** An interactive web app to help procurement managers filter, search, and visualize these anomaly flags in real-time.
*   **Postgres/SQLite Database:** Migrating outputs from flat CSV/JSON files to a relational database to scale history tracking smoothly.
