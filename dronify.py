# dronify.py — sequential UI, stage 3 two-row horizontal grid, GitHub Raw images
import streamlit as st
import pandas as pd
import yaml
from pathlib import Path

st.set_page_config(page_title="Drone Picker", layout="wide")

DATASET_PATH = Path("dji_drones_v3.yaml")   # your latest dataset
TAXONOMY_PATH = Path("taxonomy.yaml")

# ---------- Data loading ----------
def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@st.cache_data
def load_data():
    dataset = load_yaml(DATASET_PATH)
    taxonomy = load_yaml(TAXONOMY_PATH)
    df = pd.DataFrame(dataset["data"])
    # backfills so UI can rely on columns
    for col in ("eu_class_marking","uk_class_marking","image_url","segment","series"):
        if col not in df.columns:
            df[col] = ""
    return df, taxonomy

df, taxonomy = load_data()

# ---------- Image URL resolver (use GitHub Raw for images/) ----------
RAW_BASE = "https://raw.githubusercontent.com/JonathanGreen79/dronify/main/images/"

def resolve_img(url: str) -> str:
    if not url:
        return ""
    if url.startswith("images/"):
        # convert "images/foo.jpg" -> GitHub raw URL
        return RAW_BASE + url.split("/", 1)[1]
    return url  # already absolute

# ---------- Query-param driven state ----------
ss = st.session_state
ss.setdefault("segment", None)
ss.setdefault("series", None)
ss.setdefault("model_key", None)

def get_qp():
    try:
        return dict(st.query_params)
    except Exception:
        # fallback for older Streamlit
        return {k:(v[0] if isinstance(v, list) else v) for k,v in st.experimental_get_query_params().items()}

qp = get_qp()
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

# ---------- Styles ----------
CSS = """
<style>
/* shared card look */
.card{
  flex:0 0 240px;
  height:220px;
  border:1px solid #E5E7EB;
  border-radius:14px;
  background:#fff;
  text-decoration:none;
  color:#111827;
  display:block;
  padding:10px;
  transition:all .15s ease-in-out;
}
.card:hover{ border-color:#D1D5DB; box-shadow:0 4px 16px rgba(0,0,0,.06) }
.img{
  width:100%; height:130px; border-radius:10px; background:#F3F4F6;
  display:flex; align-items:center; justify-content:center;
  font-size:.8rem; color:#6B7280; margin-bottom:8px; overflow:hidden;
}
.title{ font-weight:600; font-size:.95rem; line-height:1.15 }
.sub{ font-size:.78rem; color:#6B7280; margin-top:4px }
.h1{ font-weight:700; font-size:1.05rem; margin:0 0 10px 0; color:#374151 }

/* stage 1 & 2: one-row horizontal strip */
.strip{
  display:flex; flex-wrap:nowrap; gap:12px; overflow-x:auto; padding:6px 2px; margin:0;
}

/* stage 3: TWO-ROW horizontal grid that scrolls sideways */
.strip2{
  display:grid;
  grid-auto-flow: column;           /* extend horizontally */
  grid-auto-columns: 240px;         /* card width */
  grid-template-rows: repeat(2, 1fr);
  gap: 12px;
  overflow-x: auto;                  /* only horizontal scroll */
  padding: 6px 2px; margin: 0;
}

/* summary boxes */
.summary{ border:1px solid #E5E7EB; border-radius:12px; padding:12px; background:#fff }
.summary .lab{ font-size:.78rem; color:#6B7280; margin-bottom:4px }
.summary .val{ font-size:1.05rem; font-weight:600 }
</style>
"""

def card_html(href: str, title: str, sub: str = "", img_url: str = "") -> str:
    img = f"<img src='{img_url}' class='img' style='object-fit:cover'/>" if img_url else "<div class='img'>image</div>"
    return f"<a class='card' href='{href}' target='_self'>{img}<div class='title'>{title}</div><div class='sub'>{sub}</div></a>"

def render_strip(title: str, items: list[str]):
    st.markdown(CSS + f"<div class='h1'>{title}</div><div class='strip'>{''.join(items)}</div>", unsafe_allow_html=True)

def render_strip_two_rows(title: str, items: list[str]):
    st.markdown(CSS + f"<div class='h1'>{title}</div><div class='strip2'>{''.join(items)}</div>", unsafe_allow_html=True)

# ---------- Screens ----------
if ss.segment is None:
    # screen 1 — groups (one row)
    items = [card_html(f"?segment={seg['key']}", seg["label"]) for seg in taxonomy["segments"]]
    render_strip("Choose your group", items)

elif ss.series is None:
    # screen 2 — series for selected group (one row; no back link)
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == ss.segment)
    sdefs = series_defs_for(ss.segment)
    items = [card_html(f"?segment={ss.segment}&series={s['key']}", s["label"]) for s in sdefs]
    render_strip(f"Choose a series ({seg_label})", items)

else:
    # screen 3 — models (two-row horizontal grid)
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == ss.segment)
    ser_label = next(s["label"] for s in series_defs_for(ss.segment) if s["key"] == ss.series)

    models = models_for(ss.segment, ss.series)
    if models.empty:
        st.info("No models in this series yet.")
    else:
        items = []
        for _, r in models.iterrows():
            subbits = []
            cm = r.get("class_marking", "unknown")
            if isinstance(cm, str):
                subbits.append(f"Class: {cm}")
            wb = r.get("weight_band", "")
            if isinstance(wb, str) and wb:
                subbits.append(f"Weight: {wb}")
            sub = " • ".join(subbits)
            img_url = resolve_img(str(r.get("image_url", "")))
            items.append(card_html(
                f"?segment={ss.segment}&series={ss.series}&model={r['model_key']}",
                r["marketing_name"], sub=sub, img_url=img_url
            ))
        render_strip_two_rows(f"Choose a drone ({seg_label} → {ser_label})", items)

    # summary appears after user clicks a model
    if ss.model_key:
        sel = df[df["model_key"] == ss.model_key].iloc[0]
        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(
                f"<div class='summary'><div class='lab'>MTOW (g)</div><div class='val'>{sel.get('mtom_g_nominal','—')}</div></div>",
                unsafe_allow_html=True
            )
        with c2:
            st.markdown(
                f"<div class='summary'><div class='lab'>Name</div><div class='val'>{sel.get('marketing_name','—')}</div></div>",
                unsafe_allow_html=True
            )
        with c3:
            st.markdown(
                f"<div class='summary'><div class='lab'>Model Key</div><div class='val'>{sel.get('model_key','—')}</div></div>",
                unsafe_allow_html=True
            )
        with c4:
            eu = sel.get("eu_class_marking", sel.get("class_marking","unknown"))
            uk = sel.get("uk_class_marking", sel.get("class_marking","unknown"))
            st.markdown(
                f"<div class='summary'><div class='lab'>EU / UK Class</div><div class='val'>{eu} / {uk}</div></div>",
                unsafe_allow_html=True
            )
