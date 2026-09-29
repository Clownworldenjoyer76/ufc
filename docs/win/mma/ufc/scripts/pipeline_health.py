#!/usr/bin/env python3
"""UFC pipeline health reporter.

Writes:
    docs/win/mma/ufc/pipeline_health.json
    docs/win/mma/ufc/errors/pipeline_health.txt
    frontend/data/pipeline_health/ufc.json
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path("docs/win/mma/ufc")
OUTPUT = BASE / "pipeline_health.json"
LOG = BASE / "errors/pipeline_health.txt"
FRONTEND_OUTPUT = Path("frontend/data/pipeline_health/ufc.json")
NY = ZoneInfo("America/New_York")
SPORT_KEY = "ufc"
SPORT_LABEL = "UFC"
JOB_STATUS_ENV = "UFC_PIPELINE_JOB_STATUS"
RUN_DATE_ENV = "UFC_PIPELINE_RUN_DATE"

BAD_MARKERS = (
    "STATUS: FAILED",
    "STATUS: PARTIAL",
    "STATUS: COMPLETED WITH ERRORS",
    "FATAL ERROR",
    "TRACEBACK (MOST RECENT CALL LAST)",
)

STAGES = [
    ("output", "Sportsbook", "00_intake/sportsbook/{date}_ufc_odds.csv"),
    ("output", "Predictions", "00_intake/predictions/{date}_ufc_predictions.csv"),
    ("output", "Features", "01_feature_engineering/{date}_ufc_features.csv"),
    ("output", "Edges", "02_edges/{date}_ufc_edges.csv"),
    ("output", "Select", "03_select/{date}_ufc_select.csv"),
    ("output", "Detailed Select", "03_select/detailed/{date}_ufc_select_detailed.csv"),
    ("output", "Graded", "04_final/graded/{date}_ufc_graded.csv"),
]


def clean(value) -> str:
    return "" if value is None else str(value).strip()


def clean_id(value) -> str:
    text = clean(value)
    if not text:
        return ""
    try:
        number = float(text)
        if math.isfinite(number) and number.is_integer():
            return str(int(number))
    except (TypeError, ValueError):
        pass
    return text


def read_rows(path: Path) -> list[dict]:
    if not path.exists() or not path.is_file():
        return []
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    except Exception:
        return []


def count_rows(paths: list[Path]) -> int:
    return sum(len(read_rows(path)) for path in paths)


def unique_game_ids(paths: list[Path]) -> set[str]:
    ids: set[str] = set()
    for path in paths:
        for row in read_rows(path):
            gid = clean_id(row.get("game_id") or row.get("id") or row.get("event_id"))
            if gid:
                ids.add(gid)
    return ids


def resolve_date(now_ny: datetime) -> str:
    raw = clean(os.getenv(RUN_DATE_ENV))
    if raw:
        value = raw.replace("-", "_")
        if re.fullmatch(r"\d{4}_\d{2}_\d{2}", value):
            return value
    return now_ny.strftime("%Y_%m_%d")


def last_status(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    statuses = [line.strip() for line in text.splitlines() if "STATUS:" in line]
    if statuses:
        return statuses[-1]
    upper = text.upper()
    if any(marker in upper for marker in BAD_MARKERS):
        return "STATUS: FAILED"
    return "STATUS: LOG PRESENT"


def stage_status(date: str) -> list[dict]:
    rows: list[dict] = []
    for stage in STAGES:
        kind = stage[0]
        name = stage[1]
        spec = stage[2]
        if kind == "log":
            path = BASE / spec
            rows.append({
                "name": name,
                "path": str(path),
                "exists": path.exists(),
                "status": last_status(path) or "STATUS: NO LOG",
            })
        else:
            pattern = spec.format(date=date)
            matches = sorted(BASE.glob(pattern))
            rows.append({
                "name": name,
                "path": str(BASE / pattern),
                "exists": bool(matches),
                "status": "STATUS: OUTPUT PRESENT" if matches else "STATUS: NO OUTPUT",
                "matched_files": [str(p) for p in matches[:25]],
            })
    return rows


def latest_ufc_date(now_ny: datetime) -> str:
    candidates = []
    for path in (BASE / "00_intake/sportsbook").glob("????_??_??_ufc_odds.csv"):
        match = re.match(r"(\d{4}_\d{2}_\d{2})_ufc_odds\.csv$", path.name)
        if match:
            candidates.append(match.group(1))
    return max(candidates) if candidates else now_ny.strftime("%Y_%m_%d")


def build_counts(date: str) -> tuple[dict, dict, list[str], list[str]]:
    paths = {
        "sportsbook": BASE / f"00_intake/sportsbook/{date}_ufc_odds.csv",
        "predictions": BASE / f"00_intake/predictions/{date}_ufc_predictions.csv",
        "features": BASE / f"01_feature_engineering/{date}_ufc_features.csv",
        "edges": BASE / f"02_edges/{date}_ufc_edges.csv",
        "selected": BASE / f"03_select/{date}_ufc_select.csv",
        "selected_detailed": BASE / f"03_select/detailed/{date}_ufc_select_detailed.csv",
        "graded": BASE / f"04_final/graded/{date}_ufc_graded.csv",
    }
    rows = {key: read_rows(path) for key, path in paths.items()}
    warnings: list[str] = []
    fatals: list[str] = []
    input_rows = len(rows["sportsbook"])
    if input_rows and not rows["features"]:
        warnings.append("UFC: sportsbook rows exist but no feature output exists for the report event date")
    if input_rows and rows["features"] and not rows["edges"]:
        warnings.append("UFC: feature rows exist but no edge output exists for the report event date")
    counts = {
        "sportsbook_fights": len(rows["sportsbook"]),
        "prediction_fights": len(rows["predictions"]),
        "feature_fights": len(rows["features"]),
        "edge_fights": len(rows["edges"]),
        "selected_bets": len(rows["selected"]),
        "detailed_selected_bets": len(rows["selected_detailed"]),
        "graded_bets": len(rows["graded"]),
    }
    return counts, {key: str(path) for key, path in paths.items()}, warnings, fatals


def write_log(payload: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"=== {SPORT_LABEL} PIPELINE HEALTH {payload['generated_at_utc']} ===",
        f"status={payload['status']}",
        f"workflow_status={payload['workflow']['status']}",
        f"report_date={payload['report_date']}",
        f"fatal_errors={len(payload.get('fatal_errors', []))}",
        f"warnings={len(payload.get('warnings', []))}",
    ]
    for item in payload.get("fatal_errors", []):
        lines.append(f"FATAL: {item}")
    for item in payload.get("warnings", []):
        lines.append(f"WARNING: {item}")
    LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    now_utc = datetime.now(UTC)
    now_ny = datetime.now(NY)
    date = latest_ufc_date(now_ny)
    job_status = clean(os.getenv(JOB_STATUS_ENV)) or "unknown"

    counts, paths, warnings, fatals = build_counts(date)
    stages = stage_status(date)

    if job_status.lower() != "success":
        fatals.append(f"{SPORT_LABEL} workflow status is {job_status.upper()}")

    failed_logs = [
        row for row in stages
        if any(marker in clean(row.get("status")).upper() for marker in BAD_MARKERS)
    ]
    if failed_logs and job_status.lower() == "success":
        fatals.append(
            f"{SPORT_LABEL} has failed stage log(s): "
            + "; ".join(clean(row.get("name")) for row in failed_logs)
        )

    status = "failed" if fatals else ("warning" if warnings else "healthy")
    payload = {
        "schema_version": 1,
        "sport": SPORT_KEY,
        "generated_at_utc": now_utc.isoformat(),
        "game_date_new_york": now_ny.strftime("%Y_%m_%d"),
        "report_date": date,
        "status": status,
        "fatal_errors": fatals,
        "warnings": warnings,
        "counts": counts,
        "stage_status": stages,
        "paths": paths,
        "workflow": {
            "name": "UFC Pipeline",
            "status": job_status.lower(),
            "run_id": clean(os.getenv("GITHUB_RUN_ID")),
            "run_attempt": clean(os.getenv("GITHUB_RUN_ATTEMPT")),
            "sha": clean(os.getenv("GITHUB_SHA")),
            "ref_name": clean(os.getenv("GITHUB_REF_NAME")),
        },
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    FRONTEND_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    OUTPUT.write_text(text, encoding="utf-8")
    FRONTEND_OUTPUT.write_text(text, encoding="utf-8")
    write_log(payload)

    print(f"{SPORT_LABEL} pipeline health: {status}")
    print(f"output: {OUTPUT}")
    print(f"frontend: {FRONTEND_OUTPUT}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    for fatal in fatals:
        print(f"FATAL: {fatal}")
    return 1 if fatals else 0


if __name__ == "__main__":
    raise SystemExit(main())
