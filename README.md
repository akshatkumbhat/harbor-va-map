# Virginia Industrial Market Map

A public-data prototype mapping Virginia's precision manufacturing and industrial services clusters — built to understand where permanent-capital acquisition opportunities may exist across the state.

**Live app →** https://harbor-va-map-lyeczntkij7ipjraqtpf8j.streamlit.app/

---

## What this is

An interactive Streamlit dashboard that scores all 134 Virginia counties on their concentration of industrial businesses, manufacturing employment, and proximity to the Roanoke–Wytheville corridor.

Built by **Akshat Kumbhat**, Virginia Tech CMDA/Economics, as a data-driven way to understand Virginia's industrial base.

## Data sources

All public, no API key required:

| Source | Data | Year |
|---|---|---|
| U.S. Census County Business Patterns | Establishment counts, employment, payroll by NAICS | 2021 |
| BLS Quarterly Census of Employment & Wages | County manufacturing employment, weekly wages | 2022 Q1 |

## Scoring methodology

Each county is scored on:
- Industrial establishment density (35%)
- Total industrial employment (30%)
- BLS manufacturing employment (20%)
- Proximity to Roanoke–Wytheville corridor (15%)

## Running locally

```bash
git clone https://github.com/<your-username>/harbor-va-map
cd harbor-va-map
pip install -r requirements.txt
streamlit run app.py
```

To refresh the underlying data:
```bash
python data_fetch.py
```
