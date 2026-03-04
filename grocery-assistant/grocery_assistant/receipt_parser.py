"""Parse grocery receipt images using OpenAI vision API."""

from __future__ import annotations

import base64
import json
from pathlib import Path

_SYSTEM_PROMPT = """\
You are a receipt parser. Given an image of a grocery store receipt, extract all purchased items.

Respond with valid JSON only — no markdown, no explanation. Use this exact schema:
{
  "store": "store name (e.g. Trader Joe's, Whole Foods, Kroger)",
  "date": "purchase date as YYYY-MM-DD or empty string if not visible",
  "items": [
    {
      "raw_title": "item name exactly as it appears on the receipt",
      "quantity": 1,
      "price_per_unit": 0.00
    }
  ]
}

Notes:
- For items sold by quantity (e.g. "6 @ $0.29"), set quantity to the count and price_per_unit to the unit price.
- For items with a single line price, set quantity to 1 and price_per_unit to that price.
- Exclude subtotals, taxes, totals, discounts, coupons, and payment lines.
- Return only actual purchased product lines."""

_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def parse_receipt_image(image_path: Path, api_key: str, model: str = "gpt-4o") -> dict:
    """
    Use OpenAI vision API to extract items from a receipt image.

    Returns a dict with keys:
      - store: str
      - date: str (YYYY-MM-DD or "")
      - items: list of {raw_title, quantity, price_per_unit}
    """
    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    media_type = _MEDIA_TYPES.get(image_path.suffix.lower(), "image/jpeg")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{image_data}",
                                "detail": "high",
                            },
                        },
                        {"type": "text", "text": "Extract all items from this receipt."},
                    ],
                },
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        return {
            "store": data.get("store", ""),
            "date": data.get("date", ""),
            "items": data.get("items", []),
        }
    except Exception as e:
        raise RuntimeError(f"Failed to parse receipt image: {e}") from e
