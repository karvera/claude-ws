"""Data models for wardrobe items, preferences, and profile."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4


@dataclass
class WardrobeItem:
    category: str
    subcategory: str
    color: str
    size: str
    name: str = ""
    brand: str = ""
    material: str = ""
    occasion: str = ""
    price: str = ""
    notes: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))
    date_added: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WardrobeItem":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class User:
    id: str = field(default_factory=lambda: str(uuid4()))
    email: str = ""
    preferred_colors: List[str] = field(default_factory=list)
    avoided_colors: List[str] = field(default_factory=list)
    preferred_brands: List[str] = field(default_factory=list)
    preferred_materials: str = ""
    budget_range: Dict[str, Dict[str, float]] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


Preferences = User  # backward-compat alias


@dataclass
class Profile:
    height: str = ""
    weight: str = ""
    body_type: str = ""
    chest: str = ""
    waist: str = ""
    hips: str = ""
    inseam: str = ""
    shoe_size: str = ""
    shirt_size: List[str] = field(default_factory=list)
    pant_size: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
