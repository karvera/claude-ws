"""JSON file storage for wardrobe, preferences, and profile data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Union

from .models import WardrobeItem, Preferences, Profile

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _ensure_data_dir(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> dict | list:
    if path.exists():
        return json.loads(path.read_text())
    return {} if path.name != "wardrobe.json" else []


def _save_json(path: Path, data: dict | list) -> None:
    _ensure_data_dir(path.parent)
    path.write_text(json.dumps(data, indent=2))


# --- Wardrobe ---

def load_wardrobe(data_dir: Path = DEFAULT_DATA_DIR) -> list[WardrobeItem]:
    raw = _load_json(data_dir / "wardrobe.json")
    return [WardrobeItem.from_dict(item) for item in raw]


def save_wardrobe(items: list[WardrobeItem], data_dir: Path = DEFAULT_DATA_DIR) -> None:
    _save_json(data_dir / "wardrobe.json", [item.to_dict() for item in items])


def add_wardrobe_item(item: WardrobeItem, data_dir: Path = DEFAULT_DATA_DIR) -> None:
    items = load_wardrobe(data_dir)
    items.append(item)
    save_wardrobe(items, data_dir)


def remove_wardrobe_item(item_id: str, data_dir: Path = DEFAULT_DATA_DIR) -> bool:
    items = load_wardrobe(data_dir)
    filtered = [i for i in items if i.id != item_id]
    if len(filtered) == len(items):
        return False
    save_wardrobe(filtered, data_dir)
    return True


def get_wardrobe_item(item_id: str, data_dir: Path = DEFAULT_DATA_DIR) -> Optional[WardrobeItem]:
    for item in load_wardrobe(data_dir):
        if item.id == item_id:
            return item
    return None


def update_wardrobe_item(item_id: str, updates: dict, data_dir: Path = DEFAULT_DATA_DIR) -> bool:
    items = load_wardrobe(data_dir)
    for item in items:
        if item.id == item_id:
            for key, value in updates.items():
                if hasattr(item, key) and key not in ("id", "date_added"):
                    setattr(item, key, value)
            save_wardrobe(items, data_dir)
            return True
    return False


# --- Profile ---

def load_profile(data_dir: Path = DEFAULT_DATA_DIR) -> Profile:
    raw = _load_json(data_dir / "profile.json")
    return Profile.from_dict(raw) if raw else Profile()


def save_profile(profile: Profile, data_dir: Path = DEFAULT_DATA_DIR) -> None:
    _save_json(data_dir / "profile.json", profile.to_dict())


# --- Preferences ---

def load_preferences(data_dir: Path = DEFAULT_DATA_DIR) -> Preferences:
    raw = _load_json(data_dir / "preferences.json")
    return Preferences.from_dict(raw) if raw else Preferences()


def save_preferences(prefs: Preferences, data_dir: Path = DEFAULT_DATA_DIR) -> None:
    _save_json(data_dir / "preferences.json", prefs.to_dict())
