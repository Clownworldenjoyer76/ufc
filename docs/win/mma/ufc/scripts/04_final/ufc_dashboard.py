#!/usr/bin/env python3
# docs/win/mma/ufc/scripts/04_final/ufc_dashboard.py
#
# Builds a self-contained UFC results dashboard from the existing UFC
# final-report outputs.
#
# Outputs:
#   frontend/ufc_dashboard.html
#   frontend/mma_dashboard.html

from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
import html
import json
import sys

import pandas as pd


BASE = Path("docs/win/mma/ufc/04_final")
REPORTS = BASE / "reports"
OUTPUT = Path("frontend/ufc_dashboard.html")
MASTER_OUTPUT = Path("frontend/mma_dashboard.html")

REPORT_FILES = [
    ("ev", "EV", REPORTS / "ufc_moneyline_by_ev.csv"),
    ("odds", "Odds", REPORTS / "ufc_by_odds.csv"),
    ("implied_prob", "Implied Prob", REPORTS / "ufc_by_implied_prob.csv"),
    ("model_prob", "Model Prob", REPORTS / "ufc_by_model_prob.csv"),
    ("dratings_prob", "DRatings Prob", REPORTS / "ufc_by_dratings_prob.csv"),
    ("date", "By Date", REPORTS / "ufc_by_date.csv"),
]


CSS = r"""
:root{
  --bg:#0e1117;
  --panel:#161b22;
  --panel2:#1c232c;
  --text:#e6edf3;
  --muted:#8b949e;
  --good:#3fb950;
  --bad:#f85149;
  --border:#30363d;
  --table-border:#46515e;
}
*{box-sizing:border-box}
html,body{
  margin:0;
  padding:0;
  background:var(--bg);
  color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
}
header{
  padding:18px 24px;
  border-bottom:1px solid var(--border);
  display:flex;
  justify-content:space-between;
  align-items:baseline;
  gap:12px;
  flex-wrap:wrap;
}
header h1{margin:0;font-size:20px}
header .ts{font-size:12px;color:var(--muted)}
main{max-width:1500px;margin:0 auto;padding:18px 24px}
h2{
  font-size:16px;
  margin:24px 0 8px;
  border-bottom:1px solid var(--border);
  padding-bottom:4px;
}
.kpis{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(135px,1fr));
  gap:10px;
  margin:12px 0;
}
.kpi{
  background:var(--panel);
  border:1px solid var(--border);
  border-radius:6px;
  padding:12px;
}
.kpi .label{
  font-size:11px;
  color:var(--muted);
  text-transform:uppercase;
  letter-spacing:.05em;
}
.kpi .value{
  font-size:22px;
  font-weight:600;
  margin-top:4px;
}
.good{color:var(--good)}
.bad{color:var(--bad)}
.muted{color:var(--muted)}
.tabs{
  display:flex;
  gap:4px;
  flex-wrap:wrap;
  margin:14px 0 0;
}
.tab{
  background:var(--panel2);
  border:1px solid var(--border);
  color:var(--muted);
  padding:7px 12px;
  border-radius:6px 6px 0 0;
  cursor:pointer;
  font-size:13px;
}
.tab.active{
  color:var(--text);
  border-bottom-color:var(--panel2);
}
.tab-body{
  background:var(--panel2);
  border:1px solid var(--border);
  border-top:none;
  padding:14px;
  border-radius:0 6px 6px 6px;
}
.scroll{
  overflow:auto;
  max-height:62vh;
  border:1px solid var(--table-border);
  border-radius:6px;
}
table{
  width:100%;
  border-collapse:collapse;
  font-size:13px;
}
th,td{
  padding:8px 10px;
  border:1px solid var(--table-border);
  white-space:nowrap;
  text-align:center;
  vertical-align:middle;
}
th{
  position:sticky;
  top:0;
  z-index:1;
  background:var(--panel2);
  color:var(--muted);
  font-size:11px;
  text-transform:uppercase;
  letter-spacing:.04em;
  cursor:pointer;
  user-select:none;
}
td.num{
  text-align:center;
  font-variant-numeric:tabular-nums;
}
td.win-pct-strong{
  background:rgba(63,185,80,.24);
  color:#7ee787;
  font-weight:700;
}
td.win-pct-green{
  background:rgba(63,185,80,.16);
  color:#56d364;
  font-weight:600;
}
td.win-pct-light{
  background:rgba(63,185,80,.09);
  color:#8ddb8c;
  font-weight:600;
}
td.win-pct-neutral{
  background:rgba(139,148,158,.09);
  color:#c9d1d9;
}
td.win-pct-red{
  background:rgba(248,81,73,.14);
  color:#ff7b72;
  font-weight:600;
}
"""


