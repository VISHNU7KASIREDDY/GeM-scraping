from __future__ import annotations
import sys
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import RAW_JSON_PATH, PROCESSED_CSV_PATH
from src.processing.cleaner import run_full_cleaning
from src.processing.anomaly import add_all_anomaly_flags

def main() -> None:
    print('=' * 60)
    print('  GeM DATA PROCESSING PIPELINE')
    print('=' * 60)
    if not RAW_JSON_PATH.exists():
        print(f'\n❌ Raw data not found at: {RAW_JSON_PATH}')
        print('   Run the scraper first: python scripts/run_scraper.py')
        sys.exit(1)
    print(f'\n📄 Input:  {RAW_JSON_PATH}')
    print(f'📄 Output: {PROCESSED_CSV_PATH}\n')
    df = run_full_cleaning(input_path=RAW_JSON_PATH, output_path=PROCESSED_CSV_PATH)
    print()
    df = add_all_anomaly_flags(df)
    PROCESSED_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_CSV_PATH, index=False, encoding='utf-8')
    print('\n' + '=' * 60)
    print('  📊 PROCESSING SUMMARY')
    print('=' * 60)
    print(f'  Total rows:         {len(df)}')
    if 'bid_id' in df.columns:
        print(f"  Unique bids:        {df['bid_id'].nunique()}")
    if 'vendor_name' in df.columns:
        print(f"  Unique vendors:     {df['vendor_name'].nunique()}")
    if 'is_complete' in df.columns:
        complete_pct = df['is_complete'].sum() / len(df) * 100
        print(f'  Data completeness:  {complete_pct:.1f}%')
    if 'is_duplicate' in df.columns:
        dup_count = df['is_duplicate'].sum()
        print(f'  Duplicate rows:     {dup_count}')
    if 'anomaly_count' in df.columns:
        anomalous = (df['anomaly_count'] > 0).sum()
        print(f'  Anomalous rows:     {anomalous}')
    if 'vendor_price' in df.columns:
        valid_prices = df[df['vendor_price'] > 0]['vendor_price']
        if not valid_prices.empty:
            print(f'\n  💰 Price Statistics:')
            print(f'     Min:    ₹{valid_prices.min():,.2f}')
            print(f'     Max:    ₹{valid_prices.max():,.2f}')
            print(f'     Mean:   ₹{valid_prices.mean():,.2f}')
            print(f'     Median: ₹{valid_prices.median():,.2f}')
    print(f'\n  ✅ Processed data saved to: {PROCESSED_CSV_PATH}')
    print('=' * 60)
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n🛑 Processing interrupted by user.')
        sys.exit(0)
    except Exception as e:
        print(f'\n❌ Processing failed: {e}')
        traceback.print_exc()
        sys.exit(1)