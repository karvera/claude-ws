"""CLI entry point using Click."""

from __future__ import annotations

from pathlib import Path

import click

from .analyzer import compute_all_frequencies
from .display import console, display_frequency_table, display_item_detail, display_stats
from .models import GroceryItem
from .storage import (
    find_item_by_asin,
    find_item_by_id_prefix,
    load_imported_order_ids,
    load_items,
    load_title_map,
    save_imported_order_ids,
    save_items,
    save_title_map,
)


@click.group()
def cli():
    """Grocery Assistant — track your Amazon / Whole Foods purchase history."""


@cli.command("import")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--api-key",
    envvar="OPENAI_API_KEY",
    default=None,
    help="OpenAI API key for title normalization (or set OPENAI_API_KEY)",
)
@click.option(
    "--all-categories",
    is_flag=True,
    default=False,
    help="Import all order rows, not just grocery/Whole Foods",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    default=False,
    help="Prompt to confirm AI-suggested matches for non-ASIN items",
)
def import_cmd(file: Path, api_key: str, all_categories: bool, interactive: bool):
    """Import orders from an Amazon Privacy Central ZIP or CSV.

    FILE can be:

    \b
      - A ZIP from amazon.com/hz/privacy-central/data-requests/preview.html
      - A CSV from any Amazon order export

    Each row is matched to an existing item by ASIN; new items are normalized
    via OpenAI (requires OPENAI_API_KEY). Re-running with the same file is safe
    — already-imported orders are skipped automatically.

    Use --interactive (-i) to be prompted when AI suggests a match for a title
    that has no ASIN (e.g. items from non-Amazon stores).
    """
    from .importer import parse_file
    from .normalizer import find_match, normalize_title

    if not api_key:
        console.print("[red]Error: OpenAI API key required for title normalization.[/red]")
        console.print("Set OPENAI_API_KEY or pass --api-key.")
        raise SystemExit(1)

    console.print(f"[bold]Parsing:[/bold] {file.name}")

    items = load_items()
    already_imported = load_imported_order_ids()
    title_map = load_title_map()
    grocery_only = not all_categories

    new_purchases, skipped, total = parse_file(file, already_imported, grocery_only)

    if total == 0:
        console.print("[yellow]No grocery order rows found in this file.[/yellow]")
        console.print("If you expected grocery rows, try --all-categories.")
        return

    console.print(
        f"Found [green]{len(new_purchases)}[/green] new row(s)"
        f"{f', skipped {skipped} already-imported' if skipped else ''}."
    )

    if not new_purchases:
        console.print("[green]Nothing new to import.[/green]")
        return

    added = 0
    updated = 0
    new_dedup_keys: set = set()

    # Cache normalization results per ASIN (or raw title) to avoid duplicate API calls
    norm_cache: dict[str, dict] = {}
    title_map_dirty = False

    with console.status("[bold]Normalizing product titles via OpenAI...[/bold]") as status:
        for asin, purchase in new_purchases:
            new_dedup_keys.add(f"{purchase.order_id}|{asin or purchase.raw_title}")

            # Fast path: match by ASIN
            existing = find_item_by_asin(asin, items) if asin else None

            # title_map lookup (for previously confirmed non-ASIN matches)
            if existing is None and not asin:
                title_key = purchase.raw_title.lower()
                mapped_id = title_map.get(title_key)
                if mapped_id:
                    existing = next((it for it in items if it.id == mapped_id), None)

            # Exact raw_title match in purchase history (ASIN-less rows)
            if existing is None and not asin:
                title_lower = purchase.raw_title.lower()
                for it in items:
                    if any(p.raw_title.lower() == title_lower for p in it.purchases):
                        existing = it
                        break

            if existing is not None:
                existing.purchases.append(purchase)
                updated += 1
                continue

            # New item — normalize via OpenAI
            cache_key = asin or purchase.raw_title
            if cache_key not in norm_cache:
                if interactive and not asin:
                    # Ask AI whether it matches any existing item
                    status.stop()
                    candidate_names = [it.canonical_name for it in items]
                    norm_cache[cache_key] = find_match(purchase.raw_title, candidate_names, api_key)
                    status.start()
                else:
                    norm_cache[cache_key] = normalize_title(purchase.raw_title, api_key)

            norm = norm_cache[cache_key]

            # Interactive confirmation when AI found a potential match
            if interactive and not asin and norm.get("matched"):
                suggested_name = norm["canonical_name"]
                matched_item = next((it for it in items if it.canonical_name == suggested_name), None)
                short_id = matched_item.id[:8] if matched_item else "?"

                status.stop()
                console.print(
                    f"\n[bold]AI suggests:[/bold] \"{purchase.raw_title[:60]}\"\n"
                    f"  → [cyan]{suggested_name}[/cyan] [dim](id: {short_id})[/dim]"
                )
                choice = click.prompt(
                    "  [y] accept  [n] new item  [e] edit name",
                    default="y",
                ).strip().lower()

                if choice == "y" and matched_item:
                    matched_item.purchases.append(purchase)
                    title_map[purchase.raw_title.lower()] = matched_item.id
                    title_map_dirty = True
                    updated += 1
                    status.start()
                    continue
                elif choice == "e":
                    custom_name = click.prompt("  Enter canonical name").strip()
                    # Check if it matches an existing item by canonical name
                    name_match = next(
                        (it for it in items if it.canonical_name.lower() == custom_name.lower()), None
                    )
                    if name_match:
                        name_match.purchases.append(purchase)
                        title_map[purchase.raw_title.lower()] = name_match.id
                        title_map_dirty = True
                        updated += 1
                        status.start()
                        continue
                    # Use custom_name for the new item below
                    norm = {**norm, "canonical_name": custom_name}
                # choice == "n" or unrecognized → fall through to create new item
                status.start()

            new_item = GroceryItem(
                canonical_name=norm["canonical_name"],
                category=norm.get("category", "other"),
                brand=norm.get("brand", ""),
                unit_size=norm.get("unit_size", ""),
                asin=asin,
                purchases=[purchase],
            )
            items.append(new_item)
            added += 1

    save_items(items)
    already_imported |= new_dedup_keys
    save_imported_order_ids(already_imported)
    if title_map_dirty:
        save_title_map(title_map)

    console.print(
        f"[green]Done.[/green] "
        f"Added {added} new item(s), updated {updated} existing item(s)."
    )


