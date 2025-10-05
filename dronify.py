# dronify.py — UI with flags, badges, geo-awareness placeholder, no notes
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
    for col in (
        "image_url", "segment", "series",
        "class_marking", "weight_band",
        "marketing_name", "mtom_g_nominal",
        "eu_class_marking", "uk_class_marking",
        "remote_id_builtin", "year_released",
        "notes", "operator_id_required",  # operator id logic
        "geo_awareness"                   # placeholder (to fill in YAML later)
    ):
        if col not in df.columns:
            df[col] = ""

    # normalized for robust matching
    df["segment_norm"] = df["segment"].astype(str).str.strip().str.lower()
    df["series_norm"]  = df["series"].astype(str).str.strip().str.lower()

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

# ---------- Image resolver ----------
RAW_BASE = "https://raw.githubusercontent.com/JonathanGreen79/dronify/main/images/"

def resolve_img(url: str) -> str:
    """
    Accepts:
    - Absolute URLs: returned as-is
    - 'images/...' paths: convert to GitHub raw
    - Bare filenames like 'mini_2.jpg': assume under /images
    """
    url = (url or "").strip()
    if not url:
        return ""

    low = url.lower()
    if low.startswith("http://") or low.startswith("https://") or low.startswith("data:"):
        return url

    if low.startswith("images/"):
        return RAW_BASE + url.split("/", 1)[1]

    # bare filename or relative path -> assume it's under /images
    return RAW_BASE + url.lstrip("/")

# Stage 1 hero images
SEGMENT_HERO = {
    "consumer": resolve_img("images/consumer.jpg"),
    "pro":       resolve_img("images/professional.jpg"),
    "enterprise":resolve_img("images/enterprise.jpg"),
}

# ---------- Helpers ----------
def series_defs_for(segment_key: str):
    seg = next(s for s in taxonomy["segments"] if s["key"] == segment_key)
    seg_l = str(segment_key).strip().lower()
    present = set(
        df.loc[df["segment_norm"] == seg_l, "series_norm"].dropna().unique().tolist()
    )
    out = []
    for s in seg["series"]:
        if s["key"].strip().lower() in present:
            out.append(s)
    return out

def pad_digits_for_natural(series: pd.Series, width: int = 6) -> pd.Series:
    s = series.astype(str).str.lower()
    return s.str.replace(r"\d+", lambda m: f"{int(m.group(0)):0{width}d}", regex=True)

def models_for(segment_key: str, series_key: str):
    seg_l = str(segment_key).strip().lower()
    ser_l = str(series_key).strip().lower()
    subset = df[(df["segment_norm"] == seg_l) & (df["series_norm"] == ser_l)].copy()
    subset["series_key"] = pad_digits_for_natural(subset["series"])
    subset["name_key"]   = pad_digits_for_natural(subset["marketing_name"])
    subset = subset.sort_values(
        by=["series_key", "name_key", "marketing_name"],
        kind="stable",
        ignore_index=True
    )
    return subset.drop(columns=["series_key", "name_key"])

def random_image_for_series(segment_key: str, series_key: str) -> str:
    """Pick a random model image from the series; if none, use segment hero."""
    seg_l = str(segment_key).strip().lower()
    ser_l = str(series_key).strip().lower()

    subset = df[(df["segment_norm"] == seg_l) & (df["series_norm"] == ser_l)]
    subset = subset[subset["image_url"].astype(str).str.strip() != ""]
    if subset.empty:
        return SEGMENT_HERO.get(segment_key, "")
    raw = str(subset.sample(1, random_state=None)["image_url"].iloc[0])
    return resolve_img(raw)

