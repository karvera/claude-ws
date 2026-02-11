"""AI-powered shopping advisor using OpenAI's Responses API."""

from __future__ import annotations

import json
from typing import List

from .models import User, Profile, WardrobeItem


def build_prompt(
    item_description: str,
    wardrobe: list[WardrobeItem],
    profile: Profile,
    preferences: User,
) -> str:
    """Assemble a prompt with user context for product recommendations."""
    sections: list[str] = []

    # System framing
    sections.append(
        "You are a personal shopping advisor. The user wants to buy a specific clothing\n"
        "item. Use the context below about their body measurements, existing wardrobe,\n"
        "and style preferences to recommend specific products currently available for\n"
        "purchase online."
    )

    # Body Measurements
    has_profile = any([
        profile.height, profile.weight, profile.body_type,
        profile.chest, profile.waist, profile.hips, profile.inseam,
        profile.shoe_size, profile.shirt_size, profile.pant_size,
    ])

    if has_profile:
        lines = ["## Body Measurements & Profile"]
        field_labels = [
            ("Height", profile.height),
            ("Weight", profile.weight),
            ("Body type", profile.body_type),
            ("Chest", profile.chest),
            ("Waist", profile.waist),
            ("Hips", profile.hips),
            ("Inseam", profile.inseam),
            ("Shoe size", profile.shoe_size),
            ("Shirt size", ", ".join(profile.shirt_size) if profile.shirt_size else ""),
            ("Pant size", ", ".join(profile.pant_size) if profile.pant_size else ""),
        ]
        for label, value in field_labels:
            if value:
                lines.append(f"- {label}: {value}")
        sections.append("\n".join(lines))
    else:
        sections.append(
            "## Body Measurements & Profile\n"
            "No profile set — suggest standard sizing."
        )

    # Existing Wardrobe
    if wardrobe:
        lines = ["## Existing Wardrobe (suggest items that complement, not duplicate)"]
        for item in wardrobe:
            parts = [item.category, item.subcategory, item.color, f"size {item.size}"]
            if item.brand:
                parts.append(item.brand)
            if item.material:
                parts.append(item.material)
            if item.occasion:
                parts.append(f"({item.occasion})")
            lines.append("- " + ", ".join(parts))
        sections.append("\n".join(lines))
    else:
        sections.append(
            "## Existing Wardrobe\n"
            "Wardrobe is empty — recommend versatile foundational items."
        )

    # Style Preferences
    has_prefs = any([
        preferences.preferred_colors, preferences.avoided_colors,
        preferences.preferred_brands, preferences.preferred_materials,
        preferences.notes,
    ])

    if has_prefs:
        lines = ["## Style Preferences"]
        if preferences.preferred_colors:
            lines.append(f"- Preferred colors: {', '.join(preferences.preferred_colors)}")
        if preferences.avoided_colors:
            lines.append(f"- Avoided colors: {', '.join(preferences.avoided_colors)}")
        if preferences.preferred_brands:
            lines.append(f"- Preferred brands: {', '.join(preferences.preferred_brands)}")
        if preferences.preferred_materials:
            lines.append(f"- Material preferences: {preferences.preferred_materials}")
        if preferences.budget_range:
            for category, bounds in preferences.budget_range.items():
                low = bounds.get("min", "?")
                high = bounds.get("max", "?")
                lines.append(f"- Budget for {category}: ${low} - ${high}")
        if preferences.notes:
            lines.append(f"- Style notes: {preferences.notes}")
        sections.append("\n".join(lines))

    # Item Request
    sections.append(
        f"## Item Request\n"
        f"The user is looking for: **{item_description}**\n"
        f"\n"
        f"Search the web for this item and recommend 3 to 5 specific products currently\n"
        f"available for purchase. For each product, provide:\n"
        f"1. **Product name** -- the full product name\n"
        f"2. **Brand** -- the brand/manufacturer\n"
        f"3. **Price** -- current price (include currency)\n"
        f"4. **URL** -- a direct link to the product page\n"
        f"5. **Recommended size** -- based on the user's measurements above\n"
        f"6. **Why it fits** -- 1-2 sentences on why this product matches the user's\n"
        f"   style, preferences, and existing wardrobe\n"
        f"\n"
        f"Format your response as a JSON array of objects with these exact keys:\n"
        f'"name", "brand", "price", "url", "recommended_size", "why_it_fits".\n'
        f"Return ONLY the JSON array, no other text."
    )

    return "\n\n".join(sections)


def call_openai(prompt: str, api_key: str, model: str = "gpt-4o") -> str:
    """Send prompt to OpenAI Responses API with web search and return raw text."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model,
        tools=[{"type": "web_search_preview"}],
        input=prompt,
    )

    # Extract text from output items
    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if content.type == "output_text":
                    return content.text

    return ""


def parse_recommendations(raw_text: str) -> list[dict]:
    """Parse JSON recommendations from the AI response text."""
    text = raw_text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
        return [result]
    except (json.JSONDecodeError, ValueError):
        return [{"raw_text": raw_text}]