JS = r"""
function fmtPct(v){
  if(v==null||isNaN(Number(v)))return "";
  return (Number(v)*100).toFixed(2)+"%";
}
function fmtNum(v,d=3){
  if(v==null||isNaN(Number(v)))return "";
  return Number(v).toFixed(d);
}
function fmtInt(v){
  if(v==null||isNaN(Number(v)))return "";
  return Number(v).toLocaleString();
}
function signedClass(v){
  if(v==null||isNaN(Number(v)))return "";
  return Number(v)>0?"good":(Number(v)<0?"bad":"");
}
function winPctClass(v){
  if(v==null||isNaN(Number(v)))return "";
  const pct=Number(v);
  if(pct>=0.80)return "win-pct-strong";
  if(pct>=0.70)return "win-pct-green";
  if(pct>=0.60)return "win-pct-light";
  if(pct>=0.50)return "win-pct-neutral";
  return "win-pct-red";
}
function showTab(host,key){
  host.querySelectorAll(":scope > .tabs .tab").forEach(
    x=>x.classList.toggle("active",x.dataset.key===key)
  );
  host.querySelectorAll(":scope > .tab-body > .tab-panel").forEach(
    x=>x.style.display=x.dataset.key===key?"":"none"
  );
}
function renderTable(data,columns,container){
  if(!data||!data.length){
    container.innerHTML='<div class="muted">No rows available.</div>';
    return;
  }

  const wrap=document.createElement("div");
  wrap.className="scroll";

  const table=document.createElement("table");
  const thead=document.createElement("thead");
  const tbody=document.createElement("tbody");
  const hr=document.createElement("tr");

  let sortKey=null;
  let sortDir="desc";

  columns.forEach(c=>{
    const th=document.createElement("th");
    th.textContent=c.label;
    th.addEventListener("click",()=>{
      if(sortKey===c.key){
        sortDir=sortDir==="asc"?"desc":"asc";
      }else{
        sortKey=c.key;
        sortDir="desc";
      }
      draw();
    });
    hr.appendChild(th);
  });

  thead.appendChild(hr);

  function draw(){
    const rows=data.slice();

    if(sortKey){
      rows.sort((a,b)=>{
        const av=a[sortKey];
        const bv=b[sortKey];

        if(av==null)return 1;
        if(bv==null)return -1;

        const an=Number(av);
        const bn=Number(bv);

        if(!Number.isNaN(an)&&!Number.isNaN(bn)){
          return sortDir==="asc"?an-bn:bn-an;
        }

        return sortDir==="asc"
          ?String(av).localeCompare(String(bv))
          :String(bv).localeCompare(String(av));
      });
    }

    tbody.innerHTML="";

    rows.forEach(r=>{
      const tr=document.createElement("tr");

      columns.forEach(c=>{
        const td=document.createElement("td");
        const v=r[c.key];

        if(c.fmt==="int"){
          td.classList.add("num");
          td.textContent=fmtInt(v);
        }else if(c.fmt==="pct"){
          td.classList.add("num");
          td.textContent=fmtPct(v);
          if(c.key==="win_pct"){
            const cls=winPctClass(v);
            if(cls)td.classList.add(cls);
          }
        }else if(c.fmt==="num"){
          td.classList.add("num");
          td.textContent=fmtNum(v,c.decimals==null?3:c.decimals);

          if(c.signed){
            const cls=signedClass(v);
            if(cls)td.classList.add(cls);
          }
        }else{
          td.textContent=v==null?"":String(v);
        }

        tr.appendChild(td);
      });

      tbody.appendChild(tr);
    });
  }

  draw();

  table.appendChild(thead);
  table.appendChild(tbody);
  wrap.appendChild(table);
  container.innerHTML="";
  container.appendChild(wrap);
}
"""


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>UFC Analytics</title>
<link rel="stylesheet" href="assets/css/matstheme.css">
<style>__CSS_HTML__</style>
</head>
<body>
<div id="nav-placeholder"></div>

<header>
  <h1>UFC Analytics</h1>
  <span class="ts">Built __GENERATED__ UTC</span>
</header>

