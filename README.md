# Pokemon Card Manager

A Python desktop tracker for a Pokémon card collection. Search for cards by name
or TCGplayer ID, save copies to your collection, view recorded market prices,
filter cards, and manage a local list of usernames.

This is an organized continuation of the
[CMPS 3390 team project](https://github.com/jasone9/CMPS3390-pokemoncard), imported
from branch `wade2` at commit
[`3b50fb8`](https://github.com/jasone9/CMPS3390-pokemoncard/tree/3b50fb8a5e1b3360557ab973e36d51a012c39f49).
The original repository records the contributors and their commit history.

## Project layout

```text
Pokemon-Card-Manager/
├── pokemon_card_manager/
│   ├── __init__.py
│   ├── __main__.py       # Explicit application entry point
│   ├── control.py        # Card API lookup and response handling
│   ├── model.py          # Collection, filters, users, JSON, SQLite
│   ├── theme.py          # Pokédex colors, widget styles, and device header
│   └── view.py           # Tkinter collection/search/user pages
├── examples/
│   └── collection.json   # Original sample cards; historical prices
├── tests/                # Offline storage, API, and UI-handler tests
├── .github/workflows/tests.yml
├── requirements.txt
└── data/                 # Created at runtime and ignored by Git
```

## Run locally

Use Python 3.10 or newer with Tkinter installed and a graphical desktop.
Tkinter ships with many Python installers; Linux distributions may require
their `python3-tk` package. Pillow is used to display card images. Card API
requests use Python's standard library.

The desktop interface uses a red-and-white Pokédex theme, with a blue lens,
dark display borders, and green value panels. Its colors and reusable widget
styles live in `pokemon_card_manager/theme.py`; it does not require a browser,
CSS, or downloaded theme assets. Keyboard focus and disabled controls retain
distinct styles, and the collection table uses alternating light rows.

From the repository root, create a virtual environment and install dependencies:

```text
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` in Windows PowerShell, or
`source .venv/bin/activate` on macOS/Linux, then install Pillow:

```text
python -m pip install -r requirements.txt
```

For online searches, set `POKEMON_PRICE_TRACKER_API_KEY` to your own
[Pokémon Price Tracker](https://www.pokemonpricetracker.com/) API key in the
same terminal session. In PowerShell:

```powershell
$env:POKEMON_PRICE_TRACKER_API_KEY = "your-api-key"
```

On macOS/Linux:

```sh
export POKEMON_PRICE_TRACKER_API_KEY="your-api-key"
```

Then launch:

```text
python -m pokemon_card_manager
```

The collection and user pages work without an API key. Online searches and
image downloads require network access. Secrets are read from the environment;
the application does not automatically load `.env` files.

## Collection and local data

- Search on the Add Card page, inspect the result, then choose **Save to Collection**.
- Each save represents one card copy, so duplicate cards are allowed.
- Filter by name, set, or rarity. Select one or more rows to remove those copies.
- The displayed total covers the entire collection, including cards hidden by a filter.
- Prices are saved snapshots from lookup time. They do not refresh automatically.
- Usernames are a shared local list; they are not login accounts or separate collections.

The default data folder is `data/` beside the package, independent of the
terminal's working directory. Set `POKEMON_CARD_MANAGER_DATA_DIR` to an absolute
folder path to use a different location. The app creates that folder on launch.

Cards and users are saved as `collection.json` and `users.json`, with a SQLite
mirror in `pokemon_cards_collection.db`. JSON is preferred on startup; when a
snapshot is absent, SQLite is used. Invalid JSON produces an error instead of
silently replacing saved data. JSON snapshots are replaced atomically, and
failed snapshot writes roll back SQLite changes. JSON and SQLite are separate
files, not a single cross-file transaction; startup resynchronizes SQLite from
the JSON snapshot. Run one app instance per data folder and back up that folder.

The new app starts with an empty collection. To import your previous collection,
close the app, back up the destination data folder, then copy the original
`collection.json` into it. The next launch reads that file and rebuilds the card
table. The same procedure supports the original `users.json` format. For a demo,
use `examples/collection.json` as the collection snapshot. Its prices are examples,
not current quotes. The source repository's generated databases and saved users
are not bundled here; import JSON rather than copying legacy database files.

## Tests

```text
python -m unittest discover -s tests -v
```

Tests use temporary data directories and mocked API responses. They cover
collection/user persistence, failed writes, original JSON import, payload shapes,
ID/name fallback, network errors, filter-safe deletions, stale search results,
and launch/import behavior. UI handlers are tested with mock widgets; these
tests do not contact the card service. The additional desktop smoke tests create
real Tkinter widgets and exercise navigation, saves, filtered deletions, users,
and minimum-size layout when a graphical display is available. They are skipped
in a headless terminal without a display.

GitHub Actions runs the suite on Python 3.10 and 3.12 under Xvfb so the desktop
smoke tests run as well. For a visual smoke test,
launch the app on a desktop, open each of the three pages, search with your own
API key, save a card, filter and remove a card, and restart to confirm persistence.

## Changes from the source project

- Grouped application modules into a package with relative imports and an explicit launcher.
- Kept runtime collection/user data out of the source tree and Git history.
- Replaced the embedded API credential with environment configuration.
- Fixed card-save SQL and retained TCGplayer IDs in SQLite; missing prices/images are supported.
- Implemented the existing filter controls while keeping deletion tied to original collection indices.
- Prevented failed searches from leaving a previous card available to save.
- Added setup documentation, sample data, offline tests, and CI.

Pokémon and TCGplayer names and card artwork belong to their respective owners.
