"""Data models for grocery items and purchase history."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List
from uuid import uuid4


@dataclass
class Purchase:
    order_id: str
    date: str           # ISO date string YYYY-MM-DD
    quantity: int
    price_per_unit: float
    raw_title: str      # original Amazon product title

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Purchase":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class GroceryItem:
    canonical_name: str
    category: str
    purchases: List[Purchase] = field(default_factory=list)
    brand: str = ""
    unit_size: str = ""
    asin: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict:
        d = asdict(self)
        d["purchases"] = [p.to_dict() for p in self.purchases]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "GroceryItem":
        purchases = [Purchase.from_dict(p) for p in data.get("purchases", [])]
        fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__ and k != "purchases"}
        return cls(purchases=purchases, **fields)
