"""
01_build_features.py

Builds features for upcoming UFC matchups by combining:
- Odds from docs/win/mma/ufc/00_intake/sportsbook/*_ufc_odds.csv
- Fighter attributes from docs/win/mma/ufc/data/model/fighter_attributes.json
- Fighter historical stats from docs/win/mma/ufc/data/model/fighter_historical_stats.parquet
- Rolling fight history from docs/win/mma/ufc/data/model/ufc_master_clean.parquet

Output: docs/win/mma/ufc/01_feature_engineering/{date}_ufc_features.csv
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from ufc_feature_common import (
    build_master_indexes,
    diff,
    get_rolling_stats,
    get_sos,
    implied_prob,
    parse_dob,
    parse_height_inches,
    parse_reach,
    summarize_historical_fights,
)

# --- Paths ---
ODDS_DIR = Path("docs/win/mma/ufc/00_intake/sportsbook")
ATTRS_PATH = Path("docs/win/mma/ufc/data/model/fighter_attributes.json")
HISTORY_PATH = Path("docs/win/mma/ufc/data/model/fighter_history.json")
MASTER_PATH = Path("docs/win/mma/ufc/data/model/ufc_master_clean.parquet")
OUT_DIR = Path("docs/win/mma/ufc/01_feature_engineering")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Load data ---
with ATTRS_PATH.open(encoding="utf-8") as f:
    attrs = json.load(f)

with HISTORY_PATH.open(encoding="utf-8") as f:
    raw_history = json.load(f)

fighter_history = {
    name: [
        {**fight, "date": datetime.strptime(fight["date"], "%Y-%m-%d")}
        for fight in fights
    ]
    for name, fights in raw_history.items()
}

master = pd.read_parquet(MASTER_PATH)
master = master.sort_values("match_date").reset_index(drop=True)

# --- Prepare master history once ---
rolling_history, opponent_history = build_master_indexes(master)


# --- Historical stats (time-gated) ---
def get_historical_stats(fighter, target_date):
    fights = [
        fight
        for fight in fighter_history.get(fighter, [])
        if fight["date"] < target_date
    ]
    return summarize_historical_fights(fights, cap_accuracy=True)


# --- Implied probability ---
def vig_removed(prob1, prob2):
    if prob1 and prob2:
        total = prob1 + prob2
        return prob1 / total, prob2 / total

    return prob1, prob2



# --- Process each odds file ---
odds_files = sorted(ODDS_DIR.glob("*_ufc_odds.csv"))

if not odds_files:
    print("No odds files found.")
    raise SystemExit(1)

for odds_file in odds_files:
    date_str = odds_file.stem.replace("_ufc_odds", "")

    try:
        fight_date = pd.Timestamp(
            datetime.strptime(date_str, "%Y_%m_%d")
        )
    except:
        print(
            f"Could not parse date from {odds_file.name}, skipping"
        )
        continue

    with odds_file.open(encoding="utf-8") as f:
        odds_rows = list(csv.DictReader(f))

    if not odds_rows:
        print(f"No rows in {odds_file.name}, skipping")
        continue

    out_rows = []

    for row in odds_rows:
        f1 = row["fighter_1"].strip()
        f2 = row["fighter_2"].strip()

        ml1 = row["moneyline_fighter_1"].strip()
        ml2 = row["moneyline_fighter_2"].strip()

        ip1_raw = implied_prob(ml1)
        ip2_raw = implied_prob(ml2)
        ip1, ip2 = vig_removed(ip1_raw, ip2_raw)

        s1 = get_rolling_stats(rolling_history, f1, fight_date)
        s2 = get_rolling_stats(rolling_history, f2, fight_date)

        sos1 = get_sos(rolling_history, opponent_history, f1, fight_date)
        sos2 = get_sos(rolling_history, opponent_history, f2, fight_date)

        h1 = get_historical_stats(f1, fight_date)
        h2 = get_historical_stats(f2, fight_date)

        dob1 = parse_dob(attrs, f1)
        dob2 = parse_dob(attrs, f2)

        age1 = (
            (fight_date - dob1).days / 365.25
            if dob1 is not None
            else None
        )

        age2 = (
            (fight_date - dob2).days / 365.25
            if dob2 is not None
            else None
        )

        reach1 = parse_reach(attrs, f1)
        reach2 = parse_reach(attrs, f2)

        height1 = parse_height_inches(attrs, f1)
        height2 = parse_height_inches(attrs, f2)

        out_rows.append({
            "match_date": date_str,
            "fighter_1": f1,
            "fighter_2": f2,

            "moneyline_f1": ml1,
            "moneyline_f2": ml2,

            "implied_prob_f1": round(ip1, 4) if ip1 else "",
            "implied_prob_f2": round(ip2, 4) if ip2 else "",

            "f1_win_rate_all": (
                round(s1["win_rate_all"], 4)
                if s1["win_rate_all"] is not None
                else ""
            ),

            "f1_win_rate_last5": (
                round(s1["win_rate_last5"], 4)
                if s1["win_rate_last5"] is not None
                else ""
            ),

            "f1_streak": s1["streak"],
            "f1_experience": s1["experience"],

            "f1_days_since_last": (
                s1["days_since_last"]
                if s1["days_since_last"] is not None
                else ""
            ),

            "f1_sos": (
                round(sos1, 4)
                if sos1 is not None
                else ""
            ),

            "f1_age": round(age1, 2) if age1 else "",
            "f1_reach": reach1 or "",
            "f1_height": height1 or "",

            "f2_win_rate_all": (
                round(s2["win_rate_all"], 4)
                if s2["win_rate_all"] is not None
                else ""
            ),

            "f2_win_rate_last5": (
                round(s2["win_rate_last5"], 4)
                if s2["win_rate_last5"] is not None
                else ""
            ),

            "f2_streak": s2["streak"],
            "f2_experience": s2["experience"],

            "f2_days_since_last": (
                s2["days_since_last"]
                if s2["days_since_last"] is not None
                else ""
            ),

            "f2_sos": (
                round(sos2, 4)
                if sos2 is not None
                else ""
            ),

            "f2_age": round(age2, 2) if age2 else "",
            "f2_reach": reach2 or "",
            "f2_height": height2 or "",

            "f1_h_career_wr": (
                round(h1.get("h_career_wr", 0), 4)
                if h1
                else ""
            ),

            "f1_h_career_fights": (
                h1.get("h_career_fights", "")
                if h1
                else ""
            ),

            "f1_h_slpm": (
                h1.get("h_slpm", "")
                if h1
                else ""
            ),

            "f1_h_str_acc": (
                h1.get("h_str_acc", "")
                if h1
                else ""
            ),

            "f1_h_td_acc": (
                h1.get("h_td_acc", "")
                if h1
                else ""
            ),

            "f2_h_career_wr": (
                round(h2.get("h_career_wr", 0), 4)
                if h2
                else ""
            ),

            "f2_h_career_fights": (
                h2.get("h_career_fights", "")
                if h2
                else ""
            ),

            "f2_h_slpm": (
                h2.get("h_slpm", "")
                if h2
                else ""
            ),

            "f2_h_str_acc": (
                h2.get("h_str_acc", "")
                if h2
                else ""
            ),

            "f2_h_td_acc": (
                h2.get("h_td_acc", "")
                if h2
                else ""
            ),

            "diff_win_rate_all": round(
                diff(
                    s1["win_rate_all"],
                    s2["win_rate_all"]
                ),
                4,
            ),

            "diff_win_rate_last5": round(
                diff(
                    s1["win_rate_last5"],
                    s2["win_rate_last5"]
                ),
                4,
            ),

            "diff_streak": (
                s1["streak"] - s2["streak"]
            ),

            "diff_experience": (
                s1["experience"] - s2["experience"]
            ),

            "diff_days_since_last": diff(
                s1["days_since_last"],
                s2["days_since_last"],
            ),

            "diff_sos": round(
                diff(sos1, sos2),
                4,
            ),

            "diff_age": round(
                diff(age1, age2),
                2,
            ),

            "diff_reach": diff(
                reach1,
                reach2,
            ),

            "diff_height": diff(
                height1,
                height2,
            ),

            "diff_h_career_wr": (
                round(
                    diff(
                        h1.get("h_career_wr"),
                        h2.get("h_career_wr"),
                    ),
                    4,
                )
                if h1 and h2
                else ""
            ),

            "diff_h_career_fights": (
                diff(
                    h1.get("h_career_fights"),
                    h2.get("h_career_fights"),
                )
                if h1 and h2
                else ""
            ),

            "diff_h_slpm": (
                round(
                    diff(
                        h1.get("h_slpm"),
                        h2.get("h_slpm"),
                    ),
                    4,
                )
                if h1 and h2
                else ""
            ),

            "diff_h_str_acc": (
                round(
                    diff(
                        h1.get("h_str_acc"),
                        h2.get("h_str_acc"),
                    ),
                    4,
                )
                if h1 and h2
                else ""
            ),

            "diff_h_td_acc": (
                round(
                    diff(
                        h1.get("h_td_acc"),
                        h2.get("h_td_acc"),
                    ),
                    4,
                )
                if h1 and h2
                else ""
            ),
        })

    out_file = OUT_DIR / f"{date_str}_ufc_features.csv"

    if out_rows:
        with out_file.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=list(out_rows[0].keys()),
            )
            writer.writeheader()
            writer.writerows(out_rows)

        print(
            f"WROTE {out_file} ({len(out_rows)} fights)"
        )
    else:
        print(f"No output rows for {date_str}")
