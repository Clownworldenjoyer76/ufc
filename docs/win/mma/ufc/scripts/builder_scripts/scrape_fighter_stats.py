import json
import time

from ufcstats_common import build_fighter_index, scrape_fighter_stats

HEADERS = {"User-Agent": "Mozilla/5.0"}

# --- Step 1: Build name -> URL index from all letter pages ---
print("Building fighter URL index from ufcstats.com...")
name_to_url = build_fighter_index(HEADERS, delay=1.0)

# --- Step 3: Match fighters and scrape ---
with open("fighter_attributes.json") as f:
    attrs = json.load(f)

print(f"\nMatching and scraping {len(attrs)} fighters...")
updated = 0
not_matched = []

for i, (name, info) in enumerate(attrs.items()):
    if i % 100 == 0:
        print(f"  Progress: {i}/{len(attrs)}")

    url = name_to_url.get(name)

    if not url:
        # Try title-casing variations
        variations = [
            name.title(),
            " ".join(name.split()[::-1]),  # reverse order
        ]
        for v in variations:
            url = name_to_url.get(v)
            if url:
                break

    if not url:
        not_matched.append(name)
        continue

    stats = scrape_fighter_stats(url, HEADERS)
    if stats:
        attrs[name].update(stats)
        updated += 1

    time.sleep(1.2)

with open("fighter_attributes.json", "w") as f:
    json.dump(attrs, f, indent=2)

print(f"\nDone. Updated {updated} fighters.")
print(f"Not matched ({len(not_matched)}): {not_matched}")

for check in ["Israel Adesanya", "Bobby Green", "Jon Jones"]:
    d = attrs.get(check, {})
    print(f"\n{check}: wins={d.get('career_wins','?')} losses={d.get('career_losses','?')} slpm={d.get('slpm','?')} td_acc={d.get('td_acc','?')}")