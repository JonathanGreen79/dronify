# dronify.py — “last-good” navigation + image fixer + sidebar + 3-column compliance matrix
import re
import random
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

st.set_page_config(page_title="Dronify", layout="wide")

DATASET_PATH = Path("dji_drones_v3.yaml")
TAXONOMY_PATH = Path("taxonomy.yaml")

# ------------------------------- Loaders -------------------------------

def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@st.cache_data
def load_data():
    dataset = load_yaml(DATASET_PATH)
    taxonomy = load_yaml(TAXONOMY_PATH)
    df = pd.DataFrame(dataset["data"])

    # Ensure all columns exist to avoid key errors
    for col in (
        "image_url", "segment", "series", "marketing_name", "model_key",
        "mtom_g_nominal",
        "eu_class_marking", "uk_class_marking",
        "has_camera", "geo_awareness", "remote_id_builtin", "operator_id_required",
        "year_released", "notes"
    ):
        if col not in df.columns:
            df[col] = ""

    # Normalized helpers for robust filtering
    df["segment_norm"] = df["segment"].astype(str).str.strip().str.lower()
    df["series_norm"]  = df["series"].astype(str).str.strip().str.lower()

    return df, taxonomy

df, taxonomy = load_data()

# ------------------------------- Query params -------------------------------

def get_qp():
    # Streamlit ≥1.32
    try:
        return dict(st.query_params)
    except Exception:
        qp = st.experimental_get_query_params()
        return {k: (v[0] if isinstance(v, list) else v) for k, v in qp.items()}

qp = get_qp()
segment = qp.get("segment")
series  = qp.get("series")
model   = qp.get("model")

# ------------------------------- Image resolving -------------------------------

RAW_BASE = "https://raw.githubusercontent.com/JonathanGreen79/dronify/main/"

def resolve_img(url: str) -> str:
    """
    Make image URLs robust:
    - absolute http(s): return as-is
    - if startswith 'images/': prepend RAW_BASE
    - bare filename like 'mini-5-pro.jpg' => 'images/<filename>'
    - already-raw GitHub links: pass through
    """
    u = (url or "").strip()
    if not u:
        return ""
    low = u.lower()
    if low.startswith("http://") or low.startswith("https://") or low.startswith("data:"):
        return u
    if low.startswith("images/"):
        return RAW_BASE + u
    # bare filename or subpath -> assume under /images
    return RAW_BASE + "images/" + u.lstrip("/")

# Hero images (stage 1)
SEGMENT_HERO = {
    "consumer": resolve_img("images/consumer.jpg"),
    "pro":       resolve_img("images/professional.jpg"),
    "enterprise":resolve_img("images/enterprise.jpg"),
}

# ------------------------------- Helpers -------------------------------

def series_defs_for(segment_key: str):
    seg = next(s for s in taxonomy["segments"] if s["key"] == segment_key)
    present = set(
        df.loc[df["segment_norm"] == segment_key, "series_norm"].dropna().unique().tolist()
    )
    out = []
    for s in seg["series"]:
        if s["key"] in present:
            out.append(s)
    return out

def pad_digits_for_natural(s: pd.Series, width: int = 6) -> pd.Series:
    # Lowercase + pad digits => gives natural sort via lexicographic
    s = s.astype(str).str.lower()
    return s.str.replace(r"\d+", lambda m: f"{int(m.group(0)):0{width}d}", regex=True)

def models_for(segment_key: str, series_key: str):
    subset = df[(df["segment_norm"] == segment_key) & (df["series_norm"] == series_key)].copy()
    subset["series_key"] = pad_digits_for_natural(subset["series"])
    subset["name_key"]   = pad_digits_for_natural(subset["marketing_name"])
    subset = subset.sort_values(
        by=["series_key", "name_key", "marketing_name"],
        kind="stable",
        ignore_index=True
    )
    return subset.drop(columns=["series_key", "name_key"])

def random_image_for_series(segment_key: str, series_key: str) -> str:
    subset = df[(df["segment_norm"] == segment_key) & (df["series_norm"] == series_key)]
    subset = subset[subset["image_url"].astype(str).str.strip() != ""]
    if subset.empty:
        return SEGMENT_HERO.get(segment_key, "")
    raw = str(subset.sample(1, random_state=None)["image_url"].iloc[0])
    return resolve_img(raw)

