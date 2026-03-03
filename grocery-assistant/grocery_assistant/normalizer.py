"""Normalize raw product titles to canonical grocery item info via OpenAI."""

from __future__ import annotations

import json
from typing import List

_SYSTEM_PROMPT = """\
You are a grocery item classifier. Given an Amazon product title, extract structured information.

Respond with valid JSON only — no markdown, no explanation. Use this exact schema:
{
  "canonical_name": "short common name (e.g. Whole Milk, Sourdough Bread, Ground Beef 80/20)",
  "category": "one of: dairy, produce, meat, bakery, pantry, frozen, beverages, snacks, household, other",
  "brand": "brand name or empty string if none",
  "unit_size": "package size (e.g. 1 gallon, 12 oz, 1 lb) or empty string if unclear"
}"""

_MATCH_SYSTEM_PROMPT = """\
You are a grocery item matcher. Given a raw product title and a list of existing canonical grocery item names, \
determine whether the raw title refers to the same product as any item on the list.

Rules:
- Match if the product is the same regardless of brand, size, or store
- Do NOT match if the product type is clearly different
- Respond with valid JSON only — no markdown, no explanation

If a match is found, respond with:
{"matched": true, "canonical_name": "<exact name from the list>"}

If no match is found, also extract structured info for a new item:
{
  "matched": false,
  "canonical_name": "short common name",
  "category": "one of: dairy, produce, meat, bakery, pantry, frozen, beverages, snacks, household, other",
  "brand": "brand name or empty string",
  "unit_size": "package size or empty string"
}"""


def normalize_title(raw_title: str, api_key: str, model: str = "gpt-4o-mini") -> dict:
    """
    Call OpenAI to extract canonical grocery info from a raw product title.
    Returns dict with keys: canonical_name, category, brand, unit_size.
    Falls back to a safe minimal dict on any error.
    """
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f'Product title: "{raw_title}"'},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        return {
            "canonical_name": data.get("canonical_name", raw_title[:80]),
            "category": data.get("category", "other"),
            "brand": data.get("brand", ""),
            "unit_size": data.get("unit_size", ""),
        }
    except Exception:
        return {
            "canonical_name": raw_title[:80],
            "category": "other",
            "brand": "",
            "unit_size": "",
        }


def find_match(raw_title: str, candidates: List[str], api_key: str, model: str = "gpt-4o-mini") -> dict:
    """
    Check if raw_title matches any item in candidates (list of canonical names).

    If candidates is empty, falls through to full normalization.

    Returns one of:
      {"matched": True,  "canonical_name": "<existing name>"}
      {"matched": False, "canonical_name": ..., "category": ..., "brand": ..., "unit_size": ...}
    """
    if not candidates:
        norm = normalize_title(raw_title, api_key, model)
        return {"matched": False, **norm}

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    candidates_str = "\n".join(f"- {name}" for name in candidates)
    user_msg = f'Raw title: "{raw_title}"\n\nExisting items:\n{candidates_str}'
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _MATCH_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        if data.get("matched"):
            return {
                "matched": True,
                "canonical_name": data.get("canonical_name", raw_title[:80]),
            }
        return {
            "matched": False,
            "canonical_name": data.get("canonical_name", raw_title[:80]),
            "category": data.get("category", "other"),
            "brand": data.get("brand", ""),
            "unit_size": data.get("unit_size", ""),
        }
    except Exception:
        return {
            "matched": False,
            "canonical_name": raw_title[:80],
            "category": "other",
            "brand": "",
            "unit_size": "",
        }
