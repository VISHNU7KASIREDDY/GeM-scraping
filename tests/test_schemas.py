import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.models.schemas import Bid, BidResult, VendorEvaluation, ScrapedBid

class TestBid:

    def test_bid_creation(self) -> None:
        bid = Bid(bid_id='GEM/2025/B/12345', title='Office Chairs', category='Furniture', quantity='100', uom='Nos', start_date='2025-01-01', end_date='2025-01-15', bid_url='https://bidplus.gem.gov.in/bid/12345')
        assert bid.bid_id == 'GEM/2025/B/12345'
        assert bid.title == 'Office Chairs'
        assert bid.category == 'Furniture'
        assert bid.quantity == '100'
        assert bid.uom == 'Nos'
        assert bid.start_date == '2025-01-01'
        assert bid.end_date == '2025-01-15'
        assert bid.bid_url == 'https://bidplus.gem.gov.in/bid/12345'

    def test_bid_defaults(self) -> None:
        bid = Bid()
        assert bid.bid_id == ''
        assert bid.title == ''
        assert bid.category == ''

    def test_bid_to_dict(self) -> None:
        bid = Bid(bid_id='GEM/2025/B/99', title='Laptops', category='IT Equipment')
        result = bid.to_dict()
        assert isinstance(result, dict)
        assert result['bid_id'] == 'GEM/2025/B/99'
        assert result['title'] == 'Laptops'
        assert result['category'] == 'IT Equipment'
        assert len(result) == 14

class TestScrapedBid:

    def _make_sample_scraped_bid(self, num_vendors: int=3) -> ScrapedBid:
        bid = Bid(bid_id='GEM/2025/B/100', title='Printers', category='IT Equipment', quantity='50')
        result = BidResult(winner_name='Best Tech Pvt Ltd', winner_price='₹1,50,000', total_participants=num_vendors, result_date='2025-02-01')
        evaluations = []
        for i in range(num_vendors):
            rank = f'L{i + 1}'
            ev = VendorEvaluation(vendor_name=f'Vendor {chr(65 + i)}', vendor_price=f'₹{(i + 1) * 50000}', vendor_rank=rank, status_flag='awarded' if i == 0 else 'qualified')
            evaluations.append(ev)
        return ScrapedBid(bid=bid, result=result, evaluations=evaluations)

    def test_scraped_bid_flatten_three_vendors(self) -> None:
        scraped = self._make_sample_scraped_bid(num_vendors=3)
        rows = scraped.flatten_to_rows()
        assert len(rows) == 3, f'Expected 3 rows, got {len(rows)}'
        assert isinstance(rows[0], dict)
        for row in rows:
            assert row['bid_id'] == 'GEM/2025/B/100'
        assert rows[0]['vendor_name'] == 'Vendor A'
        assert rows[1]['vendor_name'] == 'Vendor B'
        assert rows[2]['vendor_name'] == 'Vendor C'
        for row in rows:
            assert row['winner_name'] == 'Best Tech Pvt Ltd'

    def test_scraped_bid_flatten_no_result(self) -> None:
        bid = Bid(bid_id='GEM/2025/B/200', title='Desks')
        evaluations = [VendorEvaluation(vendor_name='Vendor X', vendor_price='₹10,000', vendor_rank='L1', status_flag='qualified')]
        scraped = ScrapedBid(bid=bid, result=None, evaluations=evaluations)
        rows = scraped.flatten_to_rows()
        assert len(rows) == 1
        assert rows[0]['winner_name'] == ''
        assert rows[0]['winner_price'] == ''
        assert rows[0]['total_participants'] == 0
        assert rows[0]['bid_id'] == 'GEM/2025/B/200'
        assert rows[0]['vendor_name'] == 'Vendor X'

    def test_scraped_bid_flatten_no_evaluations(self) -> None:
        bid = Bid(bid_id='GEM/2025/B/300', title='Keyboards')
        result = BidResult(winner_name='Key Corp', winner_price='₹5,000')
        scraped = ScrapedBid(bid=bid, result=result, evaluations=[])
        rows = scraped.flatten_to_rows()
        assert len(rows) == 1
        assert rows[0]['bid_id'] == 'GEM/2025/B/300'
        assert rows[0]['winner_name'] == 'Key Corp'
        assert rows[0]['vendor_name'] == ''

    def test_scraped_bid_to_dict(self) -> None:
        scraped = self._make_sample_scraped_bid(num_vendors=2)
        result = scraped.to_dict()
        assert isinstance(result, dict)
        assert 'bid' in result
        assert 'result' in result
        assert 'evaluations' in result
        assert len(result['evaluations']) == 2
        assert isinstance(result['evaluations'][0], dict)