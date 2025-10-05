# dronify.py — stage1/2/3 app with compliance columns (NOW / 2026 / 2028 planned)
# - Random series thumbnail for Stage 2
# - Stage 3 sidebar with flags + image + key specs
# - Three compliance columns with bricks (A1, A2, A3, Specific) and TOAL/separation logic
# - Badges reflect tech from YAML and credentials from sidebar
# - Fix: render A2 cards with unsafe_allow_html=True (no raw HTML)
# - Tight sidebar spacing and legend pinned to the bottom

import re
import random
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

# -------------- Page --------------
st.set_page_config(page_title="Dronify", layout="wide")

# -------------- Paths --------------
DATASET_PATH = Path("dji_drones_v3.yaml")
TAXONOMY_PATH = Path("taxonomy.yaml")

RAW_BASE = "https://raw.githubusercontent.com/JonathanGreen79/dronify/main/images/"

# -------------- Data loaders --------------
def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@st.cache_data
def load_data():
    dataset = load_yaml(DATASET_PATH)
    taxonomy = load_yaml(TAXONOMY_PATH)
    df = pd.DataFrame(dataset["data"])

    for col in (
        "image_url", "segment", "series", "class_marking", "weight_band",
        "marketing_name", "mtom_g_nominal", "eu_class_marking",
        "uk_class_marking", "remote_id_builtin", "year_released", "notes",
        "operator_id_required", "has_camera", "geo_awareness"
    ):
        if col not in df.columns:
            df[col] = ""

    df["segment_norm"] = df["segment"].astype(str).str.strip().str.lower()
    df["series_norm"] = df["series"].astype(str).str.strip().str.lower()
    return df, taxonomy

df, taxonomy = load_data()

# -------------- Query params --------------
def get_qp():
    try:
        return dict(st.query_params)  # Streamlit ≥1.32
    except Exception:
        return {
            k: (v[0] if isinstance(v, list) else v)
            for k, v in st.experimental_get_query_params().items()
        }

qp = get_qp()
segment = qp.get("segment")
series = qp.get("series")
model = qp.get("model")

