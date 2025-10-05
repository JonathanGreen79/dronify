# dronify.py — clickable cards (same tab via anchors), uniform images,
# Stage2 random per-series image, Stage3 two-row grid with *sidebar detail view*,
# natural/human sorting by series → marketing_name (Pandas 2.x safe via padded-string keys)

import re
import random
import streamlit as st
import pandas as pd
import yaml
from pathlib import Path

st.set_page_config(page_title="Dronify", layout="wide")

DATASET_PATH = Path("dji_drones_v3.yaml")
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
    # Ensure columns exist so UI never breaks
    for col in ("image_url", "segment", "series", "class_marking", "weight_band",
                "marketing_name", "mtom_g_nominal", "eu_class_marking",
                "uk_class_marking", "remote_id_builtin", "year_released", "notes"):
        if col not in df.columns:
            df[col] = ""
    return df, taxonomy

df, taxonomy = load_data()

# ---------- Query params ----------
def get_qp():
    try:
        return dict(st.query_params)  # Streamlit ≥1.32
    except Exception:
        return {k: (v[0] if isinstance(v, list) else v)
                for k, v in st.experimental_get_query_params().items()}

qp = get_qp()
segment = qp.get("segment")
series  = qp.get("series")
model   = qp.get("model")

# ---------- Image resolver (repo images via GitHub Raw) ----------
RAW_BASE = "https://raw.githubusercontent.com/JonathanGreen79/dronify/main/images/"

def resolve_img(url: str) -> str:
    if not url:
        return ""
    if url.startswith("images/"):
        return RAW_BASE + url.split("/", 1)[1]
    return url

# Stage 1 hero images
SEGMENT_HERO = {
    "consumer": resolve_img("images/consumer.jpg"),
    "pro":       resolve_img("images/professional.jpg"),
    "enterprise":resolve_img("images/enterprise.jpg"),
}

# ---------- Helpers ----------
def series_defs_for(segment_key: str):
    seg = next(s for s in taxonomy["segments"] if s["key"] == segment_key)
    # only include series that actually have models
    return [s for s in seg["series"]
            if not df[(df["segment"] == segment_key) & (df["series"] == s["key"])].empty]

def pad_digits_for_natural(series: pd.Series, width: int = 6) -> pd.Series:
    """
    Convert strings to lowercase and pad every number with leading zeros.
    'Mini 2 SE' -> 'mini 000002 se'
    This yields a string that sorts naturally with standard lexicographic sort.
    """
    s = series.astype(str).str.lower()
    return s.str.replace(r"\d+", lambda m: f"{int(m.group(0)):0{width}d}", regex=True)

def models_for(segment_key: str, series_key: str):
    """
    Return models in segment+series, sorted *naturally* by:
      1) series (harmless inside single series)
      2) marketing_name
    Uses padded-string helpers (no key=) to be Pandas 2.x safe.
    """
    subset = df[(df["segment"] == segment_key) & (df["series"] == series_key)].copy()
    subset["series_key"] = pad_digits_for_natural(subset["series"])
    subset["name_key"]   = pad_digits_for_natural(subset["marketing_name"])
    subset = subset.sort_values(
        by=["series_key", "name_key", "marketing_name"],
        kind="stable",
        ignore_index=True
    )
    return subset.drop(columns=["series_key", "name_key"])

def random_image_for_series(segment_key: str, series_key: str) -> str:
    """Pick a random image from models in the given segment+series."""
    subset = df[
        (df["segment"] == segment_key)
        & (df["series"] == series_key)
        & (df["image_url"].astype(str) != "")
    ]
    if subset.empty:
        return SEGMENT_HERO.get(segment_key, "")
    return resolve_img(str(subset.sample(1, random_state=None)["image_url"].iloc[0]))

# ---------- Styles ----------
st.markdown("""
<style>
/* Headings spacing */
.block-container { padding-top: 1.1rem; }

/* shared card look */
.card {
  width: 260px;
  height: 240px;
  border: 1px solid #E5E7EB;
  border-radius: 14px;
  background: #fff;
  text-decoration: none !important;
  color: #111827 !important;
  display: block;
  padding: 12px;
  transition: box-shadow .15s ease, transform .15s ease, border-color .15s ease;
  cursor: pointer;
}
.card:hover { border-color: #D1D5DB; box-shadow: 0 6px 18px rgba(0,0,0,.08); transform: translateY(-2px); }

.img {
  width: 100%;
  height: 150px;                 /* uniform image size */
  border-radius: 10px;
  background: #F3F4F6;
  overflow: hidden;
  display: flex; align-items: center; justify-content: center;
}
.img > img { width: 100%; height: 100%; object-fit: cover; }  /* same-size look */

.title { margin-top: 10px; text-align: center; font-weight: 700; font-size: 0.98rem; }
.sub    { margin-top: 4px;  text-align: center; font-size: .8rem; color: #6B7280; }

/* horizontal strip (stage 1 & 2) */
.strip {
  display: flex; flex-wrap: nowrap; gap: 14px; overflow-x: auto; padding: 8px 2px; margin: 0;
}

/* stage 3: two-row horizontal grid */
.strip2 {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 260px;     /* card width */
  grid-template-rows: repeat(2, 1fr);
  gap: 14px;
  overflow-x: auto;
  padding: 8px 2px; margin: 0;
}

/* headings */
.h1 { font-weight: 800; font-size: 1.2rem; color: #1F2937; margin: 0 0 12px 0; }

/* sidebar styling */
.sidebar-card img {
  border-radius: 10px;
}
.sidebar-title {
  font-weight: 800; font-size: 1.05rem; margin-top: .6rem;
}
.sidebar-kv {
  margin: .15rem 0;
  color: #374151;
  font-size: 0.93rem;
}
.sidebar-muted {
  color: #6B7280; font-size: 0.85rem;
}
.sidebar-back {
  margin-top: 0.5rem;
  display: inline-block;
  text-decoration: none;
  color: #2563EB;
  font-weight: 600;
}
.sidebar-back:hover { text-decoration: underline; }
</style>
""", unsafe_allow_html=True)

