"""
Fetches Virginia county-level industrial data from Census CBP and BLS QCEW bulk downloads.
No API key required — uses public FTP/download endpoints.
"""

import io
import os
import zipfile

import pandas as pd
import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# 4-digit NAICS codes → Harbor-relevant category (static mapping, no LLM needed)
NAICS_CATEGORY = {
    "3310": "Primary Metals",
    "3320": "Fabricated Metal / Precision Machining",
    "3330": "Industrial Machinery",
    "3340": "Electronics / Advanced Mfg",
    "3350": "Electrical Equipment",
    "3360": "Transportation Equipment",
    "3370": "Furniture & Related",
    "3390": "Specialty / Misc Manufacturing",
    "2380": "Industrial Services / Contracting",
    "4230": "Industrial Distribution",
    "8110": "Repair & Maintenance",
    "5417": "R&D / Technical Services",
}

TARGET_NAICS_4 = set(NAICS_CATEGORY.keys())


def _download_zip(url: str, desc: str) -> zipfile.ZipFile:
    print(f"  Downloading {desc}...")
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    total = int(resp.headers.get("Content-Length", 0))
    buf = io.BytesIO()
    downloaded = 0
    for chunk in resp.iter_content(chunk_size=1024 * 256):
        buf.write(chunk)
        downloaded += len(chunk)
        if total:
            pct = downloaded / total * 100
            print(f"\r    {pct:.0f}% ({downloaded // 1024 // 1024} MB / {total // 1024 // 1024} MB)", end="", flush=True)
    print()
    buf.seek(0)
    return zipfile.ZipFile(buf)


