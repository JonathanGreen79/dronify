# dronify.py — full version with detailed sidebar view & expandable spec panels
# Includes same-tab navigation via query params, natural sorting,
# random per-series image selection, and 2-row grid layout.

import re
import random
import streamlit as st
import pandas as pd
import yaml
from pathlib import Path

st.set_page_config(page_title="Dronify", layout="wide")

# ---------- Paths ----------
DATASET_PATH = Path("dji_drones.yaml")
TAXONOMY_PATH = Path("taxonomy.yaml")

# ---------- Load ----------
def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@st.cache_data
def load_data():
    dataset = load_yaml(DATASET_PATH)
    taxonomy = load_yaml(TAXONOMY_PATH)
    df = pd.DataFrame(dataset["data"])
    for col in (
        "image_url","segment","series","marketing_name","model_key",
        "eu_class_marking","uk_class_marking","operator_id_required",
        "spec_url","sensor","effective_mp","aperture","focal_length_eq",
        "video_resolutions","log_profile","transmission_system",
        "max_range_km","controller_compat","wind_resistance",
        "battery_type","battery_capacity_mah","max_flight_time_min",
        "charging_power_w","dim_folded","dim_unfolded","diagonal_length",
        "notes","year_released"
    ):
        if col not in df.columns:
            df[col] = ""
    return df, taxonomy

df, taxonomy = load_data()

# ---------- Query params ----------
def get_qp():
    try:
        return dict(st.query_params)
    except Exception:
        return {k: (v[0] if isinstance(v, list) else v)
                for k, v in st.experimental_get_query_params().items()}

qp = get_qp()
segment = qp.get("segment")
series  = qp.get("series")
model   = qp.get("model")

# ---------- Image resolver ----------
RAW_BASE = "https://raw.githubusercontent.com/JonathanGreen79/dronify/main/images/"

def resolve_img(url: str) -> str:
    if not url:
        return ""
    if url.startswith("images/"):
        return RAW_BASE + url.split("/", 1)[1]
    return url

SEGMENT_HERO = {
    "consumer": resolve_img("images/consumer.jpg"),
    "pro":       resolve_img("images/professional.jpg"),
    "enterprise":resolve_img("images/enterprise.jpg"),
}

# ---------- Helpers ----------
def series_defs_for(segment_key: str):
    seg = next(s for s in taxonomy["segments"] if s["key"] == segment_key)
    return [s for s in seg["series"]
            if not df[(df["segment"] == segment_key) & (df["series"] == s["key"])].empty]

def pad_digits_for_natural(series: pd.Series, width: int = 6) -> pd.Series:
    s = series.astype(str).str.lower()
    return s.str.replace(r"\d+", lambda m: f"{int(m.group(0)):0{width}d}", regex=True)

def models_for(segment_key: str, series_key: str):
    subset = df[(df["segment"] == segment_key) & (df["series"] == series_key)].copy()
    subset["series_key"] = pad_digits_for_natural(subset["series"])
    subset["name_key"]   = pad_digits_for_natural(subset["marketing_name"])
    subset = subset.sort_values(
        by=["series_key","name_key","marketing_name"], kind="stable", ignore_index=True
    )
    return subset.drop(columns=["series_key","name_key"])

def random_image_for_series(segment_key: str, series_key: str) -> str:
    subset = df[
        (df["segment"] == segment_key)
        & (df["series"] == series_key)
        & (df["image_url"].astype(str) != "")
    ]
    if subset.empty:
        return SEGMENT_HERO.get(segment_key, "")
    return resolve_img(str(subset.sample(1)["image_url"].iloc[0]))

# ---------- Styles ----------
st.markdown("""
<style>
.block-container { padding-top: 1.1rem; }

/* cards */
.card {
  width: 260px; height: 240px;
  border: 1px solid #E5E7EB; border-radius: 14px;
  background: #fff; color: #111827 !important; text-decoration: none !important;
  display: block; padding: 12px;
  transition: box-shadow .15s ease, transform .15s ease, border-color .15s ease;
}
.card:hover { border-color:#D1D5DB; box-shadow:0 6px 18px rgba(0,0,0,.08); transform:translateY(-2px); }

.img { width:100%; height:150px; border-radius:10px; background:#F3F4F6;
  display:flex; align-items:center; justify-content:center; overflow:hidden; }
.img img { width:100%; height:100%; object-fit:cover; }

.title { margin-top:10px; text-align:center; font-weight:700; font-size:0.98rem; }
.sub { margin-top:4px; text-align:center; font-size:.8rem; color:#6B7280; }

.strip { display:flex; flex-wrap:nowrap; gap:14px; overflow-x:auto; padding:8px 2px; margin:0; }
.strip2 { display:grid; grid-auto-flow:column; grid-auto-columns:260px;
  grid-template-rows:repeat(2,1fr); gap:14px; overflow-x:auto; padding:8px 2px; margin:0; }

.h1 { font-weight:800; font-size:1.2rem; color:#1F2937; margin:0 0 12px 0; }

.badge {
  display:inline-block; border-radius:10px; padding:4px 10px;
  font-size:0.8rem; margin:2px 4px 4px 0;
}
.chip-yes { background:#d4edda; color:#155724; }
.chip-no { background:#f8d7da; color:#721c24; }
</style>
""", unsafe_allow_html=True)

# ---------- Card builder ----------
def card_link(qs: str, title: str, sub: str = "", img_url: str = "") -> str:
    img = f"<div class='img'><img src='{img_url}' alt=''/></div>" if img_url else "<div class='img'></div>"
    sub_html = f"<div class='sub'>{sub}</div>" if sub else ""
    return f"<a class='card' href='?{qs}' target='_self'>{img}<div class='title'>{title}</div>{sub_html}</a>"

