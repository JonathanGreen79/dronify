import streamlit as st
import pandas as pd
import yaml
from pathlib import Path
from math import ceil

st.set_page_config(page_title="Drone Picker — L/R + Single Row", layout="wide")

DATASET_PATH = Path("dji_drones_v2.yaml")
TAXONOMY_PATH = Path("taxonomy.yaml")

# ---------- Loaders ----------
def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@st.cache_data
def load_data():
    dataset = load_yaml(DATASET_PATH)        # {"schema": {...}, "data": [ ... ]}
    df = pd.DataFrame(dataset["data"])
    taxonomy = load_yaml(TAXONOMY_PATH)      # {"segments": [ ... ]}
    if "eu_class_marking" not in df.columns:
        df["eu_class_marking"] = df.get("class_marking", "unknown")
    if "uk_class_marking" not in df.columns:
        df["uk_class_marking"] = df.get("class_marking", "unknown")
    return df, taxonomy

df, taxonomy = load_data()
if "segments" not in taxonomy:
    st.error("taxonomy.yaml missing 'segments'")
    st.stop()

# ---------- Styles ----------
st.markdown("""
<style>
/* make buttons look like clean cards */
.stButton > button {
  width: 100%;
  text-align: center;
  border: 1px solid #E5E7EB;
  background: #ffffff;
  border-radius: 14px;
  padding: 10px 12px;
  font-size: 0.95rem;
  line-height: 1.2;
  transition: all .15s ease-in-out;
  margin-bottom: 8px;
}
.stButton > button:hover { border-color:#D1D5DB; box-shadow:0 4px 16px rgba(0,0,0,0.06); }

.row-title { font-weight:600; margin: 4px 0 8px 0; font-size:.92rem; color:#374151; }

/* model pills row (single horizontal row) */
.model-row { display: flex; gap: 8px; overflow-x: auto; padding: 6px 2px; }
.model-row .stButton>button {
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 0.9rem;
  white-space: nowrap;
}

/* summary boxes */
.summary { border:1px solid #E5E7EB; border-radius:12px; padding:12px; background:#FFF; }
.summary .lab { font-size:.78rem; color:#6B7280; margin-bottom:4px; }
.summary .val { font-size:1.05rem; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ---------- State ----------
ss = st.session_state
ss.setdefault("segment", None)
ss.setdefault("series", None)
ss.setdefault("model_key", None)

# ---------- Helpers ----------
def series_defs_for(segment_key: str):
    seg = next(seg for seg in taxonomy["segments"] if seg["key"] == segment_key)
    # keep only series that have at least one model
    defs = []
    for s in seg["series"]:
        if not df[(df["segment"] == segment_key) & (df["series"] == s["key"])].empty:
            defs.append(s)
    return defs

def models_for(segment_key: str, series_key: str) -> pd.DataFrame:
    return df[(df["segment"] == segment_key) & (df["series"] == series_key)].sort_values("marketing_name")

# ---------- Top row: Step 1 (left) & Step 2 (right as two columns) ----------
left, right = st.columns(2, gap="large")

with left:
    st.markdown('<div class="row-title">Step 1 • Select group</div>', unsafe_allow_html=True)
    for seg in taxonomy["segments"]:
        if st.button(seg["label"], key=f"segment_{seg['key']}", use_container_width=True):
            ss.segment = seg["key"]
            ss.series = None
            ss.model_key = None

with right:
    st.markdown('<div class="row-title">Step 2 • Select series</div>', unsafe_allow_html=True)
    if ss.segment:
        sdefs = series_defs_for(ss.segment)
        # lay them out in 2 vertical columns
        c1, c2 = st.columns(2)
        mid = ceil(len(sdefs) / 2)
        with c1:
            for s in sdefs[:mid]:
                if st.button(s["label"], key=f"series_{s['key']}", use_container_width=True):
                    ss.series = s["key"]
                    ss.model_key = None
        with c2:
            for s in sdefs[mid:]:
                if st.button(s["label"], key=f"series_{s['key']}", use_container_width=True):
                    ss.series = s["key"]
                    ss.model_key = None
    else:
        st.info("Pick a group on the left.")

st.markdown("---")

# ---------- Step 3: one-row model pills ----------
st.markdown('<div class="row-title">Step 3 • Select model</div>', unsafe_allow_html=True)
if ss.segment and ss.series:
    models = models_for(ss.segment, ss.series)
    if models.empty:
        st.info("No models in this series yet.")
    else:
        # container that becomes a single horizontal row
        model_row = st.container()
        model_row.markdown('<div class="model-row">', unsafe_allow_html=True)
        # use a tiny grid of buttons; CSS above makes them inline and scrollable horizontally
        # put all buttons in the same container so they render side-by-side
        for _, row in models.iterrows():
            label_bits = [row["marketing_name"]]
            sub = []
            if isinstance(row.get("class_marking"), str):
                sub.append(f"Class: {row.get('class_marking','unknown')}")
            if isinstance(row.get("weight_band"), str):
                sub.append(f"Weight: {row.get('weight_band','?')}")
            label = f"{label_bits[0]}  ·  {' • '.join(sub)}" if sub else label_bits[0]
            if st.button(label, key=f"model_{row['model_key']}"):
                ss.model_key = row["model_key"]
        model_row.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("Choose a group and series to see models.")

st.markdown("---")

# ---------- Summary ----------
if ss.model_key:
    sel = df[df["model_key"] == ss.model_key].iloc[0]
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

st.caption("Step 1 (left) · Step 2 (right with two columns) · Models as one-row pills. No more raw HTML; pure Streamlit buttons.")