# -------------- Utilities --------------
def resolve_img(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    low = url.lower()
    if low.startswith(("http://", "https://", "data:")):
        return url
    if low.startswith("images/"):
        return RAW_BASE + url.split("/", 1)[1]
    # bare filename or /images fixups
    return RAW_BASE + url.lstrip("/")

SEGMENT_HERO = {
    "consumer": resolve_img("images/consumer.jpg"),
    "pro": resolve_img("images/professional.jpg"),
    "enterprise": resolve_img("images/enterprise.jpg"),
}

def series_defs_for(segment_key: str):
    seg = next(s for s in taxonomy["segments"] if s["key"] == segment_key)
    present = set(df.loc[df["segment_norm"] == segment_key, "series_norm"].dropna())
    out = []
    for s in seg["series"]:
        if s["key"] in present:
            out.append(s)
    return out

def pad_digits_for_natural(series: pd.Series, width: int = 6) -> pd.Series:
    s = series.astype(str).str.lower()
    return s.str.replace(r"\d+", lambda m: f"{int(m.group(0)):0{width}d}", regex=True)

def models_for(segment_key: str, series_key: str):
    subset = df[(df["segment_norm"] == segment_key) & (df["series_norm"] == series_key)].copy()
    subset["series_key"] = pad_digits_for_natural(subset["series"])
    subset["name_key"] = pad_digits_for_natural(subset["marketing_name"])
    subset = subset.sort_values(
        by=["series_key", "name_key", "marketing_name"],
        kind="stable", ignore_index=True
    )
    return subset.drop(columns=["series_key", "name_key"])

def random_image_for_series(segment_key: str, series_key: str) -> str:
    subset = df[
        (df["segment_norm"] == segment_key) &
        (df["series_norm"] == series_key) &
        (df["image_url"].astype(str).str.strip() != "")
    ]
    if subset.empty:
        return SEGMENT_HERO.get(segment_key, "")
    raw = str(subset.sample(1)["image_url"].iloc[0])
    return resolve_img(raw)

# -------------- CSS --------------
st.markdown("""
<style>
.block-container { padding-top: 0.8rem; }

/* Shared card look */
.card {
  width: 260px; height: 240px;
  border: 1px solid #E5E7EB; border-radius: 14px; background: #fff;
  text-decoration: none !important; color: #111827 !important;
  display: block; padding: 12px;
  transition: box-shadow .15s ease, transform .15s ease, border-color .15s ease;
  cursor: pointer;
}
.card:hover { border-color: #D1D5DB; box-shadow: 0 6px 18px rgba(0,0,0,.08); transform: translateY(-2px); }
.img { width: 100%; height: 150px; border-radius: 10px; background: #F3F4F6; overflow: hidden; display:flex; align-items:center; justify-content:center; }
.img > img { width: 100%; height: 100%; object-fit: cover; }
.title { margin-top: 10px; text-align: center; font-weight: 700; font-size: 0.98rem; }
.sub { margin-top: 4px; text-align: center; font-size: .8rem; color: #6B7280; }
.strip { display:flex; flex-wrap:nowrap; gap:14px; overflow-x:auto; padding:8px 2px; margin:0; }
.strip2 { display:grid; grid-auto-flow:column; grid-auto-columns:260px; grid-template-rows:repeat(2,1fr); gap:14px; overflow-x:auto; padding:8px 2px; margin:0; }
.h1 { font-weight: 800; font-size: 1.2rem; color: #1F2937; margin: 8px 0 12px 0; }

/* Sidebar tweaks */
section[data-testid="stSidebar"] .block-container { padding-top: .5rem; }
.sidebar-title { font-weight:800; font-size:1.05rem; margin:.4rem 0 .2rem; }
.sidebar-kv { margin:.22rem 0; color:#374151; font-size:.92rem; }
.badge { display:inline-block; padding:3px 8px; border-radius:999px; background:#EEF2FF; color:#3730A3; font-weight:600; font-size:.78rem; margin-right:.35rem; }
.badge-red { background:#FEE2E2; color:#991B1B; }
.badge-green { background:#DCFCE7; color:#14532D; }
.badge-blue { background:#DBEAFE; color:#1E40AF; }
.small { font-size:.85em; color:#374151; }

/* Compliance grid */
.hdr { font-weight:800; font-size:1.35rem; margin: 6px 0 18px; }
.colhead { font-weight:800; font-size:1.05rem; margin:.2rem 0 .6rem; color:#111827; }
.colrule { border-bottom:1px dashed #E5E7EB; margin: 6px 0 18px; }
.card-outer { border:1px solid #E5E7EB; border-radius:12px; padding:14px; margin-bottom:12px; }
.badge-allowed { background:#DCFCE7; color:#14532D; border-radius:999px; padding:4px 10px; font-weight:700; font-size:.8rem; }
.badge-possible { background:#DBEAFE; color:#1E40AF; border-radius:999px; padding:4px 10px; font-weight:700; font-size:.8rem; }
.badge-na { background:#F3F4F6; color:#6B7280; border-radius:999px; padding:4px 10px; font-weight:700; font-size:.8rem; }
.pill { display:inline-block; padding:4px 9px; border-radius:999px; font-weight:600; font-size:.78rem; margin: 6px 6px 0 0; }
.pill-ok { background:#E6F9ED; color:#166534; }
.pill-need { background:#FEE2E2; color:#7F1D1D; }
.pill-info { background:#F3F4F6; color:#475569; }
.card-allowed-bg { background: #F6FEF8; }
.card-possible-bg { background: #F5F8FE; }
.card-na-bg { background: #FAFAFB; }

/* Legend in sidebar */
.legend { margin-top: 14px; border-top:1px solid #E5E7EB; padding-top:10px; }
.legend .pill { margin: 6px 6px 0 0; }
</style>
""", unsafe_allow_html=True)

# -------------- Small HTML helpers --------------
def pill(label, kind="ok", title=""):
    cls = {"ok": "pill-ok", "need": "pill-need", "info": "pill-info"}[kind]
    t = f' title="{title}"' if title else ""
    return f"<span class='pill {cls}'{t}>{label}</span>"

def status_badge(kind, text=None):
    if kind == "allowed":
       return f"<span class='badge-allowed'>{text or 'Allowed'}</span>"
    if kind == "possible":
       return f"<span class='badge-possible'>{text or 'Possible (additional requirements)'}</span>"
    return f"<span class='badge-na'>{text or 'Not applicable'}</span>"

def wrap_card(title, desc, pills_html, state="possible"):
    bg = {"allowed":"card-allowed-bg", "possible":"card-possible-bg", "na":"card-na-bg"}[state]
    badge = status_badge(state, None)
    return f"""
    <div class="card-outer {bg}">
      <h4 class="colhead">{title} {badge}</h4>
      <div class="small">{desc}</div>
      <div class="pills">{pills_html}</div>
    </div>
    """

def show_html(html: str):
    # single place to render HTML (ensures A2 never shows raw HTML)
    st.markdown(html, unsafe_allow_html=True)

# -------------- Compliance engine (NOW/2026/2028) --------------
def has(val: str) -> bool:
    return str(val).strip().lower() in ("yes", "true", "1", "ok", "onboard")

def to_num(x):
    try:
        return int(float(str(x)))
    except Exception:
        return None

def compute_bricks(row: pd.Series, creds: dict, year: int):
    """
    Return HTML for A1, A2, A3, and Specific bricks based on:
    - Drone tech from YAML
    - User credentials (sidebar)
    - Year (now/2026/2028 for transitional rules)
    """
    eu = str(row.get("eu_class_marking", "")).strip().upper()
    uk = str(row.get("uk_class_marking", "")).strip().upper()
    mtom = to_num(row.get("mtom_g_nominal"))
    has_cam = has(row.get("has_camera"))
    rid_yes = has(row.get("remote_id_builtin"))
    geo_yes = has(row.get("geo_awareness"))

    # Credentials
    opid = creds["operator_id"]
    flyer = creds["flyer_id"]
    a1a3 = creds["a1a3"]
    a2cofc = creds["a2cofc"]
    gvc = creds["gvc"]
    oa  = creds["oa"]

    # -- A1 ------------------------------------------
    a1_desc = "Fly close to people; avoid assemblies/crowds. TOAL: sensible separation; follow local restrictions."
    a1_pills = []
    # Operator ID needed if camera present in UK (registration of operator)
    a1_pills.append(pill("Operator ID: Required", "need" if not opid else "ok",
                         "Required for all drones with a camera (registration of the operator)."))
    # Flyer ID needed for 100 g+ with camera (from 2026) and generally for Mini class already
    a1_pills.append(pill("Flyer ID: Required", "need" if not flyer else "ok",
                         "Pilot knowledge test (Flyer ID) is required for camera drones."))
    a1_pills.append(pill("Remote ID: OK" if rid_yes else "Remote ID: Required", "ok" if rid_yes else "need"))
    # A1/A3 training is optional for C0 / sub-250, but helpful. Mark as info.
    a1_pills.append(pill("A1/A3: Optional", "info"))
    # Geo
    a1_pills.append(pill("Geo-awareness: Onboard" if geo_yes else "Geo-awareness: Required", "ok" if geo_yes else "need"))

    # Allowed vs Possible: need Operator & Flyer & RID/Geo (if required)
    a1_state = "allowed" if (opid and flyer and (rid_yes or True) and (geo_yes or True)) else "possible"

    a1_html = wrap_card("A1 — Close to people", a1_desc, "".join(a1_pills), a1_state)

    # -- A2 ------------------------------------------
    # Rules: C2 only (≤4 kg). Transitional up to 2 kg until 1 Jan 2026 => 50 m
    # If not C2 and not transitional window -> NA
    a2_pills = []
    a2_desc = (
        "A2 mainly for C2 drones (sometimes C1 by nuance).<br>"
        "C2: 30 m from uninvolved people (5 m in low-speed)."
    )
    transitional_ok_now = (year < 2026)
    transitional_applicable = (mtom is not None and mtom <= 2000 and transitional_ok_now)

    is_c2 = (eu == "C2" or uk == "UK2")
    if not is_c2 and not transitional_applicable:
        # Not applicable brick
        a2_html = wrap_card("A2 — Close with A2 CofC", a2_desc, 
                            pill("A2 CofC: N/A", "info") + pill("Remote ID: OK" if rid_yes else "Remote ID: Required", "ok" if rid_yes else "need") +
                            pill("Geo-awareness: Onboard" if geo_yes else "Geo-awareness: Required", "ok" if geo_yes else "need"),
                            "na")
    else:
        # Credentials for A2
        a2_pills.append(pill("Operator ID: Required", "need" if not opid else "ok"))
        a2_pills.append(pill("Flyer ID: Required", "need" if not flyer else "ok"))
        a2_pills.append(pill("A2 CofC: Required", "need" if not a2cofc else "ok"))
        # Tech
        a2_pills.append(pill("Remote ID: OK" if rid_yes else "Remote ID: Required", "ok" if rid_yes else "need"))
        a2_pills.append(pill("Geo-awareness: Onboard" if geo_yes else "Geo-awareness: Required", "ok" if geo_yes else "need"))

        # TOAL/separation specifics
        if is_c2:
            a2_desc += " TOAL: keep sensible separation; crowds prohibited."
        else:
            a2_desc += " Transitional (≤2 kg) until 1 Jan 2026: keep ≥50 m from uninvolved people."

        a2_state = "allowed" if (opid and flyer and a2cofc and rid_yes and geo_yes) else "possible"
        a2_html = wrap_card("A2 — Close with A2 CofC", a2_desc, "".join(a2_pills), a2_state)

    # -- A3 ------------------------------------------
    a3_desc = ("Keep ≥ 150 m from residential/commercial/industrial/recreational areas. "
               "TOAL: well away from uninvolved people and built-up areas. Maintain ≥ 50 m from uninvolved people.")
    a3_pills = [
        pill("Operator ID: Required", "need" if not opid else "ok"),
        pill("Flyer ID: Required", "need" if not flyer else "ok"),
        pill("Remote ID: OK" if rid_yes else "Remote ID: Required", "ok" if rid_yes else "need"),
        pill("Geo-awareness: Onboard" if geo_yes else "Geo-awareness: Required", "ok" if geo_yes else "need"),
    ]
    a3_state = "allowed" if (opid and flyer and (rid_yes or True) and (geo_yes or True)) else "possible"
    a3_html = wrap_card("A3 — Far from people", a3_desc, "".join(a3_pills), a3_state)

    # -- Specific (PDRA-01) ------------------------------------------
    spec_desc = ("Risk-assessed operations per OA; distances per ops manual. "
                 "TOAL & mitigations defined by your approved procedures. "
                 "PDRA-01: ≥50 m in flight; TOAL may be reduced to 30 m. "
                 "Assemblies of people: maintain ≥50 m; overflight prohibited.")
    spec_pills = [
        pill("Operator ID: Required", "need" if not opid else "ok"),
        pill("Flyer ID: Required", "need" if not flyer else "ok"),
        pill("GVC: Required", "need" if not gvc else "ok"),
        pill("OA: Required", "need" if not oa else "ok"),
        pill("Remote ID: OK" if rid_yes else "Remote ID: Required", "ok" if rid_yes else "need"),
        pill("Geo-awareness: Onboard" if geo_yes else "Geo-awareness: Required", "ok" if geo_yes else "need"),
    ]
    # Allowed only when both GVC & OA present (plus base IDs)
    spec_state = "allowed" if (opid and flyer and gvc and oa and (rid_yes or True) and (geo_yes or True)) else "possible"
    spec_html = wrap_card("Specific — OA / GVC", spec_desc, "".join(spec_pills), spec_state)

    return a1_html, a2_html, a3_html, spec_html

# -------------- Simple cards for stage-1 & stage-2 --------------
def card_link(qs: str, title: str, sub: str = "", img_url: str = "") -> str:
    img = f"<div class='img'><img src='{img_url}' alt=''/></div>" if img_url else "<div class='img'></div>"
    sub_html = f"<div class='sub'>{sub}</div>" if sub else ""
    return f"<a class='card' href='?{qs}' target='_self' rel='noopener'>{img}<div class='title'>{title}</div>{sub_html}</a>"

def render_row(title: str, items: list[str]):
    st.markdown(f"<div class='h1'>{title}</div><div class='strip'>{''.join(items)}</div>", unsafe_allow_html=True)

def render_two_rows(title: str, items: list[str]):
    st.markdown(f"<div class='h1'>{title}</div><div class='strip2'>{''.join(items)}</div>", unsafe_allow_html=True)

# -------------- Screens --------------
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
    # Stage 3
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    ser_label = next(s["label"] for s in series_defs_for(segment) if s["key"] == series)

    # If a model is selected, show ONLY a sidebar with details; keep body for compliance
    sel = None
    if model:
        sel = df[df["model_key"] == model]

    # Sidebar for selected model, plus credentials inputs
    if sel is not None and not sel.empty:
        row = sel.iloc[0]
        back_qs = f"segment={segment}&series={series}"

        # ---- Sidebar header / back link
        st.sidebar.markdown(f"<a class='small' href='?{back_qs}' target='_self'>← Back to models</a>", unsafe_allow_html=True)

        # ---- Image
        st.sidebar.image(resolve_img(row.get("image_url", "")), use_container_width=True, caption=row.get("marketing_name", ""))

        # ---- EU/UK flags (20px)
        eu_flag = resolve_img("images/eu.png")
        uk_flag = resolve_img("images/uk.png")
        eu = row.get("eu_class_marking", "unknown") or "unknown"
        uk = row.get("uk_class_marking", "unknown") or "unknown"
        st.sidebar.markdown(
            f"<img src='{eu_flag}' width='20' style='vertical-align:middle;margin-right:6px'/> <b>EU:</b> {eu}",
            unsafe_allow_html=True
        )
        st.sidebar.markdown(
            f"<img src='{uk_flag}' width='20' style='vertical-align:middle;margin-right:6px'/> <b>UK:</b> {uk}",
            unsafe_allow_html=True
        )

        # ---- Key specs
        st.sidebar.markdown("<div class='sidebar-title'>Key specs</div>", unsafe_allow_html=True)
        st.sidebar.markdown(f"<div class='sidebar-kv'><b>Model</b>: {row.get('marketing_name','—')}</div>", unsafe_allow_html=True)
        st.sidebar.markdown(f"<div class='sidebar-kv'><b>MTOW</b>: {row.get('mtom_g_nominal','—')} g</div>", unsafe_allow_html=True)
        st.sidebar.markdown(f"<div class='sidebar-kv'><b>Remote ID</b>: {'yes' if has(row.get('remote_id_builtin')) else 'unknown'}</div>", unsafe_allow_html=True)
        st.sidebar.markdown(f"<div class='sidebar-kv'><b>Geo-awareness</b>: {'yes' if has(row.get('geo_awareness')) else 'unknown'}</div>", unsafe_allow_html=True)
        st.sidebar.markdown(f"<div class='sidebar-kv'><b>Released</b>: {row.get('year_released', '—')}</div>", unsafe_allow_html=True)

        # ---- Credentials (compact)
        st.sidebar.markdown("<br><div class='sidebar-title'>Your credentials</div>", unsafe_allow_html=True)
        operator_id = st.sidebar.checkbox("Operator ID", value=False)
        flyer_id    = st.sidebar.checkbox("Flyer ID (basic test)", value=False)
        a1a3_train  = st.sidebar.checkbox("A1/A3 training (optional)", value=False)
        a2_cofc     = st.sidebar.checkbox("A2 CofC", value=False)
        gvc         = st.sidebar.checkbox("GVC", value=False)
        oa          = st.sidebar.checkbox("OA (Operational Authorisation)", value=False)

        # ---- Legend at bottom
        st.sidebar.markdown(
            "<div class='legend'><div class='sidebar-title'>Legend</div>"
            + status_badge("allowed") + " "
            + status_badge("possible", "Possible (additional requirements)") + " "
            + status_badge("na") + "<br>"
            + pill("✓ Requirement met", "ok") + pill("✕ Requirement missing", "need") + pill("Info / optional", "info")
            + "</div>",
            unsafe_allow_html=True
        )

        # Body content: NOW / 2026 / 2028 columns
        st.markdown("<div class='hdr'>NOW</div>", unsafe_allow_html=True)
        col_now_a1, col_now_a2, col_now_a3 = st.columns(3)
        st.markdown("<div class='colrule'></div>", unsafe_allow_html=True)
        st.markdown("<div class='hdr'>2026</div>", unsafe_allow_html=True)
        col_26_a1, col_26_a2, col_26_a3 = st.columns(3)
        st.markdown("<div class='colrule'></div>", unsafe_allow_html=True)
        st.markdown("<div class='hdr'>2028 (planned)</div>", unsafe_allow_html=True)
        col_28_a1, col_28_a2, col_28_a3 = st.columns(3)

        creds = {
            "operator_id": operator_id,
            "flyer_id": flyer_id,
            "a1a3": a1a3_train,
            "a2cofc": a2_cofc,
            "gvc": gvc,
            "oa": oa
        }

        # --- NOW
        a1_html, a2_html, a3_html, spec_html = compute_bricks(row, creds, 2025)
        with col_now_a1: show_html(a1_html); show_html(a2_html)
        with col_now_a2: show_html(a3_html)
        with col_now_a3: show_html(spec_html)

        # --- 2026
        a1_html, a2_html, a3_html, spec_html = compute_bricks(row, creds, 2026)
        with col_26_a1: show_html(a1_html); show_html(a2_html)
        with col_26_a2: show_html(a3_html)
        with col_26_a3: show_html(spec_html)

        # --- 2028 planned
        a1_html, a2_html, a3_html, spec_html = compute_bricks(row, creds, 2028)
        with col_28_a1: show_html(a1_html); show_html(a2_html)
        with col_28_a2: show_html(a3_html)
        with col_28_a3: show_html(spec_html)

    # If no model selected, show series grid
    if not model:
        models = models_for(segment, series)
        items = []
        for _, r in models.iterrows():
            parts = []
            eu_c = (r.get("eu_class_marking") or r.get("class_marking") or "").strip()
            uk_c = (r.get("uk_class_marking") or r.get("class_marking") or "").strip()
            if eu_c or uk_c:
                parts.append(f"Class: EU {eu_c or '—'} • UK {uk_c or '—'}")
            year_rel = r.get("year_released", "")
            if str(year_rel).strip():
                parts.append(f"Released: {year_rel}")
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
