from dataclasses import dataclass, field, asdict
from typing import Optional
@dataclass
class Bid:
    bid_id: str = ''
    category: str = ''
    buyer: str = ''
    quantity: str = ''
    bid_value: str = ''
    award_date: str = ''
    detail_url: str = ''
    numeric_id: str = ''
    title: str = ''
    uom: str = ''
    start_date: str = ''
    end_date: str = ''
    bid_url: str = ''
    result_url: str = ''
    def to_dict(self) -> dict:
        return asdict(self)
@dataclass
class BidResult:
    bid_id: str = ''
    winner_name: str = ''
    winner_price: str = ''
    num_bidders: int = 0
    total_participants: int = 0
    result_date: str = ''
    def to_dict(self) -> dict:
        return asdict(self)
@dataclass
class VendorEvaluation:
    bid_id: str = ''
    vendor_name: str = ''
    vendor_rank: str = ''
    vendor_price: str = ''
    status_flag: str = ''
    remarks: str = ''
    def to_dict(self) -> dict:
        return asdict(self)
@dataclass
class ScrapedBid:
    bid: Bid
    result: Optional[BidResult] = None
    evaluations: list[VendorEvaluation] = field(default_factory=list)
    def to_dict(self) -> dict:
        return {'bid': self.bid.to_dict(), 'result': self.result.to_dict() if self.result else None, 'evaluations': [ev.to_dict() for ev in self.evaluations]}
    def flatten_to_rows(self) -> list[dict]:
        rows: list[dict] = []
        base_row: dict = self.bid.to_dict()
        if self.result:
            base_row.update(self.result.to_dict())
        else:
            base_row['winner_name'] = ''
            base_row['winner_price'] = ''
            base_row['num_bidders'] = 0
            base_row['total_participants'] = 0
            base_row['result_date'] = ''
        base_row['bid_id'] = self.bid.bid_id
        if self.evaluations:
            for evaluation in self.evaluations:
                row = base_row.copy()
                row.update(evaluation.to_dict())
                row['bid_id'] = self.bid.bid_id
                rows.append(row)
        else:
            base_row['vendor_name'] = ''
            base_row['vendor_rank'] = ''
            base_row['vendor_price'] = ''
            base_row['status_flag'] = ''
            base_row['remarks'] = ''
            rows.append(base_row)
        return rows