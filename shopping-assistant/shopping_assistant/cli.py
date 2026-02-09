"""CLI entry point using Click."""

import click

from .models import WardrobeItem, Preferences, Profile
from .storage import (
    add_wardrobe_item,
    get_wardrobe_item,
    load_preferences,
    load_profile,
    load_wardrobe,
    remove_wardrobe_item,
    save_preferences,
    save_profile,
    update_wardrobe_item,
)
from .display import (
    console,
    display_preferences,
    display_profile,
    display_summary,
    display_wardrobe_item,
    display_wardrobe_table,
)


@click.group()
def cli():
    """Personal Shopping Assistant - manage your wardrobe and style."""


# --- Wardrobe commands ---

@cli.group()
def wardrobe():
    """Manage your wardrobe items."""


@wardrobe.command("add")
def wardrobe_add():
    """Add a new clothing item interactively."""
    console.print("[bold]Add a new wardrobe item[/bold]\n")

    category = click.prompt("Category (e.g., shirt, pants, jacket, shoes, accessory)")
    subcategory = click.prompt("Subcategory (e.g., dress shirt, t-shirt, chinos)")
    color = click.prompt("Color")
    size = click.prompt("Size")
    brand = click.prompt("Brand", default="", show_default=False)
    material = click.prompt("Material", default="", show_default=False)
    occasion = click.prompt("Occasion (casual/formal/athletic)", default="", show_default=False)
    season = click.prompt("Season (summer/winter/spring/fall/all)", default="", show_default=False)
    notes = click.prompt("Notes", default="", show_default=False)

    item = WardrobeItem(
        category=category,
        subcategory=subcategory,
        color=color,
        size=size,
        brand=brand,
        material=material,
        occasion=occasion,
        season=season,
        notes=notes,
    )

    add_wardrobe_item(item)
    console.print(f"\n[green]Added item {item.id[:8]}...[/green]")
    display_wardrobe_item(item)


@wardrobe.command("list")
@click.option("--category", "-c", default=None, help="Filter by category")
def wardrobe_list(category):
    """List all wardrobe items."""
    items = load_wardrobe()
    if category:
        items = [i for i in items if i.category.lower() == category.lower()]
    display_wardrobe_table(items)


@wardrobe.command("show")
@click.argument("item_id")
def wardrobe_show(item_id):
    """Show details of a specific item."""
    # Support short IDs (prefix match)
    items = load_wardrobe()
    match = None
    for item in items:
        if item.id == item_id or item.id.startswith(item_id):
            match = item
            break

    if match is None:
        console.print(f"[red]Item not found: {item_id}[/red]")
        raise SystemExit(1)
    display_wardrobe_item(match)


@wardrobe.command("remove")
@click.argument("item_id")
def wardrobe_remove(item_id):
    """Remove a wardrobe item."""
    # Support short IDs
    items = load_wardrobe()
    full_id = None
    for item in items:
        if item.id == item_id or item.id.startswith(item_id):
            full_id = item.id
            break

    if full_id is None:
        console.print(f"[red]Item not found: {item_id}[/red]")
        raise SystemExit(1)

    if remove_wardrobe_item(full_id):
        console.print(f"[green]Removed item {full_id[:8]}...[/green]")
    else:
        console.print(f"[red]Failed to remove item: {item_id}[/red]")


@wardrobe.command("edit")
@click.argument("item_id")
def wardrobe_edit(item_id):
    """Edit an existing wardrobe item."""
    items = load_wardrobe()
    item = None
    for i in items:
        if i.id == item_id or i.id.startswith(item_id):
            item = i
            break

    if item is None:
        console.print(f"[red]Item not found: {item_id}[/red]")
        raise SystemExit(1)

    console.print(f"[bold]Editing item {item.id[:8]}...[/bold]")
    console.print("[dim]Press Enter to keep current value.[/dim]\n")

    updates = {}
    for field_name in ("category", "subcategory", "color", "size", "brand", "material", "occasion", "season", "notes"):
        current = getattr(item, field_name)
        prompt_text = f"{field_name.capitalize()} [{current or ''}]"
        new_val = click.prompt(prompt_text, default=current, show_default=False)
        if new_val != current:
            updates[field_name] = new_val

    if updates:
        update_wardrobe_item(item.id, updates)
        console.print(f"\n[green]Updated item {item.id[:8]}...[/green]")
    else:
        console.print("\n[dim]No changes made.[/dim]")


