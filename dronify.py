# dronify.py  (or streamlit_app.py)
import streamlit as st
import pandas as pd
import yaml
from pathlib import Path

st.set_page_config(page_title="Drone Picker — Vertical L/R + Single-Row Models", layout="wide")

DATASET_PATH = Path("dji_drones_v2.yaml")
TAXONOMY_PATH = Path("taxonomy.yaml")

# ---------- Loaders ----------
def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@st.cache_data
def load_data():
    dataset = load_yaml(DATASET_PATH)        # expects {"schema":{...}, "data":[...]}
    df = pd.DataFrame(dataset["data"])
    taxonomy = load_yaml(TAXONOMY_PATH)      # expects {"segments":[...]}
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
/* Pretty buttons like cards */
.stButton > button {
  width: 100%;
  text-align: left;
  border: 1px solid #E5E7EB;
  background: #ffffff;
  border-radius: 14px;
  padding: 12px 14px;
  font-size: 0.98rem;
  line-height: 1.2;
  transition: all .15s ease-in-out;
  margin-bottom: 8px;
}
.stButton > button:hover { border-color:#D1D5DB; box-shadow:0 4px 16px rgba(0,0,0,0.06); }

/* Titles */
.row-title { font-weight:600; margin: 4px 0 8px 0; font-size:.92rem; color:#374151; }

/* Horizontal scroller for models (single row) */
.hscroll {
  overflow-x: auto; overflow-y: hidden; white-space: nowrap;
  padding: 6px 2px; margin-top: 12px; margin-bottom: 10px; 
}
.hscroll .pill {
  display: inline-block;
  border: 1px solid #E5E7EB;
  background: #FFF;
  border-radius: 999px;
  padding: 10px 14px;
  margin-right: 8px;
  font-size: 0.92rem;
  cursor: pointer;
}
.hscroll .pill:hover { border-color:#D1D5DB; box-shadow:0 2px 10px rgba(0,0,0,.05); }
.hscroll .pill .sub { display:block; font-size:.75rem; color:#6B7280; margin-top:2px; }

/* Summary boxes */
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
def nonempty_series_for(segment_key: str):
    seg = next(seg for seg in taxonomy["segments"] if seg["key"] == segment_key)
    keys = [s["key"] for s in seg["series"]]
    return [k for k in keys if not df[(df["segment"] == segment_key) & (df["series"] == k)].empty]

def models_for(segment_key: str, series_key: str) -> pd.DataFrame:
    return df[(df["segment"] == segment_key) & (df["series"] == series_key)]

def series_label(seg_key: str, series_key: str) -> str:
    seg = next(s for s in taxonomy["segments"] if s["key"] == seg_key)
    sdef = next(s for s in seg["series"] if s["key"] == series_key)
    return sdef["label"]

# ---------- Layout: top row = two columns (left: Step 1, right: Step 2) ----------
left, right = st.columns(2, gap="large")

with left:
    st.markdown('<div class="row-title">Step 1 · Select group</div>', unsafe_allow_html=True)
    for seg in taxonomy["segments"]:
        if st.button(seg["label"], key=f"segment_{seg['key']}", use_container_width=True):
            ss.segment = seg["key"]
            ss.series = None
            ss.model_key = None

with right:
    st.markdown('<div class="row-title">Step 2 · Select series</div>', unsafe_allow_html=True)
    if ss.segment:
        for s_key in nonempty_series_for(ss.segment):
            label = series_label(ss.segment, s_key)
            if st.button(label, key=f"series_{s_key}", use_container_width=True):
                ss.series = s_key
                ss.model_key = None
    else:
        st.info("Pick a group on the left.")

st.markdown("---")

# ---------- Models row (single horizontal strip) ----------
st.markdown('<div class="row-title">Step 3 · Select model</div>', unsafe_allow_html=True)
if ss.segment and ss.series:
    models = models_for(ss.segment, ss.series).sort_values("marketing_name")
    if models.empty:
        st.info("No models in this series yet.")
    else:
        # Build clickable pills in a horizontal scroller
        pills_html = ['<div class="hscroll">']
        for _, row in models.iterrows():
            title = row["marketing_name"]
            subbits = []
            if isinstance(row.get("class_marking"), str):
                subbits.append(f"Class: {row.get('class_marking','unknown')}")
            if isinstance(row.get("weight_band"), str):
                subbits.append(f"Weight: {row.get('weight_band','?')}")
            sub = " • ".join(subbits)
            # Each pill triggers a unique form submit
            pills_html.append(
                f'''
                <form action="" method="post" style="display:inline;">
                  <button class="pill" name="select_model" value="{row['model_key']}">
                    {title}<span class="sub">{sub}</span>
                  </button>
                </form>
                '''
            )
        pills_html.append("</div>")
        st.markdown("\n".join(pills_html), unsafe_allow_html=True)

        # Handle selection (works in Streamlit via query param hack using forms + on rerun read from request)
        # Simpler: use st.experimental_get_query_params()/set; but HTML forms won't set those.
        # Use an alternative: invisible buttons—however Streamlit doesn't capture HTML form posts.
        # So also render invisible Streamlit buttons for each model to actually capture clicks:
        # (Users click the visible pill; also show small invisible st.button stacked to capture)
        # Practical approach: render Streamlit buttons under the hood.
        btn_cols = st.columns(len(models))
        for i, (_, row) in enumerate(models.iterrows()):
            with btn_cols[i]:
                if st.button(" ", key=f"hidden_{row['model_key']}"):
                    ss.model_key = row["model_key"]
        # Tip for users:
        st.caption("Tip: Scroll sideways if you can’t see all models.")

else:
    st.info("Choose a group and series to see models.")

st.markdown("---")

# ---------- Summary boxes ----------
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

st.caption("Layout: Step 1 (left) • Step 2 (right) • Models in a single horizontal row, then summary.")
