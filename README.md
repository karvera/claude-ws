# claude-ws

A monorepo of personal CLI tools built with Python, Click, and Rich.

## Apps

### [shopping-assistant](shopping-assistant/)

Wardrobe management and AI-powered shopping recommendations.

- Track clothing items manually or by scraping product URLs
- Store body measurements and style preferences
- Get personalized product recommendations via OpenAI web search
- Multi-user support with per-user data isolation

### [grocery-assistant](grocery-assistant/)

Grocery order history tracking and purchase frequency analysis.

- Import Amazon Whole Foods order history
- Analyze purchase patterns and frequency
- Normalize product names for consistent tracking

## Tech Stack

- **Python 3.9+**
- **Click** — CLI framework
- **Rich** — terminal tables, panels, and formatting
- **OpenAI** — AI-powered recommendations (shopping) and analysis (grocery)
- **Requests + BeautifulSoup** — web scraping (shopping)
- **JSON file storage** — no database required

## Getting Started

```bash
# Shopping assistant
cd shopping-assistant && pip install -e .
shopping-assistant --help

# Grocery assistant
cd grocery-assistant && pip install -e .
grocery-assistant --help
```

## Project Structure

```
claude-ws/
├── shopping-assistant/     # Wardrobe & shopping CLI
│   └── shopping_assistant/
├── grocery-assistant/      # Grocery tracking CLI
│   └── grocery_assistant/
├── .github/workflows/      # Claude Code review & agent actions
└── .claude/
    └── CLAUDE.md           # Project conventions
```

## CI/CD

This repo uses [Claude Code GitHub Actions](https://github.com/anthropics/claude-code-action) for:

- **Automated PR review** — Claude reviews pull requests on open/sync
- **Issue & PR agent** — mention `@claude` in issues or PR comments to get help