# ---------- Styles ----------
st.markdown("""
<style>
.block-container { padding-top: 1.1rem; }

.card {
  width: 260px; height: 240px; border: 1px solid #E5E7EB; border-radius: 14px;
  background: #fff; text-decoration: none !important; color: #111827 !important;
  display: block; padding: 12px;
  transition: box-shadow .15s ease, transform .15s ease, border-color .15s ease;
  cursor: pointer;
}
.card:hover { border-color: #D1D5DB; box-shadow: 0 6px 18px rgba(0,0,0,.08); transform: translateY(-2px); }

.img {
  width: 100%; height: 150px; border-radius: 10px; background: #F3F4F6;
  overflow: hidden; display:flex; align-items:center; justify-content:center;
}
.img > img { width: 100%; height: 100%; object-fit: cover; }

.title { margin-top: 10px; text-align: center; font-weight: 700; font-size: 0.98rem; }
.sub { margin-top: 4px; text-align: center; font-size: .8rem; color: #6B7280; }

.strip { display:flex; flex-wrap:nowrap; gap:14px; overflow-x:auto; padding:8px 2px; margin:0; }
.strip2 { display:grid; grid-auto-flow:column; grid-auto-columns:260px; grid-template-rows:repeat(2,1fr); gap:14px; overflow-x:auto; padding:8px 2px; margin:0; }

.h1 { font-weight:800; font-size:1.2rem; color:#1F2937; margin:0 0 12px 0; }

/* Sidebar badges + rows */
.badge { display:inline-block; padding:6px 10px; border-radius:999px; background:#EEF2FF; color:#3730A3; font-weight:600; font-size:.80rem; margin-right:.35rem; }
.badge-red { background:#FEE2E2; color:#991B1B; box-shadow:0 6px 16px rgba(255, 0, 0, .08); }
.badge-green { background:#DCFCE7; color:#14532D; box-shadow:0 6px 16px rgba(16, 185, 129, .08); }
.badge-gray { background:#F3F4F6; color:#374151; }

.flag-row {
  display:flex; align-items:center; gap:10px;
  margin: 4px 0 2px 0;
}
.flag { width:20px; height:20px; object-fit:contain; border-radius:3px; }
.flag-text { font-weight:700; color:#1F2937; }

.sidebar-title { font-weight:800; font-size:1.05rem; margin-top:.8rem; }
.sidebar-kv { margin:.25rem 0; color:#374151; font-size:0.94rem; }
.sidebar-muted { color:#6B7280; font-size:0.85rem; }
.sidebar-back { margin-top: 0.5rem; display:inline-block; text-decoration:none; color:#2563EB; font-weight:600; }
.sidebar-back:hover { text-decoration: underline; }

/* icon bullets */
.kv-icon { font-size: 1.05rem; display:inline-block; width: 1.35rem; text-align:center; }
</style>
""", unsafe_allow_html=True)

# ---------- Card (anchor in same tab) ----------
def card_link(qs: str, title: str, sub: str = "", img_url: str = "") -> str:
    img = f"<div class='img'><img src='{img_url}' alt=''/></div>" if img_url else "<div class='img'></div>"
    sub_html = f"<div class='sub'>{sub}</div>" if sub else ""
    return (f"<a class='card' href='?{qs}' target='_self' rel='noopener'>"
            f"{img}<div class='title'>{title}</div>{sub_html}</a>")

def render_row(title: str, items: list[str]):
    st.markdown(f"<div class='h1'>{title}</div><div class='strip'>{''.join(items)}</div>", unsafe_allow_html=True)

def render_two_rows(title: str, items: list[str]):
    st.markdown(f"<div class='h1'>{title}</div><div class='strip2'>{''.join(items)}</div>", unsafe_allow_html=True)

# ---------- Screens ----------
if not segment:
    # Stage 1 — choose group
    items = []
    for seg in taxonomy["segments"]:
        img = SEGMENT_HERO.get(seg["key"], "")
        items.append(card_link(f"segment={seg['key']}", seg["label"], img_url=img))
    render_row("Choose your drone category", items)

