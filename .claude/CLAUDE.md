# Claude Code - claude-ws Monorepo

## Project Overview
This is a monorepo for CLI tools and applications. Each app lives in its own top-level directory.

### Apps
- **shopping-assistant/** — Personal shopping assistant CLI for wardrobe management, body profile, and style preferences.

## Tech Stack
- Python 3.9+
- Click (CLI framework)
- Rich (terminal formatting)
- JSON file storage (per-app `data/` directories)

## Project Structure
```
claude-ws/
├── shopping-assistant/
│   ├── pyproject.toml
│   └── shopping_assistant/
│       ├── cli.py        # Click CLI entry point
│       ├── models.py     # Dataclasses (WardrobeItem, Preferences, Profile)
│       ├── storage.py    # JSON file CRUD
│       └── display.py    # Rich tables/panels
└── .claude/
    └── CLAUDE.md
```

## Conventions
- Each app is installable via `pip install -e .` from its directory.
- Data files (JSON) live in each app's `data/` directory and are gitignored.
- Models use dataclasses with `to_dict()`/`from_dict()` for serialization.
- Use `from __future__ import annotations` for Python 3.9 compatibility.
- CLI entry points are registered in `pyproject.toml` under `[project.scripts]`.

## Development
```bash
# Install shopping-assistant in editable mode
cd shopping-assistant && pip install -e .

# Run commands
shopping-assistant wardrobe add
shopping-assistant wardrobe list
shopping-assistant profile set
shopping-assistant preferences set
shopping-assistant summary
```
