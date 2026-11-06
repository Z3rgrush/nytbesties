#!/usr/bin/env python3
"""Print every Hardcover Fiction appearance the NYT Books API has on record
for one publisher. Usage: NYT_API_KEY=... python scripts/publisher_history.py "Celadon"

Uses /lists/best-sellers/history.json, which covers all lists back to 2008.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

URL = "https://api.nytimes.com/svc/books/v3/lists/best-sellers/history.json?{q}"


def main() -> int:
    pub, key = sys.argv[1], os.environ["NYT_API_KEY"]
    offset, books = 0, []
    while True:
        q = urllib.parse.urlencode({"publisher": pub, "offset": offset, "api-key": key})
        try:
            with urllib.request.urlopen(URL.format(q=q), timeout=30) as r:
                data = json.load(r)
        except urllib.error.HTTPError as err:
            print(f"HTTP {err.code}: {err.read().decode(errors='replace')[:500]}")
            return 1
        books += data["results"]
        offset += 20
        if offset >= data.get("num_results", 0) or not data["results"]:
            break
        time.sleep(12)
    print(f"{len(books)} book(s) on record for publisher={pub!r} (any list)")
    hits = []
    for b in books:
        for h in b.get("ranks_history", []):
            if h.get("list_name") == "Hardcover Fiction":
                hits.append((h["published_date"], h["rank"], b["title"], b["author"], b["publisher"]))
    hits.sort()
    print(f"{len(hits)} Hardcover Fiction appearance(s)")
    for h in hits:
        print(" | ".join(map(str, h)))
    others = sorted({h.get("list_name") for b in books for h in b.get("ranks_history", [])} - {"Hardcover Fiction"})
    print("Other lists:", ", ".join(o for o in others if o))
    return 0


if __name__ == "__main__":
    sys.exit(main())
