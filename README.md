# Best of the Best Sellers 2026

A weekly scoreboard of publisher and title performance on the 2026 *New York Times* Hardcover Fiction best-seller list. It follows the methodology from the Publiography post [“Best of the Best Sellers”](https://publiography.beehiiv.com/p/best-of-the-best-sellers-0d0656eaee377845).

The page is published with GitHub Pages from `docs/`.

## What it shows

- **Top 10 publishers**, switchable between the five approaches: Cumulative Rank (headline), List Rank points, Appearances, Titles, and Average rank.
- **Top 10 titles** by List Rank points (#1 = 15 points per week, #15 = 1).
- **Complete publisher ranking**, sortable on every metric.
- **This week's list.**

## How it updates

`.github/workflows/update.yml` runs every Wednesday night and Thursday morning (UTC times, after the NYT posts the new list). It:

1. `scripts/fetch_lists.py` downloads any new Hardcover Fiction list dated in 2026 into `data/lists/`.
2. `scripts/build.py` scores every saved list and writes `data/scoreboard.json` and `docs/index.html`.
3. Commits the result only when a new list arrived.

You can also run it by hand from the Actions tab (**Update scoreboard → Run workflow**).

## Setup

1. Get a free API key at <https://developer.nytimes.com> with the Books API enabled.
2. Add it as the repository secret `NYT_API_KEY` (Settings → Secrets and variables → Actions).
3. Turn on Pages: Settings → Pages → Deploy from a branch → `main` / `docs`.

## Scoring

| Approach | Rule |
|---|---|
| Cumulative Rank | Each week, publishers are ordered by that week's List Rank points. With N publishers on the list, the best scores N and the worst 1. Ties share the higher score. Summed over the year. |
| List Rank points | #1 = 15 points ... #15 = 1 point, summed over every appearance. |
| Appearances | One point per weekly slot. |
| Titles | Distinct books placed on the list. |
| Average rank | Mean chart position over every appearance (lower is better). |

Publishers are named exactly as the NYT lists them, so Little, Brown and Mulholland are counted separately. A list counts toward the season if its NYT list date (`published_date`) falls in 2026. Set `SEASON_YEAR` to score a different year.

## Run locally

```sh
NYT_API_KEY=... python scripts/fetch_lists.py
python scripts/build.py
open docs/index.html
```
