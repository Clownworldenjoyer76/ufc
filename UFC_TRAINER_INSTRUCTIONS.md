# Instructions Updated October 27, 2026 at 7:28:22 AM

# UFC Trainer — Instructions

Source: the scripts, docs and data in `UFC_FILES.zip`, the two GitHub repos you named (read-only), your PowerShell output, and tests run on the zip's data. Nothing in `G:\ufc\ufc_trainer` was used.

## 1. What was run and what was not

| Item | Status |
|---|---|
| `parse_ufc_files.py` | Ran on your machine 2026-10-27: 3,196 fights, 2020-06-13 to 2026-10-17 |
| `apply_corrections.py` | Ran on your machine without errors |
| `scrape_historical_stats.py`, `add_missing_fighters.py` (ufcstats) | Ran on your machine and got no data because ufcstats.com serves a bot-check page (section 2). Replaced by `build_from_greco.py` |
| `build_from_greco.py` | New file written for this guide. Ran on your machine without errors: 1,194 of 1,246 fighters matched, 59 fighters added to `fighter_attributes.json`, 53 fighters with no Greco match listed in `no_match_fighters.txt` |
| `build_features.py`, `train_model_weighted.py`, `evaluate_roi.py` | Ran on your machine without errors after `build_from_greco.py`. 686 of 6,392 feature rows have empty historical stats. `ufc_model.pkl` was written at 7:28 AM |

## 2. Facts that affect results

- **ufcstats.com is blocked for scripts.** `http://ufcstats.com/statistics/fighters?char=a&page=all` returns HTTP 200 with a "Checking your browser" JavaScript page and 0 table rows. `scrape_historical_stats.py` failed 1,246 fighters and `add_missing_fighters.py` matched 0 of 65. That run overwrote `fighter_history.json` and `fighter_historical_stats.parquet` in the working folder with empty data. Do not upload those two files unless `build_from_greco.py` has rebuilt them.
- **Replacement data source:** `github.com/Greco1899/scrape_ufc_stats`. Last commit 2026-10-25 ("data refresh"). Events through 2026-10-24. Files used: `ufc_event_details.csv`, `ufc_fight_results.csv`, `ufc_fight_stats.csv`, `ufc_fighter_tott.csv`. (`rfordatascience/tidytuesday` was checked and not used: its fights end 2026-06-27 and it has no per-fight strike or takedown stats.)
- **Greco data differs from your zip's history.** Compared against your zip's `fighter_history.json` (fights found in both):
  - `sig_landed` is identical in 100% of them.
  - `sig_attempted`, `td_landed` and `td_attempted` agree with Greco's matching columns in about 62% of the fights where the possible readings differ. I could not determine why they differ.
  - 1,244 fight rows in your zip's history have no match in Greco by fighter and date, for example Aalon Cruz 2019-07-30. I did not check what event types those are.
  - `build_from_greco.py` rebuilds every fight from Greco, so the whole history is consistent. The features will not be identical to the ones the zip's model was trained on.
- **`name_corrections.json` is not applied.** `apply_corrections.py` expects each value to be a list. All 134 values in the zip's `name_corrections.json` are plain strings. Running `apply_corrections.py` on the zip's `ufc_master.parquet` produced a file identical to the zip's `ufc_master_clean.parquet`.
- **Training cutoff is hard-coded.** `train_model_weighted.py` and `evaluate_roi.py` both use `2025-01-01`. The saved model is trained only on fights before that date. Fights from 2025-01-01 on are used only as the test set.
- **Ian Garry's attributes are wrong in the zip.** `fighter_attributes.json` has DOB Jul 13, 1978 and 155 lbs for "Ian Garry". Greco's `ufc_fighter_tott.csv` has the same values on its "Tom Aaron" row, and has "Ian Machado Garry" with DOB Nov 17, 1997. `build_from_greco.py` does not change existing entries. It reports how many existing DOBs differ from Greco.
- **Two scripts are not in the zip:** `audit_missing_attributes.py` and the original `add_missing_fighters.py`. Both are named in the README.
- **`build_features.py` is slow.** It took 8 minutes on 3,131 fights here and will take longer as fights are added.
- **Model files live at `G:\ufc\docs\win\mma\ufc\data\model`.** The repo has only the `main` branch. The zip's README, `daily_workflow.txt` and `ufc_upload_model.yml` refer to a `model-data` branch and `data/model/`. Those parts of the zip's docs are outdated.

## 3. Folders

