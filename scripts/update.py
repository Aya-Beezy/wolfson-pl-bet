#!/usr/bin/env python3
"""
Fetch live Premier League data and recompute the Wolfson bet leaderboard.

Sources (both free, public, no API key):
  https://fantasy.premierleague.com/api/bootstrap-static/  -> players (goals, assists), teams
  https://fantasy.premierleague.com/api/fixtures/          -> every fixture + result

The league table is computed from finished fixtures rather than taken from a feed,
so there is nothing to pay for and nothing to authenticate.
"""

import json
import pathlib
import sys
import unicodedata
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BASE = "https://fantasy.premierleague.com/api"
UA = {"User-Agent": "Mozilla/5.0 (wolfson-pl-bet static site builder)"}

# Names as written on the WhatsApp picks -> canonical FPL team names.
ALIASES = {
    "manchester united": "Man Utd", "man united": "Man Utd", "united": "Man Utd",
    "manchester city": "Man City", "city": "Man City",
    "tottenham hotspur": "Spurs", "tottenham": "Spurs",
    "nottingham forest": "Nott'm Forest",
    "newcastle united": "Newcastle",
    "west ham united": "West Ham",
    "afc bournemouth": "Bournemouth",
    "wolverhampton wanderers": "Wolves",
    "ipswich": "Ipswich Town", "hull": "Hull City", "coventry": "Coventry City",
    "leeds united": "Leeds", "palace": "Crystal Palace",
    "brighton & hove albion": "Brighton",
}


