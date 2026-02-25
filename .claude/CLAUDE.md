# Claude Code - claude-ws Monorepo

## Project Overview
This is a monorepo for CLI tools and applications. Each app lives in its own top-level directory.

### Apps
- **shopping-assistant/** — Personal shopping assistant CLI for wardrobe management, body profile, and style preferences.
- **grocery-assistant/** — Grocery tracking CLI that imports Amazon order history and computes purchase frequency per item.

## Tech Stack
- Python 3.9+
- Click (CLI framework)
- Rich (terminal formatting)
- Requests + BeautifulSoup (web scraping for product pages)
- OpenAI (Responses API with web search for shopping recommendations; Chat Completions for grocery title normalization)
- JSON file storage (per-app `data/` directories)

## Project Structure
```
claude-ws/
├── shopping-assistant/
│   ├── pyproject.toml
│   └── shopping_assistant/
│       ├── cli.py        # Click CLI entry point
│       ├── models.py     # Dataclasses (WardrobeItem, User, Profile)
│       ├── storage.py    # JSON file CRUD, multi-user support, migration
│       ├── advisor.py    # AI-powered shopping recommendations (OpenAI)
│       ├── display.py    # Rich tables/panels
│       └── scraper.py    # Product page fetching & parsing (JSON-LD, OpenGraph, meta)
├── grocery-assistant/
│   ├── pyproject.toml
│   └── grocery_assistant/
│       ├── cli.py        # Click CLI entry point (`grocery-assistant` binary)
│       ├── models.py     # Dataclasses (GroceryItem, Purchase)
│       ├── storage.py    # JSON file CRUD, import deduplication log
│       ├── importer.py   # Amazon Privacy Central ZIP/CSV parser + Whole Foods filter
│       ├── normalizer.py # OpenAI: raw product title → canonical name + category
│       ├── analyzer.py   # Purchase frequency computation (avg interval, predicted next)
│       └── display.py    # Rich tables/panels
└── .claude/
    └── CLAUDE.md
```

## Conventions
- Each app is installable via `pip install -e .` from its directory.
- Data files (JSON) live in each app's `data/` directory and are gitignored.
- Multi-user (shopping-assistant): data is scoped per-user under `data/users/<uuid>/` with `data/active_user.json` tracking the active user.
- Single-user (grocery-assistant): data lives directly in `data/items.json` and `data/import_log.json`.
- `User` model (formerly `Preferences`) holds id, email, and style preference fields. `Preferences = User` alias exists for backward compat.
- Old flat-file data is auto-migrated to per-user directories on first access.
- `WardrobeItem` has optional `name` and `price` fields. Both auto-populated from product pages when using `add-from-url`.
- `Profile` fields `shirt_size` and `pant_size` are `List[str]` (comma-separated input) to support multiple sizes.
- The `shop` command uses OpenAI's Responses API with web search. The prompt requires web-search-sourced results only, and URLs are validated via HEAD requests before display. Use `--dry-run` to preview the prompt without calling the API.
- `grocery-assistant import` accepts an Amazon Privacy Central ZIP (from `amazon.com/hz/privacy-central/data-requests/preview.html`) or any flat CSV. The real Privacy Central ZIP uses non-obvious column names: `Product Name` (title), `Original Quantity`, `Unit Price`, `Website`; no `Category` or `Seller` columns.
- Grocery row filtering checks `Category`/`Seller` (old B2B CSV format) **and** `Website` (Privacy Central format). Rows with `Website` = `AmazonFresh`, `PrimeNow-US`, or `Amazon Go` are treated as grocery orders. Use `--all-categories` to skip filtering entirely.
- `grocery-assistant import` deduplicates by `order_id|asin` key stored in `import_log.json`; re-running with the same file is safe.
- `grocery-assistant` normalizer calls OpenAI once per unique ASIN (cached in memory per import run) to extract canonical name, category, brand, unit_size.
- Models use dataclasses with `to_dict()`/`from_dict()` for serialization.
- Use `from __future__ import annotations` for Python 3.9 compatibility.
- CLI entry points are registered in `pyproject.toml` under `[project.scripts]`.

## Git Workflow
- Always create a new feature branch off master for any changes. Never commit directly to master.
- Branch naming: use short kebab-case names describing the change (e.g., `add-budget-command`, `fix-profile-display`).
- After committing and pushing the feature branch, create a PR.

## Development
```bash
# Install shopping-assistant in editable mode
cd shopping-assistant && pip install -e .

# Run commands
shopping-assistant user create
shopping-assistant user list
shopping-assistant user switch <identifier>
shopping-assistant wardrobe add
shopping-assistant wardrobe add-from-url <product-url>
shopping-assistant wardrobe list [--category <cat>]
shopping-assistant wardrobe show <item_id>
shopping-assistant wardrobe edit <item_id>
shopping-assistant wardrobe remove <item_id>
shopping-assistant profile set
shopping-assistant profile show
shopping-assistant preferences set
shopping-assistant preferences show
shopping-assistant summary
shopping-assistant shop "description"
shopping-assistant shop "description" --dry-run

# Install grocery-assistant in editable mode
cd grocery-assistant && pip install -e .

# Run commands
grocery-assistant import <orders.zip>            # Amazon Privacy Central ZIP
grocery-assistant import <orders.csv>            # flat CSV
grocery-assistant import <file> --all-categories # skip Whole Foods filter
grocery-assistant list                           # all items + frequency
grocery-assistant list --category dairy          # filter by category
grocery-assistant list --sort name|last|next     # change sort order
grocery-assistant stats                          # summary + overdue items
grocery-assistant show <item_id>                 # full purchase history (prefix OK)
```
