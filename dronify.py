# dronify.py — horizontal clickable cards (same tab), uniform images,
# Stage2 random per-series image, Stage3 two-row grid,
# and natural/human sorting by series → marketing_name (Pandas 2.x safe).

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
    for col in ("image_url", "segment", "series", "class_marking", "weight_band"):
        if col not in df.columns:
            df[col] = ""
    return df, taxonomy

df, taxonomy = load_data()

# ---------- Query-param state (pure in-tab updates) ----------
def get_qp():
    try:
        return dict(st.query_params)  # Streamlit ≥1.32
    except Exception:
        # legacy fallback
        return {k: (v[0] if isinstance(v, list) else v)
                for k, v in st.experimental_get_query_params().items()}

qp = get_qp()
segment = qp.get("segment")   # e.g. 'consumer' | 'pro' | 'enterprise' | None
series  = qp.get("series")    # series key or None
model   = qp.get("model")     # model_key or None

# ---------- Image resolver (serve repo images via GitHub Raw) ----------
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

def natural_key(text: str):
    """Split text into text/number chunks for human/natural sorting."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', str(text))]

def models_for(segment_key: str, series_key: str):
    """
    Return models in segment+series, sorted *naturally* by:
      1) series
      2) marketing_name
    (Uses helper columns so Pandas 2.x 'key=' is applied once per sort.)
    """
    subset = df[(df["segment"] == segment_key) & (df["series"] == series_key)].copy()

    # helper columns as strings
    subset["series_sort"] = subset["series"].astype(str)
    subset["name_sort"]   = subset["marketing_name"].astype(str)

    # sort with a single key function applied to the column being sorted
    subset = subset.sort_values(
        by=["series_sort", "name_sort"],
        key=lambda col: col.map(natural_key),
        ignore_index=True
    )

    # drop helpers (optional)
    subset = subset.drop(columns=["series_sort", "name_sort"])
    return subset

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
</style>
""", unsafe_allow_html=True)

# ---------- Card (same tab) ----------
# We update URL query params *in place* using Streamlit's postMessage API.
def card_link(qs: str, title: str, sub: str = "", img_url: str = "") -> str:
    """
    qs example: 'segment=consumer' or 'segment=consumer&series=mini'
    """
    img = f"<div class='img'><img src='{img_url}' alt=''/></div>" if img_url else "<div class='img'></div>"
    js = (
        "window.parent.postMessage("
        "{type: 'streamlit:setQueryParams', query: '" + qs.replace("'", "%27") + "'}"
        ", '*'); return false;"
    )
    sub_html = f"<div class='sub'>{sub}</div>" if sub else ""
    return f"<a class='card' href='#' onclick=\"{js}\">{img}<div class='title'>{title}</div>{sub_html}</a>"

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
    # Stage 3 — choose model (two rows)
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    ser_label = next(s["label"] for s in series_defs_for(segment) if s["key"] == series)

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

    # Summary after a model is picked
    if model:
        sel = df[df["model_key"] == model]
        if not sel.empty:
            row = sel.iloc[0]
            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("MTOW (g)", row.get("mtom_g_nominal", "—"))
            with c2: st.metric("Name", row.get("marketing_name", "—"))
            with c3: st.metric("Model Key", row.get("model_key", "—"))
            with c4:
                eu = row.get("eu_class_marking", row.get("class_marking", "unknown"))
                uk = row.get("uk_class_marking", row.get("class_marking", "unknown"))
                st.metric("EU / UK Class", f"{eu} / {uk}")