# ------------------------------- Styles -------------------------------

st.markdown("""
<style>
.block-container { padding-top: 1.1rem; }

/* ====== Cards ====== */
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

/* ====== Sidebar badges and icons ====== */
.sidebar-title { font-weight:800; font-size:1.05rem; margin-top:.6rem; }
.sidebar-kv { margin:.18rem 0; color:#374151; font-size:.95rem; }
.sidebar-muted { color:#6B7280; font-size:.85rem; }
.sidebar-back { margin-top:0.5rem; display:inline-block; text-decoration:none; color:#2563EB; font-weight:600; }
.sidebar-back:hover { text-decoration: underline; }
.badge { display:inline-block; padding:6px 10px; border-radius:999px; background:#EEF2FF; color:#3730A3; font-weight:600; font-size:.82rem; margin-right:.35rem; }
.badge-red { background:#FEE2E2; color:#991B1B; }
.badge-green { background:#DCFCE7; color:#14532D; }
.badge-grey { background:#F3F4F6; color:#6B7280; }
.flag-row { display:flex; align-items:center; gap:10px; margin:.25rem 0; }
.flag-row img { width:20px; height:20px; border-radius:3px; object-fit:cover; }

/* ====== Compliance columns ====== */
.matrix h3 { margin:0 0 .7rem 0; font-size:1.2rem; }
.rowline { display:flex; align-items:center; gap:12px; margin:.25rem 0; }
.rowline .label { width:120px; color:#374151; }
.pill { display:inline-block; padding:6px 10px; border-radius:999px; font-weight:600; font-size:.82rem; }
.pill-ok { background:#DCFCE7; color:#14532D; }
.pill-warn { background:#FEF3C7; color:#92400E; }
.pill-attn { background:#FEE2E2; color:#991B1B; }
.pill-info { background:#DBEAFE; color:#1E3A8A; }
.pill-na { background:#F3F4F6; color:#6B7280; }

.small { font-size:.82rem; color:#6B7280; }

/* icons (emoji) alignment tweak */
.icon { width:1.2rem; display:inline-block; text-align:center; }
</style>
""", unsafe_allow_html=True)

# ------------------------------- Card builders -------------------------------

def card_link(qs: str, title: str, sub: str = "", img_url: str = "") -> str:
    img = f"<div class='img'><img src='{img_url}' alt=''/></div>" if img_url else "<div class='img'></div>"
    sub_html = f"<div class='sub'>{sub}</div>" if sub else ""
    return (f"<a class='card' href='?{qs}' target='_self' rel='noopener'>"
            f"{img}<div class='title'>{title}</div>{sub_html}</a>")

def render_row(title: str, items: list[str]):
    st.markdown(f"<div class='h1'>{title}</div><div class='strip'>{''.join(items)}</div>", unsafe_allow_html=True)

def render_two_rows(title: str, items: list[str]):
    st.markdown(f"<div class='h1'>{title}</div><div class='strip2'>{''.join(items)}</div>", unsafe_allow_html=True)

# ------------------------------- Compliance logic helpers -------------------------------

def coalesce(*vals, default=""):
    for v in vals:
        s = str(v or "").strip()
        if s:
            return s
    return default

def is_c0(eu, uk, weight):
    return (eu.upper() == "C0") or (weight and float(str(weight) or "0") <= 250)

def a2_applicable(eu_cls: str) -> bool:
    """
    Very simplified: A2 only meaningful for C2 (and sometimes C1 transitional variants),
    but for our purpose:
      - C0 / Legacy => not applicable
      - C1 => effectively A1/A3 routes; we’ll grey A2
      - C2 => applicable (with A2 CofC)
      - C3/C4 => A2 not applicable (A3 / Specific)
    """
    e = eu_cls.upper()
    if e in ("", "UNKNOWN", "LEGACY"):
        return False
    if e == "C0":
        return False
    if e == "C1":
        return False
    if e == "C2":
        return True
    return False  # C3/C4 etc.