- Working folder: `G:\ufc\ufc_trainer\original\UFC FILES`
- Event CSVs stay in `G:\ufc\docs\win\mma\ufc\manual_files`. A folder link named `docs` inside the working folder points to `G:\ufc\docs`, so `parse_ufc_files.py` finds them without moving anything.
- Greco CSVs are downloaded into `G:\ufc\ufc_trainer\original\UFC FILES\greco`.
- All outputs are written to the working folder, including `.bak` copies of `fighter_attributes.json`, `fighter_history.json` and `fighter_historical_stats.parquet`, and `builder_scripts\build_from_greco.py`. The list of fighters with no match is written to `C:\Users\Mat\Downloads\no_match_fighters.txt`. Section 7 copies five model files to `G:\ufc\docs\win\mma\ufc\data\model`.

## 4. Full run (reusable)

First run: searches `C:\Users\Mat` and `G:\ufc` for a zip matching `*UFC*FILES*.zip` (prints which one it used, or `ZIP NOT FOUND` and stops), extracts it, copies the model files next to the scripts, and links your CSV folder. Later runs skip that and never overwrite your trained files. Every run then installs the packages, downloads the latest Greco CSVs, writes `build_from_greco.py`, and runs 6 steps in order. It stops at the first failure and shows each step's last 8 lines. `build_features` takes about 8 minutes.

`build_from_greco.py` replaces both ufcstats scripts. It rebuilds `fighter_history.json` and `fighter_historical_stats.parquet` from Greco for every fighter in `ufc_master_clean.parquet`, adds fighters missing from `fighter_attributes.json`, and saves `.bak` copies of the three files before writing. If fewer than 90% of fighters match Greco, it writes nothing and stops.

