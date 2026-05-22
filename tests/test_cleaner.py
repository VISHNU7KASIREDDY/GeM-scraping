import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.processing.cleaner import clean_currency, normalize_vendor_names
import pandas as pd

class TestCleanCurrency:

    def test_clean_currency_normal(self) -> None:
        result: float = clean_currency('1,23,456.00')
        assert result == 123456.0, f'Expected 123456.0, got {result}'

    def test_clean_currency_with_symbol(self) -> None:
        result: float = clean_currency('₹1,23,456')
        assert result == 123456.0, f'Expected 123456.0, got {result}'

    def test_clean_currency_empty(self) -> None:
        result: float = clean_currency('')
        assert result == 0.0, f'Expected 0.0, got {result}'

    def test_clean_currency_na(self) -> None:
        result: float = clean_currency('N/A')
        assert result == 0.0, f'Expected 0.0, got {result}'

    def test_clean_currency_none(self) -> None:
        result: float = clean_currency(None)
        assert result == 0.0, f'Expected 0.0, got {result}'

    def test_clean_currency_plain_number(self) -> None:
        result: float = clean_currency('5000.50')
        assert result == 5000.5, f'Expected 5000.5, got {result}'

    def test_clean_currency_international_format(self) -> None:
        result: float = clean_currency('1,234,567.89')
        assert result == 1234567.89, f'Expected 1234567.89, got {result}'

    def test_clean_currency_nil(self) -> None:
        result: float = clean_currency('NIL')
        assert result == 0.0, f'Expected 0.0, got {result}'

class TestNormalizeVendorNames:

    def test_normalize_vendor_names_basic(self) -> None:
        df = pd.DataFrame({'vendor_name': ['ABC PVT LTD'], 'winner_name': ['XYZ Corp']})
        result_df = normalize_vendor_names(df)
        assert result_df['vendor_name'].iloc[0] == 'abc private limited', f"Got: {result_df['vendor_name'].iloc[0]}"

    def test_normalize_vendor_names_corp(self) -> None:
        df = pd.DataFrame({'vendor_name': ['Vendor A'], 'winner_name': ['XYZ CORP']})
        result_df = normalize_vendor_names(df)
        assert result_df['winner_name'].iloc[0] == 'xyz corporation', f"Got: {result_df['winner_name'].iloc[0]}"

    def test_normalize_preserves_other_text(self) -> None:
        df = pd.DataFrame({'vendor_name': ['SUNSHINE ENTERPRISES'], 'winner_name': ['Same']})
        result_df = normalize_vendor_names(df)
        assert result_df['vendor_name'].iloc[0] == 'sunshine enterprises'

    def test_normalize_strips_extra_spaces(self) -> None:
        df = pd.DataFrame({'vendor_name': ['  ABC   PVT   LTD  '], 'winner_name': ['test']})
        result_df = normalize_vendor_names(df)
        assert result_df['vendor_name'].iloc[0] == 'abc private limited'