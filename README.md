#  GeM Bid Scraper

> Automated scraper for India's Government e-Marketplace (GeM) — extracts bid listings, results, vendor evaluations, and generates procurement insights.

---

##  Project Structure

```
GeM-scraping/

 config/
    __init__.py
    settings.py              # Central configuration (paths, URLs, settings)

 src/
    __init__.py
    browser/
       __init__.py
       driver.py            # BrowserManager — Playwright wrapper
   
    models/
       __init__.py
       schemas.py           # Data models: Bid, BidResult, VendorEvaluation, ScrapedBid
   
    scrapers/
       __init__.py
       filter.py            # Apply search filters on GeM portal
       listing.py           # Scrape bid listing cards
       bid_result.py        # Scrape bid results (winner info)
       evaluation.py        # Scrape vendor evaluation tables
   
    processing/
       __init__.py
       cleaner.py           # Data cleaning pipeline (currency, names, missing values)
       anomaly.py           # Anomaly detection (winner-not-lowest, single-bidder, etc.)
   
    insights/
        __init__.py
        analyzer.py          # Analytics: competition %, price gaps, repeat winners

 scripts/
    run_scraper.py           #  Main entry point — runs the full scraping pipeline
    run_processing.py        #  Standalone cleaning + anomaly detection
    run_insights.py          #  Standalone insights generation

 tests/
    __init__.py
    test_cleaner.py          # Unit tests for data cleaning functions
    test_schemas.py          # Unit tests for data model schemas

 docs/
    writeup.md               # Project writeup and documentation

 output/                      # Generated at runtime (git-ignored)
    raw/
       bids_raw.json        # Raw scraped data
    processed/
       bids_cleaned.csv     # Cleaned & anomaly-flagged data
    insights/
       summary_report.json  # Analytics report
    screenshots/             # Error/debug screenshots

 .env.example                 # Environment variable template
 requirements.txt             # Python dependencies
 README.md                    # This file
```

---

##  Prerequisites

- **Python 3.10+** — required for type hints and modern syntax
- **pip** — Python package manager
- **Git** — version control

---

##  Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/GeM-scraping.git
cd GeM-scraping
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate       # macOS / Linux
# venv\Scripts\activate        # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright browsers

```bash
playwright install chromium
```

### 5. Configure environment

```bash
cp .env.example .env
# Edit .env with your settings (if needed)
```

---

##  How to Run

### Full Pipeline (Scrape → Process → Analyse)

```bash
# Step 1: Scrape data from GeM portal
python scripts/run_scraper.py

# Step 2: Clean and flag anomalies
python scripts/run_processing.py

# Step 3: Generate insights report
python scripts/run_insights.py
```

### Individual Steps

| Command | What it does |
|:--------|:-------------|
| `python scripts/run_scraper.py` | Launches browser, scrapes GeM, saves raw JSON |
| `python scripts/run_processing.py` | Cleans raw data, detects anomalies, saves CSV |
| `python scripts/run_insights.py` | Analyses processed data, saves JSON report |

### Run Tests

```bash
python -m pytest tests/ -v
```

---

##  Output Files

| File | Format | Description |
|:-----|:-------|:------------|
| `output/raw/bids_raw.json` | JSON | Raw scraped bid data (nested structure) |
| `output/processed/bids_cleaned.csv` | CSV | Cleaned data with anomaly flags |
| `output/insights/summary_report.json` | JSON | Analytics report with competition, pricing, vendor insights |
| `output/screenshots/*.png` | PNG | Debug screenshots from failed scraping attempts |

---

##  Architecture Overview

```
               
   SCRAPER      CLEANER      ANOMALY      INSIGHTS   
                                      DETECTOR           ANALYZER   
 • Filters         • Currency                                       
 • Listings        • Names           • WinnerL1        • % Multi   
 • Results         • Missing         • Single bid       • L1-L2 gap 
 • Evals           • Dupes           • Price gap        • Repeats   
               
                                                                 
                                                                 
  bids_raw.json     bids_cleaned.csv    (updated CSV)      summary_report.json
```

### Data Flow

1. **Scraper** uses Playwright to navigate the GeM portal, extract bid cards, drill into each bid for results and vendor evaluations, then saves everything as nested JSON.

2. **Cleaner** loads the JSON, flattens the nested structure into tabular rows, parses Indian currency strings, normalises vendor names, fills missing values, and detects duplicates.

3. **Anomaly Detector** scans the cleaned data for suspicious patterns: winners who weren't the cheapest, bids with no competition, and unusually large price gaps.

4. **Insights Analyzer** computes aggregate statistics: competition health percentages, L1-L2 price gap distributions, repeat winner rankings, and category breakdowns.

---

##  Configuration

All settings live in `config/settings.py`:

| Setting | Default | Description |
|:--------|:--------|:------------|
| `HEADLESS` | `False` | Run browser without a visible window |
| `SLOW_MO` | `100` | Milliseconds between browser actions |
| `DEFAULT_TIMEOUT` | `30000` | Page timeout in milliseconds |
| `MAX_RETRIES` | `3` | Retry count for failed requests |
| `GEM_BASE_URL` | `https://bidplus.gem.gov.in/all-bids` | Starting URL |

---

##  Troubleshooting

### "Playwright not found"
```bash
pip install playwright
playwright install chromium
```

### "No bids found"
- The GeM portal may have changed its HTML structure
- Check `output/screenshots/` for debug screenshots
- Try running with `HEADLESS = False` in `config/settings.py` to watch the browser

### "ModuleNotFoundError"
- Make sure you're running from the project root directory
- Ensure your virtual environment is activated: `source venv/bin/activate`

### "Raw data file not found"
- Run the scraper first: `python scripts/run_scraper.py`
- Check that `output/raw/bids_raw.json` exists

### Tests failing
```bash
# Run with verbose output to see which tests fail
python -m pytest tests/ -v --tb=short

# Run a specific test file
python -m pytest tests/test_cleaner.py -v
```

---

##  License

This project is licensed under the MIT License.

```
MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```