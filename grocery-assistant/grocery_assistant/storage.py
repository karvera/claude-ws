"""JSON file storage for grocery items and import deduplication log."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Set

from .models import GroceryItem

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

ITEMS_FILE = "items.json"
IMPORT_LOG_FILE = "import_log.json"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default


def _save_json(path: Path, data) -> None:
    _ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2))


# --- Items ---

def load_items(data_dir: Path = DEFAULT_DATA_DIR) -> List[GroceryItem]:
    raw = _load_json(data_dir / ITEMS_FILE, [])
    return [GroceryItem.from_dict(item) for item in raw]


def save_items(items: List[GroceryItem], data_dir: Path = DEFAULT_DATA_DIR) -> None:
    _save_json(data_dir / ITEMS_FILE, [item.to_dict() for item in items])


def find_item_by_asin(asin: str, items: List[GroceryItem]) -> Optional[GroceryItem]:
    if not asin:
        return None
    for item in items:
        if item.asin == asin:
            return item
    return None


def find_item_by_id_prefix(prefix: str, items: List[GroceryItem]) -> Optional[GroceryItem]:
    for item in items:
        if item.id == prefix or item.id.startswith(prefix):
            return item
    return None


# --- Import log ---

def load_imported_order_ids(data_dir: Path = DEFAULT_DATA_DIR) -> Set[str]:
    raw = _load_json(data_dir / IMPORT_LOG_FILE, [])
    return set(raw)


def save_imported_order_ids(order_ids: Set[str], data_dir: Path = DEFAULT_DATA_DIR) -> None:
    _save_json(data_dir / IMPORT_LOG_FILE, sorted(order_ids))