```powershell
& {
$W = "G:\ufc\ufc_trainer\original\UFC FILES"
if (-not (Test-Path "$W\model")) {
  $z = Get-ChildItem "C:\Users\Mat","G:\ufc" -Recurse -Filter "*UFC*FILES*.zip" -ErrorAction SilentlyContinue | Select -First 1
  if (-not $z) { "ZIP NOT FOUND under C:\Users\Mat or G:\ufc"; return }
  "Using zip: " + $z.FullName
  Expand-Archive $z.FullName "G:\ufc\ufc_trainer\original" -Force
  Copy-Item "$W\model\*" $W -Force
}
if (-not (Test-Path "$W\docs")) { cmd /c mklink /J "$W\docs" "G:\ufc\docs" | Out-Null }
python -m pip install -q pandas pyarrow scikit-learn xgboost 2>&1 | Out-Null
New-Item -ItemType Directory -Force "$W\greco" | Out-Null
foreach ($f in "ufc_event_details","ufc_fight_results","ufc_fight_stats","ufc_fighter_tott") {
  Invoke-WebRequest "https://raw.githubusercontent.com/Greco1899/scrape_ufc_stats/main/$f.csv" -OutFile "$W\greco\$f.csv"
}
@'
import json, re, shutil, sys, unicodedata
from pathlib import Path
import pandas as pd

G = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("greco")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(r"C:\Users\Mat\Downloads\no_match_fighters.txt")

def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)

# Name overrides copied from scrape_historical_stats.py (only those that norm() alone cannot match)
MANUAL = {"Ian Garry": "Ian Machado Garry", "Nuerdanbieke Shayilan": "Shayilan Nuerdanbieke"}

def pair(s):
    m = re.match(r"\s*(\d+)\s+of\s+(\d+)", str(s))
    return (int(m[1]), int(m[2])) if m else (0, 0)

# ---- Load Greco1899 data ----
ev = pd.read_csv(G / "ufc_event_details.csv")
ev["d"] = pd.to_datetime(ev["DATE"], format="%B %d, %Y", errors="coerce")
date_of = dict(zip(ev["EVENT"], ev["d"]))
res = pd.read_csv(G / "ufc_fight_results.csv").drop_duplicates(["EVENT", "BOUT"])
st = pd.read_csv(G / "ufc_fight_stats.csv").dropna(subset=["FIGHTER"])
for _d in (ev, res, st):
    for _c in ("EVENT", "BOUT", "FIGHTER", "OUTCOME"):
        if _c in _d: _d[_c] = _d[_c].astype(str).str.strip()
date_of = dict(zip(ev["EVENT"], ev["d"]))
st["sl"], st["sa"] = zip(*st["SIG.STR."].map(pair))
st["tl"], st["ta"] = zip(*st["TD"].map(pair))
agg = st.groupby(["EVENT", "BOUT", "FIGHTER"])[["sl", "sa", "tl", "ta"]].sum().to_dict("index")

WORD = {"W": "win", "L": "loss", "D": "draw", "NC": "no contest"}
greco_hist = {}
for r in res.itertuples(index=False):
    d = date_of.get(r.EVENT)
    if d is None or pd.isna(d) or " vs. " not in str(r.BOUT) or "/" not in str(r.OUTCOME):
        continue
    a, b = str(r.BOUT).split(" vs. ", 1)
    oa, ob = str(r.OUTCOME).split("/", 1)
    try:
        rnd = int(r.ROUND)
        m, s = str(r.TIME).split(":")
        last = int(m) * 60 + int(s)
    except Exception:
        rnd, last = 1, 300
    minutes = round(max(0.5, (rnd - 1) * 5 + last / 60), 2)
    for me, opp, o in ((a, b, oa), (b, a, ob)):
        x = agg.get((r.EVENT, r.BOUT, me), {"sl": 0, "sa": 0, "tl": 0, "ta": 0})
        greco_hist.setdefault(me, []).append({
            "date": d.to_pydatetime(), "result": WORD.get(o, o.lower()), "opponent_name": opp,
            "sig_landed": int(x["sl"]), "sig_attempted": int(x["sa"]),
            "td_landed": int(x["tl"]), "td_attempted": int(x["ta"]),
            "minutes": minutes, "detail_url": getattr(r, "URL", "")})
for k in greco_hist:
    greco_hist[k].sort(key=lambda f: f["date"])
g_norm = {}
for k in greco_hist:
    g_norm.setdefault(norm(k), k)

tott = pd.read_csv(G / "ufc_fighter_tott.csv").fillna("")
t_norm = {}
for row in tott.to_dict("records"):
    t_norm.setdefault(norm(row["FIGHTER"]), row)

# ---- Load your data ----
df = pd.read_parquet("ufc_master_clean.parquet")
attrs = json.load(open("fighter_attributes.json", encoding="utf-8"))
names = sorted(set(df["fighter_1"]) | set(df["fighter_2"]))

def gkey(name):
    return norm(MANUAL.get(name, name))

# ---- Fight history (same fields as scrape_historical_stats.py) ----
fighter_history, failed = {}, []
for n in names:
    g = g_norm.get(gkey(n))
    if g: fighter_history[n] = greco_hist[g]
    else: failed.append(n)
if len(fighter_history) < 0.9 * len(names):
    print(f"STOPPED: only {len(fighter_history)} of {len(names)} fighters matched. Nothing was written.")
    sys.exit(1)

def compute_stats_before(fights, before_date):
    prior = [f for f in fights if f["date"] < before_date]
    if not prior: return {}
    wins = sum(1 for f in prior if f["result"] == "win")
    losses = sum(1 for f in prior if f["result"] == "loss")
    tm = sum(f["minutes"] for f in prior)
    sl = sum(f["sig_landed"] for f in prior); sa = sum(f["sig_attempted"] for f in prior)
    tl = sum(f["td_landed"] for f in prior); ta = sum(f["td_attempted"] for f in prior)
    return {"h_career_wins": wins, "h_career_losses": losses, "h_career_fights": wins + losses,
            "h_career_wr": wins / (wins + losses) if (wins + losses) > 0 else 0,
            "h_slpm": round(sl / tm, 4) if tm > 0 else 0,
            "h_str_acc": round(sl / sa, 4) if sa > 0 else 0,
            "h_td_acc": round(tl / ta, 4) if ta > 0 else 0}

records = []
for _, row in df.iterrows():
    f1, f2, date = row["fighter_1"], row["fighter_2"], row["match_date"].to_pydatetime()
    rec = {"match_date": row["match_date"], "fighter_1": f1, "fighter_2": f2}
    for k, v in compute_stats_before(fighter_history.get(f1, []), date).items(): rec[f"f1_{k}"] = v
    for k, v in compute_stats_before(fighter_history.get(f2, []), date).items(): rec[f"f2_{k}"] = v
    records.append(rec)
hist_df = pd.DataFrame(records)

# ---- Add fighters missing from fighter_attributes.json (existing entries are not changed) ----
added, no_attr = 0, []
for n in names:
    if n in attrs: continue
    t = t_norm.get(gkey(n))
    if not t: no_attr.append(n); continue
    attrs[n] = {"height": t["HEIGHT"], "weight": t["WEIGHT"], "reach": t["REACH"],
                "stance": t["STANCE"], "dob": t["DOB"]}
    added += 1
mismatch = []
for n, a in attrs.items():
    t = t_norm.get(gkey(n))
    if t and t["DOB"] and a.get("dob") and t["DOB"] != a["dob"]:
        mismatch.append(n)

# ---- Write ----
for f in ("fighter_attributes.json", "fighter_history.json", "fighter_historical_stats.parquet"):
    if Path(f).exists(): shutil.copy(f, f + ".bak")
json.dump(attrs, open("fighter_attributes.json", "w", encoding="utf-8"), indent=2)
json.dump({n: [{**f, "date": f["date"].strftime("%Y-%m-%d")} for f in fs] for n, fs in fighter_history.items()},
          open("fighter_history.json", "w", encoding="utf-8"), indent=2)
hist_df.to_parquet("fighter_historical_stats.parquet", index=False)
OUT.write_text("\n".join(sorted(set(failed) | set(no_attr))), encoding="utf-8")

print(f"Greco data through {ev['d'].max().date()} | your fights: {len(df)} through {df['match_date'].max().date()}")
print(f"History matched: {len(fighter_history)} of {len(names)} fighters | saved fighter_history.json, fighter_historical_stats.parquet")
print(f"Attributes added: {added} | still missing: {len(no_attr)}")
print(f"No Greco match: {len(set(failed) | set(no_attr))} -> {OUT}")
print(f"Existing attribute DOBs that differ from Greco: {len(mismatch)} {mismatch[:4]}")
'@ | Set-Content "$W\builder_scripts\build_from_greco.py" -Encoding UTF8
cd $W
foreach ($s in "parse_ufc_files","apply_corrections","build_from_greco","build_features","train_model_weighted","evaluate_roi") {
  "=== $s"; python "builder_scripts\$s.py" 2>&1 | Select -Last 8
  if ($LASTEXITCODE) { break }
}
Get-ChildItem $W -File | Where Extension -in ".pkl",".parquet",".json" | Sort LastWriteTime -Desc | Select -First 6 Name,LastWriteTime
}
```

