# dronify.py — clickable cards (same tab), uniform images,
# Stage2 random per-series image, Stage3 two-row grid with sidebar,
# plus MAIN BODY 3-column compliance comparator (Current / 2026 / 2028)
# and a robust image resolver that can’t break.

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
        "notes", "operator_id_required",
        "has_camera", "geo_awareness",
        "model_key",
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

# ---------- Image resolver (robust) ----------
RAW_BASE = "https://raw.githubusercontent.com/JonathanGreen79/dronify/main/images/"

def resolve_img(url: str) -> str:
    """
    Robustly resolve any image reference to a valid GitHub raw URL:
    - Absolute http(s)/data URLs are returned as-is.
    - Any local-ish reference (with or without 'images/') is normalised to RAW_BASE + <filename>.
    Handles mixed case, duplicate "images/", leading slashes and backslashes.
    """
    url = (url or "").strip()
    if not url:
        return ""

    low = url.lower()
    if low.startswith("http://") or low.startswith("https://") or low.startswith("data:"):
        return url

    # normalise local paths
    path = url.replace("\\", "/").strip()
    while path.startswith("/"):
        path = path[1:]
    # strip repeated leading images/
    while path.lower().startswith("images/"):
        path = path.split("/", 1)[1] if "/" in path else ""

    if not path:
        return ""

    return RAW_BASE + path

# Stage 1 hero images
SEGMENT_HERO = {
    "consumer": resolve_img("images/consumer.jpg"),
    "pro":       resolve_img("images/professional.jpg"),
    "enterprise":resolve_img("images/enterprise.jpg"),
}

# Flag icons
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
    """
    Convert strings to lowercase and pad every number with leading zeros.
    'Mini 2 SE' -> 'mini 000002 se' (so lexicographic sorts naturally).
    """
    s = series.astype(str).str.lower()
    return s.str.replace(r"\d+", lambda m: f"{int(m.group(0)):0{width}d}", regex=True)

def models_for(segment_key: str, series_key: str):
    """
    Return models in segment+series, sorted *naturally* by:
      1) series (harmless inside single series)
      2) marketing_name
    Uses padded-string helpers (no key=) to be Pandas 2.x safe.
    """
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
    """Pick a random image from models in the given segment+series."""
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
/* Headings spacing */
.block-container { padding-top: 1.1rem; }

