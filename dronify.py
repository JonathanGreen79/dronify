# dronify.py  (sequential horizontal strips)
import streamlit as st
import pandas as pd
import yaml
from pathlib import Path

st.set_page_config(page_title="Drone Picker — Sequential Strips", layout="wide")

DATASET_PATH = Path("dji_drones_v2.yaml")
TAXONOMY_PATH = Path("taxonomy.yaml")

# ---------- Loaders ----------
def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@st.cache_data
def load_data():
    dataset = load_yaml(DATASET_PATH)    # {"schema": {...}, "data": [ ... ]}
    df = pd.DataFrame(dataset["data"])
    taxonomy = load_yaml(TAXONOMY_PATH)  # {"segments": [ ... ]}
    if "eu_class_marking" not in df.columns:
        df["eu_class_marking"] = df.get("class_marking", "unknown")
    if "uk_class_marking" not in df.columns:
        df["uk_class_marking"] = df.get("class_marking", "unknown")
    if "image_url" not in df.columns:
        df["image_url"] = ""           # optional, for photos later
    return df, taxonomy

df, taxonomy = load_data()
if "segments" not in taxonomy:
    st.error("taxonomy.yaml missing 'segments'")
    st.stop()

# ---------- Styles ----------
st.markdown("""
<style>
/* One-row horizontal strip of cards */
.strip { display:flex; flex-wrap:nowrap; gap:12px; overflow-x:auto; padding:6px 2px; }
.card {
  flex:0 0 220px; height:200px;
  border:1px solid #E5E7EB; border-radius:14px; background:#fff;
  text-decoration:none !important; color:#111827 !important;
  display:block; padding:10px; transition:all .15s ease-in-out;
}
.card:hover { border-color:#D1D5DB; box-shadow:0 4px 16px rgba(0,0,0,.06); }
.card .img {
  width:100%; height:110px; border-radius:10px; background:#F3F4F6;
  display:flex; align-items:center; justify-content:center; font-size:.8rem; color:#6B7280; margin-bottom:8px;
}
.card .title { font-weight:600; font-size:.95rem; line-height:1.15; }
.card .sub { font-size:.78rem; color:#6B7280; margin-top:4px; }
.header { font-weight:700; font-size:1.05rem; margin:2px 0 10px 0; color:#374151; }
.summary { border:1px solid #E5E7EB; border-radius:12px; padding:12px; background:#FFF; }
.summary .lab { font-size:.78rem; color:#6B7280; margin-bottom:4px; }
.summary .val { font-size:1.05rem; font-weight:600; }
.back { font-size:.9rem; color:#2563EB; text-decoration:none; }
</style>
""", unsafe_allow_html=True)

# ---------- State & query params ----------
ss = st.session_state
ss.setdefault("segment", None)
ss.setdefault("series", None)
ss.setdefault("model_key", None)

def qp_get():
    try:    return dict(st.query_params)
    except: return {k: (v[0] if isinstance(v, list) and v else v)
                    for k,v in st.experimental_get_query_params().items()}

def qp_set(**kwargs):
    try:    st.query_params.update(kwargs)
    except: st.experimental_set_query_params(**kwargs)

def qp_clear():
    try:    st.query_params.clear()
    except: st.experimental_set_query_params()

# Read URL selections if present
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

def strip_link(href: str, title: str, sub: str = "", img_url: str = "") -> str:
    img_html = (f'<img src="{img_url}" class="img" style="object-fit:cover;width:100%;height:110px;border-radius:10px;" />'
                if img_url else '<div class="img">image</div>')
    return f'''
        <a class="card" href="{href}">
          {img_html}
          <div class="title">{title}</div>
          <div class="sub">{sub}</div>
        </a>
    '''

# ---------- Flow: sequential screens ----------
if ss.segment is None:
    # STEP 1 — Segments (single horizontal row)
    st.markdown('<div class="header">Step 1 • Select group</div>', unsafe_allow_html=True)
    items = []
    for seg in taxonomy["segments"]:
        items.append(strip_link(f"?segment={seg['key']}", seg["label"]))
    st.markdown('<div class="strip">' + "\n".join(items) + "</div>", unsafe_allow_html=True)

elif ss.series is None:
    # STEP 2 — Series for chosen segment (single horizontal row)
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == ss.segment)
    st.markdown(f'<a class="back" href="?">← Back</a>', unsafe_allow_html=True)
    st.markdown(f'<div class="header">Step 2 • {seg_label} — Select series</div>', unsafe_allow_html=True)
    sdefs = series_defs_for(ss.segment)
    items = []
    for s in sdefs:
        items.append(strip_link(f"?segment={ss.segment}&series={s['key']}", s["label"]))
    st.markdown('<div class="strip">' + "\n".join(items) + "</div>", unsafe_allow_html=True)

else:
    # STEP 3 — Models for chosen series (single horizontal row)
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == ss.segment)
    ser_label = next(s["label"] for s in series_defs_for(ss.segment) if s["key"] == ss.series)
    st.markdown(f'<a class="back" href="?segment={ss.segment}">← Back</a>', unsafe_allow_html=True)
    st.markdown(f'<div class="header">Step 3 • {seg_label} → {ser_label} — Select model</div>', unsafe_allow_html=True)

    models = models_for(ss.segment, ss.series)
    if models.empty:
        st.info("No models in this series yet.")
    else:
        cards = []
        for _, row in models.iterrows():
            title = row["marketing_name"]
            subbits = []
            if isinstance(row.get("class_marking"), str):
                subbits.append(f"Class: {row.get('class_marking','unknown')}")
            if isinstance(row.get("weight_band"), str):
                subbits.append(f"Weight: {row.get('weight_band','?')}")
            sub = " • ".join(subbits)
            cards.append(strip_link(f"?segment={ss.segment}&series={ss.series}&model={row['model_key']}",
                                    title, sub, row.get("image_url","")))
        st.markdown('<div class="strip">' + "\n".join(cards) + "</div>", unsafe_allow_html=True)

    # Summary boxes appear after a model is chosen
    if ss.model_key:
        sel = df[df["model_key"] == ss.model_key].iloc[0]
        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="summary"><div class="lab">MTOW (g)</div><div class="val">{sel.get("mtom_g_nominal","—")}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="summary"><div class="lab">Name</div><div class="val">{sel.get("marketing_name","—")}</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="summary"><div class="lab">Model Key</div><div class="val">{sel.get("model_key","—")}</div></div>', unsafe_allow_html=True)
        with c4:
            eu = sel.get("eu_class_marking", sel.get("class_marking","unknown"))
            uk = sel.get("uk_class_marking", sel.get("class_marking","unknown"))
            st.markdown(f'<div class="summary"><div class="lab">EU / UK Class</div><div class="val">{eu} / {uk}</div></div>', unsafe_allow_html=True)
