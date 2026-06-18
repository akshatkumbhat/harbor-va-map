"""
Virginia Industrial Market Map — Public Data Prototype
Built for Harbor Capital context: where Virginia's next machining/industrial clusters may be.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
import requests

st.set_page_config(
    page_title="Virginia Industrial Market Map",
    page_icon="🏭",
    layout="wide",
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SCORES_FILE = os.path.join(DATA_DIR, "county_scores.csv")
CBP_FILE = os.path.join(DATA_DIR, "cbp_virginia.csv")


# ── helpers ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_scores() -> pd.DataFrame:
    if not os.path.exists(SCORES_FILE):
        return pd.DataFrame()
    df = pd.read_csv(SCORES_FILE, dtype={"fips": str})
    df["fips"] = df["fips"].str.zfill(5)
    return df


@st.cache_data(ttl=3600)
def load_cbp() -> pd.DataFrame:
    if not os.path.exists(CBP_FILE):
        return pd.DataFrame()
    df = pd.read_csv(CBP_FILE, dtype={"fips": str})
    df["fips"] = df["fips"].str.zfill(5)
    return df


@st.cache_data(ttl=86400)
def load_va_geojson():
    """Load Virginia county GeoJSON from public Census TIGER source."""
    url = (
        "https://raw.githubusercontent.com/plotly/datasets/master/"
        "geojson-counties-fips.json"
    )
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        geo = resp.json()
        # Filter to Virginia (FIPS starts with 51)
        geo["features"] = [
            f for f in geo["features"] if f["id"].startswith("51")
        ]
        return geo
    except Exception as e:
        st.warning(f"Could not load county boundaries: {e}")
        return None


# ── layout ───────────────────────────────────────────────────────────────────

st.title("Virginia Industrial Market Map")
st.markdown(
    "**Public-data prototype** — Where Virginia's precision manufacturing & "
    "industrial services clusters are concentrated, and where Harbor-style "
    "opportunities may be hiding."
)
st.caption("Data: U.S. Census County Business Patterns (2021) · BLS QCEW (2022) · Static NAICS classification")

scores = load_scores()
cbp = load_cbp()

if scores.empty:
    st.error(
        "No data found. Run `python data_fetch.py` first to pull Census & BLS data."
    )
    st.stop()

# ── sidebar filters ───────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Filters")
    min_estab = st.slider("Min. industrial establishments", 0, 200, 5)
    highlight_roanoke = st.checkbox("Highlight Roanoke/Wytheville corridor", value=True)
    top_n = st.slider("Top N counties to highlight", 5, 30, 10)

filtered = scores[scores.get("total_estab", scores.get("total_estab", 0)) >= min_estab].copy() if "total_estab" in scores.columns else scores.copy()

# ── Tab layout ────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs(["County Map", "Top Counties", "Industry Breakdown", "Methodology"])

# ── TAB 1: Choropleth map ─────────────────────────────────────────────────────

with tab1:
    st.subheader("Harbor Score by Virginia County")
    st.caption(
        "Score combines industrial establishment density, employment, manufacturing "
        "workforce, and proximity to the Roanoke–Wytheville corridor."
    )

    geojson = load_va_geojson()

    if geojson and not filtered.empty and "harbor_score" in filtered.columns:
        fig_map = px.choropleth(
            filtered,
            geojson=geojson,
            locations="fips",
            color="harbor_score",
            color_continuous_scale="Blues",
            range_color=(0, filtered["harbor_score"].max()),
            hover_data={
                "fips": False,
                "county_name": True,
                "harbor_score": ":.2f",
                "total_estab": True,
                "total_emp": True,
                "top_category": True,
            },
            labels={
                "harbor_score": "Harbor Score",
                "county_name": "County",
                "total_estab": "Establishments",
                "total_emp": "Employment",
                "top_category": "Top Sector",
            },
        )
        fig_map.update_geos(
            fitbounds="locations",
            visible=False,
        )
        fig_map.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            coloraxis_colorbar=dict(title="Harbor<br>Score"),
            height=520,
        )
        st.plotly_chart(fig_map, use_container_width=True)

        if highlight_roanoke:
            st.info(
                "**Roanoke–Wytheville corridor counties** receive a proximity bonus "
                "in scoring. Harbor's first acquisition (Clarke Precision Machine, Wytheville) "
                "anchors this region."
            )
    else:
        st.warning("Map data unavailable — check that data_fetch.py ran successfully.")

# ── TAB 2: Top counties bar chart ─────────────────────────────────────────────

with tab2:
    st.subheader(f"Top {top_n} Virginia Counties by Harbor Score")

    if not filtered.empty and "harbor_score" in filtered.columns:
        top = filtered.nlargest(top_n, "harbor_score").copy()
        name_col = "county_name" if "county_name" in top.columns else "fips"

        fig_bar = px.bar(
            top,
            x="harbor_score",
            y=name_col,
            orientation="h",
            color="harbor_score",
            color_continuous_scale="Blues",
            hover_data=["total_estab", "total_emp", "top_category"],
            labels={
                "harbor_score": "Harbor Score",
                name_col: "County",
                "total_estab": "Establishments",
                "total_emp": "Employment",
                "top_category": "Top Sector",
            },
        )
        fig_bar.update_layout(
            yaxis={"categoryorder": "total ascending"},
            showlegend=False,
            height=max(350, top_n * 32),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("**Scored county table**")
        display_cols = [c for c in [name_col, "harbor_score", "total_estab", "total_emp", "top_category", "avg_weekly_wage"] if c in top.columns]
        st.dataframe(
            top[display_cols].reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("No scored data available.")

# ── TAB 3: Industry breakdown ─────────────────────────────────────────────────

with tab3:
    st.subheader("Establishment Count by Harbor Category")

    if not cbp.empty and "harbor_category" in cbp.columns:
        cat_agg = (
            cbp.groupby("harbor_category")[["ESTAB", "EMP"]]
            .sum()
            .reset_index()
            .sort_values("ESTAB", ascending=False)
        )

        col1, col2 = st.columns(2)
        with col1:
            fig_pie = px.pie(
                cat_agg,
                names="harbor_category",
                values="ESTAB",
                title="Share of Industrial Establishments",
                hole=0.4,
            )
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            fig_pie.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            fig_emp = px.bar(
                cat_agg,
                x="EMP",
                y="harbor_category",
                orientation="h",
                title="Total Employment by Category",
                color="EMP",
                color_continuous_scale="Blues",
            )
            fig_emp.update_layout(
                yaxis={"categoryorder": "total ascending"},
                coloraxis_showscale=False,
                height=400,
            )
            st.plotly_chart(fig_emp, use_container_width=True)

        st.markdown("---")
        st.subheader("Where is each category concentrated?")

        selected_cat = st.selectbox(
            "Select a Harbor category:",
            options=sorted(cbp["harbor_category"].unique()),
        )

        cat_counties = (
            cbp[cbp["harbor_category"] == selected_cat]
            .groupby(["fips", "county_name"])[["ESTAB", "EMP", "PAYANN"]]
            .sum()
            .reset_index()
            .sort_values("ESTAB", ascending=False)
            .head(20)
        )
        cat_counties["Avg Annual Pay ($k)"] = (
            (cat_counties["PAYANN"] / cat_counties["EMP"].replace(0, float("nan")) / 1000).round(1)
        )

        st.dataframe(
            cat_counties.rename(columns={"county_name": "County", "ESTAB": "Establishments", "EMP": "Employment"})[
                ["County", "Establishments", "Employment", "Avg Annual Pay ($k)"]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("CBP data not available. Run data_fetch.py first.")

# ── TAB 4: Methodology & caveats ──────────────────────────────────────────────

with tab4:
    st.subheader("How This Was Built")

    st.markdown(
        """
