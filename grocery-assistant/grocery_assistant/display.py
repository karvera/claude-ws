"""Terminal display helpers using Rich."""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .analyzer import ItemFrequency
from .models import GroceryItem

console = Console()


def _overdue_label(predicted_next: Optional[str]) -> str:
    """Return a Rich-formatted '(overdue)' tag if the predicted date has passed."""
    if not predicted_next:
        return ""
    try:
        if date.fromisoformat(predicted_next) < date.today():
            return " [red](overdue)[/red]"
    except ValueError:
        pass
    return ""


def display_frequency_table(
    freqs: List[ItemFrequency],
    title: str = "Grocery Purchase Frequency",
) -> None:
    if not freqs:
        console.print("[dim]No grocery items found.[/dim]")
        return

    table = Table(title=title, show_lines=True)
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("Item", style="bold")
    table.add_column("Category", style="cyan")
    table.add_column("Brand", style="green")
    table.add_column("Buys", justify="right")
    table.add_column("Units", justify="right")
    table.add_column("Avg Every", justify="right")
    table.add_column("Last Bought", style="yellow")
    table.add_column("Next Est.", style="magenta")

    for f in freqs:
        avg = f"{round(f.avg_interval_days)} days" if f.avg_interval_days else "-"
        next_str = f.predicted_next or "-"
        overdue = _overdue_label(f.predicted_next)
        table.add_row(
            f.id[:8],
            f.canonical_name,
            f.category,
            f.brand or "-",
            str(f.total_purchases),
            str(f.total_units),
            avg,
            f.last_purchased,
            f"{next_str}{overdue}",
        )

    console.print(table)


def display_item_detail(item: GroceryItem) -> None:
    from .analyzer import compute_frequency

    freq = compute_frequency(item)
    avg = f"{round(freq.avg_interval_days)} days" if freq.avg_interval_days else "-"
    next_str = (freq.predicted_next or "-") + _overdue_label(freq.predicted_next)

    lines = [
        f"[bold]ID:[/bold]             {item.id}",
        f"[bold]Name:[/bold]           {item.canonical_name}",
        f"[bold]Category:[/bold]       {item.category}",
        f"[bold]Brand:[/bold]          {item.brand or '-'}",
        f"[bold]Unit Size:[/bold]      {item.unit_size or '-'}",
        f"[bold]ASIN:[/bold]           {item.asin or '-'}",
        "",
        f"[bold]Total Purchases:[/bold]  {freq.total_purchases}",
        f"[bold]Total Units:[/bold]      {freq.total_units}",
        f"[bold]Avg Interval:[/bold]     {avg}",
        f"[bold]Last Purchased:[/bold]   {freq.last_purchased}",
        f"[bold]Predicted Next:[/bold]   {next_str}",
        "",
        "[bold]Purchase History:[/bold]",
    ]

    for p in sorted(item.purchases, key=lambda p: p.date, reverse=True):
        lines.append(
            f"  {p.date}  qty={p.quantity}  ${p.price_per_unit:.2f}/unit"
            f"  [dim][{p.order_id[:16]}][/dim]"
        )
        lines.append(f"    [dim]{p.raw_title[:80]}[/dim]")

    console.print(Panel("\n".join(lines), title=item.canonical_name, border_style="cyan"))


def display_stats(freqs: List[ItemFrequency]) -> None:
    if not freqs:
        console.print("[dim]No data yet. Run 'grocery-assistant import <file>' first.[/dim]")
        return

    today = date.today()

    def _is_overdue(predicted_next: Optional[str]) -> bool:
        if not predicted_next:
            return False
        try:
            return date.fromisoformat(predicted_next) < today
        except ValueError:
            return False

    overdue = [f for f in freqs if _is_overdue(f.predicted_next)]

    categories: dict[str, int] = {}
    for f in freqs:
        categories[f.category] = categories.get(f.category, 0) + 1

    lines = [
        f"[bold]Total Unique Items:[/bold] {len(freqs)}",
        f"[bold]Total Categories:[/bold]  {len(categories)}",
        "",
        "[bold]By Category:[/bold]",
    ]
    for cat, count in sorted(categories.items()):
        lines.append(f"  {cat}: {count} item{'s' if count != 1 else ''}")

    lines += ["", "[bold]Top 10 Most Purchased:[/bold]"]
    for f in freqs[:10]:
        avg = f" (every {round(f.avg_interval_days)} days)" if f.avg_interval_days else ""
        lines.append(f"  {f.canonical_name}: {f.total_purchases}x{avg}")

    if overdue:
        lines += ["", f"[bold][red]Overdue — buy soon ({len(overdue)}):[/red][/bold]"]
        for f in sorted(overdue, key=lambda f: f.predicted_next or ""):
            lines.append(f"  [red]{f.canonical_name}[/red] — was due {f.predicted_next}")

    console.print(Panel("\n".join(lines), title="Grocery Stats", border_style="blue"))
