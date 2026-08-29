# The Wolfson Premier League Bet — 2026/27

Live leaderboard for a five-way season-long Premier League prediction bet.
Predictions are locked before the season; the page scores them automatically all year.

**Players:** Akin, Bharat, Majid, Tola, Wax

## How it works

| Piece | What it does |
|---|---|
| `data/picks.json` | Everyone's locked predictions. Do not edit after the season starts. |
| `data/rules.json` | The points table. |
| `data/manual.json` | The one thing no free API tracks: first manager sacked. |
| `scripts/update.py` | Fetches live data, rebuilds the table, recomputes every score, writes `data/data.json`. |
| `index.html` | The page. Reads `data/data.json`. No build step, no framework. |
| `.github/workflows/update.yml` | Runs the script every 6 hours and redeploys the site. |

## Data sources

Both free, public, and require no API key or account:

- `https://fantasy.premierleague.com/api/bootstrap-static/` — every player's goals and assists
- `https://fantasy.premierleague.com/api/fixtures/` — every fixture and result

The league table is **computed from finished fixtures** rather than read from a paid feed.
Goals and assists come from the official Fantasy Premier League data, which is the agreed
source of truth for the Golden Boot and top-assists categories.

## Scoring

| Category | Points |
|---|---|
| Champion called correctly (1st) | +2 |
| Exact position, 2nd to 6th | +9 |
| Your top-6 club finishes in the top 6, wrong slot | +1 |
| Relegated club in the exact right slot | +6 |
| Relegated club relegated, wrong slot | +3 |
| Top goalscorer | +2 |
| Top assist maker | +4 |
| First manager sacked | +7 |

There are **no penalties**. The gradient already pays nothing for a miss.

Points are set in proportion to how hard each call actually is, anchored to the
easiest event on the board. The Golden Boot favourite runs at roughly 55%, so it
is the baseline; every other line is priced at its difficulty relative to that.
An exact league position (2nd to 6th) is the hardest repeatable call in the game
at roughly 12-14%, which is why it pays most. Naming the champion is a ~45% call
and pays accordingly.

## House rules

1. **A manager pick follows the man, not the job.** If your manager moves clubs,
   your pick moves with him to whichever Premier League club employs him.
2. **"Sacked" means the first Premier League manager to leave his post in-season
   for any reason** - sacked, resigned, mutual consent, or poached.
3. **If no manager leaves all season, the category is void** for everyone.
4. Goals and assists settle on the official Fantasy Premier League data. On a
   dead heat, everyone who picked any of the joint leaders scores.
5. Table positions settle on the final-day table.

## When the first manager gets sacked

Edit `data/manual.json`:

```json
{ "first_manager_sacked": "Glasner", "date": "2026-10-14" }
```

Use the surname exactly as it appears in `picks.json`. Commit; the site updates itself.

## Running it locally

```bash
python3 scripts/update.py && python3 -m http.server 8000
```