def get(path):
    req = urllib.request.Request(f"{BASE}/{path}", headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def resolve_team(name, valid):
    """Map a pick to a real team name, or fail loudly rather than silently scoring zero."""
    if name in valid:
        return name
    key = fold(name).strip()
    if key in ALIASES and ALIASES[key] in valid:
        return ALIASES[key]
    for t in valid:
        if fold(t) == key:
            return t
    matches = [t for t in valid if key in fold(t) or fold(t) in key]
    if len(matches) == 1:
        return matches[0]
    raise SystemExit(f"ERROR: cannot resolve team {name!r} to a 2026/27 Premier League club. "
                     f"Fix data/picks.json. Candidates: {matches or sorted(valid)}")


def build_table(fixtures, team_names):
    rows = {n: dict(team=n, played=0, won=0, drawn=0, lost=0, gf=0, ga=0, pts=0) for n in team_names.values()}
    for f in fixtures:
        if not f.get("finished"):
            continue
        h, a = team_names[f["team_h"]], team_names[f["team_a"]]
        hs, as_ = f["team_h_score"], f["team_a_score"]
        if hs is None or as_ is None:
            continue
        for team, gf, ga in ((h, hs, as_), (a, as_, hs)):
            r = rows[team]
            r["played"] += 1
            r["gf"] += gf
            r["ga"] += ga
            if gf > ga:
                r["won"] += 1
                r["pts"] += 3
            elif gf == ga:
                r["drawn"] += 1
                r["pts"] += 1
            else:
                r["lost"] += 1
    table = sorted(rows.values(), key=lambda r: (-r["pts"], -(r["gf"] - r["ga"]), -r["gf"], r["team"]))
    for i, r in enumerate(table, 1):
        r["pos"] = i
        r["gd"] = r["gf"] - r["ga"]
    return table


def leaders(players, team_names, field, n=10):
    ranked = sorted((p for p in players if p[field] > 0), key=lambda p: (-p[field], p["web_name"]))
    top = ranked[:n]
    best = ranked[0][field] if ranked else 0
    return [{"id": p["id"], "name": p["web_name"],
             "full_name": f"{p['first_name']} {p['second_name']}".strip(),
             "team": team_names[p["team"]], "value": p[field],
             "leading": p[field] == best and best > 0} for p in top]


def score_player(name, pick, table, rules, scorer_ids, assist_ids, sacked):
    pos_of = {r["team"]: r["pos"] for r in table}
    valid = set(pos_of)
    lines, totals = [], {}

    top6_total = 0
    for i, raw in enumerate(pick["top6"], start=1):
        team = resolve_team(raw, valid)
        actual = pos_of[team]
        if actual == i:
            # the title is a ~45% call; slots 2-6 are ~12-14% and pay accordingly
            pts = rules["champion_exact"] if i == 1 else rules["top6_exact"]
            status = "exact"
        elif actual <= 6:
            pts, status = rules["top6_wrong_slot"], "near"
        else:
            pts, status = 0, "miss"
        top6_total += pts
        lines.append({"category": "top6", "slot": i, "pick": team,
                      "actual": actual, "points": pts, "status": status})
    totals["top6"] = top6_total

    rel_total = 0
    for i, raw in enumerate(pick["relegation"], start=18):
        team = resolve_team(raw, valid)
        actual = pos_of[team]
        if actual == i:
            pts, status = rules["relegation_exact"], "exact"
        elif actual >= 18:
            # naming a relegated club is the skill; the exact slot is close to a coin toss
            pts, status = rules["relegation_wrong_slot"], "near"
        else:
            pts, status = 0, "miss"
        rel_total += pts
        lines.append({"category": "relegation", "slot": i, "pick": team,
                      "actual": actual, "points": pts, "status": status})
    totals["relegation"] = rel_total

    ts = pick["top_scorer"]
    ts_hit = ts["id"] in scorer_ids
    totals["top_scorer"] = rules["top_scorer"] if ts_hit else 0
    lines.append({"category": "top_scorer", "pick": ts["name"],
                  "points": totals["top_scorer"], "status": "leading" if ts_hit else "behind"})

    ta = pick["top_assists"]
    ta_hit = ta["id"] in assist_ids
    totals["top_assists"] = rules["top_assists"] if ta_hit else 0
    lines.append({"category": "top_assists", "pick": ta["name"],
                  "points": totals["top_assists"], "status": "leading" if ta_hit else "behind"})

    mgr_hit = bool(sacked) and fold(sacked) == fold(pick["manager_sacked"])
    totals["manager_sacked"] = rules["manager_sacked"] if mgr_hit else 0
    lines.append({"category": "manager_sacked", "pick": pick["manager_sacked"],
                  "points": totals["manager_sacked"],
                  "status": "hit" if mgr_hit else ("missed" if sacked else "pending")})

    return {"player": name, "breakdown": totals, "lines": lines,
            "total": sum(totals.values())}


def main():
    picks_doc = json.loads((DATA / "picks.json").read_text())
    rules = json.loads((DATA / "rules.json").read_text())
    manual = json.loads((DATA / "manual.json").read_text())

    boot = get("bootstrap-static/")
    fixtures = get("fixtures/")

    team_names = {t["id"]: t["name"] for t in boot["teams"]}
    table = build_table(fixtures, team_names)
    gw_done = sum(1 for e in boot["events"] if e.get("finished"))
    next_gw = next((e["name"] for e in boot["events"] if not e.get("finished")), "Season complete")

    top_scorers = leaders(boot["elements"], team_names, "goals_scored")
    top_assists = leaders(boot["elements"], team_names, "assists")
    scorer_ids = {p["id"] for p in top_scorers if p["leading"]}
    assist_ids = {p["id"] for p in top_assists if p["leading"]}
    sacked = manual.get("first_manager_sacked")

    results = [score_player(n, picks_doc["picks"][n], table, rules, scorer_ids, assist_ids, sacked)
               for n in picks_doc["players"]]
    results.sort(key=lambda r: (-r["total"], r["player"]))
    rank = 0
    for i, r in enumerate(results):
        if i == 0 or r["total"] != results[i - 1]["total"]:
            rank = i + 1
        r["rank"] = rank

    out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "season": picks_doc["season"],
        "gameweeks_played": gw_done,
        "next_gameweek": next_gw,
        "rules": rules,
        "table": table,
        "top_scorers": top_scorers,
        "top_assists": top_assists,
        "manager_sacked": {"name": sacked, "date": manual.get("date")},
        "leaderboard": results,
        "picks": picks_doc["picks"],
    }
    (DATA / "data.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"OK  GW{gw_done} played  |  " + "  ".join(f"{r['player']} {r['total']}" for r in results))


if __name__ == "__main__":
    sys.exit(main())