/* shared card look */
.card {
  width: 260px; height: 240px;
  border: 1px solid #E5E7EB; border-radius: 14px;
  background: #fff; text-decoration: none !important; color: #111827 !important;
  display: block; padding: 12px;
  transition: box-shadow .15s ease, transform .15s ease, border-color .15s ease;
  cursor: pointer;
}
.card:hover { border-color: #D1D5DB; box-shadow: 0 6px 18px rgba(0,0,0,.08); transform: translateY(-2px); }

.img {
  width: 100%; height: 150px; border-radius: 10px; background: #F3F4F6;
  overflow: hidden; display: flex; align-items: center; justify-content: center;
}
.img > img { width: 100%; height: 100%; object-fit: cover; }  /* same-size look */

.title { margin-top: 10px; text-align: center; font-weight: 700; font-size: 0.98rem; }
.sub    { margin-top: 4px;  text-align: center; font-size: .8rem; color: #6B7280; }

/* horizontal strip (stage 1 & 2) */
.strip {
  display: flex; flex-wrap: nowrap; gap: 14px; overflow-x: auto; padding: 8px 2px; margin: 0;
}

/* stage 3: two-row horizontal grid */
.strip2 {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 260px;     /* card width */
  grid-template-rows: repeat(2, 1fr);
  gap: 14px;
  overflow-x: auto;
  padding: 8px 2px; margin: 0;
}

/* headings */
.h1 { font-weight: 800; font-size: 1.2rem; color: #1F2937; margin: 0 0 12px 0; }

/* sidebar styling */
.sidebar-title { font-weight: 800; font-size: 1.05rem; margin-top: .6rem; }
.sidebar-kv { margin: .15rem 0; color: #374151; font-size: 0.93rem; }
.sidebar-muted { color: #6B7280; font-size: 0.85rem; }
.sidebar-back { margin-top: 0.5rem; display: inline-block; text-decoration: none; color: #2563EB; font-weight: 600; }
.sidebar-back:hover { text-decoration: underline; }

/* pills/badges */
.badge { display:inline-block; padding:4px 8px; border-radius:999px; font-weight:600; font-size:.84rem; }
.badge-ok   { background:#DCFCE7; color:#14532D; }
.badge-warn { background:#FEF9C3; color:#854D0E; }
.badge-bad  { background:#FEE2E2; color:#991B1B; }
.badge-grey { background:#F3F4F6; color:#374151; }

/* small text helper */
.small { font-size:.88rem; color:#374151; }

/* flag rows */
.flag-row { display:flex; align-items:center; gap:8px; margin-bottom:6px; }
.flag-row img { width:20px; height:20px; object-fit:cover; border-radius:3px; }
</style>
""", unsafe_allow_html=True)

# ---------- Card (anchor in same tab) ----------
def card_link(qs: str, title: str, sub: str = "", img_url: str = "") -> str:
    img = f"<div class='img'><img src='{img_url}' alt=''/></div>" if img_url else "<div class='img'></div>"
    sub_html = f"<div class='sub'>{sub}</div>" if sub else ""
    return (
        f"<a class='card' href='?{qs}' target='_self' rel='noopener'>"
        f"{img}<div class='title'>{title}</div>{sub_html}</a>"
    )

def render_row(title: str, items: list[str]):
    st.markdown(f"<div class='h1'>{title}</div><div class='strip'>{''.join(items)}</div>", unsafe_allow_html=True)

def render_two_rows(title: str, items: list[str]):
    st.markdown(f"<div class='h1'>{title}</div><div class='strip2'>{''.join(items)}</div>", unsafe_allow_html=True)

# ---------- Compliance panels (main body) ----------
def _pill(text: str, kind: str = "grey") -> str:
    cls = {
        "ok": "badge badge-ok",
        "warn": "badge badge-warn",
        "bad": "badge badge-bad",
        "grey": "badge badge-grey",
    }.get(kind, "badge badge-grey")
    return f"<span class='{cls}'>{text}</span>"

def _line(label: str, value_html: str) -> str:
    return (
        "<div style='margin:.25rem 0 .35rem 0'>"
        f"<span style='display:inline-block;width:120px;color:#6B7280'>{label}</span>"
        f"{value_html}</div>"
    )

def _where_row(a1: str, a2: str, a3: str, spec: str) -> str:
    return (
        "<div style='margin:.35rem 0 .5rem 0'>"
        f"{_line('A1', _pill(a1))}"
        f"{_line('A2', _pill(a2))}"
        f"{_line('A3', _pill(a3))}"
        f"{_line('Specific', _pill(spec, 'warn'))}"
        "</div>"
    )

def _yesno_badge(needed: bool, unknown=False, text_yes="Required", text_no="Not required"):
    if unknown:
        return _pill("Unknown", "grey")
    return _pill(text_yes, "bad") if needed else _pill(text_no, "ok")

def render_compliance_panels(row: pd.Series):
    # Parse values
    def to_int(x):
        try:
            return int(x)
        except Exception:
            return None

    weight = to_int(row.get("mtom_g_nominal", None))
    has_cam = str(row.get("has_camera", "")).strip().lower() == "yes"
    rid = (row.get("remote_id_builtin", "") or "unknown").strip().lower()
    geo = (row.get("geo_awareness", "") or "unknown").strip().lower()

    # Helper: simple “where can I fly” summaries
    def where_current():
        if weight is not None and weight < 250 and has_cam:
            return _where_row("Yes (close)", "No", "Yes (far)", "If needed")
        elif weight is not None and weight <= 900:
            return _where_row("No", "Yes (with proof)", "Yes", "If needed")
        else:
            return _where_row("No", "No", "Yes (far)", "Likely")

    def where_2026():
        if weight and weight < 250:
            return _where_row("Yes (close)", "No", "Yes (far)", "If needed")
        elif weight and weight <= 900:
            return _where_row("No", "Yes (with proof)", "Yes", "If needed")
        else:
            return _where_row("No", "No", "Yes (far)", "Likely")

    def where_2028():
        if weight and weight < 250:
            return _where_row("Yes (close)", "No", "Yes (far)", "If needed")
        elif weight and weight <= 900:
            return _where_row("No", "Yes (with proof)", "Yes", "If needed")
        else:
            return _where_row("No", "No", "Yes (far)", "Likely")

    # Flyer ID rules
    flyer_now   = has_cam or (weight is not None and weight >= 250)  # pragmatic: camera → yes
    flyer_26_28 = has_cam and (weight is not None and weight >= 100)

    # Operator ID rules (camera generally => yes)
    oper_now = has_cam
    oper_26  = has_cam
    oper_28  = has_cam

    # Remote ID & Geo awareness rules per era
    rid_now  = (rid == "yes")  # some newer models yes; else unknown
    rid_26   = (rid == "yes") or (has_cam and (weight is not None and weight >= 100))
    rid_28   = has_cam and (weight is not None and weight >= 100)

    geo_now  = (geo == "yes")  # if firmware supports
    geo_26   = (geo == "yes")  # UK1–3 need it; keep as product capability gate
    geo_28   = has_cam and (weight is not None and weight >= 100)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("### Current", unsafe_allow_html=True)
        st.markdown(where_current(), unsafe_allow_html=True)
        st.markdown(
            _line("Operator ID", _yesno_badge(oper_now)) +
            _line("Flyer ID",     _yesno_badge(flyer_now)) +
            _line("Remote ID",    _yesno_badge(rid_now, unknown=(rid == "unknown"))) +
            _line("Geo-awareness",_yesno_badge(geo_now, unknown=(geo == "unknown"))),
            unsafe_allow_html=True
        )

    with c2:
        st.markdown("### 2026", unsafe_allow_html=True)
        st.markdown(where_2026(), unsafe_allow_html=True)
        st.markdown(
            _line("Operator ID", _yesno_badge(oper_26)) +
            _line("Flyer ID",     _yesno_badge(flyer_26_28)) +
            _line("Remote ID",    _yesno_badge(rid_26)) +
            _line("Geo-awareness",_yesno_badge(geo_26, unknown=(geo == "unknown"))),
            unsafe_allow_html=True
        )

    with c3:
        st.markdown("### 2028 (planned)", unsafe_allow_html=True)
        st.markdown(where_2028(), unsafe_allow_html=True)
        st.markdown(
            _line("Operator ID", _yesno_badge(oper_28)) +
            _line("Flyer ID",     _yesno_badge(flyer_26_28)) +
            _line("Remote ID",    _yesno_badge(rid_28)) +
            _line("Geo-awareness",_yesno_badge(geo_28)),
            unsafe_allow_html=True
        )

# ---------- Screens ----------
if not segment:
    # Stage 1 — choose group (horizontal)
    items = []
    for seg in taxonomy["segments"]:
        img = SEGMENT_HERO.get(seg["key"], "")
        items.append(card_link(f"segment={seg['key']}", seg["label"], img_url=img))
    render_row("Choose your drone category", items)

elif not series:
    # Stage 2 — choose series (horizontal, random image from that series only)
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    items = []
    for s in series_defs_for(segment):
        rnd_img = random_image_for_series(segment, s["key"])
        items.append(card_link(f"segment={segment}&series={s['key']}",
                               f"{s['label']}", img_url=rnd_img))
    render_row(f"Choose a series ({seg_label})", items)

else:
    # Stage 3
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    ser_label = next(s["label"] for s in series_defs_for(segment) if s["key"] == series)

    # If a model is selected, show sidebar + MAIN BODY 3 columns
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

            # Thumbnail + caption
            img_url = resolve_img(row.get("image_url", ""))
            if img_url:
                st.sidebar.image(img_url, use_container_width=True, caption=row.get("marketing_name", ""))

            # EU/UK flags on separate lines
            eu = (row.get("eu_class_marking") or "unknown")
            uk = (row.get("uk_class_marking") or "unknown")
            st.sidebar.markdown(
                f"<div class='flag-row'><img src='{EU_FLAG}' alt='EU flag'/> <span>EU: <b>{eu}</b></span></div>",
                unsafe_allow_html=True
            )
            st.sidebar.markdown(
                f"<div class='flag-row'><img src='{UK_FLAG}' alt='UK flag'/> <span>UK: <b>{uk}</b></span></div>",
                unsafe_allow_html=True
            )

            # Key specs (kept lean)
            st.sidebar.markdown("<div class='sidebar-title'>Key specs</div>", unsafe_allow_html=True)

            mtow_txt = "—"
            try:
                mtow_val = int(row.get("mtom_g_nominal", "") or 0)
                if mtow_val > 0:
                    mtow_txt = f"{mtow_val} g"
            except Exception:
                pass

            st.sidebar.markdown(
                _line("Model", f"<span class='small'>{row.get('marketing_name','')}</span>") +
                _line("MTOW", f"<span class='small'>{mtow_txt}</span>") +
                _line("Remote ID", f"<span class='small'>{(row.get('remote_id_builtin') or 'unknown')}</span>") +
                _line("Geo-awareness", f"<span class='small'>{(row.get('geo_awareness') or 'unknown')}</span>") +
                _line("Released", f"<span class='small'>{row.get('year_released','')}</span>"),
                unsafe_allow_html=True
            )

            # MAIN BODY: 3-column compliance comparator
            render_compliance_panels(row)

        else:
            model = None  # invalid model key, fall back to grid

    # If no model selected, show the model grid (two rows)
    if not model:
        models = models_for(segment, series)
        items = []
        for _, r in models.iterrows():
            # Sub info: EU/UK class + year
            eu_c = (r.get("eu_class_marking") or "").strip()
            uk_c = (r.get("uk_class_marking") or "").strip()
            year = str(r.get("year_released") or "").strip()
            parts = []
            if eu_c or uk_c:
                eu_show = eu_c if eu_c else "—"
                uk_show = uk_c if uk_c else "—"
                parts.append(f"Class: EU {eu_show} • UK {uk_show}")
            if year:
                parts.append(f"Released: {year}")
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