@cli.command("import-receipt")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--api-key",
    envvar="OPENAI_API_KEY",
    default=None,
    help="OpenAI API key (or set OPENAI_API_KEY)",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    default=False,
    help="Prompt to confirm AI-suggested matches",
)
def import_receipt_cmd(file: Path, api_key: str, interactive: bool):
    """Import grocery items from a receipt image using OpenAI vision.

    FILE must be a photo of a grocery receipt (JPEG, PNG, or WebP).
    Items are normalized via OpenAI and matched against existing items.
    Re-running with the same receipt image is safe — already-imported
    items are skipped automatically.
    """
    import hashlib
    from datetime import date

    from .models import Purchase
    from .normalizer import find_match, normalize_title
    from .receipt_parser import parse_receipt_image

    if not api_key:
        console.print("[red]Error: OpenAI API key required for receipt parsing.[/red]")
        console.print("Set OPENAI_API_KEY or pass --api-key.")
        raise SystemExit(1)

    console.print(f"[bold]Parsing receipt image:[/bold] {file.name}")

    with console.status("[bold]Extracting items from receipt via OpenAI vision...[/bold]"):
        receipt = parse_receipt_image(file, api_key)

    store = receipt.get("store", "")
    date_str = receipt.get("date", "") or date.today().isoformat()
    items_data = receipt.get("items", [])

    if not items_data:
        console.print("[yellow]No items found in receipt.[/yellow]")
        return

    store_label = f"[cyan]{store}[/cyan]" if store else "unknown store"
    console.print(
        f"Detected [green]{len(items_data)}[/green] item(s)"
        f" from {store_label} on {date_str}."
    )

    # Stable receipt ID from file content hash — enables safe re-runs
    receipt_id = hashlib.sha256(file.read_bytes()).hexdigest()[:12]

    items = load_items()
    already_imported = load_imported_order_ids()
    title_map = load_title_map()

    new_purchases: list[tuple[str, Purchase]] = []
    new_dedup_keys: set[str] = set()
    skipped = 0

    for idx, item_data in enumerate(items_data):
        raw_title = item_data.get("raw_title", "").strip()
        if not raw_title:
            continue
        # order_id encodes receipt + line index so duplicates on the same receipt are tracked separately
        order_id = f"receipt:{receipt_id}:{idx}"
        dedup_key = f"{order_id}|{raw_title}"
        if dedup_key in already_imported:
            skipped += 1
            continue

        quantity = max(1, int(item_data.get("quantity", 1)))
        price = float(item_data.get("price_per_unit", 0.0))

        purchase = Purchase(
            order_id=order_id,
            date=date_str,
            quantity=quantity,
            price_per_unit=price,
            raw_title=raw_title,
            store=store,
            source="receipt",
        )
        new_purchases.append(("", purchase))
        new_dedup_keys.add(dedup_key)

    if skipped:
        console.print(f"Skipped {skipped} already-imported item(s).")

    if not new_purchases:
        console.print("[green]Nothing new to import.[/green]")
        return

    added = 0
    updated = 0
    norm_cache: dict[str, dict] = {}
    title_map_dirty = False

    with console.status("[bold]Normalizing product titles via OpenAI...[/bold]") as status:
        for _asin, purchase in new_purchases:
            # title_map lookup (previously confirmed matches)
            title_key = purchase.raw_title.lower()
            existing = None
            mapped_id = title_map.get(title_key)
            if mapped_id:
                existing = next((it for it in items if it.id == mapped_id), None)

            # Exact raw_title match in purchase history
            if existing is None:
                for it in items:
                    if any(p.raw_title.lower() == title_key for p in it.purchases):
                        existing = it
                        break

            if existing is not None:
                existing.purchases.append(purchase)
                updated += 1
                continue

            # New item — normalize via OpenAI
            cache_key = purchase.raw_title
            if cache_key not in norm_cache:
                if interactive:
                    status.stop()
                    candidate_names = [it.canonical_name for it in items]
                    norm_cache[cache_key] = find_match(purchase.raw_title, candidate_names, api_key)
                    status.start()
                else:
                    norm_cache[cache_key] = normalize_title(purchase.raw_title, api_key)

            norm = norm_cache[cache_key]

            if interactive and norm.get("matched"):
                suggested_name = norm["canonical_name"]
                matched_item = next((it for it in items if it.canonical_name == suggested_name), None)
                short_id = matched_item.id[:8] if matched_item else "?"

                status.stop()
                console.print(
                    f"\n[bold]AI suggests:[/bold] \"{purchase.raw_title[:60]}\"\n"
                    f"  → [cyan]{suggested_name}[/cyan] [dim](id: {short_id})[/dim]"
                )
                choice = click.prompt(
                    "  [y] accept  [n] new item  [e] edit name",
                    default="y",
                ).strip().lower()

                if choice == "y" and matched_item:
                    matched_item.purchases.append(purchase)
                    title_map[title_key] = matched_item.id
                    title_map_dirty = True
                    updated += 1
                    status.start()
                    continue
                elif choice == "e":
                    custom_name = click.prompt("  Enter canonical name").strip()
                    name_match = next(
                        (it for it in items if it.canonical_name.lower() == custom_name.lower()), None
                    )
                    if name_match:
                        name_match.purchases.append(purchase)
                        title_map[title_key] = name_match.id
                        title_map_dirty = True
                        updated += 1
                        status.start()
                        continue
                    norm = {**norm, "canonical_name": custom_name}
                status.start()

            from .models import GroceryItem

            new_item = GroceryItem(
                canonical_name=norm["canonical_name"],
                category=norm.get("category", "other"),
                brand=norm.get("brand", ""),
                unit_size=norm.get("unit_size", ""),
                asin="",
                purchases=[purchase],
            )
            items.append(new_item)
            added += 1

    save_items(items)
    already_imported |= new_dedup_keys
    save_imported_order_ids(already_imported)
    if title_map_dirty:
        save_title_map(title_map)

    console.print(
        f"[green]Done.[/green] "
        f"Added {added} new item(s), updated {updated} existing item(s)."
    )