def render_row(title: str, items: list[str]):
    st.markdown(f"<div class='h1'>{title}</div><div class='strip'>{''.join(items)}</div>", unsafe_allow_html=True)

def render_two_rows(title: str, items: list[str]):
    st.markdown(f"<div class='h1'>{title}</div><div class='strip2'>{''.join(items)}</div>", unsafe_allow_html=True)

# ---------- Stage logic ----------
if not segment:
    # Stage 1
    items = [card_link(f"segment={s['key']}", s["label"], img_url=SEGMENT_HERO.get(s["key"], ""))
             for s in taxonomy["segments"]]
    render_row("Choose your drone category", items)

elif not series:
    # Stage 2
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    items = []
    for s in series_defs_for(segment):
        rnd_img = random_image_for_series(segment, s["key"])
        items.append(card_link(f"segment={segment}&series={s['key']}", s["label"], img_url=rnd_img))
    render_row(f"Choose a series ({seg_label})", items)

else:
    # Stage 3
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    ser_label = next(s["label"] for s in series_defs_for(segment) if s["key"] == series)

    if model:
        sel = df[df["model_key"] == model]
        if not sel.empty:
            row = sel.iloc[0]

            # --- Sidebar ---
            st.sidebar.markdown(f"**{seg_label} → {ser_label}**")
            st.sidebar.markdown(
                f"<a class='sidebar-back' href='?segment={segment}&series={series}' target='_self'>← Back to models</a>",
                unsafe_allow_html=True
            )
            st.sidebar.image(resolve_img(row.get("image_url", "")),
                             use_column_width=True, caption=row.get("marketing_name", ""))

            # Compliance badges
            eu_class = row.get("eu_class_marking", "—")
            uk_class = row.get("uk_class_marking", "—")
            st.sidebar.markdown(
                f"<div><span class='badge' style='background:#e3f2fd;color:#0d47a1;'>EU Class: {eu_class}</span>"
                f"<span class='badge' style='background:#fff3e0;color:#e65100;'>UK Class: {uk_class}</span></div>",
                unsafe_allow_html=True
            )

            opid = str(row.get("operator_id_required","")).lower()
            if opid == "yes":
                st.sidebar.markdown("<div class='badge chip-yes'>Operator ID Required</div>", unsafe_allow_html=True)
            elif opid == "no":
                st.sidebar.markdown("<div class='badge chip-no'>No Operator ID Required</div>", unsafe_allow_html=True)

            # Quick Facts
            st.sidebar.markdown("### 🧾 Quick Facts")
            st.sidebar.markdown(f"**Year Released:** {row.get('year_released','—')}")
            st.sidebar.markdown(f"**Segment:** {row.get('segment','—').capitalize()}")
            st.sidebar.markdown(f"**Series:** {row.get('series','—').capitalize()}")
            if row.get("spec_url"):
                st.sidebar.markdown(f"[📄 Official Specs Page]({row['spec_url']})")

            # --- Main Details ---
            st.markdown(f"<h2>{row['marketing_name']}</h2>", unsafe_allow_html=True)

            with st.expander("📸 Camera"):
                st.markdown(f"**Sensor:** {row.get('sensor','—')}")
                st.markdown(f"**Effective Megapixels:** {row.get('effective_mp','—')}")
                st.markdown(f"**Aperture:** {row.get('aperture','—')}")
                st.markdown(f"**Focal Length:** {row.get('focal_length_eq','—')}")
                st.markdown(f"**Video Resolutions:** {row.get('video_resolutions','—')}")
                st.markdown(f"**Log Profile:** {row.get('log_profile','—')}")

            with st.expander("📡 Transmission"):
                st.markdown(f"**System:** {row.get('transmission_system','—')}")
                st.markdown(f"**Max Range (CE):** {row.get('max_range_km','—')}")
                st.markdown(f"**Controllers:** {row.get('controller_compat','—')}")
                st.markdown(f"**Wind Resistance:** {row.get('wind_resistance','—')}")

            with st.expander("🔋 Battery & Flight"):
                st.markdown(f"**Battery Type:** {row.get('battery_type','—')}")
                st.markdown(f"**Capacity:** {row.get('battery_capacity_mah','—')}")
                st.markdown(f"**Flight Time:** {row.get('max_flight_time_min','—')} min")
                st.markdown(f"**Charge Power:** {row.get('charging_power_w','—')} W")

            with st.expander("📏 Dimensions"):
                st.markdown(f"**Folded:** {row.get('dim_folded','—')}")
                st.markdown(f"**Unfolded:** {row.get('dim_unfolded','—')}")
                st.markdown(f"**Diagonal:** {row.get('diagonal_length','—')}")

            with st.expander("🗒 Notes"):
                st.markdown(f"{row.get('notes','—')}")

    if not model:
        models = models_for(segment, series)
        items = []
        for _, r in models.iterrows():
            sub = " • ".join(
                [f"Class: {r.get('eu_class_marking','')}",
                 f"UK: {r.get('uk_class_marking','')}"]
            ).strip(" •")
            items.append(
                card_link(f"segment={segment}&series={series}&model={r['model_key']}",
                          r.get("marketing_name",""), sub=sub,
                          img_url=resolve_img(str(r.get("image_url",""))))
            )
        render_two_rows(f"Choose a drone ({seg_label} → {ser_label})", items)
