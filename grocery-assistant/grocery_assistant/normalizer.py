"""Normalize raw Amazon product titles to canonical grocery item info via OpenAI."""

from __future__ import annotations

import json

_SYSTEM_PROMPT = """\
You are a grocery item classifier. Given an Amazon product title, extract structured information.

Respond with valid JSON only — no markdown, no explanation. Use this exact schema:
{
  "canonical_name": "short common name (e.g. Whole Milk, Sourdough Bread, Ground Beef 80/20)",
  "category": "one of: dairy, produce, meat, bakery, pantry, frozen, beverages, snacks, household, other",
  "brand": "brand name or empty string if none",
  "unit_size": "package size (e.g. 1 gallon, 12 oz, 1 lb) or empty string if unclear"
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
