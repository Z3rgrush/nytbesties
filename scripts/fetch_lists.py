#!/usr/bin/env python3
"""Download NYT Hardcover Fiction lists for the season year into data/lists/.

Walks backward from the current list using `previous_published_date` and
saves every list whose published_date falls in SEASON_YEAR. Lists already on
disk are skipped, so a weekly run makes only one or two API calls.

Needs NYT_API_KEY in the environment. The NYT Books API allows about
5 requests per minute, so calls are spaced 12 seconds apart.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIST_DIR = ROOT / "data" / "lists"
LIST_NAME = "hardcover-fiction"
API = "https://api.nytimes.com/svc/books/v3/lists/{date}/{name}.json?api-key={key}"
SEASON_YEAR = int(os.environ.get("SEASON_YEAR", "2026"))
# Optional list date to start walking back from (for backfilling past years).
START_DATE = os.environ.get("START_DATE") or "current"
PAUSE_SECONDS = 12


def fetch(date: str, key: str) -> dict:
    url = API.format(date=date, name=LIST_NAME, key=key)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.load(resp)["results"]
        except urllib.error.HTTPError as err:
            if err.code == 429 and attempt < 3:
                time.sleep(60)
                continue
            raise
    raise RuntimeError("unreachable")


def slim(results: dict) -> dict:
    return {
        "published_date": results["published_date"],
        "bestsellers_date": results.get("bestsellers_date"),
        "books": [
            {
                "rank": b["rank"],
                "title": b["title"].strip(),
                "author": b["author"].strip(),
                "publisher": b["publisher"].strip(),
                "isbn13": b.get("primary_isbn13"),
                "weeks_on_list": b.get("weeks_on_list"),
            }
            for b in sorted(results["books"], key=lambda b: b["rank"])
        ],
    }


def main() -> int:
    key = os.environ.get("NYT_API_KEY")
    if not key:
        print("NYT_API_KEY is not set", file=sys.stderr)
        return 1
    LIST_DIR.mkdir(parents=True, exist_ok=True)

    date, saved = START_DATE, 0
    while date:
        if date != START_DATE:
            if int(date[:4]) < SEASON_YEAR:
                break
            if (LIST_DIR / f"{date}.json").exists():
                break  # everything older is already on disk
        results = fetch(date, key)
        pub = results["published_date"]
        if int(pub[:4]) == SEASON_YEAR and not (LIST_DIR / f"{pub}.json").exists():
            (LIST_DIR / f"{pub}.json").write_text(json.dumps(slim(results), indent=1) + "\n")
            print(f"saved {pub}")
            saved += 1
        date = results.get("previous_published_date")
        if date:
            time.sleep(PAUSE_SECONDS)

    print(f"{saved} new list(s) saved for {SEASON_YEAR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
