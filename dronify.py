# dronify.py — UI wired to the new "core" YAML fields
import random
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

st.set_page_config(page_title="Dronify", layout="wide")

DATASET_PATH = Path("dji_drones_v3.yaml")   # now the core-only YAML
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

    # Ensure fields exist (new core schema)
    required = [
        "model_key","marketing_name","segment","series","year_released",
        "eu_class_marking","uk_class_marking","has_camera","operator_id_required",
        "remote_id","geo_awareness","mtow_g","image_url"
    ]
    for col in required:
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

qp      = get_qp()
segment = qp.get("segment")
series  = qp.get("series")
model   = qp.get("model")

# ---------- Image resolver (repo images via GitHub Raw) ----------
RAW_BASE = "https://raw.githubusercontent.com/JonathanGreen79/dronify/main/images/"

def resolve_img(url: str) -> str:
    """
    - Absolute URLs: return as-is
    - 'images/...' paths: convert to GitHub raw
    - Bare filenames: treat as 'images/<filename>'
    """
    url = (url or "").strip()
    if not url:
        return ""
    low = url.lower()
    if low.startswith("http://") or low.startswith("https://") or low.startswith("data:"):
        return url
    if low.startswith("images/"):
        return RAW_BASE + url.split("/", 1)[1]
    return RAW_BASE + url.lstrip("/")

# Stage 1 hero images
SEGMENT_HERO = {
    "consumer": resolve_img("images/consumer.jpg"),
    "pro":       resolve_img("images/professional.jpg"),
    "enterprise":resolve_img("images/enterprise.jpg"),
}

# Flag icons (20 px PNGs you added)
EU_FLAG = resolve_img("images/eu.png")
UK_FLAG = resolve_img("images/uk.png")

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

/* shared card look */
.card {
  width: 260px; height: 240px;
  border: 1px solid #E5E7EB; border-radius: 14px; background: #fff;
  text-decoration: none !important; color: #111827 !important;
  display: block; padding: 12px;
  transition: box-shadow .15s ease, transform .15s ease, border-color .15s ease;
  cursor: pointer;
}
.card:hover { border-color: #D1D5DB; box-shadow: 0 6px 18px rgba(0,0,0,.08); transform: translateY(-2px); }

.img { width: 100%; height: 150px; border-radius: 10px; background: #F3F4F6;
  overflow: hidden; display:flex; align-items:center; justify-content:center; }
.img > img { width: 100%; height: 100%; object-fit: cover; }

.title { margin-top: 10px; text-align: center; font-weight: 700; font-size: 0.98rem; }
.sub    { margin-top: 4px;  text-align: center; font-size: .8rem; color: #6B7280; }

/* horizontal strips */
.strip { display:flex; flex-wrap:nowrap; gap:14px; overflow-x:auto; padding:8px 2px; margin:0; }
.strip2{ display:grid; grid-auto-flow:column; grid-auto-columns:260px;
         grid-template-rows:repeat(2,1fr); gap:14px; overflow-x:auto; padding:8px 2px; margin:0; }

/* headings */
.h1 { font-weight: 800; font-size: 1.2rem; color: #1F2937; margin: 0 0 12px 0; }

/* sidebar */
.sidebar-title { font-weight: 800; font-size: 1.05rem; margin-top: .6rem; }
.sidebar-kv { margin: .25rem 0; color: #374151; font-size: 0.93rem; }
.sidebar-muted { color: #6B7280; font-size: 0.85rem; }
.sidebar-back { margin-top: 0.5rem; display: inline-block; text-decoration: none; color: #2563EB; font-weight: 600; }
.sidebar-back:hover { text-decoration: underline; }

/* badges */
.badge { display:inline-block; padding:6px 12px; border-radius:999px; background:#EEF2FF; color:#3730A3; font-weight:600; font-size:.82rem; margin-right:.45rem; box-shadow: 0 6px 14px rgba(0,0,0,.08); }
.badge-red { background:#FEE2E2; color:#991B1B; }
.badge-green { background:#DCFCE7; color:#14532D; }

/* flag line */
.flagline { display:flex; align-items:center; gap:8px; margin:4px 0; }
.flagline img { width:20px; height:20px; border-radius:3px; }

.small { color:#6B7280; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

# ---------- Card link ----------
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
    # Stage 2 — choose series (random per-series image)
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

    if model:
        sel = df[df["model_key"] == model]
        if not sel.empty:
            row = sel.iloc[0]

            # Back link to grid (we removed breadcrumb per your request)
            back_qs = f"segment={segment}&series={series}"
            st.sidebar.markdown(f"<a class='sidebar-back' href='?{back_qs}' target='_self'>← Back to models</a>", unsafe_allow_html=True)

            # Thumbnail
            img_url = resolve_img(row.get("image_url", ""))
            if img_url:
                st.sidebar.image(img_url, use_container_width=True, caption=row.get("marketing_name", ""))

            # EU/UK flag lines
            eu = (row.get("eu_class_marking") or "unknown")
            uk = (row.get("uk_class_marking") or "unknown")
            st.sidebar.markdown(
                f"""
                <div class='flagline'><img src="{EU_FLAG}" alt="EU"/> <span>EU: <b>{eu}</b></span></div>
                <div class='flagline'><img src="{UK_FLAG}" alt="UK"/> <span>UK: <b>{uk}</b></span></div>
                """,
                unsafe_allow_html=True
            )

            # Badges — Operator ID & Flyer ID (placeholder)
            op = str(row.get("operator_id_required", "")).strip().lower()
            if op in ("yes","true","1"):
                op_badge = "<span class='badge badge-red'>Operator ID: Required</span>"
            elif op in ("no","false","0"):
                op_badge = "<span class='badge badge-green'>Operator ID: Not required</span>"
            else:
                op_badge = "<span class='badge'>Operator ID: Unknown</span>"
            flyer_badge = "<span class='badge'>Flyer ID</span>"

            st.sidebar.markdown(f"{op_badge} {flyer_badge}", unsafe_allow_html=True)

            # Key specs
            def line_row(label, val, emoji):
                return f"<div class='sidebar-kv'>{emoji} <b>{label}</b> : {val}</div>"

            mtow = row.get("mtow_g", "")
            mtow_txt = f"{mtow} g" if str(mtow).strip() != "" else "—"
            rid  = (row.get("remote_id") or "unknown")
            geo  = (row.get("geo_awareness") or "unknown")
            rel  = (row.get("year_released") or "—")

            st.sidebar.markdown("<div class='sidebar-title'>Key specs</div>", unsafe_allow_html=True)
            st.sidebar.markdown(
                "".join([
                    line_row("Model", row.get("marketing_name", "—"), "🛰️"),
                    line_row("MTOW", mtow_txt, "⚖️"),
                    line_row("Remote ID", rid, "🔧"),
                    line_row("Geo-awareness", geo, "🛰️"),
                    line_row("Released", rel, "📅"),
                ]),
                unsafe_allow_html=True
            )

            # main body intentionally blank (for compliance columns later)
            st.write("")
            st.write("")
        else:
            model = None

    if not model:
        # Model grid (two rows)
        models = models_for(segment, series)
        items = []
        for _, r in models.iterrows():
            parts = []
            eu = (r.get("eu_class_marking") or "").strip()
            uk = (r.get("uk_class_marking") or "").strip()
            if eu or uk:
                parts.append(f"Class: EU {eu if eu else '—'} • UK {uk if uk else '—'}")
            rel = r.get("year_released", "")
            if str(rel).strip():
                parts.append(f"Released: {rel}")
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
