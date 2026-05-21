from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from typing import Any
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import RAW_JSON_PATH, PROCESSED_CSV_PATH
from src.models.schemas import ScrapedBid, Bid, BidResult, VendorEvaluation

def load_raw_data(filepath: Path) -> pd.DataFrame:
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f'Raw data file not found: {filepath}')
    with open(filepath, 'r', encoding='utf-8') as f:
        raw_list: list[dict[str, Any]] = json.load(f)
    print(f'[CLEAN] Loaded {len(raw_list)} bid(s) from {filepath.name}')
    all_rows: list[dict] = []
    for entry in raw_list:
        bid = Bid(**entry.get('bid', {}))
        result_data = entry.get('result')
        result = BidResult(**result_data) if result_data else None
        evaluations = [VendorEvaluation(**ev) for ev in entry.get('evaluations', [])]
        scraped_bid = ScrapedBid(bid=bid, result=result, evaluations=evaluations)
        all_rows.extend(scraped_bid.flatten_to_rows())
    df = pd.DataFrame(all_rows)
    print(f'[CLEAN] Flattened to {len(df)} row(s) × {len(df.columns)} column(s)')
    return df

def clean_currency(value: str) -> float:
    if value is None:
        return 0.0
    value = str(value).strip()
    if value == '' or value.upper() in ('N/A', 'NA', 'NIL', '-', 'NONE'):
        return 0.0
    value = value.replace('₹', '').replace('\xa0', '').strip()
    value = value.replace(',', '')
    try:
        return float(value)
    except ValueError:
        match = re.search('[\\d]+\\.?\\d*', value)
        if match:
            return float(match.group())
        return 0.0

def normalize_vendor_names(df: pd.DataFrame) -> pd.DataFrame:
    abbreviations: dict[str, str] = {'\\bpvt\\b': 'private', '\\bltd\\b': 'limited', '\\bcorp\\b': 'corporation', '\\binc\\b': 'incorporated', '\\bco\\b': 'company'}

    def _normalize(name: str) -> str:
        if not isinstance(name, str):
            return str(name)
        name = name.lower()
        name = name.strip()
        name = re.sub('\\s+', ' ', name)
        for pattern, replacement in abbreviations.items():
            name = re.sub(pattern, replacement, name)
        name = name.replace('.', '')
        return name
    name_columns = ['vendor_name', 'winner_name']
    for col in name_columns:
        if col in df.columns:
            df[col] = df[col].astype(str).apply(_normalize)
            print(f'[CLEAN] Normalised {col}: {df[col].nunique()} unique values')
    return df

def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    df['is_complete'] = ~df.isnull().any(axis=1)
    complete_count = df['is_complete'].sum()
    print(f'[CLEAN] Completeness: {complete_count}/{len(df)} rows are fully populated')
    for col in df.columns:
        if col == 'is_complete':
            continue
        if df[col].dtype == 'object':
            df[col] = df[col].fillna('Unknown')
        elif df[col].dtype in ('float64', 'int64', 'Float64', 'Int64'):
            df[col] = df[col].fillna(0)
        elif df[col].dtype == 'bool':
            df[col] = df[col].fillna(False)
    print(f"[CLEAN] Missing values filled (strings→'Unknown', numbers→0)")
    return df

def detect_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    if 'bid_id' in df.columns and 'vendor_name' in df.columns:
        df['is_duplicate'] = df.duplicated(subset=['bid_id', 'vendor_name'], keep=False)
        dup_count = df['is_duplicate'].sum()
        print(f'[CLEAN] Found {dup_count} duplicate row(s) across all bids')
    else:
        df['is_duplicate'] = False
        print('[CLEAN] ⚠ Missing bid_id/vendor_name columns — skipping duplicate check')
    return df

def run_full_cleaning(input_path: Path=RAW_JSON_PATH, output_path: Path=PROCESSED_CSV_PATH) -> pd.DataFrame:
    print('=' * 60)
    print('  DATA CLEANING PIPELINE')
    print('=' * 60)
    print('\n── Step 1/5: Loading raw data …')
    df = load_raw_data(input_path)
    print('\n── Step 2/5: Cleaning currency values …')
    currency_columns = ['vendor_price', 'winner_price']
    for col in currency_columns:
        if col in df.columns:
            df[col] = df[col].apply(clean_currency)
            print(f'   {col}: min={df[col].min():.2f}, max={df[col].max():.2f}')
    print('\n── Step 3/5: Normalising vendor names …')
    df = normalize_vendor_names(df)
    print('\n── Step 4/5: Handling missing values …')
    df = handle_missing_values(df)
    print('\n── Step 5/5: Detecting duplicates …')
    df = detect_duplicates(df)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding='utf-8')
    print(f'\n✅ Cleaned data saved to: {output_path}')
    print(f'   Shape: {df.shape[0]} rows × {df.shape[1]} columns')
    print('=' * 60)
    return df
if __name__ == '__main__':
    run_full_cleaning()