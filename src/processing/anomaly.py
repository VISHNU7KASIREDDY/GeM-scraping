from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
def flag_winner_not_lowest(df: pd.DataFrame) -> pd.DataFrame:
    df['anomaly_winner_not_lowest'] = False
    if 'vendor_price' not in df.columns or 'winner_price' not in df.columns:
        print('[ANOMALY]  Missing price columns  skipping winner-not-lowest check')
        return df
    if 'bid_id' not in df.columns:
        print('[ANOMALY]  Missing bid_id column  skipping winner-not-lowest check')
        return df
    valid_prices = df[df['vendor_price'] > 0]
    if valid_prices.empty:
        print('[ANOMALY] No valid vendor prices found  skipping check')
        return df
    min_price_per_bid = valid_prices.groupby('bid_id')['vendor_price'].min()
    for bid_id, min_price in min_price_per_bid.items():
        mask = (df['bid_id'] == bid_id) & (df['winner_price'] > 0)
        df.loc[mask & (df['winner_price'] > min_price), 'anomaly_winner_not_lowest'] = True
    flagged = df['anomaly_winner_not_lowest'].sum()
    print(f'[ANOMALY] Winner-not-lowest: {flagged} row(s) flagged')
    return df
def flag_single_bidder(df: pd.DataFrame) -> pd.DataFrame:
    df['anomaly_single_bidder'] = False
    if 'bid_id' not in df.columns or 'vendor_name' not in df.columns:
        print('[ANOMALY]  Missing columns  skipping single-bidder check')
        return df
    vendor_counts = df.groupby('bid_id')['vendor_name'].nunique()
    single_bid_ids = vendor_counts[vendor_counts == 1].index
    df.loc[df['bid_id'].isin(single_bid_ids), 'anomaly_single_bidder'] = True
    flagged_bids = len(single_bid_ids)
    print(f'[ANOMALY] Single-bidder: {flagged_bids} bid(s) flagged')
    return df
def flag_large_price_gap(df: pd.DataFrame, threshold: float=0.5) -> pd.DataFrame:
    df['anomaly_large_gap'] = False
    if 'bid_id' not in df.columns or 'vendor_price' not in df.columns:
        print('[ANOMALY]  Missing columns  skipping large-gap check')
        return df
    for bid_id, group in df[df['vendor_price'] > 0].groupby('bid_id'):
        sorted_prices = group['vendor_price'].sort_values().values
        if len(sorted_prices) < 2:
            continue
        l1_price = sorted_prices[0]
        l2_price = sorted_prices[1]
        if l1_price == 0:
            continue
        gap_ratio = (l2_price - l1_price) / l1_price
        if gap_ratio > threshold:
            df.loc[df['bid_id'] == bid_id, 'anomaly_large_gap'] = True
    flagged = df.loc[df['anomaly_large_gap'], 'bid_id'].nunique()
    print(f'[ANOMALY] Large price gap (>{threshold * 100:.0f}%): {flagged} bid(s) flagged')
    return df
def add_all_anomaly_flags(df: pd.DataFrame) -> pd.DataFrame:
    print('=' * 60)
    print('  ANOMALY DETECTION')
    print('=' * 60)
    df = flag_winner_not_lowest(df)
    df = flag_single_bidder(df)
    df = flag_large_price_gap(df)
    anomaly_columns = ['anomaly_winner_not_lowest', 'anomaly_single_bidder', 'anomaly_large_gap']
    df['anomaly_count'] = df[anomaly_columns].sum(axis=1).astype(int)
    total_anomalous = (df['anomaly_count'] > 0).sum()
    print(f'\n✅ Anomaly detection complete:')
    print(f'   Total rows:      {len(df)}')
    print(f'   Rows with ≥1 flag: {total_anomalous}')
    print(f"   Rows with ≥2 flags: {(df['anomaly_count'] >= 2).sum()}")
    print('=' * 60)
    return df
if __name__ == '__main__':
    from src.processing.cleaner import run_full_cleaning
    from config.settings import PROCESSED_CSV_PATH
    df = run_full_cleaning()
    df = add_all_anomaly_flags(df)
    df.to_csv(PROCESSED_CSV_PATH, index=False)
    print(f'\n✅ Updated CSV saved with anomaly flags: {PROCESSED_CSV_PATH}')