<main>
  <div class="kpis" id="headline"></div>

  <h2>Moneyline Performance</h2>

  <div id="report-tabs">
    <div class="tabs">__TABS__</div>
    <div class="tab-body">__PANELS__</div>
  </div>
</main>

<script src="assets/js/shared/nav.js"></script>
<script>
__JS_HTML__

const DATA=__DATA__;

const REPORT_COLUMNS=[
  {key:"bucket",label:"Bucket"},
  {key:"bets",label:"Bets",fmt:"int"},
  {key:"wins",label:"W",fmt:"int"},
  {key:"losses",label:"L",fmt:"int"},
  {key:"pushes",label:"P",fmt:"int"},
  {key:"win_pct",label:"Win %",fmt:"pct"},
  {key:"units_flat",label:"Units",fmt:"num",decimals:3,signed:true},
  {key:"roi_flat",label:"ROI",fmt:"pct"},
  {key:"avg_implied_prob",label:"Avg Implied",fmt:"pct"},
  {key:"avg_model_prob",label:"Avg Model",fmt:"pct"},
  {key:"avg_dratings_prob",label:"Avg DRatings",fmt:"pct"},
  {key:"avg_odds_american",label:"Avg Odds"}
];

function kpi(label,value,fmt){
  let text="—";

  if(value!=null&&!Number.isNaN(Number(value))){
    if(fmt==="pct")text=fmtPct(value);
    else if(fmt==="int")text=fmtInt(value);
    else if(fmt==="num")text=fmtNum(value,3);
  }

  return '<div class="kpi"><div class="label">'+label+
    '</div><div class="value">'+text+'</div></div>';
}

document.addEventListener("DOMContentLoaded",()=>{
  const h=DATA.headline||{};

  document.getElementById("headline").innerHTML=[
    kpi("Bets",h.bets,"int"),
    kpi("Wins",h.wins,"int"),
    kpi("Losses",h.losses,"int"),
    kpi("Pushes",h.pushes,"int"),
    kpi("Win %",h.win_pct,"pct"),
    kpi("Units",h.units,"num"),
    kpi("ROI",h.roi,"pct")
  ].join("");

  const host=document.getElementById("report-tabs");

  Object.entries(DATA.reports||{}).forEach(([key,report])=>{
    const panel=host.querySelector(
      '.tab-panel[data-key="'+key+'"]'
    );
    if(panel){
      renderTable(report.rows||[],REPORT_COLUMNS,panel);
    }
  });

  host.querySelectorAll(":scope > .tabs .tab").forEach(
    tab=>tab.addEventListener(
      "click",
      ()=>showTab(host,tab.dataset.key)
    )
  );
});
</script>
</body>
</html>
"""


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
    except Exception:
        pass

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
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


def build_html(payload: dict) -> str:
    tabs = "\n".join(
        '<button class="tab{}" data-key="{}">{}</button>'.format(
            " active" if index == 0 else "",
            key,
            html.escape(label),
        )
        for index, (key, label, _) in enumerate(REPORT_FILES)
    )

    panels = "\n".join(
        '<div class="tab-panel" data-key="{}"{}></div>'.format(
            key,
            ' style="display:none"' if index else "",
        )
        for index, (key, _, _) in enumerate(REPORT_FILES)
    )

    data = (
        json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
        )
        .replace("</", "<\\/")
    )

    return (
        HTML_TEMPLATE
        .replace("__CSS_HTML__", CSS)
        .replace("__JS_HTML__", JS)
        .replace(
            "__GENERATED__",
            html.escape(
                datetime.now(UTC).isoformat(
                    timespec="seconds"
                )
            ),
        )
        .replace("__TABS__", tabs)
        .replace("__PANELS__", panels)
        .replace("__DATA__", data)
    )


def main() -> None:
    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    league_page = build_html(
        build_payload()
    )

    master_page = (
        league_page
        .replace(
            "<title>UFC Analytics</title>",
            "<title>MMA Dashboard</title>",
            1,
        )
        .replace(
            "<h1>UFC Analytics</h1>",
            "<h1>MMA Dashboard</h1>",
            1,
        )
    )

    OUTPUT.write_text(
        league_page,
        encoding="utf-8",
    )

    MASTER_OUTPUT.write_text(
        master_page,
        encoding="utf-8",
    )

    print(
        f"UFC dashboard generated: {OUTPUT}"
    )

    print(
        f"MMA master dashboard generated: "
        f"{MASTER_OUTPUT}"
    )


if __name__ == "__main__":
    main()
