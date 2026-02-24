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
    save_imported_order_ids,
    save_items,
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
def import_cmd(file: Path, api_key: str, all_categories: bool):
    """Import orders from an Amazon Privacy Central ZIP or CSV.

    FILE can be:

    \b
      - A ZIP from amazon.com/hz/privacy-central/data-requests/preview.html
      - A CSV from any Amazon order export

    Each row is matched to an existing item by ASIN; new items are normalized
    via OpenAI (requires OPENAI_API_KEY). Re-running with the same file is safe
    — already-imported orders are skipped automatically.
    """
    from .importer import parse_file
    from .normalizer import normalize_title

    if not api_key:
        console.print("[red]Error: OpenAI API key required for title normalization.[/red]")
        console.print("Set OPENAI_API_KEY or pass --api-key.")
        raise SystemExit(1)

    console.print(f"[bold]Parsing:[/bold] {file.name}")

    items = load_items()
    already_imported = load_imported_order_ids()
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

    with console.status("[bold]Normalizing product titles via OpenAI...[/bold]"):
        for asin, purchase in new_purchases:
            new_dedup_keys.add(f"{purchase.order_id}|{asin or purchase.raw_title}")

            # Find an existing item by ASIN first
            existing = find_item_by_asin(asin, items) if asin else None

            # Fall back to matching by raw title for ASIN-less rows
            if existing is None and not asin:
                title_lower = purchase.raw_title.lower()
                for it in items:
                    if any(p.raw_title.lower() == title_lower for p in it.purchases):
                        existing = it
                        break

            if existing is not None:
                existing.purchases.append(purchase)
                updated += 1
            else:
                cache_key = asin or purchase.raw_title
                if cache_key not in norm_cache:
                    norm_cache[cache_key] = normalize_title(purchase.raw_title, api_key)
                norm = norm_cache[cache_key]

                new_item = GroceryItem(
                    canonical_name=norm["canonical_name"],
                    category=norm["category"],
                    brand=norm["brand"],
                    unit_size=norm["unit_size"],
                    asin=asin,
                    purchases=[purchase],
                )
                items.append(new_item)
                added += 1

    save_items(items)
    already_imported |= new_dedup_keys
    save_imported_order_ids(already_imported)

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
