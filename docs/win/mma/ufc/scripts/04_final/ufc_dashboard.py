#!/usr/bin/env python3
# docs/win/mma/ufc/scripts/04_final/ufc_dashboard.py
#
# Builds the UFC results dashboard data (read live by the React UFC page)
# from the existing UFC final-report outputs.
#
# Output:
#   frontend/data/dashboards/ufc.json  ({"generated_at": <UTC ISO>, "data": <payload>})

from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
import json
import math
import os
import sys

import pandas as pd


BASE = Path("docs/win/mma/ufc/04_final")
REPORTS = BASE / "reports"
OUTPUT = Path("frontend/data/dashboards/ufc.json")

REPORT_FILES = [
    ("ev", "EV", REPORTS / "ufc_moneyline_by_ev.csv"),
    ("odds", "Odds", REPORTS / "ufc_by_odds.csv"),
    ("implied_prob", "Implied Prob", REPORTS / "ufc_by_implied_prob.csv"),
    ("model_prob", "Model Prob", REPORTS / "ufc_by_model_prob.csv"),
    ("dratings_prob", "DRatings Prob", REPORTS / "ufc_by_dratings_prob.csv"),
    ("date", "By Date", REPORTS / "ufc_by_date.csv"),
]


def read_csv(path: Path, required: bool = False) -> pd.DataFrame:
    if not path.exists():
        print(
            f"{'ERROR' if required else 'WARNING'}: missing {path}",
            file=sys.stderr,
        )
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception as exc:
        print(
            f"WARNING: unable to read {path}: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return pd.DataFrame()


def clean_value(value):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass

    return value


def records(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []

    return [
        {key: clean_value(value) for key, value in row.items()}
        for row in df.to_dict(orient="records")
    ]


def build_payload() -> dict:
    summary = read_csv(BASE / "ufc_summary_overall.csv", True)

    loaded = {}
    report_data = {}

    for key, label, path in REPORT_FILES:
        df = read_csv(path)
        loaded[key] = df
        report_data[key] = {
            "label": label,
            "rows": records(df),
        }

    headline = {
        "bets": None,
        "wins": None,
        "losses": None,
        "pushes": None,
        "win_pct": None,
        "units": None,
        "roi": None,
    }

    if not summary.empty:
        row = summary.iloc[0]
        headline.update(
            {
                "bets": clean_value(row.get("Total")),
                "wins": clean_value(row.get("Win")),
                "losses": clean_value(row.get("Loss")),
                "pushes": clean_value(row.get("Push")),
                "win_pct": clean_value(row.get("Win_Pct")),
            }
        )

    by_date = loaded.get("date", pd.DataFrame())

    if not by_date.empty:
        units = (
            pd.to_numeric(
                by_date["units_flat"],
                errors="coerce",
            ).sum(min_count=1)
            if "units_flat" in by_date.columns
            else None
        )

        bets = (
            pd.to_numeric(
                by_date["bets"],
                errors="coerce",
            ).sum(min_count=1)
            if "bets" in by_date.columns
            else None
        )

        headline["units"] = clean_value(units)

        if (
            units is not None
            and bets is not None
            and pd.notna(units)
            and pd.notna(bets)
            and bets
        ):
            headline["roi"] = clean_value(
                float(units) / float(bets)
            )

    return {
        "headline": headline,
        "reports": report_data,
    }


def json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def write_json(path: Path, data) -> int:
    document = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "data": json_safe(data),
    }
    content = json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
        allow_nan=False,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(path.name + ".tmp")
    staging.write_text(content, encoding="utf-8")
    os.replace(staging, path)
    return len(content.encode("utf-8"))


def main() -> None:
    bytes_written = write_json(OUTPUT, build_payload())
    print(f"UFC dashboard data generated: {OUTPUT} ({bytes_written} bytes)")


if __name__ == "__main__":
    main()
