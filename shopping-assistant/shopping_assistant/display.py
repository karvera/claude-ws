"""Terminal display helpers using Rich."""

from __future__ import annotations

from typing import Dict, List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.panel import Panel

from .models import WardrobeItem, User, Preferences, Profile

console = Console()


def display_wardrobe_table(items: list[WardrobeItem]) -> None:
    if not items:
        console.print("[dim]No items in wardrobe.[/dim]")
        return

    table = Table(title="Wardrobe", show_lines=True)
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("Category", style="cyan")
    table.add_column("Subcategory", style="cyan")
    table.add_column("Color", style="magenta")
    table.add_column("Size")
    table.add_column("Brand", style="green")
    table.add_column("Occasion", style="yellow")
    table.add_column("Season")

    for item in items:
        table.add_row(
            item.id[:8],
            item.category,
            item.subcategory,
            item.color,
            item.size,
            item.brand or "-",
            item.occasion or "-",
            item.season or "-",
        )

    console.print(table)


def display_wardrobe_item(item: WardrobeItem) -> None:
    lines = [
        f"[bold]ID:[/bold]          {item.id}",
        f"[bold]Category:[/bold]    {item.category}",
        f"[bold]Subcategory:[/bold] {item.subcategory}",
        f"[bold]Color:[/bold]       {item.color}",
        f"[bold]Size:[/bold]        {item.size}",
        f"[bold]Brand:[/bold]       {item.brand or '-'}",
        f"[bold]Material:[/bold]    {item.material or '-'}",
        f"[bold]Occasion:[/bold]    {item.occasion or '-'}",
        f"[bold]Season:[/bold]      {item.season or '-'}",
        f"[bold]Notes:[/bold]       {item.notes or '-'}",
        f"[bold]Added:[/bold]       {item.date_added}",
    ]
    console.print(Panel("\n".join(lines), title="Wardrobe Item", border_style="cyan"))


def display_profile(profile: Profile) -> None:
    fields = [
        ("Height", profile.height),
        ("Weight", profile.weight),
        ("Body Type", profile.body_type),
        ("Chest", profile.chest),
        ("Waist", profile.waist),
        ("Hips", profile.hips),
        ("Inseam", profile.inseam),
        ("Shoe Size", profile.shoe_size),
        ("Shirt Size", ", ".join(profile.shirt_size) if profile.shirt_size else ""),
        ("Pant Size", ", ".join(profile.pant_size) if profile.pant_size else ""),
        ("Notes", profile.notes),
    ]

    lines = []
    for label, value in fields:
        lines.append(f"[bold]{label}:[/bold] {value or '[dim]-[/dim]'}")

    console.print(Panel("\n".join(lines), title="Profile", border_style="green"))


def display_preferences(prefs: User) -> None:
    lines = [
        f"[bold]Preferred Colors:[/bold]    {', '.join(prefs.preferred_colors) or '-'}",
        f"[bold]Avoided Colors:[/bold]      {', '.join(prefs.avoided_colors) or '-'}",
        f"[bold]Preferred Brands:[/bold]    {', '.join(prefs.preferred_brands) or '-'}",
        f"[bold]Preferred Materials:[/bold] {prefs.preferred_materials or '-'}",
        f"[bold]Notes:[/bold]               {prefs.notes or '-'}",
    ]

    if prefs.budget_range:
        lines.append("[bold]Budget Ranges:[/bold]")
        for category, bounds in prefs.budget_range.items():
            low = bounds.get("min", "?")
            high = bounds.get("max", "?")
            lines.append(f"  {category}: ${low} - ${high}")

    console.print(Panel("\n".join(lines), title="Style Preferences", border_style="yellow"))


def display_user(user: User) -> None:
    """Display a single user's info panel."""
    has_prefs = any([user.preferred_colors, user.preferred_brands, user.preferred_materials])
    lines = [
        f"[bold]ID:[/bold]    {user.id}",
        f"[bold]Email:[/bold] {user.email or '[dim]-[/dim]'}",
        f"[bold]Prefs:[/bold] {'[green]Set[/green]' if has_prefs else '[dim]Not set[/dim]'}",
    ]
    console.print(Panel("\n".join(lines), title="User", border_style="blue"))


