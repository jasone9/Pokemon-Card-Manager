"""Look up cards using the original project's Pokémon Price Tracker API."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://www.pokemonpricetracker.com/api/v2/cards"
HTTP_TIMEOUT = 10
API_KEY_ENV = "POKEMON_PRICE_TRACKER_API_KEY"


class CardLookupError(RuntimeError):
    """A lookup could not complete; this is different from finding no cards."""


def _extract_first_card(payload):
    """Accept the list, nested-container, and single-card shapes used upstream."""
    if isinstance(payload, list):
        for item in payload:
            card = _extract_first_card(item)
            if card is not None:
                return card
    elif isinstance(payload, dict):
        if any(key in payload for key in ("name", "rarity", "set", "prices")):
            return payload
        for key in ("data", "cards", "results", "items"):
            card = _extract_first_card(payload.get(key))
            if card is not None:
                return card
    return None


def _request_one(params, api_key):
    request = Request(
        f"{BASE_URL}?{urlencode(params)}",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        with urlopen(request, timeout=HTTP_TIMEOUT) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise CardLookupError(f"Card service returned HTTP {exc.code}.") from exc
    except (URLError, OSError) as exc:
        raise CardLookupError("Unable to reach the card service. Try again later.") from exc
    except (ValueError, UnicodeError) as exc:
        raise CardLookupError("Card service returned invalid JSON.") from exc
    return _extract_first_card(payload)


def get_card_info(query):
    """Search by name or TCGplayer ID, returning the first match or None."""
    query = (query or "").strip()
    if not query:
        return None
    api_key = os.environ.get(API_KEY_ENV, "").strip()
    if not api_key:
        raise CardLookupError(f"Set {API_KEY_ENV} to enable online card searches.")
    fields = ("tcgPlayerId", "search") if query.isdigit() else ("search", "tcgPlayerId")
    for field in fields:
        card = _request_one(
            {field: query, "includeHistory": "false", "limit": 1}, api_key
        )
        if card is not None:
            return card
    return None