**Data sources (all public)**
- **U.S. Census County Business Patterns (2021)** — establishment counts, employment, annual payroll by NAICS industry and county. [Census CBP API](https://www.census.gov/data/developers/data-sets/cbp-zbp/cbp-api.html)
- **BLS Quarterly Census of Employment & Wages (2022)** — county manufacturing employment and average weekly wages. [BLS QCEW](https://www.bls.gov/cew/)
- **Static NAICS classification** — NAICS 4-digit codes mapped manually to Harbor-relevant categories (precision machining, fabricated metal, industrial services, machinery, etc.)

**Scoring methodology**

| Factor | Weight | Rationale |
|---|---|---|
| Industrial establishment density (normalized) | 35% | More businesses = richer ecosystem |
| Total industrial employment (normalized) | 30% | Labor pool depth |
| BLS manufacturing employment (normalized) | 20% | Corroborates Census data |
| Proximity to Roanoke–Wytheville corridor | 15% | Alignment with Harbor's existing footprint |

**What I might be wrong about**

- Proximity weighting is subjective. Harbor may deliberately want to diversify *away* from Southwest Virginia rather than concentrate there.
- CBP suppresses data for counties where establishment counts are too small to protect confidentiality — so the most interesting rural targets may be invisible in this data.
- NAICS categories are broad. "Fabricated Metal" covers everything from precision machining to HVAC ductwork; a real sourcing filter would need to go deeper.
- Score does not capture owner age/succession readiness, relationship networks, or local economic-development incentives — all of which Harbor likely weighs heavily.

**Where a real operator's feedback would improve this**

1. Which NAICS codes actually overlap with Harbor's acquisition criteria?
2. Does proximity to Roanoke/Wytheville matter more than labor pool depth?
3. Are there Virginia regions Harbor has already ruled out for strategic reasons?
        """
    )

    st.divider()
    st.caption(
        "Built by Akshat Kumbhat · Virginia Tech CMDA/Economics · "
        "Public data only · Not affiliated with Harbor Capital"
    )
