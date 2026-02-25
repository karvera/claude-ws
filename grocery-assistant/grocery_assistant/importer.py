"""Parse Amazon Privacy Central ZIP or CSV exports into Purchase records."""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .models import Purchase

# Candidate column name variations (matched case-insensitively)
_COL_ORDER_ID = ["order id", "order_id"]
_COL_DATE = ["order date", "order_date", "shipment date", "shipment_date"]
_COL_TITLE = ["title", "product name", "item name", "item title"]
_COL_ASIN = ["asin/isbn", "asin", "isbn"]
_COL_QUANTITY = ["quantity", "qty", "original quantity"]
_COL_PRICE = [
    "purchase price per unit",
    "unit price",
    "price per unit",
    "list price per unit",
    "item price",
]
_COL_CATEGORY = ["category"]
_COL_SELLER = ["seller"]
_COL_WEBSITE = ["website"]


def _normalize_header(headers: List[str]) -> Dict[str, str]:
    """Map logical field names to actual CSV column names (case-insensitive)."""
    lower = {h.lower().strip(): h for h in headers}

    def find(candidates: List[str]) -> Optional[str]:
        for c in candidates:
            if c in lower:
                return lower[c]
        return None

    mapping: Dict[str, str] = {}
    for logical, candidates in [
        ("order_id", _COL_ORDER_ID),
        ("date", _COL_DATE),
        ("title", _COL_TITLE),
        ("asin", _COL_ASIN),
        ("quantity", _COL_QUANTITY),
        ("price", _COL_PRICE),
        ("category", _COL_CATEGORY),
        ("seller", _COL_SELLER),
        ("website", _COL_WEBSITE),
    ]:
        col = find(candidates)
        if col:
            mapping[logical] = col

    return mapping


def _is_grocery_row(row: dict, col_map: Dict[str, str]) -> bool:
    """Return True if the row looks like a Whole Foods / Amazon Fresh purchase."""
    category = row.get(col_map.get("category", ""), "").lower()
    seller = row.get(col_map.get("seller", ""), "").lower()
    website = row.get(col_map.get("website", ""), "").lower()

    if "grocery" in category or "gourmet" in category or "fresh" in category:
        return True
    if "whole foods" in seller or "amazon fresh" in seller:
        return True
    # Amazon Privacy Central export uses Website column to identify Fresh/WF orders
    if "amazonfresh" in website or "primenow" in website or "amazon go" in website:
        return True
    return False


def _parse_date(raw: str) -> str:
    """Parse various date formats into YYYY-MM-DD; fall back to today."""
    raw = raw.strip()
    # Strip ISO 8601 timezone suffix (e.g. 2024-04-05T14:55:53Z)
    if "T" in raw:
        raw = raw.split("T")[0]
    for fmt in (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%m/%d/%y",
    ):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return date.today().isoformat()


def _parse_price(raw: str) -> float:
    cleaned = raw.strip().lstrip("$£€").replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_quantity(raw: str) -> int:
    try:
        return max(1, int(raw.strip()))
    except ValueError:
        return 1


def _rows_from_csv_text(text: str) -> Tuple[Dict[str, str], List[Dict]]:
    """Parse CSV text; return (col_map, rows)."""
    reader = csv.DictReader(io.StringIO(text))
    headers = list(reader.fieldnames or [])
    col_map = _normalize_header(headers)
    rows = list(reader)
    return col_map, rows


def _purchases_from_rows(
    rows: List[Dict],
    col_map: Dict[str, str],
    already_imported: Set[str],
    grocery_only: bool,
) -> Tuple[List[Tuple[str, Purchase]], int]:
    """
    Convert CSV rows to (asin, Purchase) tuples.
    Returns (new_purchases, skipped_count).
    """
    results: List[Tuple[str, Purchase]] = []
    skipped = 0

    for row in rows:
        if grocery_only and not _is_grocery_row(row, col_map):
            continue

        title = row.get(col_map.get("title", ""), "").strip()
        if not title:
            continue

        order_id = row.get(col_map.get("order_id", ""), "").strip()
        asin = row.get(col_map.get("asin", ""), "").strip()

        # Dedup key: order_id + (asin or title)
        dedup_key = f"{order_id}|{asin or title}"
        if dedup_key in already_imported:
            skipped += 1
            continue

        parsed_date = _parse_date(row.get(col_map.get("date", ""), ""))
        quantity = _parse_quantity(row.get(col_map.get("quantity", ""), "1"))
        price = _parse_price(row.get(col_map.get("price", ""), "0"))

        purchase = Purchase(
            order_id=order_id,
            date=parsed_date,
            quantity=quantity,
            price_per_unit=price,
            raw_title=title,
        )
        results.append((asin, purchase))

    return results, skipped


def parse_file(
    file_path: Path,
    already_imported: Set[str],
    grocery_only: bool = True,
) -> Tuple[List[Tuple[str, Purchase]], int, int]:
    """
    Parse a ZIP or CSV file.
    Returns ([(asin, Purchase), ...], skipped_count, total_rows_examined).
    """
    if file_path.suffix.lower() == ".zip":
        return _parse_zip(file_path, already_imported, grocery_only)
    return _parse_csv_file(file_path, already_imported, grocery_only)


def _parse_csv_file(
    file_path: Path,
    already_imported: Set[str],
    grocery_only: bool,
) -> Tuple[List[Tuple[str, Purchase]], int, int]:
    text = file_path.read_text(encoding="utf-8-sig", errors="replace")
    col_map, rows = _rows_from_csv_text(text)
    purchases, skipped = _purchases_from_rows(rows, col_map, already_imported, grocery_only)
    return purchases, skipped, len(purchases) + skipped


def _parse_zip(
    file_path: Path,
    already_imported: Set[str],
    grocery_only: bool,
) -> Tuple[List[Tuple[str, Purchase]], int, int]:
    all_purchases: List[Tuple[str, Purchase]] = []
    total_skipped = 0
    total_rows = 0

    with zipfile.ZipFile(file_path, "r") as zf:
        # Prefer files with "order" in the name, fall back to any CSV
        order_files = [
            name for name in zf.namelist()
            if "order" in name.lower() and name.lower().endswith(".csv")
        ]
        if not order_files:
            order_files = [name for name in zf.namelist() if name.lower().endswith(".csv")]

        for name in order_files:
            text = zf.read(name).decode("utf-8-sig", errors="replace")
            col_map, rows = _rows_from_csv_text(text)
            if not col_map.get("title"):
                continue  # not an order-like file
            purchases, skipped = _purchases_from_rows(rows, col_map, already_imported, grocery_only)
            all_purchases.extend(purchases)
            total_skipped += skipped
            total_rows += len(purchases) + skipped

    return all_purchases, total_skipped, total_rows
