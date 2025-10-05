# dronify.py  (or streamlit_app.py)
import streamlit as st
import pandas as pd
import yaml
from pathlib import Path

st.set_page_config(page_title="Drone Picker — 3-Row Cascade", layout="wide")

# ---------- File paths ----------
DATASET_PATH = Path("dji_drones_v2.yaml")
TAXONOMY_PATH = Path("taxonomy.yaml")

# ---------- Load YAMLs ----------
def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@st.cache_data
def load_data():
    dataset = load_yaml(DATASET_PATH)
    df = pd.DataFrame(dataset["data"])
    taxonomy = load_yaml(TAXONOMY_PATH)

    if "eu_class_marking" not in df.columns:
        df["eu_class_marking"] = df.get("class_marking", "unknown")
    if "uk_class_marking" not in df.columns:
        df["uk_class_marking"] = df.get("class_marking", "unknown")
    return df, taxonomy

df, taxonomy = load_data()

if "segments" not in taxonomy:
    st.error("Taxonomy file missing 'segments'.")
    st.stop()

# ---------- Styles ----------
st.markdown("""
<style>
.stButton > button {
  width: 100%;
  text-align: left;
  border: 1px solid #E5E7EB;
  background: #ffffff;
  border-radius: 16px;
  padding: 14px 16px;
  font-size: 1.05rem;
  line-height: 1.2;
  transition: all .15s ease-in-out;
  margin-bottom: 10px;
}
.stButton > button:hover {
  border-color: #D1D5DB;
  box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}
.card-selected > button {
  border-color: #10B981 !important;
  box-shadow: 0 0 0 2px rgba(16,185,129,.25) !important;
}
.card-sub {
  display:block;
  font-size: .78rem;
  color: #6B7280;
  margin-top: 4px;
}
.row-title {
  font-weight:600;
  margin: 8px 0 6px 0;
  font-size:0.95rem;
  color:#374151;
}
.summary-box {
  border:1px solid #E5E7EB;
  border-radius:14px;
  padding:14px;
  background:#ffffff;
}
.summary-label {
  font-size:.8rem;
  color:#6B7280;
  margin-bottom:6px;
}
.summary-value {
  font-size:1.1rem;
  font-weight:600;
}
</style>
""", unsafe_allow_html=True)

# ---------- State ----------
if "segment" not in st.session_state: st.session_state.segment = None
if "series" not in st.session_state: st.session_state.series = None
if "model_key" not in st.session_state: st.session_state.model_key = None

# ---------- Helpers ----------
def clickable_card(label: str, sub: str = "", key: str = "", selected: bool = False) -> bool:
    css = "card-selected" if selected else ""
    html = f"""
    <div class="{css}">
        <button>{label}<span class="card-sub">{sub}</span></button>
    </div>
    """
    return st.button(label, key=key, use_container_width=True)

def nonempty_series_for(segment_key: str):
    seg = next(seg for seg in taxonomy["segments"] if seg["key"] == segment_key)
    keys = [s["key"] for s in seg["series"]]
    return [k for k in keys if not df[(df["segment"] == segment_key) & (df["series"] == k)].empty]

def models_for(segment_key: str, series_key: str) -> pd.DataFrame:
    return df[(df["segment"] == segment_key) & (df["series"] == series_key)]

# ---------- Row 1: Segments ----------
st.markdown('<div class="row-title">Step 1 · Select segment</div>', unsafe_allow_html=True)
cols = st.columns(len(taxonomy["segments"]))
for i, seg in enumerate(taxonomy["segments"]):
    with cols[i]:
        selected = (st.session_state.segment == seg["key"])
        if st.button(seg["label"], key=f"segment_{seg['key']}", use_container_width=True):
            st.session_state.segment = seg["key"]
            st.session_state.series = None
            st.session_state.model_key = None

st.divider()

# ---------- Row 2: Series ----------
if st.session_state.segment:
    st.markdown('<div class="row-title">Step 2 · Select series</div>', unsafe_allow_html=True)
    available_series_keys = nonempty_series_for(st.session_state.segment)
    series_defs = [
        s for s in next(seg for seg in taxonomy["segments"] if seg["key"] == st.session_state.segment)["series"]
        if s["key"] in available_series_keys
    ]
    cols = st.columns(max(1, len(series_defs)))
    for i, s in enumerate(series_defs):
        with cols[i]:
            selected = (st.session_state.series == s["key"])
            if st.button(s["label"], key=f"series_{s['key']}", use_container_width=True):
                st.session_state.series = s["key"]
                st.session_state.model_key = None

    st.divider()

# ---------- Row 3: Models ----------
if st.session_state.segment and st.session_state.series:
    st.markdown('<div class="row-title">Step 3 · Select model</div>', unsafe_allow_html=True)
    models = models_for(st.session_state.segment, st.session_state.series)
    if models.empty:
        st.info("No models in this series yet.")
    else:
        cols = st.columns(3)
        for i, (_, row) in enumerate(models.sort_values("marketing_name").iterrows()):
            with cols[i % 3]:
                subtitle_bits = []
                if isinstance(row.get("class_marking"), str):
                    subtitle_bits.append(f"Class: {row.get('class_marking', 'unknown')}")
                if isinstance(row.get("weight_band"), str):
                    subtitle_bits.append(f"Weight: {row.get('weight_band', '?')}")
                subline = " • ".join(subtitle_bits)
                if st.button(f"{row['marketing_name']}\n{subline}", key=f"model_{row['model_key']}", use_container_width=True):
                    st.session_state.model_key = row["model_key"]

    st.divider()

# ---------- Summary Boxes ----------
if st.session_state.model_key:
    sel = df[df["model_key"] == st.session_state.model_key].iloc[0]
    st.subheader("Selected model")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            '<div class="summary-box"><div class="summary-label">MTOW (g)</div>'
            f'<div class="summary-value">{sel.get("mtom_g_nominal", "—")}</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            '<div class="summary-box"><div class="summary-label">Name</div>'
            f'<div class="summary-value">{sel.get("marketing_name", "—")}</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            '<div class="summary-box"><div class="summary-label">Model Key</div>'
            f'<div class="summary-value">{sel.get("model_key", "—")}</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        eu = sel.get("eu_class_marking", sel.get("class_marking", "unknown"))
        uk = sel.get("uk_class_marking", sel.get("class_marking", "unknown"))
        st.markdown(
            '<div class="summary-box"><div class="summary-label">EU / UK Class</div>'
            f'<div class="summary-value">{eu} / {uk}</div></div>',
            unsafe_allow_html=True,
        )

st.caption("MVP: Full-width clickable cards for Segment → Series → Model, plus summary boxes below.")