def pill(text, kind="ok"):
    klass = {
        "ok": "pill-ok",
        "warn": "pill-warn",
        "attn": "pill-attn",
        "info": "pill-info",
        "na": "pill-na",
    }.get(kind, "pill-ok")
    return f"<span class='pill {klass}'>{text}</span>"

def line(label, badge_html):
    return f"<div class='rowline'><div class='label'>{label}</div>{badge_html}</div>"

def compliance_column(title: str, eu_cls: str, uk_cls: str, weight_g, *, year_tag: str):
    """
    Returns HTML for one compliance column (Current / 2026 / 2028 planned).
    Super-simplified policy model (we learned together):
      - A1 Yes (close to people) for C0/≤250g. C1 often A1 transitional in practice; we keep “Yes (close)”.
      - A2 shows grey “N/A for this class” except for C2 (shows “Yes – with A2 CofC”).
      - A3 always “Yes (far)”.
      - Specific always “If needed”.
      - Operator ID, Flyer ID, Remote ID, Geo awareness:
          * We show them under each column to reinforce the changing timeline;
            values are “Required” for these examples; geo is required by 2026+.
    """
    e = (eu_cls or "").strip().upper()
    uk = (uk_cls or "").strip().upper()
    w  = float(str(weight_g or "0") or "0")

    # A1
    if is_c0(e, uk, w):
        a1 = pill("Yes (close)", "ok")
    else:
        # keep simple/optimistic view for modern CE classes (C1)
        a1 = pill("Yes (close)", "ok")

    # A2
    if a2_applicable(e):
        a2 = pill("Yes – with A2 CofC", "info")
    else:
        a2 = pill("N/A for this class", "na")

    # A3
    a3 = pill("Yes (far)", "info")

    # Specific
    sp = pill("If needed", "warn")

    # Registration/ID expectations (we present consistently for clarity)
    opid = pill("Required", "attn")
    flyid = pill("Required", "attn")

    # Remote ID & Geo awareness — show as required from 2026+, optional/unknown now
    if year_tag == "current":
        rid = pill("Required", "attn")  # many models now have it; still show red to prompt check
        geo = pill("Required", "attn")  # geo db / NFZ warnings expected on modern models
    else:
        rid = pill("Required", "attn")
        geo = pill("Required", "attn")

    html = []
    html.append(f"<div class='matrix'><h3>{title}</h3>")
    html.append(line("A1", a1))
    html.append(line("A2", a2))
    html.append(line("A3", a3))
    html.append(line("Specific", sp))
    html.append(line("Operator ID", opid))
    html.append(line("Flyer ID", flyid))
    html.append(line("Remote ID", rid))
    html.append(line("Geo-awareness", geo))
    html.append("</div>")
    return "\n".join(html)

# ------------------------------- UI flow -------------------------------

if not segment:
    # Stage 1 — categories
    items = []
    for seg in taxonomy["segments"]:
        img = SEGMENT_HERO.get(seg["key"], "")
        items.append(card_link(f"segment={seg['key']}", seg["label"], img_url=img))
    render_row("Choose your drone category", items)

elif not series:
    # Stage 2 — series (random image from that series)
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    items = []
    for s in series_defs_for(segment):
        rnd_img = random_image_for_series(segment, s["key"])
        items.append(card_link(f"segment={segment}&series={s['key']}", s["label"], img_url=rnd_img))
    render_row(f"Choose a series ({seg_label})", items)

