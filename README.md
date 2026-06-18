# Virginia Industrial Market Map

> A public-data prototype mapping Virginia's precision manufacturing and industrial services clusters — built to understand where permanent-capital acquisition opportunities may exist across the state.

**Live app →** https://harbor-va-map-lyeczntkij7ipjraqtpf8j.streamlit.app/

**Built by** Akshat Kumbhat · Virginia Tech CMDA / Economics

---

## The question this answers

Harbor Capital (Roanoke, VA) is building a statewide machine group through the acquisition of established, owner-led Virginia manufacturers. The obvious question is: *where are the remaining clusters?*

This tool scores all 134 Virginia counties on the density and quality of their industrial base using only public data — no proprietary sources, no API keys.

---

## Key finding

The most interesting result is what the data **cannot** see.

Wythe County, Roanoke County, and most of the Southwest Virginia corridor return suppressed or missing values in the Census data. The Census Bureau withholds establishment-level figures for small counties to protect confidentiality — which means the businesses most relevant to a permanent-capital acquirer (profitable, owner-led, 10–75 employees) are largely **invisible in public datasets**.

This is not a flaw in the tool. It is a structural feature of the market: the best targets in this space cannot be found by scraping databases. They require relationships, local knowledge, and trust — exactly the sourcing model a firm like Harbor is building.

Northern Virginia dominates the raw rankings (Fairfax County scores 8x higher than any other county) because it concentrates defense R&D contractors, not precision machining shops. The geographic mismatch between where public data points and where the actual opportunity is concentrated is itself a useful signal.

---

## Industries tracked

Mapped using static NAICS classification across 12 Harbor-relevant categories:

| NAICS | Category |
|---|---|
| 3320 | Fabricated Metal / Precision Machining |
| 3330 | Industrial Machinery |
| 3310 | Primary Metals |
| 3350 | Electrical Equipment |
| 3360 | Transportation Equipment |
| 3390 | Specialty / Misc Manufacturing |
| 2380 | Industrial Services / Contracting |
| 4230 | Industrial Distribution |
| 8110 | Repair & Maintenance |
| 3340 | Electronics / Advanced Mfg |
| 3370 | Furniture & Related |
| 5417 | R&D / Technical Services |

---

## Scoring methodology

Each county receives a composite Harbor Score (0–10):

| Factor | Weight | Rationale |
|---|---|---|
| Industrial establishment density | 35% | More businesses = richer ecosystem |
| Total industrial employment | 30% | Labor pool depth |
| BLS manufacturing employment | 20% | Corroborates Census data |
| Proximity to Roanoke–Wytheville corridor | 15% | Alignment with existing Harbor footprint |

---

## Data sources

All public, no API key required:

| Source | Data | Year |
|---|---|---|
| U.S. Census County Business Patterns (bulk download) | Establishment counts, employment, annual payroll by NAICS | 2021 |
| BLS Quarterly Census of Employment & Wages (per-county API) | Manufacturing employment, average weekly wages | 2022 Q1 |
| Census TIGER / Plotly GeoJSON | Virginia county boundaries for choropleth map | 2020 |

---

## What I might be wrong about

- **Proximity weighting is subjective.** Harbor may want to diversify *away* from Southwest Virginia rather than concentrate there.
- **NAICS categories are broad.** "Fabricated Metal" covers precision machining and HVAC ductwork equally — a real sourcing filter needs to go deeper.
- **Score ignores succession readiness.** Owner age, business age, and transition intent are the variables that matter most to permanent capital — none of these are in public data.
- **CBP suppression is systematic.** The most interesting targets are the ones missing from this map, not the ones on it.

---

## Run locally

```bash
git clone https://github.com/akshatkumbhat/harbor-va-map
cd harbor-va-map
pip install -r requirements.txt
streamlit run app.py
```

To refresh the underlying data from Census and BLS:

```bash
python data_fetch.py
```
