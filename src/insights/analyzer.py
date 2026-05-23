from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import INSIGHTS_JSON_PATH
def compute_multi_bidder_percentage(df: pd.DataFrame) -> float:
    if 'bid_id' not in df.columns or 'vendor_name' not in df.columns:
        print('[INSIGHT]  Missing columns for multi-bidder calculation')
        return 0.0
    vendor_counts: pd.Series = df.groupby('bid_id')['vendor_name'].nunique()
    if len(vendor_counts) == 0:
        return 0.0
    multi_bidder_count: int = (vendor_counts > 3).sum()
    total_bids: int = len(vendor_counts)
    percentage: float = multi_bidder_count / total_bids * 100
    print(f'[INSIGHT] Bids with >3 participants: {multi_bidder_count}/{total_bids} ({percentage:.1f}%)')
    return round(percentage, 2)
def compute_l1_l2_gap(df: pd.DataFrame) -> dict:
    empty_result: dict = {'average': 0.0, 'median': 0.0, 'min': 0.0, 'max': 0.0}
    if 'bid_id' not in df.columns or 'vendor_price' not in df.columns:
        print('[INSIGHT]  Missing columns for L1-L2 gap calculation')
        return empty_result
    gaps: list[float] = []
    for bid_id, group in df[df['vendor_price'] > 0].groupby('bid_id'):
        sorted_prices = sorted(group['vendor_price'].unique())
        if len(sorted_prices) < 2:
            continue
        l1: float = sorted_prices[0]
        l2: float = sorted_prices[1]
        if l1 == 0:
            continue
        gap_pct: float = (l2 - l1) / l1 * 100
        gaps.append(gap_pct)
    if not gaps:
        print('[INSIGHT] No valid L1-L2 gaps found')
        return empty_result
    gap_series = pd.Series(gaps)
    result: dict = {'average': round(gap_series.mean(), 2), 'median': round(gap_series.median(), 2), 'min': round(gap_series.min(), 2), 'max': round(gap_series.max(), 2)}
    print(f"[INSIGHT] L1-L2 gap: avg={result['average']}%, median={result['median']}%")
    return result
def find_repeat_winners(df: pd.DataFrame) -> list[dict]:
    if 'bid_id' not in df.columns or 'winner_name' not in df.columns:
        print('[INSIGHT]  Missing columns for repeat-winners analysis')
        return []
    winners = df[['bid_id', 'winner_name']].drop_duplicates()
    win_counts = winners.groupby('winner_name')['bid_id'].agg(['count', list])
    win_counts.columns = ['win_count', 'bid_ids']
    repeats = win_counts[win_counts['win_count'] >= 2].sort_values('win_count', ascending=False)
    result: list[dict] = []
    for vendor_name, row in repeats.iterrows():
        result.append({'vendor_name': vendor_name, 'win_count': int(row['win_count']), 'bid_ids': row['bid_ids']})
    print(f'[INSIGHT] Repeat winners: {len(result)} vendor(s) with ≥2 wins')
    return result
def category_distribution(df: pd.DataFrame) -> dict:
    if 'bid_id' not in df.columns or 'category' not in df.columns:
        print('[INSIGHT]  Missing columns for category distribution')
        return {}
    bids_per_category = df[['bid_id', 'category']].drop_duplicates().groupby('category').size().sort_values(ascending=False)
    result: dict = bids_per_category.to_dict()
    print(f'[INSIGHT] Categories found: {len(result)}')
    return result
def generate_summary_report(df: pd.DataFrame) -> dict:
    print('=' * 60)
    print('  INSIGHTS GENERATION')
    print('=' * 60)
    unique_bids: int = df['bid_id'].nunique() if 'bid_id' in df.columns else 0
    total_rows: int = len(df)
    report: dict[str, Any] = {'overview': {'total_bids': unique_bids, 'total_rows': total_rows, 'columns': list(df.columns)}, 'competition': {'multi_bidder_percentage': compute_multi_bidder_percentage(df)}, 'pricing': {'l1_l2_gap': compute_l1_l2_gap(df)}, 'vendors': {'repeat_winners': find_repeat_winners(df)}, 'categories': category_distribution(df)}
    anomaly_cols = [c for c in df.columns if c.startswith('anomaly_')]
    if anomaly_cols:
        anomaly_summary: dict = {}
        for col in anomaly_cols:
            if col == 'anomaly_count':
                continue
            anomaly_summary[col] = int(df[col].sum())
        report['anomalies'] = anomaly_summary
    print(f'\n✅ Report generated with {len(report)} sections')
    print('=' * 60)
    return report
def save_insights(report: dict, output_path: Path=INSIGHTS_JSON_PATH) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    def _default_serializer(obj: Any) -> Any:
        if hasattr(obj, 'item'):
            return obj.item()
        if hasattr(obj, 'tolist'):
            return obj.tolist()
        raise TypeError(f'Object of type {type(obj)} is not JSON serializable')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=_default_serializer, ensure_ascii=False)
    print(f'✅ Insights saved to: {output_path}')
if __name__ == '__main__':
    from config.settings import PROCESSED_CSV_PATH
    df = pd.read_csv(PROCESSED_CSV_PATH)
    report = generate_summary_report(df)
    save_insights(report)