elif not series:
    # Stage 2 — choose series, show random image from that series
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    items = []
    for s in series_defs_for(segment):
        rnd_img = random_image_for_series(segment, s["key"])
        items.append(card_link(f"segment={segment}&series={s['key']}", f"{s['label']}", img_url=rnd_img))
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

            # Back link to series grid (breadcrumb removed per request)
            back_qs = f"segment={segment}&series={series}"
            st.sidebar.markdown(
                f"<a class='sidebar-back' href='?{back_qs}' target='_self'>← Back to models</a>",
                unsafe_allow_html=True
            )

            # Thumbnail
            img_url = resolve_img(row.get("image_url", ""))
            if img_url:
                st.sidebar.image(img_url, use_container_width=True, caption=row.get("marketing_name", ""))

            # EU/UK classes as separate rows with flags
            eu = (row.get("eu_class_marking") or row.get("class_marking") or "unknown") or "unknown"
            uk = (row.get("uk_class_marking") or row.get("class_marking") or "unknown") or "unknown"

            eu_flag = resolve_img("images/eu.png")
            uk_flag = resolve_img("images/uk.png")

            st.sidebar.markdown(
                f"<div class='flag-row'><img class='flag' src='{eu_flag}' alt='EU flag'><span class='flag-text'>EU:</span> <span class='badge'>{eu}</span></div>",
                unsafe_allow_html=True
            )
            st.sidebar.markdown(
                f"<div class='flag-row'><img class='flag' src='{uk_flag}' alt='UK flag'><span class='flag-text'>UK:</span> <span class='badge'>{uk}</span></div>",
                unsafe_allow_html=True
            )

            # Operator ID badge (color-coded)
            op = str(row.get("operator_id_required", "")).strip().lower()
            if op in ("yes", "true", "1"):
                op_badge = "<span class='badge badge-red'>Operator ID: Required</span>"
            elif op in ("no", "false", "0"):
                op_badge = "<span class='badge badge-green'>Operator ID: Not required</span>"
            else:
                op_badge = "<span class='badge badge-gray'>Operator ID: Unknown</span>"
            st.sidebar.markdown(op_badge, unsafe_allow_html=True)

            # Flyer ID placeholder badge
            st.sidebar.markdown("<span class='badge badge-gray'>Flyer ID</span>", unsafe_allow_html=True)

            # Key specs
            st.sidebar.markdown("<div class='sidebar-title'>Key specs</div>", unsafe_allow_html=True)

            # Icons: model (🛩️), weight/MTOW (⚖️), remote (🛰️), calendar (📅)
            mtow = str(row.get("mtom_g_nominal", "")).strip()
            mtow_display = (mtow + " g") if mtow else "—"

            remote_id = str(row.get("remote_id_builtin", "")).strip() or "unknown"

            # Geo-awareness placeholder (to be populated later from YAML)
            geo_awareness = str(row.get("geo_awareness", "")).strip() or "—"

            st.sidebar.markdown(
                f"""
                <div class='sidebar-kv'><span class='kv-icon'>🛩️</span><b>Model</b> : {row.get('marketing_name', '—')}</div>
                <div class='sidebar-kv'><span class='kv-icon'>⚖️</span><b>MTOW</b> : {mtow_display}</div>
                <div class='sidebar-kv'><span class='kv-icon'>🛰️</span><b>Remote ID</b> : {remote_id}</div>
                <div class='sidebar-kv'><span class='kv-icon'>🗺️</span><b>Geo-awareness</b> : {geo_awareness}</div>
                <div class='sidebar-kv'><span class='kv-icon'>📅</span><b>Released</b> : {row.get('year_released', '—')}</div>
                """,
                unsafe_allow_html=True
            )

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
            # Sub info: show EU/UK class + weight band
            eu_c = (r.get("eu_class_marking") or r.get("class_marking") or "").strip()
            uk_c = (r.get("uk_class_marking") or r.get("class_marking") or "").strip()
            parts = []
            if eu_c or uk_c:
                eu_show = eu_c if eu_c else "—"
                uk_show = uk_c if uk_c else "—"
                parts.append(f"Class: EU {eu_show} • UK {uk_show}")
            else:
                cm = r.get("class_marking", "").strip()
                if cm:
                    parts.append(f"Class: {cm}")
            # keep weight band out of sidebar per your ask, but OK in card subtitle:
            wb = r.get("weight_band", "")
            if isinstance(wb, str) and wb:
                parts.append(f"Weight: {wb}")
            sub = " • ".join(parts)

            items.append(
                card_link(
                    f"segment={segment}&series={series}&model={r['model_key']}",
                    r.get("marketing_name", ""),
                    sub=sub,
                    img_url=resolve_img(str(r.get("image_url", "")))
                )
            )
        render_two_rows(f"Choose a drone ({seg_label} → {ser_label})", items)
