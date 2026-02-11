"""Fetch and parse product details from e-commerce URLs."""

from __future__ import annotations

import json
from dataclasses import dataclass, fields as dataclass_fields
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup


class ScraperError(Exception):
    """Raised when fetching or parsing a product URL fails."""


@dataclass
class ProductDetails:
    """Raw product details extracted from a URL."""
    name: str = ""
    brand: str = ""
    color: str = ""
    size: str = ""
    material: str = ""
    category: str = ""
    description: str = ""
    price: str = ""
    image_url: str = ""
    source_url: str = ""


CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "shirt": ["shirt", "blouse", "top", "tee", "polo", "henley", "tank"],
    "pants": ["pants", "trousers", "jeans", "chinos", "shorts", "leggings"],
    "jacket": ["jacket", "coat", "blazer", "hoodie", "sweater", "cardigan", "parka", "vest", "fleece"],
    "shoes": ["shoes", "sneakers", "boots", "sandals", "loafers", "heels", "flats", "mules"],
    "dress": ["dress", "gown", "romper", "jumpsuit"],
    "skirt": ["skirt"],
    "accessory": ["hat", "scarf", "belt", "bag", "watch", "sunglasses", "jewelry", "tie", "socks", "gloves", "wallet"],
}


def fetch_page(url: str) -> str:
    """Fetch HTML content from a URL."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ShoppingAssistant/0.1)"}
    max_size = 5_000_000  # 5 MB
    try:
        resp = requests.get(url, headers=headers, timeout=15, stream=True)
        resp.raise_for_status()
        content_length = resp.headers.get("content-length")
        if content_length and int(content_length) > max_size:
            resp.close()
            raise ScraperError(f"Response too large ({int(content_length)} bytes, max {max_size})")
        chunks = []
        size = 0
        for chunk in resp.iter_content(decode_unicode=True):
            size += len(chunk)
            if size > max_size:
                resp.close()
                raise ScraperError(f"Response too large (exceeded {max_size} bytes)")
            chunks.append(chunk)
        return "".join(chunks)
    except requests.exceptions.MissingSchema:
        raise ScraperError(f"Invalid URL: {url}")
    except requests.exceptions.ConnectionError:
        raise ScraperError(f"Could not connect to {url}")
    except requests.exceptions.Timeout:
        raise ScraperError("Request timed out after 15 seconds")
    except requests.exceptions.HTTPError as e:
        raise ScraperError(f"Server returned HTTP {e.response.status_code}")
    except requests.exceptions.RequestException as e:
        raise ScraperError(str(e))


def extract_product_details(html: str, url: str) -> ProductDetails:
    """Extract product details from HTML using multiple strategies.

    Tries JSON-LD, OpenGraph, then meta/title fallback.
    Merges results with earlier strategies taking priority.
    """
    soup = BeautifulSoup(html, "html.parser")

    strategies = [
        _extract_from_json_ld(soup),
        _extract_from_opengraph(soup),
        _extract_from_meta_and_title(soup),
    ]

    merged = ProductDetails(source_url=url)
    for field in dataclass_fields(merged):
        if field.name == "source_url":
            continue
        for details in strategies:
            val = getattr(details, field.name)
            if val:
                setattr(merged, field.name, val)
                break

    return merged


def _find_product_in_json_ld(data: Any) -> Optional[Dict]:
    """Recursively search JSON-LD data for a Product object."""
    if isinstance(data, dict):
        type_val = data.get("@type", "")
        if isinstance(type_val, list):
            type_val = " ".join(type_val)
        if "Product" in type_val:
            return data
        # Check @graph
        if "@graph" in data:
            result = _find_product_in_json_ld(data["@graph"])
            if result:
                return result
        # Check nested values
        for v in data.values():
            if isinstance(v, (dict, list)):
                result = _find_product_in_json_ld(v)
                if result:
                    return result
    elif isinstance(data, list):
        for item in data:
            result = _find_product_in_json_ld(item)
            if result:
                return result
    return None


def _extract_from_json_ld(soup: BeautifulSoup) -> ProductDetails:
    """Extract product details from JSON-LD structured data."""
    details = ProductDetails()
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        product = _find_product_in_json_ld(data)
        if not product:
            continue

        details.name = _str(product.get("name", ""))
        details.description = _str(product.get("description", ""))
        details.color = _str(product.get("color", ""))
        details.material = _str(product.get("material", ""))
        details.category = _str(product.get("category", ""))

        # Brand can be a string or {"@type": "Brand", "name": "..."}
        brand = product.get("brand", "")
        if isinstance(brand, dict):
            details.brand = _str(brand.get("name", ""))
        else:
            details.brand = _str(brand)

        # Image can be a string, list, or {"url": "..."}
        image = product.get("image", "")
        if isinstance(image, list):
            image = image[0] if image else ""
        if isinstance(image, dict):
            image = image.get("url", "")
        details.image_url = _str(image)

        # Price from offers
        offers = product.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        price = offers.get("price", "")
        currency = offers.get("priceCurrency", "")
        if price:
            details.price = f"{currency} {price}".strip() if currency else str(price)

        break  # Use first product found

    return details


def _extract_from_opengraph(soup: BeautifulSoup) -> ProductDetails:
    """Extract product details from OpenGraph meta tags."""
    details = ProductDetails()

    def og(prop: str) -> str:
        tag = soup.find("meta", property=prop)
        return _str(tag.get("content", "")) if tag else ""

    details.name = og("og:title")
    details.description = og("og:description")
    details.image_url = og("og:image")
    details.brand = og("product:brand")
    details.color = og("product:color")

    price = og("product:price:amount") or og("og:price:amount")
    currency = og("product:price:currency") or og("og:price:currency")
    if price:
        details.price = f"{currency} {price}".strip() if currency else price

    return details


def _extract_from_meta_and_title(soup: BeautifulSoup) -> ProductDetails:
    """Fallback: extract from title and meta description."""
    details = ProductDetails()

    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        # Strip common store suffixes
        title = title_tag.string.strip()
        for sep in [" | ", " - ", " – ", " — ", " :: "]:
            if sep in title:
                title = title.split(sep)[0].strip()
        details.name = title

    desc_tag = soup.find("meta", attrs={"name": "description"})
    if desc_tag:
        details.description = _str(desc_tag.get("content", ""))

    return details


def _str(val: Any) -> str:
    """Safely convert a value to a stripped string."""
    if val is None:
        return ""
    return str(val).strip()


def map_to_wardrobe_fields(details: ProductDetails) -> Dict[str, str]:
    """Map extracted ProductDetails to WardrobeItem field names."""
    category, subcategory = _classify_category(details)

    # Build notes from source URL, price, and description
    notes_parts = []
    if details.source_url:
        notes_parts.append(f"From: {details.source_url}")
    if details.price:
        notes_parts.append(f"Price: {details.price}")
    if details.description:
        desc = details.description[:200]
        if len(details.description) > 200:
            desc += "..."
        notes_parts.append(desc)

    return {
        "category": category,
        "subcategory": subcategory,
        "color": details.color,
        "size": details.size,
        "brand": details.brand,
        "material": details.material,
        "occasion": "",
        "notes": "\n".join(notes_parts),
    }


def _classify_category(details: ProductDetails) -> tuple:
    """Classify product into category/subcategory using keyword matching."""
    text = f"{details.name} {details.category}".lower()

    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                # Use the product name as subcategory, or the matched keyword
                subcategory = details.name if details.name else kw
                return cat, subcategory

    # No match — return what we have, user will fill in
    return details.category, details.name
