#!/usr/bin/env python3
"""Combine UFC edges and selected picks into one frontend CSV per date."""

import csv
from pathlib import Path

EDGES_DIR = Path("docs/win/mma/ufc/02_edges")
SELECT_DIR = Path("docs/win/mma/ufc/03_select")
OUTPUT_DIR = Path("frontend/data/ufc")

EDGE_SUFFIX = "_ufc_edges.csv"
SELECT_SUFFIX = "_ufc_select.csv"
OUTPUT_SUFFIX = "_ufc.csv"
EXTRA_COLUMNS = ["selected_fighter", "selected_kelly"]


def read_csv(path: Path, required: set[str]) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        missing = required.difference(headers)
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(sorted(missing))}")
        return headers, list(reader)


def fight_key(fighter: str, opponent: str) -> tuple[str, str]:
    return fighter.strip().casefold(), opponent.strip().casefold()


def main() -> None:
    edge_files = sorted(EDGES_DIR.glob(f"*{EDGE_SUFFIX}"))
    if not edge_files:
        raise FileNotFoundError(f"No UFC edges CSVs found in {EDGES_DIR}")

    edge_dates = {path.name[: -len(EDGE_SUFFIX)] for path in edge_files}
    for selection_path in SELECT_DIR.glob(f"*{SELECT_SUFFIX}"):
        date = selection_path.name[: -len(SELECT_SUFFIX)]
        if date not in edge_dates:
            raise FileNotFoundError(f"Selection file has no matching edges file: {selection_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for edges_path in edge_files:
        date = edges_path.name[: -len(EDGE_SUFFIX)]
        select_path = SELECT_DIR / f"{date}{SELECT_SUFFIX}"

        headers, edges = read_csv(edges_path, {"match_date", "fighter_1", "fighter_2"})
        if any(column in headers for column in EXTRA_COLUMNS):
            raise ValueError(f"{edges_path}: output column already exists in edges file")

        picks: dict[tuple[str, str], dict[str, str]] = {}
        if select_path.is_file():
            _, select_rows = read_csv(select_path, {"match_date", "fighter", "opponent", "kelly"})
            for pick in select_rows:
                if pick["match_date"].strip() != date:
                    raise ValueError(f"{select_path}: mismatched match_date: {pick['match_date']}")
                key = fight_key(pick["fighter"], pick["opponent"])
                if key in picks:
                    raise ValueError(f"{select_path}: duplicate pick: {pick['fighter']} vs {pick['opponent']}")
                picks[key] = pick

        output_rows = []
        for edge in edges:
            if edge["match_date"].strip() != date:
                raise ValueError(f"{edges_path}: mismatched match_date: {edge['match_date']}")
            direct = fight_key(edge["fighter_1"], edge["fighter_2"])
            reverse = (direct[1], direct[0])
            pick = picks.pop(direct, None)
            if pick is None:
                pick = picks.pop(reverse, None)
            output_rows.append({
                **edge,
                "selected_fighter": pick["fighter"] if pick else "",
                "selected_kelly": pick["kelly"] if pick else "",
            })

        if picks:
            unmatched = next(iter(picks.values()))
            raise ValueError(
                f"{select_path}: selected fighter not found in edges: "
                f"{unmatched['fighter']} vs {unmatched['opponent']}"
            )

        output_path = OUTPUT_DIR / f"{date}{OUTPUT_SUFFIX}"
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers + EXTRA_COLUMNS)
            writer.writeheader()
            writer.writerows(output_rows)
        print(f"Wrote {output_path} ({len(output_rows)} fights)")


if __name__ == "__main__":
    main()
