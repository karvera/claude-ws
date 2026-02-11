"""JSON file storage for wardrobe, preferences, and profile data."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import List, Optional

import click

from .models import WardrobeItem, User, Profile

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

USERS_DIR_NAME = "users"
ACTIVE_USER_FILE = "active_user.json"


# Sentinel used as default argument to signal "resolve active user directory"
class _ActiveUserSentinel:
    pass


_ACTIVE_USER = _ActiveUserSentinel()


def _ensure_data_dir(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> dict | list:
    if path.exists():
        return json.loads(path.read_text())
    return {} if path.name != "wardrobe.json" else []


def _save_json(path: Path, data: dict | list) -> None:
    _ensure_data_dir(path.parent)
    path.write_text(json.dumps(data, indent=2))


# --- Directory helpers ---

def _users_dir(data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    return data_dir / USERS_DIR_NAME


def _user_dir(user_id: str, data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    return _users_dir(data_dir) / user_id


# --- Active user ---

def load_active_user_id(data_dir: Path = DEFAULT_DATA_DIR) -> Optional[str]:
    path = data_dir / ACTIVE_USER_FILE
    if path.exists():
        data = json.loads(path.read_text())
        return data.get("user_id")
    return None


def save_active_user_id(user_id: str, data_dir: Path = DEFAULT_DATA_DIR) -> None:
    _save_json(data_dir / ACTIVE_USER_FILE, {"user_id": user_id})


def get_active_user_data_dir(data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    """Return the active user's data directory, running migration if needed."""
    maybe_migrate(data_dir)
    user_id = load_active_user_id(data_dir)
    if not user_id:
        raise click.ClickException(
            "No active user. Run 'shopping-assistant user create' to create one."
        )
    user_path = _user_dir(user_id, data_dir)
    if not user_path.exists():
        raise click.ClickException(
            f"Active user directory not found ({user_id[:8]}...). "
            "Run 'shopping-assistant user create' to create a new user."
        )
    return user_path


def _resolve_data_dir(data_dir: Optional[Path | _ActiveUserSentinel]) -> Path:
    """Resolve data_dir: if sentinel, return active user dir; otherwise pass through."""
    if isinstance(data_dir, _ActiveUserSentinel):
        return get_active_user_data_dir()
    return data_dir


# --- User CRUD ---

def create_user(email: str, data_dir: Path = DEFAULT_DATA_DIR) -> User:
    user = User(email=email)
    user_path = _user_dir(user.id, data_dir)
    _ensure_data_dir(user_path)
    _save_json(user_path / "user.json", user.to_dict())
    save_active_user_id(user.id, data_dir)
    return user


def load_user(user_id: str, data_dir: Path = DEFAULT_DATA_DIR) -> Optional[User]:
    path = _user_dir(user_id, data_dir) / "user.json"
    if not path.exists():
        return None
    raw = json.loads(path.read_text())
    return User.from_dict(raw)


def save_user(user: User, data_dir: Path = DEFAULT_DATA_DIR) -> None:
    user_path = _user_dir(user.id, data_dir)
    _ensure_data_dir(user_path)
    _save_json(user_path / "user.json", user.to_dict())


def list_users(data_dir: Path = DEFAULT_DATA_DIR) -> list[User]:
    users_path = _users_dir(data_dir)
    if not users_path.exists():
        return []
    users: list[User] = []
    for entry in sorted(users_path.iterdir()):
        if entry.is_dir():
            user_file = entry / "user.json"
            if user_file.exists():
                raw = json.loads(user_file.read_text())
                users.append(User.from_dict(raw))
    return users


def find_user_by_email_prefix(prefix: str, data_dir: Path = DEFAULT_DATA_DIR) -> Optional[User]:
    prefix_lower = prefix.lower()
    matches = [u for u in list_users(data_dir) if u.email.lower().startswith(prefix_lower)]
    if len(matches) == 1:
        return matches[0]
    return None


def switch_user(identifier: str, data_dir: Path = DEFAULT_DATA_DIR) -> User:
    """Switch active user by UUID, UUID prefix, or email prefix."""
    users = list_users(data_dir)

    # Exact UUID match
    for u in users:
        if u.id == identifier:
            save_active_user_id(u.id, data_dir)
            return u

    # UUID prefix match
    prefix_matches = [u for u in users if u.id.startswith(identifier)]
    if len(prefix_matches) == 1:
        save_active_user_id(prefix_matches[0].id, data_dir)
        return prefix_matches[0]

    # Email prefix match
    email_match = find_user_by_email_prefix(identifier, data_dir)
    if email_match:
        save_active_user_id(email_match.id, data_dir)
        return email_match

    raise click.ClickException(
        f"Could not find a unique user matching '{identifier}'. "
        "Use 'shopping-assistant user list' to see available users."
    )


# --- Migration ---