def fetch_cbp_virginia(year: int = 2021) -> pd.DataFrame:
    """
    Download Census County Business Patterns bulk file and filter to
    Virginia (FIPS state 51) + target NAICS sectors.
    """
    url = f"https://www2.census.gov/programs-surveys/cbp/datasets/{year}/cbp{str(year)[2:]}co.zip"
    print(f"Fetching Census CBP {year}...")
    zf = _download_zip(url, f"CBP {year} county file (~11 MB)")

    # The main county file is named cbpYYco.txt
    fname = [n for n in zf.namelist() if n.lower().endswith("co.txt")][0]
    with zf.open(fname) as f:
        df = pd.read_csv(f, dtype=str, low_memory=False)

    df.columns = [c.strip().upper() for c in df.columns]

    # Keep Virginia (FIPS state = 51) only
    df = df[df["FIPSTATE"] == "51"].copy()

    # NAICS column name varies by year
    naics_col = next((c for c in df.columns if "NAICS" in c), None)
    if naics_col is None:
        print("  Could not find NAICS column. Columns:", df.columns.tolist())
        return pd.DataFrame()

    # Keep only 4-digit NAICS in our target set (CBP uses right-dash-padded codes like "3320--")
    df["NAICS4"] = df[naics_col].str.strip().str[:4]
    df = df[df["NAICS4"].isin(TARGET_NAICS_4)].copy()

    # CBP column names: EST=establishments, AP=annual payroll, EMP=employment
    df = df.rename(columns={"EST": "ESTAB", "AP": "PAYANN"})

    # Numeric conversion (CBP uses flags like 'N' for suppressed data)
    for col in ["EMP", "ESTAB", "PAYANN"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["harbor_category"] = df["NAICS4"].map(NAICS_CATEGORY)
    df["fips"] = df["FIPSTATE"].str.zfill(2) + df["FIPSCTY"].str.zfill(3)

    # Load county names from CBP layout file included in the zip, or build from FIPS
    # County names are in a separate file; we'll join from a built-in mapping below
    df["county_name"] = df["fips"]  # placeholder; enriched later

    out = os.path.join(DATA_DIR, "cbp_virginia.csv")
    df.to_csv(out, index=False)
    print(f"  Saved {len(df)} rows → {out}")
    return df


def fetch_qcew_virginia(year: int = 2022) -> pd.DataFrame:
    """
    Fetch BLS QCEW quarterly data for all Virginia counties via individual API calls.
    Uses Q1 data (quarter=1) as a proxy for annual snapshot — no API key needed.
    """
    # All Virginia county + independent city FIPS codes
    va_fips = [
        "51001","51003","51005","51007","51009","51011","51013","51015","51017","51019",
        "51021","51023","51025","51027","51029","51031","51033","51035","51036","51037",
        "51041","51043","51045","51047","51049","51051","51053","51057","51059","51061",
        "51063","51065","51067","51069","51071","51073","51075","51077","51079","51081",
        "51083","51085","51087","51089","51091","51093","51095","51097","51099","51101",
        "51103","51105","51107","51109","51111","51113","51115","51117","51119","51121",
        "51125","51127","51131","51133","51135","51137","51139","51141","51143","51145",
        "51147","51149","51153","51155","51157","51159","51161","51163","51165","51167",
        "51169","51171","51173","51175","51177","51179","51181","51183","51185","51187",
        "51191","51193","51195","51197","51199","51510","51515","51520","51530","51540",
        "51550","51570","51580","51590","51595","51600","51610","51620","51630","51640",
        "51650","51660","51670","51678","51680","51683","51685","51690","51700","51710",
        "51720","51730","51735","51740","51750","51760","51770","51775","51790","51800",
        "51810","51820","51830","51840",
    ]

    print(f"Fetching BLS QCEW {year} Q1 for {len(va_fips)} Virginia counties...")
    frames = []
    for i, fips in enumerate(va_fips):
        url = f"https://data.bls.gov/cew/data/api/{year}/1/area/{fips}.csv"
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                continue
            from io import StringIO
            sub = pd.read_csv(StringIO(resp.text), dtype=str, low_memory=False)
            sub.columns = [c.strip().strip('"').lower().replace(" ", "_") for c in sub.columns]
            frames.append(sub)
            if (i + 1) % 25 == 0:
                print(f"  {i + 1}/{len(va_fips)} counties fetched...")
        except Exception as e:
            pass  # Skip failed counties silently

    if not frames:
        print("  No QCEW Virginia data found.")
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)

    # Keep total manufacturing (industry_code 31-33) or all industries (10) for reference
    mfg_codes = {"31-33", "1013", "1014", "10"}
    if "industry_code" in df.columns:
        df = df[df["industry_code"].str.strip('"').isin(mfg_codes)].copy()

    numeric_cols = ["month1_emplvl", "month2_emplvl", "month3_emplvl", "avg_wkly_wage", "qtrly_estabs"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.strip('"').str.replace(",", ""), errors="coerce"
            ).fillna(0)

    # Use avg of monthly employment as proxy for annual avg
    if "month1_emplvl" in df.columns:
        df["annual_avg_emplvl"] = ((df["month1_emplvl"] + df["month2_emplvl"] + df["month3_emplvl"]) / 3).round(0)
    if "avg_wkly_wage" in df.columns:
        df["annual_avg_wkly_wage"] = df["avg_wkly_wage"]

    if "area_fips" in df.columns:
        df["fips"] = df["area_fips"].astype(str).str.strip('"').str.zfill(5)

    out = os.path.join(DATA_DIR, "qcew_virginia.csv")
    df.to_csv(out, index=False)
    print(f"  Saved {len(df)} rows → {out}")
    return df


