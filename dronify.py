# dronify.py — sequential single-row UI (clean titles, no inner scrollbars)
import streamlit as st
import pandas as pd
import yaml
from pathlib import Path

st.set_page_config(page_title="Drone Picker", layout="wide")

DATASET_PATH = Path("dji_drones_v2.yaml")
TAXONOMY_PATH = Path("taxonomy.yaml")

# ---------- Loaders ----------
def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@st.cache_data
def load_data():
    dataset = load_yaml(DATASET_PATH)
    df = pd.DataFrame(dataset["data"])
    taxonomy = load_yaml(TAXONOMY_PATH)
    # sane fallbacks
    if "eu_class_marking" not in df.columns:
        df["eu_class_marking"] = df.get("class_marking", "unknown")
    if "uk_class_marking" not in df.columns:
        df["uk_class_marking"] = df.get("class_marking", "unknown")
    if "image_url" not in df.columns:
        df["image_url"] = ""
    return df, taxonomy

df, taxonomy = load_data()
if "segments" not in taxonomy:
    st.error("taxonomy.yaml missing 'segments'")
    st.stop()

# ---------- State via query params (so card clicks just use links) ----------
ss = st.session_state
ss.setdefault("segment", None)
ss.setdefault("series", None)
ss.setdefault("model_key", None)

def qp_get():
    try:
        return dict(st.query_params)
    except Exception:
        return {k: (v[0] if isinstance(v, list) and v else v)
                for k, v in st.experimental_get_query_params().items()}

qp = qp_get()
if "segment" in qp and qp["segment"] != ss.segment:
    ss.segment, ss.series, ss.model_key = qp["segment"], None, None
if "series" in qp and qp["series"] != ss.series:
    ss.series, ss.model_key = qp["series"], None
if "model" in qp and qp["model"] != ss.model_key:
    ss.model_key = qp["model"]

# ---------- Helpers ----------
def series_defs_for(segment_key: str):
    seg = next(s for s in taxonomy["segments"] if s["key"] == segment_key)
    return [s for s in seg["series"]
            if not df[(df["segment"] == segment_key) & (df["series"] == s["key"])].empty]

def models_for(segment_key: str, series_key: str):
    return df[(df["segment"] == segment_key) & (df["series"] == series_key)].sort_values("marketing_name")

# ---------- Shared CSS ----------
CSS = """
<style>
.strip{display:flex;flex-wrap:nowrap;gap:12px;overflow-x:auto;padding:6px 2px;margin:0}
.card{flex:0 0 240px;height:220px;border:1px solid #E5E7EB;border-radius:14px;background:#fff;
      text-decoration:none;color:#111827;display:block;padding:10px;transition:all .15s ease-in-out}
.card:hover{border-color:#D1D5DB;box-shadow:0 4px 16px rgba(0,0,0,.06)}
.img{width:100%;height:130px;border-radius:10px;background:#F3F4F6;display:flex;align-items:center;
     justify-content:center;font-size:.8rem;color:#6B7280;margin-bottom:8px;overflow:hidden}
.title{font-weight:600;font-size:.95rem;line-height:1.15}
.sub{font-size:.78rem;color:#6B7280;margin-top:4px}
.h1{font-weight:700;font-size:1.05rem;margin:0 0 10px 0;color:#374151}
.summary{border:1px solid #E5E7EB;border-radius:12px;padding:12px;background:#fff}
.summary .lab{font-size:.78rem;color:#6B7280;margin-bottom:4px}
.summary .val{font-size:1.05rem;font-weight:600}
</style>
"""

from streamlit.components.v1 import html as html_component

def card_html(href: str, title: str, sub: str = "", img_url: str = "") -> str:
    if img_url:
        img = f"<img src='{img_url}' class='img' style='object-fit:cover'/>"
    else:
        img = "<div class='img'>image</div>"
    return f"<a class='card' href='{href}' target='_self'>{img}<div class='title'>{title}</div><div class='sub'>{sub}</div></a>"

def render_strip(title: str, cards: list[str], height: int = 280):
    # Use components.html so Streamlit doesn’t try to syntax-highlight it as code.
    html_component(
        f"{CSS}<div class='h1'>{title}</div><div class='strip'>{''.join(cards)}</div>",
        height=height, scrolling=False  # no inner scrollbar
    )

# ---------- SCREENS ----------
if ss.segment is None:
    # Screen 1 — groups
    cards = [card_html(f"?segment={seg['key']}", seg["label"]) for seg in taxonomy["segments"]]
    render_strip("Choose your group", cards, height=280)

elif ss.series is None:
    # Screen 2 — series (no Back link per your request)
    sdefs = series_defs_for(ss.segment)
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == ss.segment)
    cards = [card_html(f"?segment={ss.segment}&series={s['key']}", s["label"]) for s in sdefs]
    render_strip(f"Choose a series ({seg_label})", cards, height=280)

else:
    # Screen 3 — models (one row)
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == ss.segment)
    ser_label = next(s["label"] for s in series_defs_for(ss.segment) if s["key"] == ss.series)

    models = models_for(ss.segment, ss.series)
    if models.empty:
        st.info("No models in this series yet.")
    else:
        cards = []
        for _, row in models.iterrows():
            sub = " • ".join(
                [f"Class: {row.get('class_marking','unknown')}",
                 f"Weight: {row.get('weight_band','?')}"]
                if isinstance(row.get("weight_band"), str) else
                [f"Class: {row.get('class_marking','unknown')}"]
            )
            cards.append(card_html(
                f"?segment={ss.segment}&series={ss.series}&model={row['model_key']}",
                row["marketing_name"], sub=sub, img_url=row.get("image_url","")
            ))
        render_strip(f"Choose a drone ({seg_label} → {ser_label})", cards, height=290)

    # Summary shows only after a model is clicked
    if ss.model_key:
        sel = df[df["model_key"] == ss.model_key].iloc[0]
        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f"<div class='summary'><div class='lab'>MTOW (g)</div><div class='val'>{sel.get('mtom_g_nominal','—')}</div></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='summary'><div class='lab'>Name</div><div class='val'>{sel.get('marketing_name','—')}</div></div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='summary'><div class='lab'>Model Key</div><div class='val'>{sel.get('model_key','—')}</div></div>", unsafe_allow_html=True)
        with c4:
            eu = sel.get("eu_class_marking", sel.get("class_marking","unknown"))
            uk = sel.get("uk_class_marking", sel.get("class_marking","unknown"))
            st.markdown(f"<div class='summary'><div class='lab'>EU / UK Class</div><div class='val'>{eu} / {uk}</div></div>", unsafe_allow_html=True)
