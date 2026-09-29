from __future__ import annotations

import time

import requests
from bs4 import BeautifulSoup


def build_fighter_index(headers, delay=0.8):
    name_to_url = {}

    for char in "abcdefghijklmnopqrstuvwxyz":
        url = f"http://ufcstats.com/statistics/fighters?char={char}&page=all"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for row in soup.select("tr.b-statistics__table-row"):
                cols = row.select("td")
                anchor = row.select_one("a")
                if not cols or anchor is None:
                    continue
                first = cols[0].get_text(strip=True)
                last = cols[1].get_text(strip=True)
                href = anchor.get("href")
                if first and last and href:
                    name_to_url[f"{first} {last}"] = href
        except requests.RequestException as exc:
            print(f"  Error {char}: {exc}")

        time.sleep(delay)

    print(f"Index: {len(name_to_url)} fighters")
    return name_to_url


def scrape_fighter_stats(url, headers):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"  Page error: {exc}")
        return {}

    soup = BeautifulSoup(response.text, "html.parser")
    data = {}

    record_el = soup.select_one("span.b-content__title-record")
    if record_el:
        try:
            parts = (
                record_el.get_text(strip=True)
                .replace("Record:", "")
                .strip()
                .split("-")
            )
            data["career_wins"] = int(parts[0])
            data["career_losses"] = int(parts[1])
        except (IndexError, ValueError):
            pass

    for item in soup.select("li.b-list__box-list-item"):
        label_tag = item.find("i")
        if label_tag is None:
            continue

        label = label_tag.get_text(strip=True).rstrip(":")
        label_tag.decompose()
        value = item.get_text(strip=True)

        try:
            if label == "SLpM":
                data["slpm"] = float(value)
            elif label == "Str. Acc.":
                data["str_acc"] = float(value.replace("%", "")) / 100
            elif label == "SApM":
                data["sapm"] = float(value)
            elif label == "Str. Def":
                data["str_def"] = float(value.replace("%", "")) / 100
            elif label == "TD Acc.":
                data["td_acc"] = float(value.replace("%", "")) / 100
            elif label == "TD Def.":
                data["td_def"] = float(value.replace("%", "")) / 100
        except ValueError:
            pass

    return data