# ---------- Card (anchor in same tab) ----------
def card_link(qs: str, title: str, sub: str = "", img_url: str = "") -> str:
    """
    qs example: 'segment=consumer' or 'segment=consumer&series=mini'
    Plain anchor with target="_self" stays in same tab.
    """
    img = f"<div class='img'><img src='{img_url}' alt=''/></div>" if img_url else "<div class='img'></div>"
    sub_html = f"<div class='sub'>{sub}</div>" if sub else ""
    return (
        f"<a class='card' href='?{qs}' target='_self' rel='noopener'>"
        f"{img}<div class='title'>{title}</div>{sub_html}</a>"
    )

def render_row(title: str, items: list[str]):
    st.markdown(f"<div class='h1'>{title}</div><div class='strip'>{''.join(items)}</div>", unsafe_allow_html=True)

def render_two_rows(title: str, items: list[str]):
    st.markdown(f"<div class='h1'>{title}</div><div class='strip2'>{''.join(items)}</div>", unsafe_allow_html=True)

# ---------- Screens ----------
if not segment:
    # Stage 1 — choose group (horizontal)
    items = []
    for seg in taxonomy["segments"]:
        img = SEGMENT_HERO.get(seg["key"], "")
        items.append(card_link(f"segment={seg['key']}", seg["label"], img_url=img))
    render_row("Choose your drone category", items)

elif not series:
    # Stage 2 — choose series (horizontal, random image from that series only)
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    items = []
    for s in series_defs_for(segment):
        rnd_img = random_image_for_series(segment, s["key"])
        items.append(card_link(f"segment={segment}&series={s['key']}",
                               f"{s['label']}", img_url=rnd_img))
    render_row(f"Choose a series ({seg_label})", items)

else:
    # Stage 3
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    ser_label = next(s["label"] for s in series_defs_for(segment) if s["key"] == series)

    # If a model is selected, show ONLY a sidebar with details; keep body blank.
    if model:
        sel = df[df["model_key"] == model]
        if not sel.empty:
            row = sel.iloc[0]

            # Sidebar content
            st.sidebar.markdown(f"**{seg_label} → {ser_label}**")
            # Back link to series grid
            back_qs = f"segment={segment}&series={series}"
            st.sidebar.markdown(f"<a class='sidebar-back' href='?{back_qs}' target='_self'>← Back to models</a>", unsafe_allow_html=True)

            # Thumbnail
            st.sidebar.image(resolve_img(row.get("image_url", "")),
                             use_column_width=True, caption=row.get("marketing_name", ""))

            # Key specs
            st.sidebar.markdown("<div class='sidebar-title'>Key specs</div>", unsafe_allow_html=True)
            st.sidebar.markdown(
                f"""
                <div class='sidebar-kv'><b>Model</b>: {row.get('marketing_name', '—')}</div>
                <div class='sidebar-kv'><b>Model key</b>: {row.get('model_key', '—')}</div>
                <div class='sidebar-kv'><b>MTOW</b>: {row.get('mtom_g_nominal', '—')} g</div>
                <div class='sidebar-kv'><b>Weight band</b>: {row.get('weight_band', '—')}</div>
                <div class='sidebar-kv'><b>EU / UK class</b>: {row.get('eu_class_marking', row.get('class_marking', 'unknown'))} / {row.get('uk_class_marking', row.get('class_marking', 'unknown'))}</div>
                <div class='sidebar-kv'><b>Remote ID</b>: {row.get('remote_id_builtin', 'unknown')}</div>
                <div class='sidebar-kv'><b>Released</b>: {row.get('year_released', '—')}</div>
                """,
                unsafe_allow_html=True
            )

            # Notes (optional)
            notes = str(row.get("notes", "")).strip()
            if notes:
                st.sidebar.markdown("<div class='sidebar-title'>Notes</div>", unsafe_allow_html=True)
                st.sidebar.markdown(f"<div class='sidebar-muted'>{notes}</div>", unsafe_allow_html=True)

            # Keep main body intentionally blank for now
            st.write("")
            st.write("")
        else:
            # If invalid model key, just fall back to grid
            model = None

    # If no model selected, show the model grid (two rows)
    if not model:
        models = models_for(segment, series)
        items = []
        for _, r in models.iterrows():
            subbits = []
            cm = r.get("class_marking", "unknown")
            if isinstance(cm, str) and cm:
                subbits.append(f"Class: {cm}")
            wb = r.get("weight_band", "")
            if isinstance(wb, str) and wb:
                subbits.append(f"Weight: {wb}")
            sub = " • ".join(subbits)
            items.append(
                card_link(
                    f"segment={segment}&series={series}&model={r['model_key']}",
                    r.get("marketing_name", ""),
                    sub=sub,
                    img_url=resolve_img(str(r.get("image_url", "")))
                )
            )
        render_two_rows(f"Choose a drone ({seg_label} → {ser_label})", items)

