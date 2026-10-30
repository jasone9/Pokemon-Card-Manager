"""Collection and user persistence, independent of the GUI and working directory."""

import json
import math
import os
from pathlib import Path
import sqlite3
import tempfile

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
COLLECTION_FILE = DEFAULT_DATA_DIR / "collection.json"
USERS_FILE = DEFAULT_DATA_DIR / "users.json"
DB_FILE = DEFAULT_DATA_DIR / "pokemon_cards_collection.db"
collection = []
users = []
conn = None


def init_database(data_dir=None):
    """Open local storage. Importing this module does not create any files."""
    global conn, COLLECTION_FILE, USERS_FILE, DB_FILE
    close_database()
    directory = Path(
        data_dir or os.environ.get("POKEMON_CARD_MANAGER_DATA_DIR") or DEFAULT_DATA_DIR
    ).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    COLLECTION_FILE = directory / "collection.json"
    USERS_FILE = directory / "users.json"
    DB_FILE = directory / "pokemon_cards_collection.db"
    connection = sqlite3.connect(DB_FILE)
    try:
        with connection:
            connection.execute('''
                CREATE TABLE IF NOT EXISTS cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    "set" TEXT NOT NULL,
                    rarity TEXT NOT NULL,
                    market REAL,
                    tcg_player_id TEXT,
                    image_url TEXT
                )
            ''')
            connection.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    except Exception:
        connection.close()
        raise
    conn = connection
    collection.clear()
    users.clear()


def _database():
    if conn is None:
        raise RuntimeError("Call init_database() before using storage.")
    return conn


def _write_json(path, records):
    """Replace complete snapshots rather than truncating a working data file."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            json.dump(records, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _read_records(path):
    with path.open(encoding="utf-8") as handle:
        records = json.load(handle)
    if not isinstance(records, list) or any(not isinstance(r, dict) for r in records):
        raise ValueError(f"{path.name} must contain a JSON list of records.")
    return records


def record_from_card(card):
    """Normalize API fields into the original collection JSON format."""
    prices = card.get("prices")
    set_info = card.get("set")
    set_name = set_info.get("name") if isinstance(set_info, dict) else set_info
    return {
        "name": card.get("name") or "Unknown",
        "set": card.get("setName") or set_name or "Unknown Set",
        "rarity": card.get("rarity") or "Unknown Rarity",
        "market": prices.get("market") if isinstance(prices, dict) else None,
        "tcgPlayerId": card.get("tcgPlayerId"),
        "imageUrl": card.get("imageUrl"),
    }


def _replace_cards(connection, records):
    connection.execute("DELETE FROM cards")
    connection.executemany(
        'INSERT INTO cards (name, "set", rarity, market, tcg_player_id, image_url) '
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (r.get("name", "Unknown"), r.get("set", "Unknown Set"),
             r.get("rarity", "Unknown Rarity"), r.get("market"),
             r.get("tcgPlayerId"), r.get("imageUrl"))
            for r in records
        ],
    )


def persist_collection():
    """Save JSON plus a SQLite mirror, rolling back SQL if snapshot writing fails."""
    connection = _database()
    with connection:
        _replace_cards(connection, collection)
        _write_json(COLLECTION_FILE, collection)


def load_collection():
    """Prefer JSON; fall back to SQLite when the snapshot is absent."""
    connection = _database()
    if COLLECTION_FILE.exists():
        records = _read_records(COLLECTION_FILE)
    else:
        rows = connection.execute(
            'SELECT name, "set", rarity, market, tcg_player_id, image_url '
            "FROM cards ORDER BY id"
        )
        keys = ("name", "set", "rarity", "market", "tcgPlayerId", "imageUrl")
        records = [dict(zip(keys, row)) for row in rows]
    with connection:
        _replace_cards(connection, records)
    collection[:] = records


def filter_collection(field="Name", text=""):
    """Return original indices with matches so filtered deletions stay correct."""
    fields = {"Name": "name", "Set": "set", "Rarity": "rarity"}
    if field not in fields:
        raise ValueError("Filter must be Name, Set, or Rarity.")
    needle = text.strip().casefold()
    return [
        (index, record) for index, record in enumerate(collection)
        if needle in str(record.get(fields[field]) or "").casefold()
    ]


def market_value(value):
    """Unknown or non-finite prices are unavailable, not dollar amounts."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def collection_total():
    return sum(market_value(record.get("market")) or 0.0 for record in collection)


def load_users():
    connection = _database()
    if USERS_FILE.exists():
        records = _read_records(USERS_FILE)
        for record in records:
            username = record.get("username")
            if not isinstance(username, str) or not username.strip():
                raise ValueError("users.json contains an empty or invalid username.")
    else:
        records = [
            {"id": row[0], "username": row[1]}
            for row in connection.execute("SELECT id, username FROM users ORDER BY id")
        ]
    with connection:
        connection.execute("DELETE FROM users")
        connection.executemany(
            "INSERT INTO users (id, username) VALUES (?, ?)",
            [(record.get("id"), record["username"]) for record in records],
        )
        loaded = [
            {"id": row[0], "username": row[1]}
            for row in connection.execute("SELECT id, username FROM users ORDER BY id")
        ]
    users[:] = loaded


def add_user(username):
    username = username.strip()
    if not username:
        return False, "Username cannot be empty."
    if any(user["username"] == username for user in users):
        return False, "User already exists."
    connection = _database()
    try:
        with connection:
            result = connection.execute("INSERT INTO users (username) VALUES (?)", (username,))
            record = {"id": result.lastrowid, "username": username}
            _write_json(USERS_FILE, users + [record])
    except sqlite3.IntegrityError:
        return False, "User already exists."
    except (OSError, sqlite3.Error, ValueError) as exc:
        return False, f"Failed to add user: {exc}"
    users.append(record)
    return True, "User added successfully."


def remove_user(username):
    remaining = [user for user in users if user["username"] != username]
    if len(remaining) == len(users):
        return False, "User not found."
    connection = _database()
    try:
        with connection:
            connection.execute("DELETE FROM users WHERE username = ?", (username,))
            _write_json(USERS_FILE, remaining)
    except (OSError, sqlite3.Error, ValueError) as exc:
        return False, f"Failed to remove user: {exc}"
    users[:] = remaining
    return True, "User removed successfully."


def get_all_users():
    return [user.copy() for user in users]


def get_user_count():
    return len(users)


def close_database():
    global conn
    if conn is not None:
        conn.close()
        conn = None