# --- Profile commands ---

@cli.group()
def profile():
    """Manage your body measurements and profile."""


@profile.command("set")
def profile_set():
    """Set or update your profile interactively."""
    current = load_profile()
    console.print("[bold]Set your profile[/bold]")
    console.print("[dim]Press Enter to keep current value.[/dim]\n")

    fields = {
        "height": "Height (e.g., 5'10\", 178cm)",
        "weight": "Weight (e.g., 170lbs, 77kg)",
        "body_type": "Body type (e.g., athletic, slim, average)",
        "chest": "Chest measurement",
        "waist": "Waist measurement",
        "hips": "Hips measurement",
        "inseam": "Inseam measurement",
        "shoe_size": "Shoe size (e.g., 10 US, 43 EU)",
        "shirt_size": "Shirt size (e.g., M, L, 15.5)",
        "pant_size": "Pant size (e.g., 32x32, M)",
        "notes": "Notes",
    }

    data = {}
    for field_name, prompt_text in fields.items():
        current_val = getattr(current, field_name)
        display = f" [{current_val}]" if current_val else ""
        new_val = click.prompt(f"{prompt_text}{display}", default=current_val, show_default=False)
        data[field_name] = new_val

    new_profile = Profile(**data)
    save_profile(new_profile)
    console.print("\n[green]Profile saved.[/green]")
    display_profile(new_profile)


@profile.command("show")
def profile_show():
    """Display your current profile."""
    display_profile(load_profile())


# --- Preferences commands ---

@cli.group()
def preferences():
    """Manage your style preferences."""


def _prompt_list(prompt_text: str, current: list[str]) -> list[str]:
    """Prompt for a comma-separated list."""
    current_str = ", ".join(current)
    display = f" [{current_str}]" if current_str else ""
    raw = click.prompt(f"{prompt_text} (comma-separated){display}", default=current_str, show_default=False)
    if not raw.strip():
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]


@preferences.command("set")
def preferences_set():
    """Set or update your style preferences interactively."""
    current = load_preferences()
    console.print("[bold]Set your style preferences[/bold]")
    console.print("[dim]Press Enter to keep current value.[/dim]\n")

    preferred_colors = _prompt_list("Preferred colors", current.preferred_colors)
    avoided_colors = _prompt_list("Avoided colors", current.avoided_colors)
    preferred_brands = _prompt_list("Preferred brands", current.preferred_brands)

    current_mats = current.preferred_materials
    mat_display = f" [{current_mats}]" if current_mats else ""
    preferred_materials = click.prompt(
        f"Preferred materials (free text){mat_display}",
        default=current_mats,
        show_default=False,
    )

    current_notes = current.notes
    notes_display = f" [{current_notes}]" if current_notes else ""
    notes = click.prompt(f"Notes{notes_display}", default=current_notes, show_default=False)

    prefs = Preferences(
        preferred_colors=preferred_colors,
        avoided_colors=avoided_colors,
        preferred_brands=preferred_brands,
        preferred_materials=preferred_materials,
        budget_range=current.budget_range,
        notes=notes,
    )

    save_preferences(prefs)
    console.print("\n[green]Preferences saved.[/green]")
    display_preferences(prefs)


@preferences.command("show")
def preferences_show():
    """Display your current style preferences."""
    display_preferences(load_preferences())


# --- Summary ---

@cli.command()
def summary():
    """Show a high-level overview of your wardrobe and profile."""
    items = load_wardrobe()
    prof = load_profile()
    prefs = load_preferences()
    display_summary(items, prof, prefs)


if __name__ == "__main__":
    cli()
