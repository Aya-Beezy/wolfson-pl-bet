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
| Top-6 team in the exact right slot | +5 |
| Top-4 team finishes in the top 4 but the wrong slot | +2 |
| Top-4 pick finishes outside the top 6 | **−5** |
| Relegated team in the exact right slot | +5 |
| Top goalscorer | +10 |
| Top assist maker | +10 |
| First manager sacked | +10 |

Relegation picks only score on an exact positional match — finishing in the bottom three
in the wrong order is worth nothing.

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