def maybe_migrate(data_dir: Path = DEFAULT_DATA_DIR) -> None:
    """Auto-migrate old flat-file layout to per-user directories."""
    users_path = _users_dir(data_dir)
    if users_path.exists():
        return  # already migrated

    old_files = {
        "wardrobe": data_dir / "wardrobe.json",
        "profile": data_dir / "profile.json",
        "preferences": data_dir / "preferences.json",
    }

    has_old = any(f.exists() for f in old_files.values())
    if not has_old:
        return

    click.echo("Existing data detected. Migrating to multi-user layout.")
    email = click.prompt("Enter your email to create your user profile")

    # Load old preferences to seed User fields
    old_prefs_data: dict = {}
    if old_files["preferences"].exists():
        old_prefs_data = json.loads(old_files["preferences"].read_text())

    user = User(email=email, **{
        k: v for k, v in old_prefs_data.items()
        if k in User.__dataclass_fields__ and k not in ("id", "email")
    })

    user_path = _user_dir(user.id, data_dir)
    _ensure_data_dir(user_path)

    # Save user.json
    _save_json(user_path / "user.json", user.to_dict())

    # Move wardrobe and profile into user dir
    if old_files["wardrobe"].exists():
        shutil.move(str(old_files["wardrobe"]), str(user_path / "wardrobe.json"))
    if old_files["profile"].exists():
        shutil.move(str(old_files["profile"]), str(user_path / "profile.json"))

    # Remove old preferences file (data merged into user.json)
    if old_files["preferences"].exists():
        old_files["preferences"].unlink()

    save_active_user_id(user.id, data_dir)
    click.echo(f"Migration complete. User created: {user.email} ({user.id[:8]}...)")


# --- Wardrobe ---

def load_wardrobe(data_dir: Path | _ActiveUserSentinel = _ACTIVE_USER) -> list[WardrobeItem]:
    data_dir = _resolve_data_dir(data_dir)
    raw = _load_json(data_dir / "wardrobe.json")
    return [WardrobeItem.from_dict(item) for item in raw]


def save_wardrobe(items: list[WardrobeItem], data_dir: Path | _ActiveUserSentinel = _ACTIVE_USER) -> None:
    data_dir = _resolve_data_dir(data_dir)
    _save_json(data_dir / "wardrobe.json", [item.to_dict() for item in items])


def add_wardrobe_item(item: WardrobeItem, data_dir: Path | _ActiveUserSentinel = _ACTIVE_USER) -> None:
    data_dir = _resolve_data_dir(data_dir)
    items = load_wardrobe(data_dir)
    items.append(item)
    save_wardrobe(items, data_dir)


def remove_wardrobe_item(item_id: str, data_dir: Path | _ActiveUserSentinel = _ACTIVE_USER) -> bool:
    data_dir = _resolve_data_dir(data_dir)
    items = load_wardrobe(data_dir)
    filtered = [i for i in items if i.id != item_id]
    if len(filtered) == len(items):
        return False
    save_wardrobe(filtered, data_dir)
    return True


def get_wardrobe_item(item_id: str, data_dir: Path | _ActiveUserSentinel = _ACTIVE_USER) -> Optional[WardrobeItem]:
    data_dir = _resolve_data_dir(data_dir)
    for item in load_wardrobe(data_dir):
        if item.id == item_id:
            return item
    return None


def update_wardrobe_item(item_id: str, updates: dict, data_dir: Path | _ActiveUserSentinel = _ACTIVE_USER) -> bool:
    data_dir = _resolve_data_dir(data_dir)
    items = load_wardrobe(data_dir)
    for item in items:
        if item.id == item_id:
            for key, value in updates.items():
                if hasattr(item, key) and key not in ("id", "date_added"):
                    setattr(item, key, value)
            save_wardrobe(items, data_dir)
            return True
    return False


# --- Profile ---

def load_profile(data_dir: Path | _ActiveUserSentinel = _ACTIVE_USER) -> Profile:
    data_dir = _resolve_data_dir(data_dir)
    raw = _load_json(data_dir / "profile.json")
    return Profile.from_dict(raw) if raw else Profile()


def save_profile(profile: Profile, data_dir: Path | _ActiveUserSentinel = _ACTIVE_USER) -> None:
    data_dir = _resolve_data_dir(data_dir)
    _save_json(data_dir / "profile.json", profile.to_dict())


# --- Preferences (compat wrappers reading/writing user.json) ---

def load_preferences(data_dir: Path | _ActiveUserSentinel = _ACTIVE_USER) -> User:
    data_dir = _resolve_data_dir(data_dir)
    raw = _load_json(data_dir / "user.json")
    return User.from_dict(raw) if raw else User()


def save_preferences(prefs: User, data_dir: Path | _ActiveUserSentinel = _ACTIVE_USER) -> None:
    data_dir = _resolve_data_dir(data_dir)
    _save_json(data_dir / "user.json", prefs.to_dict())