@cli.command("list")
@click.option("--category", "-c", default=None, help="Filter by category (e.g. dairy, produce)")
@click.option(
    "--sort",
    default="frequency",
    type=click.Choice(["frequency", "name", "last", "next"]),
    show_default=True,
    help="Sort order",
)
def list_cmd(category: str, sort: str):
    """List all grocery items with purchase frequency."""
    items = load_items()
    freqs = compute_all_frequencies(items)

    if category:
        freqs = [f for f in freqs if f.category.lower() == category.lower()]

    if sort == "name":
        freqs = sorted(freqs, key=lambda f: f.canonical_name.lower())
    elif sort == "last":
        freqs = sorted(freqs, key=lambda f: f.last_purchased, reverse=True)
    elif sort == "next":
        freqs = sorted(freqs, key=lambda f: f.predicted_next or "9999")
    # "frequency" is already default from compute_all_frequencies

    title = "Grocery Purchase Frequency"
    if category:
        title += f" — {category}"

    display_frequency_table(freqs, title=title)


@cli.command("stats")
def stats_cmd():
    """Show a summary: top items, category breakdown, and overdue items."""
    items = load_items()
    freqs = compute_all_frequencies(items)
    display_stats(freqs)


@cli.command("show")
@click.argument("item_id")
def show_cmd(item_id: str):
    """Show full purchase history for a specific item (supports ID prefix)."""
    items = load_items()
    item = find_item_by_id_prefix(item_id, items)
    if item is None:
        console.print(f"[red]Item not found: {item_id}[/red]")
        raise SystemExit(1)
    display_item_detail(item)


if __name__ == "__main__":
    cli()