def display_user_table(users: list[User], active_user_id: Optional[str] = None) -> None:
    """Display a table of all users, marking the active one."""
    if not users:
        console.print("[dim]No users found.[/dim]")
        return

    table = Table(title="Users", show_lines=True)
    table.add_column("", max_width=1)
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("Email", style="cyan")
    table.add_column("Prefs", style="yellow")

    for user in users:
        marker = "*" if active_user_id and user.id == active_user_id else ""
        has_prefs = any([user.preferred_colors, user.preferred_brands, user.preferred_materials])
        table.add_row(
            marker,
            user.id[:8],
            user.email or "-",
            "Set" if has_prefs else "-",
        )

    console.print(table)


def display_summary(items: list[WardrobeItem], profile: Profile, prefs: User, active_email: Optional[str] = None) -> None:
    # Category counts
    categories: dict[str, int] = {}
    for item in items:
        categories[item.category] = categories.get(item.category, 0) + 1

    lines: list[str] = []
    if active_email:
        lines.append(f"[bold]User:[/bold] {active_email}")
        lines.append("")
    lines.append(f"[bold]Total Items:[/bold] {len(items)}")
    if categories:
        for cat, count in sorted(categories.items()):
            lines.append(f"  {cat}: {count}")

    has_profile = any([profile.height, profile.weight, profile.body_type])
    has_prefs = any([prefs.preferred_colors, prefs.preferred_brands, prefs.preferred_materials])

    lines.append("")
    lines.append(f"[bold]Profile:[/bold]     {'[green]Set[/green]' if has_profile else '[dim]Not set[/dim]'}")
    lines.append(f"[bold]Preferences:[/bold] {'[green]Set[/green]' if has_prefs else '[dim]Not set[/dim]'}")

    console.print(Panel("\n".join(lines), title="Summary", border_style="blue"))


def display_extracted_details(fields: Dict[str, str], source_url: str) -> None:
    """Display scraped product details for user review."""
    lines = [f"[dim]Source: {source_url}[/dim]", ""]

    display_fields = [
        ("Category", "category"),
        ("Subcategory", "subcategory"),
        ("Color", "color"),
        ("Size", "size"),
        ("Brand", "brand"),
        ("Material", "material"),
        ("Occasion", "occasion"),
        ("Season", "season"),
        ("Notes", "notes"),
    ]

    for label, key in display_fields:
        val = fields.get(key, "")
        if val:
            lines.append(f"[bold]{label}:[/bold] [green]{val}[/green]")
        else:
            lines.append(f"[bold]{label}:[/bold] [yellow]\\[not detected][/yellow]")

    console.print(Panel("\n".join(lines), title="Extracted Product Details", border_style="magenta"))


def display_recommendations(recommendations: list[dict], item_description: str) -> None:
    """Display AI-generated product recommendations."""
    # Fallback: raw text that couldn't be parsed as JSON
    if len(recommendations) == 1 and "raw_text" in recommendations[0]:
        md = Markdown(recommendations[0]["raw_text"])
        console.print(Panel(md, title=f"Recommendations: {item_description}", border_style="magenta"))
        return

    console.print(f"\n[bold]Found {len(recommendations)} recommendation(s) for:[/bold] {item_description}\n")

    for i, rec in enumerate(recommendations, 1):
        lines = [
            f"[bold]Name:[/bold]             {rec.get('name', '-')}",
            f"[bold]Brand:[/bold]            {rec.get('brand', '-')}",
            f"[bold]Price:[/bold]            {rec.get('price', '-')}",
            f"[bold]Recommended Size:[/bold] {rec.get('recommended_size', '-')}",
            f"[bold]Why It Fits:[/bold]      {rec.get('why_it_fits', '-')}",
            f"[bold]Link:[/bold]             {rec.get('url', '-')}",
        ]
        console.print(Panel("\n".join(lines), title=f"#{i}", border_style="magenta"))