else:
    # Stage 3 — models grid + sidebar details (or compliance columns if a model is selected)
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    ser_label = next(s["label"] for s in series_defs_for(segment) if s["key"] == series)

    # If a model is selected, show sidebar details + compliance columns in main body
    if model:
        sel = df[df["model_key"] == model]
        if not sel.empty:
            row = sel.iloc[0]

            # Sidebar: back link
            back_qs = f"segment={segment}&series={series}"
            st.sidebar.markdown(
                f"<a class='sidebar-back' href='?{back_qs}' target='_self'>← Back to models</a>",
                unsafe_allow_html=True
            )

            # Thumbnail
            img_url = resolve_img(row.get("image_url", ""))
            if img_url:
                st.sidebar.image(img_url, use_container_width=True, caption=row.get("marketing_name", ""))

            # EU/UK flags and class badges (each on its own line with flag)
            eu_cls = coalesce(row.get("eu_class_marking"), row.get("class_marking"), default="unknown")
            uk_cls = coalesce(row.get("uk_class_marking"), row.get("class_marking"), default="unknown")
            st.sidebar.markdown(
                f"<div class='flag-row'><img src='{resolve_img('images/eu.png')}' alt='EU'/>"
                f"<span>EU: <b>{eu_cls}</b></span></div>",
                unsafe_allow_html=True
            )
            st.sidebar.markdown(
                f"<div class='flag-row'><img src='{resolve_img('images/uk.png')}' alt='UK'/>"
                f"<span>UK: <b>{uk_cls}</b></span></div>",
                unsafe_allow_html=True
            )

            # Operator ID / Flyer ID badges
            op = str(row.get("operator_id_required", "")).strip().lower()
            if op in ("yes", "true", "1"):
                op_badge = "<span class='badge badge-red'>Operator ID: Required</span>"
            elif op in ("no", "false", "0"):
                op_badge = "<span class='badge badge-green'>Operator ID: Not required</span>"
            else:
                op_badge = "<span class='badge'>Operator ID: Unknown</span>"
            st.sidebar.markdown(op_badge, unsafe_allow_html=True)

            st.sidebar.markdown("<span class='badge'>Flyer ID</span>", unsafe_allow_html=True)

            # Key specs with icons (emoji)
            st.sidebar.markdown("<div class='sidebar-title'>Key specs</div>", unsafe_allow_html=True)

            model_name = row.get("marketing_name", "—")
            st.sidebar.markdown(f"<div class='sidebar-kv'><span class='icon'>🧷</span><b>Model</b> : {model_name}</div>", unsafe_allow_html=True)

            mtow = row.get("mtom_g_nominal", "")
            mtow_str = f"{mtow} g" if str(mtow).strip() else "—"
            st.sidebar.markdown(f"<div class='sidebar-kv'><span class='icon'>⚖️</span><b>MTOW</b> : {mtow_str}</div>", unsafe_allow_html=True)

            rid = str(row.get("remote_id_builtin", "unknown")).strip() or "unknown"
            st.sidebar.markdown(f"<div class='sidebar-kv'><span class='icon'>📡</span><b>Remote ID</b> : {rid}</div>", unsafe_allow_html=True)

            geo = str(row.get("geo_awareness", "unknown")).strip() or "unknown"
            st.sidebar.markdown(f"<div class='sidebar-kv'><span class='icon'>🗺️</span><b>Geo-awareness</b> : {geo}</div>", unsafe_allow_html=True)

            yr = coalesce(row.get("year_released"), default="—")
            st.sidebar.markdown(f"<div class='sidebar-kv'><span class='icon'>📅</span><b>Released</b> : {yr}</div>", unsafe_allow_html=True)

            # ----------------- Main body: compliance matrix -----------------
            col1, col2, col3 = st.columns(3)

            weight_g = row.get("mtom_g_nominal", "")
            col1.markdown(
                compliance_column("Current", eu_cls, uk_cls, weight_g, year_tag="current"),
                unsafe_allow_html=True
            )
            col2.markdown(
                compliance_column("2026", eu_cls, uk_cls, weight_g, year_tag="2026"),
                unsafe_allow_html=True
            )
            col3.markdown(
                compliance_column("2028 (planned)", eu_cls, uk_cls, weight_g, year_tag="2028"),
                unsafe_allow_html=True
            )

        else:
            model = None  # fall back to grid below

    # No model selected => show the models grid
    if not model:
        items = []
        models = models_for(segment, series)
        for _, r in models.iterrows():
            eu_c = coalesce(r.get("eu_class_marking"), r.get("class_marking"))
            uk_c = coalesce(r.get("uk_class_marking"), r.get("class_marking"))
            yr = str(r.get("year_released", "") or "").strip()
            parts = []
            if eu_c or uk_c:
                eu_show = eu_c if eu_c else "—"
                uk_show = uk_c if uk_c else "—"
                parts.append(f"Class: EU {eu_show} • UK {uk_show}")
            if yr:
                parts.append(f"Released: {yr}")
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
