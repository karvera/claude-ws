"""Compute purchase frequency statistics for grocery items."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional

from .models import GroceryItem


@dataclass
class ItemFrequency:
    id: str
    canonical_name: str
    category: str
    brand: str
    unit_size: str
    total_purchases: int        # number of purchase events
    total_units: int            # sum of quantities across all purchases
    avg_interval_days: Optional[float]  # None if bought only once
    last_purchased: str         # ISO date string
    predicted_next: Optional[str]       # ISO date string, None if avg_interval unknown


def compute_frequency(item: GroceryItem) -> ItemFrequency:
    purchases = sorted(item.purchases, key=lambda p: p.date)
    total_units = sum(p.quantity for p in purchases)

    intervals: List[float] = []
    for i in range(1, len(purchases)):
        try:
            d1 = date.fromisoformat(purchases[i - 1].date)
            d2 = date.fromisoformat(purchases[i].date)
            delta = (d2 - d1).days
            if delta > 0:
                intervals.append(float(delta))
        except ValueError:
            continue

    avg_interval = sum(intervals) / len(intervals) if intervals else None
    last_date_str = purchases[-1].date if purchases else date.today().isoformat()

    predicted_next: Optional[str] = None
    if avg_interval is not None:
        try:
            last = date.fromisoformat(last_date_str)
            predicted_next = (last + timedelta(days=round(avg_interval))).isoformat()
        except ValueError:
            pass

    return ItemFrequency(
        id=item.id,
        canonical_name=item.canonical_name,
        category=item.category,
        brand=item.brand,
        unit_size=item.unit_size,
        total_purchases=len(purchases),
        total_units=total_units,
        avg_interval_days=avg_interval,
        last_purchased=last_date_str,
        predicted_next=predicted_next,
    )


def compute_all_frequencies(items: List[GroceryItem]) -> List[ItemFrequency]:
    """Return frequency stats for all items with at least one purchase, sorted by purchase count."""
    freqs = [compute_frequency(item) for item in items if item.purchases]
    return sorted(freqs, key=lambda f: f.total_purchases, reverse=True)
