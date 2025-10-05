# dronify.py — same UI as your “last good”, with robust image resolving
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
        "notes", "operator_id_required"
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
    Be generous:
    - Absolute URLs: return as-is
    - 'images/...' paths: convert to GitHub raw
    - Bare filenames like 'mini_2.jpg' or 'air_3.png': treat as 'images/<filename>'
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
.sidebar-title { font-weight:800; font-size:1.05rem; margin-top:.6rem; }
.sidebar-kv { margin:.15rem 0; color:#374151; font-size:.93rem; }
.sidebar-muted { color:#6B7280; font-size:.85rem; }
.sidebar-back { margin-top:0.5rem; display:inline-block; text-decoration:none; color:#2563EB; font-weight:600; }
.sidebar-back:hover { text-decoration: underline; }
.badge { display:inline-block; padding:3px 8px; border-radius:999px; background:#EEF2FF; color:#3730A3; font-weight:600; font-size:.78rem; margin-right:.35rem; }
.badge-red { background:#FEE2E2; color:#991B1B; }
.badge-green { background:#DCFCE7; color:#14532D; }
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
    items = []
    for seg in taxonomy["segments"]:
        img = SEGMENT_HERO.get(seg["key"], "")
        items.append(card_link(f"segment={seg['key']}", seg["label"], img_url=img))
    render_row("Choose your drone category", items)

elif not series:
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    items = []
    for s in series_defs_for(segment):
        rnd_img = random_image_for_series(segment, s["key"])
        items.append(card_link(f"segment={segment}&series={s['key']}", f"{s['label']}", img_url=rnd_img))
    render_row(f"Choose a series ({seg_label})", items)

else:
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    ser_label = next(s["label"] for s in series_defs_for(segment) if s["key"] == series)

    if model:
        sel = df[df["model_key"] == model]
        if not sel.empty:
            row = sel.iloc[0]
            st.sidebar.markdown(f"**{seg_label} → {ser_label}**")
            back_qs = f"segment={segment}&series={series}"
            st.sidebar.markdown(f"<a class='sidebar-back' href='?{back_qs}' target='_self'>← Back to models</a>", unsafe_allow_html=True)

            img_url = resolve_img(row.get("image_url", ""))
            if img_url:
                st.sidebar.image(img_url, use_container_width=True, caption=row.get("marketing_name", ""))

            eu = (row.get("eu_class_marking") or row.get("class_marking") or "unknown") or "unknown"
            uk = (row.get("uk_class_marking") or row.get("class_marking") or "unknown") or "unknown"
            op = str(row.get("operator_id_required", "")).strip().lower()
            if op in ("yes", "true", "1"):
                op_badge = "<span class='badge badge-red'>Operator ID: Required</span>"
            elif op in ("no", "false", "0"):
                op_badge = "<span class='badge badge-green'>Operator ID: Not required</span>"
            else:
                op_badge = "<span class='badge'>Operator ID: Unknown</span>"

            st.sidebar.markdown(
                f"<div style='margin:.4rem 0 .2rem 0'>"
                f"<span class='badge'>EU: {eu}</span>"
                f"<span class='badge'>UK: {uk}</span>"
                f"{op_badge}</div>",
                unsafe_allow_html=True
            )

            st.sidebar.markdown("<div class='sidebar-title'>Key specs</div>", unsafe_allow_html=True)
            st.sidebar.markdown(
                f"""
                <div class='sidebar-kv'><b>Model</b>: {row.get('marketing_name', '—')}</div>
                <div class='sidebar-kv'><b>MTOW</b>: {row.get('mtom_g_nominal', '—')} g</div>
                <div class='sidebar-kv'><b>Weight band</b>: {row.get('weight_band', '—')}</div>
                <div class='sidebar-kv'><b>EU class</b>: {eu}</div>
                <div class='sidebar-kv'><b>UK class</b>: {uk}</div>
                <div class='sidebar-kv'><b>Remote ID</b>: {row.get('remote_id_builtin', 'unknown')}</div>
                <div class='sidebar-kv'><b>Released</b>: {row.get('year_released', '—')}</div>
                """,
                unsafe_allow_html=True
            )

            notes = str(row.get("notes", "")).strip()
            if notes:
                st.sidebar.markdown("<div class='sidebar-title'>Notes</div>", unsafe_allow_html=True)
                st.sidebar.markdown(f"<div class='sidebar-muted'>{notes}</div>", unsafe_allow_html=True)

            st.write("")
            st.write("")
        else:
            model = None

    if not model:
        models = models_for(segment, series)
        items = []
        for _, r in models.iterrows():
            # Sub info: EU/UK class + weight band
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
