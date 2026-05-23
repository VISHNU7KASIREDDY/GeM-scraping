from __future__ import annotations
import json
import sys
import traceback
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import PROCESSED_CSV_PATH, INSIGHTS_JSON_PATH
from src.insights.analyzer import generate_summary_report, save_insights

def pretty_print_report(report: dict) -> None:
    print('\n' + '=' * 60)
    print('  📊 INSIGHTS REPORT')
    print('=' * 60)
    overview = report.get('overview', {})
    print(f'\n  📋 Overview:')
    print(f"     Total bids analysed:  {overview.get('total_bids', 'N/A')}")
    print(f"     Total data rows:      {overview.get('total_rows', 'N/A')}")
    competition = report.get('competition', {})
    multi_pct = competition.get('multi_bidder_percentage', 0)
    print(f'\n  🏆 Competition:')
    print(f'     Bids with >3 participants: {multi_pct:.1f}%')
    if multi_pct > 50:
        print(f'     → Healthy competition across most bids ✅')
    elif multi_pct > 25:
        print(f'     → Moderate competition — room for improvement ⚠')
    else:
        print(f'     → Low competition — many bids lack competitive bidding ❌')
    pricing = report.get('pricing', {})
    gap = pricing.get('l1_l2_gap', {})
    print(f'\n  💰 L1-L2 Price Gap:')
    print(f"     Average:  {gap.get('average', 0):.2f}%")
    print(f"     Median:   {gap.get('median', 0):.2f}%")
    print(f"     Min:      {gap.get('min', 0):.2f}%")
    print(f"     Max:      {gap.get('max', 0):.2f}%")
    vendors = report.get('vendors', {})
    repeat_winners = vendors.get('repeat_winners', [])
    print(f'\n  🔁 Repeat Winners ({len(repeat_winners)} vendor(s)):')
    if repeat_winners:
        for i, winner in enumerate(repeat_winners[:5], start=1):
            name = winner.get('vendor_name', 'Unknown')
            count = winner.get('win_count', 0)
            print(f'     {i}. {name} — {count} win(s)')
        if len(repeat_winners) > 5:
            print(f'     … and {len(repeat_winners) - 5} more')
    else:
        print(f'     No repeat winners found.')
    categories = report.get('categories', {})
    print(f'\n  📂 Category Distribution ({len(categories)} categories):')
    if categories:
        for i, (cat, count) in enumerate(categories.items()):
            if i >= 10:
                print(f'     … and {len(categories) - 10} more categories')
                break
            print(f'     • {cat}: {count} bid(s)')
    else:
        print(f'     No category data available.')
    anomalies = report.get('anomalies', {})
    if anomalies:
        print(f'\n  ⚠ Anomalies Detected:')
        for flag, count in anomalies.items():
            label = flag.replace('anomaly_', '').replace('_', ' ').title()
            print(f'     • {label}: {count} row(s)')
    print('\n' + '=' * 60)

def main() -> None:
    print('=' * 60)
    print('  GeM INSIGHTS GENERATOR')
    print('=' * 60)
    if not PROCESSED_CSV_PATH.exists():
        print(f'\n❌ Processed data not found at: {PROCESSED_CSV_PATH}')
        print('   Run processing first: python scripts/run_processing.py')
        sys.exit(1)
    print(f'\n📄 Loading data from: {PROCESSED_CSV_PATH}')
    df = pd.read_csv(PROCESSED_CSV_PATH)
    print(f'   Loaded {len(df)} rows × {len(df.columns)} columns')
    report = generate_summary_report(df)
    save_insights(report, INSIGHTS_JSON_PATH)
    pretty_print_report(report)
    print(f'\n  📁 Full report saved to: {INSIGHTS_JSON_PATH}')
    print('=' * 60)
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n🛑 Insights generation interrupted by user.')
        sys.exit(0)
    except Exception as e:
        print(f'\n❌ Insights generation failed: {e}')
        traceback.print_exc()
        sys.exit(1)