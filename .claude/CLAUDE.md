# Claude Code - claude-ws Monorepo

## Project Overview
This is a monorepo for CLI tools and applications. Each app lives in its own top-level directory.

### Apps
- **shopping-assistant/** — Personal shopping assistant CLI for wardrobe management, body profile, and style preferences.

## Tech Stack
- Python 3.9+
- Click (CLI framework)
- Rich (terminal formatting)
- Requests + BeautifulSoup (web scraping for product pages)
- OpenAI (Responses API with web search for shopping recommendations)
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
└── .claude/
    └── CLAUDE.md
```

## Conventions
- Each app is installable via `pip install -e .` from its directory.
- Data files (JSON) live in each app's `data/` directory and are gitignored.
- Multi-user: data is scoped per-user under `data/users/<uuid>/` with `data/active_user.json` tracking the active user.
- `User` model (formerly `Preferences`) holds id, email, and style preference fields. `Preferences = User` alias exists for backward compat.
- Old flat-file data is auto-migrated to per-user directories on first access.
- `WardrobeItem` has optional `name` and `price` fields. Both auto-populated from product pages when using `add-from-url`.
- `Profile` fields `shirt_size` and `pant_size` are `List[str]` (comma-separated input) to support multiple sizes.
- The `shop` command uses OpenAI's Responses API with web search. The prompt requires web-search-sourced results only, and URLs are validated via HEAD requests before display. Use `--dry-run` to preview the prompt without calling the API.
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
```
