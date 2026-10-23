#!/usr/bin/env python3
"""Copy UFC edges CSVs to the frontend Games Today directory."""

from pathlib import Path
from shutil import copy2


SOURCE_DIR = Path("docs/win/mma/ufc/02_edges")
OUTPUT_DIR = Path("frontend/data/index_home/ufc")


def main() -> None:
    files = sorted(SOURCE_DIR.glob("*_ufc_edges.csv"))
    if not files:
        print(f"No UFC edges CSV files found in {SOURCE_DIR}; nothing to copy.")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for source in files:
        destination = OUTPUT_DIR / source.name
        copy2(source, destination)
        print(f"Copied {source} -> {destination}")

    print(f"Copied {len(files)} UFC edges CSV file(s).")


if __name__ == "__main__":
    main()