def load_county_names() -> pd.DataFrame:
    """Return a DataFrame mapping FIPS → county name using Census national county file."""
    url = "https://www2.census.gov/geo/docs/reference/codes2020/national_county2020.txt"
    try:
        import ssl
        import urllib.request
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        resp = requests.get(url, verify=False, timeout=30)
        resp.raise_for_status()
        from io import StringIO
        df = pd.read_csv(StringIO(resp.text), sep="|", dtype=str)
        df.columns = [c.strip() for c in df.columns]
        df["fips"] = df["STATEFP"].str.zfill(2) + df["COUNTYFP"].str.zfill(3)
        va = df[df["STATEFP"] == "51"][["fips", "COUNTYNAME"]].rename(columns={"COUNTYNAME": "county_name"})
        return va
    except Exception as e:
        print(f"  County name lookup failed ({e}); using FIPS codes as names.")
        return pd.DataFrame(columns=["fips", "county_name"])


def build_county_scores(cbp: pd.DataFrame, qcew: pd.DataFrame) -> pd.DataFrame:
    """Aggregate CBP + QCEW into one scored county table."""

    county_names = load_county_names()

    # --- CBP aggregation ---
    if cbp.empty:
        cbp_agg = pd.DataFrame(columns=["fips", "total_estab", "total_emp", "total_payann", "top_category"])
    else:
        cbp_agg = (
            cbp.groupby("fips")
            .agg(total_estab=("ESTAB", "sum"), total_emp=("EMP", "sum"), total_payann=("PAYANN", "sum"))
            .reset_index()
        )
        top_cat = (
            cbp.groupby(["fips", "harbor_category"])["ESTAB"]
            .sum()
            .reset_index()
            .sort_values("ESTAB", ascending=False)
            .drop_duplicates("fips")[["fips", "harbor_category"]]
            .rename(columns={"harbor_category": "top_category"})
        )
        cbp_agg = cbp_agg.merge(top_cat, on="fips", how="left")

    # --- QCEW aggregation ---
    if qcew.empty:
        qcew_agg = pd.DataFrame(columns=["fips", "mfg_employment", "avg_weekly_wage"])
    else:
        qcew_agg = (
            qcew.groupby("fips")
            .agg(mfg_employment=("annual_avg_emplvl", "mean"), avg_weekly_wage=("annual_avg_wkly_wage", "mean"))
            .reset_index()
        )

    df = cbp_agg.merge(qcew_agg, on="fips", how="outer")
    df = df.merge(county_names, on="fips", how="left")

    # Fallback county name from fips
    df["county_name"] = df["county_name"].fillna(df["fips"])

    # --- Proximity score (closer to Roanoke/Wytheville corridor = higher score) ---
    roanoke_adjacent = {
        "51770",  # Roanoke City
        "51023",  # Botetourt
        "51045",  # Craig
        "51067",  # Franklin
        "51161",  # Roanoke County
        "51197",  # Wythe (Clarke acquisition)
        "51021",  # Bland
        "51071",  # Giles
        "51155",  # Pulaski
        "51185",  # Tazewell
        "51063",  # Floyd
        "51173",  # Smyth
        "51035",  # Carroll
        "51141",  # Patrick
        "51775",  # Salem City
    }
    df["proximity_score"] = df["fips"].apply(lambda f: 3 if str(f) in roanoke_adjacent else 1)

    # --- Normalize + composite score ---
    for col in ["total_estab", "total_emp", "mfg_employment"]:
        if col in df.columns:
            max_val = df[col].max()
            df[f"{col}_norm"] = (df[col] / max_val * 10).round(2) if max_val else 0
        else:
            df[f"{col}_norm"] = 0

    df["harbor_score"] = (
        df["total_estab_norm"] * 0.35
        + df["total_emp_norm"] * 0.30
        + df["mfg_employment_norm"] * 0.20
        + df["proximity_score"] * 0.15
    ).round(2)

    out = os.path.join(DATA_DIR, "county_scores.csv")
    df.to_csv(out, index=False)
    print(f"Saved scored county table ({len(df)} counties) → {out}")
    return df


if __name__ == "__main__":
    cbp = fetch_cbp_virginia()
    qcew = fetch_qcew_virginia()
    build_county_scores(cbp, qcew)
    print("\nData fetch complete. Run: streamlit run app.py")
