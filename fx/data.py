import requests
import datetime
import json
# ===============================
# CONFIG and CACHE
# ===============================

PRIMARY_URL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date}/{api_version}/currencies/{base}.json"
FALLBACK_URL = (
    "https://{date}.currency-api.pages.dev/{api_version}/currencies/{base}.json"
)
# ---Cache part---
CACHE_FILE = "fx_cache.json"


def load_cache():
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


# ---End Cache part---


# ===============================
# FX Data Fetching
# ===============================


def get_current_rate(base="inr", target="aud", date="latest", api_version="v1"):
    # Cache check first
    cache = load_cache()
    cache_key = f"{date}_{base}_{target}"
    if cache_key in cache:
        return cache[cache_key]

    primary_url = PRIMARY_URL.format(date=date, api_version=api_version, base=base)
    fallback_url = FALLBACK_URL.format(date=date, api_version=api_version, base=base)

    try:
        response = requests.get(primary_url, timeout=5)
        response.raise_for_status()
        rate = response.json()[base][target]

    except Exception:
        response = requests.get(fallback_url, timeout=5)
        response.raise_for_status()
        rate = response.json()[base][target]

    # save to cache if its not latest
    if date != "latest":
        cache[cache_key] = rate
        save_cache(cache)

    return rate


def get_historical_rates(base="inr", target="aud", days=40):
    rates = []
    # Using a cache means this loop will eventually run instantly
    cache = load_cache()

    # identify which dates we need to fetch
    print(f"Checking cache for {days} days of history...")

    for i in range(days, 0, -1):
        date = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime(
            "%Y-%m-%d"
        )
        try:
            # We use the same get_current_rate function but pass a specific date
            rate = get_current_rate(base=base, target=target, date=date)
            rates.append(rate)
        except Exception as e:
            print(f"Skipping {date} due to fetch error.{e}")
            continue
    return rates