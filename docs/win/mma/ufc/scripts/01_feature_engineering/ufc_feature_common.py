from __future__ import annotations

import numpy as np
import pandas as pd


def parse_dob(attrs, name):
    try:
        return pd.to_datetime(attrs[name]["dob"])
    except (KeyError, TypeError, ValueError):
        return None


def parse_height_inches(attrs, name):
    try:
        height = attrs[name]["height"]
        parts = height.replace('"', "").split("'")
        return int(parts[0]) * 12 + int(parts[1].strip())
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return None


def parse_reach(attrs, name):
    try:
        return float(attrs[name]["reach"].replace('"', "").strip())
    except (AttributeError, KeyError, TypeError, ValueError):
        return None


def build_master_indexes(master):
    rolling_history = {}
    opponent_history = {}

    for _, row in master.iterrows():
        date = row["match_date"]
        f1 = row["fighter_1"]
        f2 = row["fighter_2"]

        rolling_history.setdefault(f1, []).append(
            (date, 1 if row["result_fighter_1"] == "Win" else 0)
        )
        rolling_history.setdefault(f2, []).append(
            (date, 1 if row["result_fighter_2"] == "Win" else 0)
        )
        opponent_history.setdefault(f1, []).append((date, f2))
        opponent_history.setdefault(f2, []).append((date, f1))

    for history in (rolling_history, opponent_history):
        for fighter, entries in history.items():
            history[fighter] = sorted(entries, key=lambda item: item[0])

    return rolling_history, opponent_history


def get_rolling_stats(rolling_history, fighter, fight_date):
    fights = [
        (date, win)
        for date, win in rolling_history.get(fighter, [])
        if date < fight_date
    ]
    if not fights:
        return {
            "win_rate_all": None,
            "win_rate_last5": None,
            "streak": 0,
            "experience": 0,
            "days_since_last": None,
        }

    wins = [win for _, win in fights]
    dates = [date for date, _ in fights]
    last = wins[-1]
    streak = 0
    for win in reversed(wins):
        if win != last:
            break
        streak += 1

    return {
        "win_rate_all": np.mean(wins),
        "win_rate_last5": np.mean(wins[-5:]),
        "streak": streak if last == 1 else -streak,
        "experience": len(fights),
        "days_since_last": (fight_date - dates[-1]).days,
    }


def get_sos(rolling_history, opponent_history, fighter, fight_date):
    opponents = [
        opponent
        for date, opponent in opponent_history.get(fighter, [])
        if date < fight_date
    ]
    if not opponents:
        return None

    rates = []
    for opponent in opponents:
        prior = [
            win
            for date, win in rolling_history.get(opponent, [])
            if date < fight_date
        ]
        if prior:
            rates.append(np.mean(prior))

    return np.mean(rates) if rates else None


def summarize_historical_fights(fights, cap_accuracy=False):
    if not fights:
        return {}

    wins = sum(1 for fight in fights if fight["result"] == "win")
    losses = sum(1 for fight in fights if fight["result"] == "loss")
    total_minutes = sum(fight["minutes"] for fight in fights)
    sig_landed = sum(fight["sig_landed"] for fight in fights)
    sig_attempted = sum(fight["sig_attempted"] for fight in fights)
    td_landed = sum(fight["td_landed"] for fight in fights)
    td_attempted = sum(fight["td_attempted"] for fight in fights)

    str_acc = sig_landed / sig_attempted if sig_attempted > 0 else 0
    td_acc = td_landed / td_attempted if td_attempted > 0 else 0
    if cap_accuracy:
        str_acc = min(str_acc, 1.0)
        td_acc = min(td_acc, 1.0)

    return {
        "h_career_wins": wins,
        "h_career_losses": losses,
        "h_career_fights": wins + losses,
        "h_career_wr": wins / (wins + losses) if (wins + losses) > 0 else 0,
        "h_slpm": round(sig_landed / total_minutes, 4) if total_minutes > 0 else 0,
        "h_str_acc": round(str_acc, 4),
        "h_td_acc": round(td_acc, 4),
    }


def implied_prob(moneyline):
    try:
        ml = float(str(moneyline).replace("+", ""))
    except (TypeError, ValueError):
        return None
    return 100 / (ml + 100) if ml > 0 else abs(ml) / (abs(ml) + 100)


def diff(a, b):
    if a is None or b is None:
        return 0
    return a - b
