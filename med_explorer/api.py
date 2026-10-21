"""Thin client for the openFDA drug adverse event endpoint (FAERS).

Every call returns a (data, error) pair: exactly one of them is None.
Successful responses are cached in memory, so the app and the notebook
don't spend the rate limit asking the same question twice.
"""

import os

import requests

BASE_URL = "https://api.fda.gov/drug/event.json"
TIMEOUT = 15

# Without a key openFDA allows 240 requests/minute and 1,000/day per IP,
# and caps "count" queries at 500 terms. A free key lifts the daily limit
# to 120,000: https://open.fda.gov/apis/authentication/
API_KEY = os.environ.get("OPENFDA_API_KEY")
MAX_COUNT_LIMIT = 1000 if API_KEY else 500

_cache = {}


def fetch_openfda(params):
    """GET the endpoint with `params`. Returns (json, None) or (None, message)."""
    params = dict(params)
    if API_KEY:
        params["api_key"] = API_KEY

    key = tuple(sorted(params.items()))
    if key in _cache:
        return _cache[key], None

    try:
        response = requests.get(BASE_URL, params=params, timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        return None, "openFDA took too long to answer. Please try again."
    except requests.exceptions.ConnectionError:
        return None, "Could not connect to openFDA. Check your internet connection."

    if response.status_code == 200:
        data = response.json()
        _cache[key] = data
        return data, None
    elif response.status_code == 404:
        return None, "No reports found for this search."
    elif response.status_code == 429:
        return None, "Too many requests right now. Wait a minute and try again."
    else:
        return None, f"Unexpected error from openFDA (code {response.status_code})"


def is_not_found(error):
    """openFDA answers 404 when a search matches nothing: that is 'zero', not a failure."""
    return error == "No reports found for this search."


def clear_cache():
    _cache.clear()
