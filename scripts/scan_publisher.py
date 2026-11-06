#!/usr/bin/env python3
"""Walk the weekly Hardcover Fiction lists backward and report every entry
from one publisher. Read-only: nothing is saved.

Usage: NYT_API_KEY=... python scripts/scan_publisher.py "Celadon" 2024-12-29 2018
(publisher, list date to start from, earliest year to scan)
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.nytimes.com/svc/books/v3/lists/{date}/hardcover-fiction.json?api-key={key}"


def fetch(date, key):
    for attempt in range(5):
        try:
            with urllib.request.urlopen(API.format(date=date, key=key), timeout=30) as r:
                return json.load(r)["results"]
        except urllib.error.HTTPError as err:
            if err.code == 429 and attempt < 4:
                time.sleep(60)
                continue
            raise


def main():
    pub, date, stop_year = sys.argv[1].lower(), sys.argv[2], int(sys.argv[3])
    key = os.environ["NYT_API_KEY"]
    weeks, hits = 0, []
    while date and int(date[:4]) >= stop_year:
        res = fetch(date, key)
        weeks += 1
        for b in res["books"]:
            if pub in (b.get("publisher") or "").lower():
                hits.append((res["published_date"], b["rank"], b["title"], b["author"], b["publisher"]))
                print("HIT", res["published_date"], b["rank"], b["title"], "|", b["author"], "|", b["publisher"], flush=True)
        date = res.get("previous_published_date")
        time.sleep(12)
    print(f"Scanned {weeks} weekly lists back to {stop_year}: {len(hits)} appearance(s) matching {sys.argv[1]!r}")
    titles = {}
    for d, r, t, a, p in hits:
        x = titles.setdefault(t, {"author": a, "weeks": 0, "best": 99, "first": d})
        x["weeks"] += 1; x["best"] = min(x["best"], r); x["first"] = min(x["first"], d)
    for t, x in sorted(titles.items(), key=lambda kv: kv[1]["first"]):
        print(f"SUMMARY {t} | {x['author']} | {x['weeks']} wks | best #{x['best']} | first {x['first']}")


if __name__ == "__main__":
    main()
