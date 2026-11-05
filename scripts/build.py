#!/usr/bin/env python3
"""Score the saved lists and write data/scoreboard.json and docs/index.html.

Scoring follows "Best of the Best Sellers" (Publiography, Feb 2026):
  1. Appearances      one point per weekly slot
  2. Titles           distinct titles that reached the list
  3. Average rank     mean chart position over all appearances (lower is better)
  4. List Rank points #1 = 15 points ... #15 = 1 point, summed over the year
  5. Cumulative Rank  each week, publishers are ordered by that week's List Rank
                      points; the best of N publishers gets N, the worst gets 1.
                      Publishers tied in a week share the higher score.
Publishers are named exactly as the NYT lists them.
"""
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIST_DIR = ROOT / "data" / "lists"
SEASON_YEAR = int(os.environ.get("SEASON_YEAR", "2027"))
SLOTS = 15


def points(rank: int) -> int:
    return max(SLOTS + 1 - rank, 0)


def load_lists() -> list:
    lists = []
    for path in sorted(LIST_DIR.glob(f"{SEASON_YEAR}-*.json")):
        lists.append(json.loads(path.read_text()))
    return lists


def compete_rank(items, key, reverse=True):
    """Standard competition ranking (1, 2, 2, 4) with a tie flag."""
    ordered = sorted(items, key=key, reverse=reverse)
    out, prev, prev_rank = [], object(), 0
    for i, item in enumerate(ordered, start=1):
        val = key(item)
        rank = prev_rank if val == prev else i
        out.append((rank, item))
        prev, prev_rank = val, rank
    counts = defaultdict(int)
    for rank, _ in out:
        counts[rank] += 1
    return [(rank, counts[rank] > 1, item) for rank, item in out]


def score(lists: list) -> dict:
    pubs = defaultdict(lambda: {
        "appearances": 0, "rank_sum": 0, "list_points": 0, "cumulative": 0,
        "titles": set(), "weeks_at_1": 0, "best_rank": 99,
    })
    titles = {}
    weekly = []

    for lst in lists:
        week_pts = defaultdict(int)
        for b in lst["books"]:
            p = pubs[b["publisher"]]
            p["appearances"] += 1
            p["rank_sum"] += b["rank"]
            p["list_points"] += points(b["rank"])
            p["best_rank"] = min(p["best_rank"], b["rank"])
            p["weeks_at_1"] += b["rank"] == 1
            week_pts[b["publisher"]] += points(b["rank"])

            # Titles are matched by title+author so new ISBNs (e.g. a
            # reissue mid-run) do not split one book into two entries.
            tk = f'{b["title"].lower()}|{b["author"].lower()}'
            p["titles"].add(tk)
            t = titles.setdefault(tk, {
                "title": b["title"], "author": b["author"], "publisher": b["publisher"],
                "weeks": 0, "list_points": 0, "best_rank": 99, "weeks_at_1": 0,
                "first_week": lst["published_date"],
            })
            t["weeks"] += 1
            t["list_points"] += points(b["rank"])
            t["best_rank"] = min(t["best_rank"], b["rank"])
            t["weeks_at_1"] += b["rank"] == 1
            t["last_week"] = lst["published_date"]
            t["last_rank"] = b["rank"]

        n = len(week_pts)
        ranked = compete_rank(list(week_pts.items()), key=lambda kv: kv[1])
        week_rows = []
        for rank, tied, (pub, pts) in ranked:
            cum = n + 1 - rank
            pubs[pub]["cumulative"] += cum
            week_rows.append({"publisher": pub, "list_points": pts, "cumulative": cum})
        weekly.append({"published_date": lst["published_date"], "publishers": n, "rows": week_rows})

    pub_rows = []
    for name, p in pubs.items():
        pub_rows.append({
            "publisher": name,
            "appearances": p["appearances"],
            "titles": len(p["titles"]),
            "avg_rank": round(p["rank_sum"] / p["appearances"], 2),
            "list_points": p["list_points"],
            "cumulative": p["cumulative"],
            "weeks_at_1": p["weeks_at_1"],
            "best_rank": p["best_rank"],
            "share": round(100 * p["appearances"] / (SLOTS * len(lists)), 1) if lists else 0,
        })

    # Rank publishers under every approach.
    approaches = {
        "cumulative": dict(key=lambda r: r["cumulative"], reverse=True),
        "list_points": dict(key=lambda r: r["list_points"], reverse=True),
        "appearances": dict(key=lambda r: r["appearances"], reverse=True),
        "titles": dict(key=lambda r: r["titles"], reverse=True),
        "avg_rank": dict(key=lambda r: r["avg_rank"], reverse=False),
    }
    for name, spec in approaches.items():
        for rank, tied, row in compete_rank(pub_rows, **spec):
            row[f"rank_{name}"] = rank
            row[f"tied_{name}"] = tied
    pub_rows.sort(key=lambda r: (r["rank_cumulative"], -r["list_points"], r["publisher"]))

    # Movement since last week on the headline (cumulative) ranking.
    if len(lists) > 1:
        prev = score_prev(lists[:-1])
        for row in pub_rows:
            row["prev_rank_cumulative"] = prev.get(row["publisher"])

    title_rows = list(titles.values())
    for rank, tied, row in compete_rank(title_rows, key=lambda r: (r["list_points"])):
        row["rank"] = rank
        row["tied"] = tied
    title_rows.sort(key=lambda r: (r["rank"], -r["weeks"], r["best_rank"], r["title"]))
    latest = lists[-1]["published_date"] if lists else None
    for row in title_rows:
        row["on_latest"] = row["last_week"] == latest

    return {
        "season": SEASON_YEAR,
        "list": "Hardcover Fiction",
        "weeks": len(lists),
        "latest_list": latest,
        "latest_books": lists[-1]["books"] if lists else [],
        "total_titles": len(titles),
        "total_publishers": len(pubs),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "publishers": pub_rows,
        "titles": title_rows,
        "weekly": weekly,
    }


def score_prev(lists: list) -> dict:
    """Cumulative rank for each publisher as of the previous week."""
    totals = defaultdict(int)
    for lst in lists:
        week_pts = defaultdict(int)
        for b in lst["books"]:
            week_pts[b["publisher"]] += points(b["rank"])
        n = len(week_pts)
        for rank, _, (pub, _) in compete_rank(list(week_pts.items()), key=lambda kv: kv[1]):
            totals[pub] += n + 1 - rank
    return {pub: rank for rank, _, (pub, _) in compete_rank(list(totals.items()), key=lambda kv: kv[1])}


def main() -> None:
    board = score(load_lists())
    (ROOT / "data" / "scoreboard.json").write_text(json.dumps(board, indent=1) + "\n")
    template = (ROOT / "scripts" / "template.html").read_text()
    payload = json.dumps(board, separators=(",", ":")).replace("</", "<\\/")
    html = template.replace("/*__DATA__*/null", payload).replace("__SEASON__", str(SEASON_YEAR))
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "index.html").write_text(html)
    print(f"Built scoreboard: {board['weeks']} week(s), {board['total_publishers']} publishers, {board['total_titles']} titles")


if __name__ == "__main__":
    main()