Step order: `parse_ufc_files` → `apply_corrections` → `build_from_greco` → `build_features` → `train_model_weighted` → `evaluate_roi`.

## 5. Missing fighters

**What counts as missing:** any fighter in `ufc_master_clean.parquet` who is not a key in `fighter_attributes.json`.

**Check the list only (no internet, changes nothing). Prints 2 lines:**

```powershell
cd "G:\ufc\ufc_trainer\original\UFC FILES"
python -c "import pandas as pd,json; d=pd.read_parquet('ufc_master_clean.parquet'); k=set(json.load(open('fighter_attributes.json'))); m=sorted((set(d.fighter_1)|set(d.fighter_2))-k); print('Missing:',len(m)); print(m[:8])"
```

**Add them:** `build_from_greco.py` (inside the full run) looks each missing fighter up in Greco's `ufc_fighter_tott.csv` by name (ignoring case, accents, hyphens and punctuation; plus an override for "Ian Garry" and "Nuerdanbieke Shayilan"). It adds `height`, `weight`, `reach`, `stance` and `dob`. It does not add `career_wins`, `career_losses`, `slpm`, `str_acc`, `sapm`, `str_def`, `td_acc` or `td_def`. In the zip's scripts, only `dob`, `height` and `reach` are read from this file (`build_features.py`, `01_build_features.py`). The pipeline scripts `02_edges.py` and later are not in the zip, so I can't say whether they read the other fields.

**Fighters with no Greco match** are listed in `C:\Users\Mat\Downloads\no_match_fighters.txt`. The README says to add such fighters manually to `mappings/mma/ufc/fighter_name_map.csv` and to `UFC_Master\mappings\mma\ufc\ALERT-----missing_attributes_retry.txt`.
**Copy `fighter_attributes.json`** to `G:\ufc\docs\win\mma\ufc\data\model` afterward (section 7).

## 6. New event results

`manual_ufc_final.yml` (workflow "_Manual UFC Final Scores") writes event CSVs into `docs/win/mma/ufc/manual_files` and pushes them to the repo. Pull them to your machine before a run. This prints the last 5 lines:

```powershell
git -C G:\ufc pull origin main 2>&1 | Select -Last 5
```

## 7. Update the model files in the repo

Copy these five files from the working folder to `G:\ufc\docs\win\mma\ufc\data\model`, then commit and push to `main` yourself:
`ufc_model.pkl`, `ufc_master_clean.parquet`, `fighter_history.json`, `fighter_historical_stats.parquet`, `fighter_attributes.json`.

This copies them (overwriting the same-named files there) and lists the five with their dates and sizes:

```powershell
$W = "G:\ufc\ufc_trainer\original\UFC FILES"; $M = "G:\ufc\docs\win\mma\ufc\data\model"
$f = "ufc_model.pkl","ufc_master_clean.parquet","fighter_history.json","fighter_historical_stats.parquet","fighter_attributes.json"
$f | % { Copy-Item "$W\$_" $M -Force }
Get-ChildItem $M | Where Name -in $f | Select Name,LastWriteTime,@{n="MB";e={[math]::Round($_.Length/1MB,2)}}
```

## 8. Reading results

- `train_model_weighted.py` prints Brier score and log loss for the baseline (implied probability only), logistic regression and XGBoost. Lower is better. The README reports XGBoost at Brier 0.1796 versus 0.1979 for the baseline.
- `evaluate_roi.py` prints bets, win % and ROI by edge threshold (3%, 5%, 7%, 10%) for all fighters, underdogs and favorites, and writes `test_predictions.csv`.
