import random
from pathlib import Path
import streamlit as st
import pandas as pd
import yaml

# ---------- App setup ----------
st.set_page_config(page_title="Dronify", layout="wide")

DATASET_PATH = Path("dji_drones_v3.yaml")
TAXONOMY_PATH = Path("taxonomy.yaml")

RAW_BASE = "https://raw.githubusercontent.com/JonathanGreen79/dronify/main/images/"

def _restart_app():
    try:
        st.query_params.clear()
    except Exception:
        st.experimental_set_query_params()
    st.session_state.clear()
    st.rerun()

# ---------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------
def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@st.cache_data(show_spinner=False)
def load_data():
    dataset = load_yaml(DATASET_PATH)
    taxonomy = load_yaml(TAXONOMY_PATH)
    df = pd.DataFrame(dataset["data"])

    needed = [
        "image_url", "segment", "series", "marketing_name", "model_key",
        "mtom_g_nominal", "eu_class_marking", "uk_class_marking",
        "has_camera", "geo_awareness", "remote_id_builtin", "year_released"
    ]
    for col in needed:
        if col not in df.columns:
            df[col] = ""

    df["segment_norm"] = df["segment"].astype(str).str.strip().str.lower()
    df["series_norm"]  = df["series"].astype(str).str.strip().str.lower()
    return df, taxonomy

def resolve_img(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    low = url.lower()
    if low.startswith(("http://", "https://", "data:")):
        return url
    if low.startswith("images/"):
        return RAW_BASE + url.split("/", 1)[1]
    return RAW_BASE + url.lstrip("/")

# ---------------------------------------------------------------------
# UI CSS
# ---------------------------------------------------------------------
st.markdown(
    """
<style>
.block-container { padding-top: .7rem; }

/* Landing cards & layout */
.h1 { font-weight: 800; font-size: 1.2rem; color: #1F2937; margin: 6px 0 12px 0; }
.hdr { font-weight: 800; font-size: 1.35rem; margin: 6px 0 12px; }

/* Sidebar (compact) */
section[data-testid="stSidebar"] .block-container { padding-top: .4rem; }
.sidebar-title { font-weight:800; font-size:1.02rem; margin:.6rem 0 .25rem; }
.sidebar-kv { margin:.18rem 0; color:#374151; font-size:.90rem; }
section[data-testid="stSidebar"] div[data-testid="stCheckbox"] { margin: 2px 0 !important; }
section[data-testid="stSidebar"] label p { font-size: .9rem; margin: 0; }

/* Badges & pills */
.badge      { display:inline-block; padding:4px 10px; border-radius:999px; font-weight:700; font-size:.8rem; }
.badge-allowed  { background:#DCFCE7; color:#14532D; }
.badge-possible { background:#DBEAFE; color:#1E40AF; }
.badge-na       { background:#F3F4F6; color:#6B7280; }
.badge-oagvc    { background:#FEF3C7; color:#92400E; }

.pill { display:inline-block; padding:4px 9px; border-radius:999px; font-weight:600; font-size:.78rem; margin: 6px 6px 0 0; }
.pill-ok   { background:#E6F9ED; color:#166534; }
.pill-need { background:#FEE2E2; color:#7F1D1D; }
.pill-info { background:#F3F4F6; color:#475569; }

/* Cards / bricks */
.card-outer { border:1px solid #E5E7EB; border-radius:12px; padding:14px; margin-bottom:12px; width:100%; display:flex; flex-direction:column; }
.card-allowed-bg  { background: #F6FEF8; }
.card-possible-bg { background: #F5F8FE; }
.card-na-bg       { background: #FAFAFB; }
.card-oagvc-bg    { background: #FFFBEB; }

.card-title { font-weight:800; font-size:1.02rem; }
.sep { height: 1px; background:#EEF2F7; margin:10px 0; }

/* Inline flag row */
.flagline { display:flex; align-items:center; gap: 8px; margin: 8px 0 6px; }
.flagline img { width: 20px; height: 14px; border-radius:2px; box-shadow:0 0 0 1px rgba(0,0,0,.06); }
.small { font-size:.85em; color:#374151; }

/* Grids */
.grid3 { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 16px; align-items: stretch; }
.grid3 > div { display:flex; }
.divided.grid3 > div:not(:first-child) { border-left: 1px solid #EDEFF3; padding-left: 12px; }

/* Legend */
.legend { margin-top: 8px; border-top:1px solid #E5E7EB; padding-top:6px; }
.legend .badge { margin-right:6px; }

/* Report page chips */
.cat-chip { display:inline-flex; align-items:center; gap:6px; padding:8px 10px; border:1px solid #E5E7EB;
            border-radius:12px; margin:6px 6px 0 0; background:#fff; font-weight:600; }
.cat-pill { display:inline-block; font-size:.7rem; padding:2px 6px; border-radius:999px; background:#EFF6FF; color:#1E3A8A; }
.report-head { font-weight:800; font-size:1.4rem; margin: 6px 0 6px; }
.count-bubble { display:inline-block; margin-left:8px; padding:2px 8px; border-radius:999px; background:#111827; color:#fff; font-size:.78rem; }
.report-hr { height:1px; background:#E5E7EB; margin:10px 0 8px; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# Query params
# ---------------------------------------------------------------------
def get_qp():
    try:
        return dict(st.query_params)
    except Exception:
        return {
            k: (v[0] if isinstance(v, list) else v)
            for k, v in st.experimental_get_query_params().items()
        }

qp = get_qp()
segment = qp.get("segment")
series  = qp.get("series")
model   = qp.get("model")
page    = qp.get("page")  # 'report' optionally

df, taxonomy = load_data()

# ---------------------------------------------------------------------
# Taxonomy helpers
# ---------------------------------------------------------------------
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

def random_image_for_series(segment_key: str, series_key: str) -> str:
    seg_l = str(segment_key).strip().lower()
    ser_l = str(series_key).strip().lower()
    subset = df[(df["segment_norm"] == seg_l) & (df["series_norm"] == ser_l)]
    subset = subset[subset["image_url"].astype(str).str.strip() != ""]
    if subset.empty:
        return ""
    raw = str(subset.sample(1)["image_url"].iloc[0])
    return resolve_img(raw)

def models_for(segment_key: str, series_key: str):
    seg_l = str(segment_key).strip().lower()
    ser_l = str(series_key).strip().lower()
    subset = df[(df["segment_norm"] == seg_l) & (df["series_norm"] == ser_l)].copy()
    subset["name_key"] = (
        subset["marketing_name"]
        .astype(str)
        .str.lower()
        .str.replace(r"\d+", lambda m: f"{int(m.group(0)):06d}", regex=True)
    )
    subset = subset.sort_values(
        by=["name_key", "marketing_name"], kind="stable", ignore_index=True
    )
    return subset.drop(columns=["name_key"])

# ---------------------------------------------------------------------
# Brick rendering bits
# ---------------------------------------------------------------------
def pill_ok(txt, title=None):
    t = f' title="{title}"' if title else ""
    return f"<span class='pill pill-ok'{t}>{txt}</span>"

def pill_need(txt, title=None):
    t = f' title="{title}"' if title else ""
    return f"<span class='pill pill-need'{t}>{txt}</span>"

def pill_info(txt, title=None):
    t = f' title="{title}"' if title else ""
    return f"<span class='pill pill-info'{t}>{txt}</span>"

def badge(txt, kind="possible"):
    cls = {
        "allowed": "badge badge-allowed",
        "possible": "badge badge-possible",
        "na": "badge badge-na",
        "oagvc": "badge badge-oagvc",
    }[kind]
    return f"<span class='{cls}'>{txt}</span>"

def card(title, status_badge, body_html, kind="possible"):
    bg = {
        "allowed": "card-allowed-bg",
        "possible": "card-possible-bg",
        "na": "card-na-bg",
        "oagvc": "card-oagvc-bg",
    }[kind]
    return f"""
<div class='card-outer {bg}'>
  <div class='card-title'>{title} {status_badge}</div>
  <div class='sep'></div>
  <div>{body_html}</div>
</div>
"""

def yesish(val: str) -> bool:
    return str(val).strip().lower() in {"yes", "true", "1", "ok"}

# ---------------------------------------------------------------------
# Regulatory helpers + rules text
# ---------------------------------------------------------------------
def _lc(x):
    return str(x or "").strip().lower()

def _parse_mtow_g(row) -> float | None:
    raw = row.get("mtom_g_nominal", "")
    if pd.isna(raw):
        return None
    s = str(raw)
    try:
        return float(s)
    except Exception:
        import re
        m = re.search(r"([\d\.]+)", s)
        return float(m.group(1)) if m else None

def rule_text_a1():
    return (
        "Fly close to people; avoid assemblies/crowds. TOAL: sensible separation; "
        "follow local restrictions."
    )

def rule_text_a2(year: int):
    if year < 2026:
        return (
            "A2 mainly for C2 drones (sometimes C1 by nuance). Transitional (≤2 kg) "
            "until Jan 2026: keep ≥50 m from uninvolved people."
        )
    return "C2/UK2: keep 30 m from uninvolved people (5 m in low-speed)."

def rule_text_a3():
    return (
        "Keep ≥150 m from residential/commercial/industrial/recreational areas. "
        "TOAL: well away from uninvolved people and built-up areas."
    )

def rule_text_specific():
    return (
        "Risk-assessed operations per OA; distances per ops manual. TOAL & "
        "mitigations defined by your approved procedures (e.g., PDRA-01: ≥50 m in "
        "flight; TOAL may be reduced to 30 m; no overflight of assemblies)."
    )

def eligible_open_subcats(row: pd.Series, year: int, jurisdiction: str = "UK") -> dict:
    eu = _lc(row.get("eu_class_marking", ""))
    uk = _lc(row.get("uk_class_marking", ""))
    mtow = _parse_mtow_g(row)
    is_classed = eu in {"c0","c1","c2","c3","c4"} or uk in {"uk0","uk1","uk2","uk3","uk4"}
    bridge = (jurisdiction.upper() == "UK" and year <= 2027)

    if mtow is not None and mtow < 100:
        return {"a1": True, "a2": False, "a3": True}

    a1 = False
    if mtow is not None and mtow <= 250:
        a1 = True
    if uk in {"uk0", "uk1"}:
        a1 = True
    if bridge and year >= 2026 and eu in {"c0","c1"}:
        a1 = True

    a2 = False
    if uk == "uk2" or (bridge and eu == "c2"):
        if mtow is None or mtow <= 4000:
            a2 = True
    if (jurisdiction.upper() == "UK" and year < 2026 and not is_classed
        and mtow is not None and mtow <= 2000):
        a2 = True

    a3 = False
    if mtow is not None and mtow < 25000:
        a3 = True
    if uk in {"uk3", "uk4"} or (bridge and eu in {"c2", "c3", "c4"}):
        a3 = True

    return {"a1": a1, "a2": a2, "a3": a3}

def rid_is_required(row: pd.Series, year: int, jurisdiction: str = "UK") -> bool:
    has_cam = yesish(row.get("has_camera", "yes"))
    eu = _lc(row.get("eu_class_marking", ""))
    uk = _lc(row.get("uk_class_marking", ""))
    mtow = _parse_mtow_g(row) or 0.0

    if year >= 2028 and has_cam and mtow > 100:
        return True
    if 2026 <= year <= 2027:
        if uk in {"uk1","uk2","uk3","uk5","uk6"} or eu in {"c1","c2","c3"}:
            return True
    return False

def rid_pill(row: pd.Series, year: int, rid_ok: bool, jurisdiction: str = "UK") -> str:
    required = rid_is_required(row, year, jurisdiction)
    if required:
        return pill_ok("Remote ID: Required (Onboard)") if rid_ok else pill_need("Remote ID: Required")
    else:
        return pill_ok("Remote ID: Not required (Onboard)") if rid_ok else pill_info("Remote ID: Not required")

def pills_all_ok(pills: list[str]) -> bool:
    return all("pill-need" not in p for p in pills)

# --- kinds only (for report & counting) --------------------------------
def _kinds_for(row: pd.Series, creds: dict, year: int, jurisdiction: str = "UK") -> dict:
    """Return {'A1': kind, 'A2': kind, 'A3': kind, 'Specific': kind} where kind is 'allowed'|'possible'|'na'|'oagvc'."""
    has_cam = yesish(row.get("has_camera", "yes"))
    geo_ok  = yesish(row.get("geo_awareness", "unknown"))
    rid_ok  = yesish(row.get("remote_id_builtin", "unknown"))
    elig    = eligible_open_subcats(row, year, jurisdiction)

    have_op, have_fl = creds.get("op", False), creds.get("flyer", False)
    have_a2, have_gvc, have_oa = creds.get("a2", False), creds.get("gvc", False), creds.get("oa", False)
    mtow = _parse_mtow_g(row) or 0.0
    sub100 = mtow < 100

    kinds = {}

    # A1
    if not elig["a1"]:
        kinds["A1"] = "na"
    else:
        pills = []
        if has_cam and not sub100 and not have_op: pills.append(pill_need("x"))
        if has_cam and not sub100 and not have_fl: pills.append(pill_need("x"))
        pills.append(rid_pill(row, year, rid_ok, jurisdiction))
        if not geo_ok: pills.append(pill_need("x"))
        kinds["A1"] = "allowed" if pills_all_ok(pills) else "possible"

    # A2
    if not elig["a2"]:
        kinds["A2"] = "na"
    else:
        pills = []
        if not have_op: pills.append(pill_need("x"))
        if not have_fl: pills.append(pill_need("x"))
        if not have_a2: pills.append(pill_need("x"))
        pills.append(rid_pill(row, year, rid_ok, jurisdiction))
        if not geo_ok: pills.append(pill_need("x"))
        kinds["A2"] = "allowed" if pills_all_ok(pills) else "possible"

    # A3
    if not elig["a3"]:
        kinds["A3"] = "na"
    else:
        pills = []
        if not have_op: pills.append(pill_need("x"))
        if not have_fl: pills.append(pill_need("x"))
        pills.append(rid_pill(row, year, rid_ok, jurisdiction))
        if not geo_ok: pills.append(pill_need("x"))
        kinds["A3"] = "allowed" if pills_all_ok(pills) else "possible"

    # Specific
    pills = []
    if not have_op: pills.append(pill_need("x"))
    if not have_fl: pills.append(pill_need("x"))
    if not have_gvc: pills.append(pill_need("x"))
    if not have_oa: pills.append(pill_need("x"))
    pills.append(rid_pill(row, year, rid_ok, jurisdiction))
    if not geo_ok: pills.append(pill_need("x"))
    kinds["Specific"] = "allowed" if pills_all_ok(pills) else "oagvc"

    return kinds

# --- HTML bricks (product page) ----------------------------------------
def compute_bricks(row: pd.Series, creds: dict, year: int, jurisdiction: str = "UK"):
    has_cam = yesish(row.get("has_camera", "yes"))
    geo_ok  = yesish(row.get("geo_awareness", "unknown"))
    rid_ok  = yesish(row.get("remote_id_builtin", "unknown"))

    elig = eligible_open_subcats(row, year, jurisdiction)

    have_op   = creds.get("op", False)
    have_fl   = creds.get("flyer", False)
    have_a2   = creds.get("a2", False)
    have_gvc  = creds.get("gvc", False)
    have_oa   = creds.get("oa", False)

    mtow = _parse_mtow_g(row) or 0.0
    sub100 = mtow < 100

    # A1
    if not elig["a1"]:
        html_a1 = card(
            "A1 — Close to people",
            badge("Not applicable", "na"),
            f"<div class='small'>{rule_text_a1()}</div>"
            f"<div>{pill_info('Not eligible by class/weight')}</div>",
            "na",
        )
    else:
        pills_a1 = []
        if has_cam and not sub100 and not have_op:
            pills_a1.append(pill_need("Operator ID: Required"))
        else:
            pills_a1.append(pill_ok("Operator ID: OK" if not sub100 else "Operator ID: Not required"))
        if has_cam and not sub100 and not have_fl:
            pills_a1.append(pill_need("Flyer ID: Required"))
        else:
            pills_a1.append(pill_ok("Flyer ID: OK" if not sub100 else "Flyer ID: Not required"))
        pills_a1.append(rid_pill(row, year, rid_ok, jurisdiction))
        pills_a1.append(pill_ok("Geo-awareness: Onboard") if geo_ok else pill_need("Geo-awareness: Required"))

        a1_kind   = "allowed" if pills_all_ok(pills_a1) else "possible"
        a1_badge  = badge("Allowed" if a1_kind == "allowed" else "Possible (additional requirements)", a1_kind)
        a1_body   = f"<div class='small'>{rule_text_a1()}</div><div>{''.join(pills_a1)}</div>"
        html_a1   = card("A1 — Close to people", a1_badge, a1_body, a1_kind)

    # A2
    if not elig["a2"]:
        html_a2 = card(
            "A2 — Close with A2 CofC",
            badge("Not applicable", "na"),
            f"<div class='small'>{rule_text_a2(year)}</div>"
            f"<div>{pill_info('Not eligible by class/weight for A2')}</div>",
            "na",
        )
    else:
        pills_a2 = []
        pills_a2.append(pill_need("Operator ID: Required") if not have_op else pill_ok("Operator ID: OK"))
        pills_a2.append(pill_need("Flyer ID: Required") if not have_fl else pill_ok("Flyer ID: OK"))
        pills_a2.append(pill_need("A2 CofC: Required") if not have_a2 else pill_ok("A2 CofC: OK"))
        pills_a2.append(rid_pill(row, year, rid_ok, jurisdiction))
        pills_a2.append(pill_ok("Geo-awareness: Onboard") if geo_ok else pill_need("Geo-awareness: Required"))

        a2_kind   = "allowed" if pills_all_ok(pills_a2) else "possible"
        a2_badge  = badge("Allowed" if a2_kind == "allowed" else "Possible (additional requirements)", a2_kind)
        a2_body   = f"<div class='small'>{rule_text_a2(year)}</div><div>{''.join(pills_a2)}</div>"
        html_a2   = card("A2 — Close with A2 CofC", a2_badge, a2_body, a2_kind)

    # A3
    if not elig["a3"]:
        html_a3 = card(
            "A3 — Far from people",
            badge("Not applicable", "na"),
            f"<div class='small'>{rule_text_a3()}</div>"
            f"<div>{pill_info('Not eligible by class/weight for A3')}</div>",
            "na",
        )
    else:
        pills_a3 = []
        pills_a3.append(pill_need("Operator ID: Required") if not have_op else pill_ok("Operator ID: OK"))
        pills_a3.append(pill_need("Flyer ID: Required") if not have_fl else pill_ok("Flyer ID: OK"))
        pills_a3.append(rid_pill(row, year, rid_ok, jurisdiction))
        pills_a3.append(pill_ok("Geo-awareness: Onboard") if geo_ok else pill_need("Geo-awareness: Required"))

        a3_kind   = "allowed" if pills_all_ok(pills_a3) else "possible"
        a3_badge  = badge("Allowed" if a3_kind == "allowed" else "Possible (additional requirements)", a3_kind)
        a3_body   = f"<div class='small'>{rule_text_a3()}</div><div>{''.join(pills_a3)}</div>"
        html_a3   = card("A3 — Far from people", a3_badge, a3_body, a3_kind)

    # Specific
    pills_sp = []
    pills_sp.append(pill_need("Operator ID: Required") if not have_op else pill_ok("Operator ID: OK"))
    pills_sp.append(pill_need("Flyer ID: Required")   if not have_fl else pill_ok("Flyer ID: OK"))
    pills_sp.append(pill_need("GVC: Required")        if not have_gvc else pill_ok("GVC: OK"))
    pills_sp.append(pill_need("OA: Required")         if not have_oa else pill_ok("OA: OK"))
    pills_sp.append(rid_pill(row, year, rid_ok, jurisdiction))
    pills_sp.append(pill_ok("Geo-awareness: Onboard") if geo_ok else pill_need("Geo-awareness: Required"))

    sp_kind   = "allowed" if pills_all_ok(pills_sp) else "oagvc"
    sp_lbl    = "Allowed" if sp_kind == "allowed" else "Available via OA/GVC"
    sp_badge  = badge(sp_lbl, "allowed" if sp_kind == "allowed" else "oagvc")
    sp_body   = f"<div class='small'>{rule_text_specific()}</div><div>{''.join(pills_sp)}</div>"
    html_sp   = card("Specific — OA / GVC", sp_badge, sp_body, sp_kind)

    return html_a1, html_a2, html_a3, html_sp

# ---------------------------------------------------------------------
# Landing/series helpers
# ---------------------------------------------------------------------
SEGMENT_HERO = {
    "consumer": resolve_img("images/consumer.jpg"),
    "pro": resolve_img("images/professional.jpg"),
    "enterprise": resolve_img("images/enterprise.jpg"),
}
WHAT_IMG = resolve_img("images/mini_mavic.jpg")  # any neutral image you have

def card_link(qs: str, title: str, sub: str = "", img_url: str = "") -> str:
    img = (
        f"<div style='width:260px;height:150px;border-radius:10px;background:#F3F4F6;overflow:hidden;display:flex;align-items:center;justify-content:center'><img src='{img_url}' style='width:100%;height:100%;object-fit:cover' /></div>"
        if img_url else "<div style='width:260px;height:150px;border-radius:10px;background:#F3F4F6'></div>"
    )
    sub_html = f"<div style='margin-top:4px;text-align:center;font-size:.8rem;color:#6B7280'>{sub}</div>" if sub else ""
    return (
        f"<a href='?{qs}' target='_self' rel='noopener' "
        f"style='display:block;width:260px;height:240px;border:1px solid #E5E7EB;border-radius:14px;background:#fff;padding:12px;text-decoration:none;color:#111827;transition:.15s ease;cursor:pointer'>"
        f"{img}<div style='margin-top:10px;text-align:center;font-weight:700;font-size:.98rem'>{title}</div>{sub_html}</a>"
    )

def render_row(title: str, items: list[str]):
    st.markdown(
        f"<div class='h1'>{title}</div>"
        f"<div style='display:flex;gap:14px;overflow-x:auto;padding:8px 2px'>{''.join(items)}</div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------
# REPORT PAGE
# ---------------------------------------------------------------------
def render_report_page():
    st.markdown("<div class='report-head'>What/where can I fly?</div>", unsafe_allow_html=True)
    st.markdown("Tell us what credentials you hold; we’ll check **all drones** in the list and show what’s **Allowed** by year.", unsafe_allow_html=True)

    # Credentials across the top
    col_creds = st.columns(5)
    with col_creds[0]: c_op = st.checkbox("Operator ID", key="r_op")
    with col_creds[1]: c_fl = st.checkbox("Flyer ID", key="r_fl")
    with col_creds[2]: c_a2 = st.checkbox("A2 CofC", key="r_a2")
    with col_creds[3]: c_gv = st.checkbox("GVC", key="r_gvc")
    with col_creds[4]: c_oa = st.checkbox("OA", key="r_oa")
    creds = dict(op=c_op, flyer=c_fl, a2=c_a2, gvc=c_gv, oa=c_oa)

    # Category filter chips
    st.markdown("<div class='report-hr'></div>", unsafe_allow_html=True)
    fc = st.columns(4)
    with fc[0]: fa1 = st.checkbox("Filter A1", value=True, key="rf_a1")
    with fc[1]: fa2 = st.checkbox("Filter A2", value=True, key="rf_a2")
    with fc[2]: fa3 = st.checkbox("Filter A3", value=True, key="rf_a3")
    with fc[3]: fsp = st.checkbox("Filter Specific", value=True, key="rf_sp")

    cat_on = {"A1": fa1, "A2": fa2, "A3": fa3, "Specific": fsp}

    # Three year columns with dynamic counts
    c_now, c_2627, c_28 = st.columns(3)
    cols = [(c_now, 2025, "Now – 31 Dec 2025"),
            (c_2627, 2026, "1 Jan 2026 – 31 Dec 2027 (UK–EU bridge)"),
            (c_28, 2028, "From 1 Jan 2028 (planned)")]

    for col, yr, title in cols:
        # Compute list once to derive count, then render
        matches = []
        for _, r in df.iterrows():
            kinds = _kinds_for(r, creds, yr)
            allowed_cats = [k for k, v in kinds.items() if v == "allowed" and cat_on.get(k, True)]
            if allowed_cats:
                matches.append((r, allowed_cats))

        with col:
            st.markdown(f"### {title} <span class='count-bubble'>{len(matches)}</span>", unsafe_allow_html=True)
            for r, cats in matches:
                chips = " ".join([f"<span class='cat-pill'>{c}</span>" for c in cats])
                st.markdown(
                    f"<div class='cat-chip'>{r.get('marketing_name','')} {chips}</div>",
                    unsafe_allow_html=True
                )

# ---------------------------------------------------------------------
# PAGE FLOW
# ---------------------------------------------------------------------
if page == "report":
    # Dedicated report page (no sidebar)
    render_report_page()

elif not segment:
    # Landing page: choose group + report card
    items = []
    for seg in taxonomy["segments"]:
        img = SEGMENT_HERO.get(seg["key"], "")
        items.append(card_link(f"segment={seg['key']}", seg["label"], img_url=img))
    # Add the report card (only on landing)
    items.append(
        card_link(
            "page=report",
            "What/where can I fly?",
            sub="Tell us your credentials and we’ll scan all drones by year.",
            img_url=WHAT_IMG,
        )
    )
    render_row("Choose your drone category", items)

elif not series:
    # Series page (no sidebar, no report card)
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    items = []
    for s in series_defs_for(segment):
        items.append(
            card_link(
                f"segment={segment}&series={s['key']}",
                s["label"],
                img_url=random_image_for_series(segment, s["key"]),
            )
        )
    render_row(f"Choose a series ({seg_label})", items)

else:
    # Product page (sidebar visible)
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    ser_label = next(s["label"] for s in series_defs_for(segment) if s["key"] == series)

    sel = df[df["model_key"] == model] if model else None

    if sel is not None and not sel.empty:
        row = sel.iloc[0]

        # --- Sidebar (only on product page) ---
        st.sidebar.markdown("### Navigation")
        if st.sidebar.button("Restart"):
            _restart_app()

        img_url = resolve_img(row.get("image_url", ""))
        if img_url:
            st.sidebar.image(img_url, use_container_width=True, caption=row.get("marketing_name", ""))

        # Flags & classes
        eu_flag = resolve_img("images/eu.png")
        uk_flag = resolve_img("images/uk.png")
        eu_cls  = row.get("eu_class_marking", "unknown")
        uk_cls  = row.get("uk_class_marking", "unknown")
        st.sidebar.markdown(
            f"""
<div class='flagline'><img src="{eu_flag}"/><div><b>EU:</b> {eu_cls}</div></div>
<div class='flagline'><img src="{uk_flag}"/><div><b>UK:</b> {uk_cls}</div></div>
""",
            unsafe_allow_html=True,
        )

        st.sidebar.markdown("<div class='sidebar-title'>Key specs</div>", unsafe_allow_html=True)
        st.sidebar.markdown(
            f"<div class='sidebar-kv'><b>Model</b>: {row.get('marketing_name','—')}</div>"
            f"<div class='sidebar-kv'><b>MTOW</b>: {row.get('mtom_g_nominal','—')} g</div>"
            f"<div class='sidebar-kv'><b>Remote ID</b>: {row.get('remote_id_builtin','unknown')}</div>"
            f"<div class='sidebar-kv'><b>Geo-awareness</b>: {row.get('geo_awareness','unknown')}</div>"
            f"<div class='sidebar-kv'><b>Released</b>: {row.get('year_released','—')}</div>",
            unsafe_allow_html=True,
        )

        # Credentials (compact) + legend
        st.sidebar.markdown("<div class='sidebar-title' style='margin-top:.7rem'>Your credentials</div>", unsafe_allow_html=True)
        have_op   = st.sidebar.checkbox("Operator ID", value=False, key="c_op")
        have_fl   = st.sidebar.checkbox("Flyer ID", value=False, key="c_fl")
        have_a2   = st.sidebar.checkbox("A2 CofC", value=False, key="c_a2")
        have_gvc  = st.sidebar.checkbox("GVC", value=False, key="c_gvc")
        have_oa   = st.sidebar.checkbox("OA (Operational Authorisation)", value=False, key="c_oa")

        st.sidebar.markdown(
            "<div class='legend'>"
            f"{badge('Allowed','allowed')} "
            f"{badge('Possible (additional requirements)','possible')} "
            f"{badge('Available via OA/GVC','oagvc')}"
            "</div>",
            unsafe_allow_html=True,
        )

        creds = dict(op=have_op, flyer=have_fl, a2=have_a2, gvc=have_gvc, oa=have_oa)

        # --------- Compute all bricks (UK by default) ---------
        a_now = compute_bricks(row, creds, 2025, jurisdiction="UK")
        a_26  = compute_bricks(row, creds, 2026, jurisdiction="UK")
        a_28  = compute_bricks(row, creds, 2028, jurisdiction="UK")

        # ---------- HEADERS ----------
        st.markdown(
            "<div class='grid3 divided' style='margin:0 0 8px 0;'>"
            "<div style='text-align:left;font-weight:600;font-size:.95rem;color:#374151;margin-bottom:4px;'>"
            "Now – 31 Dec 2025"
            "</div>"
            "<div style='text-align:left;font-weight:600;font-size:.95rem;color:#374151;margin-bottom:4px;'>"
            "1 Jan 2026 – 31 Dec 2027 (UK–EU bridge)"
            "</div>"
            "<div style='text-align:left;font-weight:600;font-size:.95rem;color:#374151;margin-bottom:4px;'>"
            "From 1 Jan 2028 (planned)"
            "</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        # Row 1: A1 across 3 cells
        st.markdown(
            "<div class='grid3 divided'>"
            f"<div>{a_now[0]}</div>"
            f"<div>{a_26[0]}</div>"
            f"<div>{a_28[0]}</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        # Row 2: A2
        st.markdown(
            "<div class='grid3 divided'>"
            f"<div>{a_now[1]}</div>"
            f"<div>{a_26[1]}</div>"
            f"<div>{a_28[1]}</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        # Row 3: A3
        st.markdown(
            "<div class='grid3 divided'>"
            f"<div>{a_now[2]}</div>"
            f"<div>{a_26[2]}</div>"
            f"<div>{a_28[2]}</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        # Row 4: Specific
        st.markdown(
            "<div class='grid3 divided'>"
            f"<div>{a_now[3]}</div>"
            f"<div>{a_26[3]}</div>"
            f"<div>{a_28[3]}</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    else:
        # Models grid (no sidebar)
        st.markdown(f"<div class='h1'>Choose a drone ({seg_label} → {ser_label})</div>", unsafe_allow_html=True)
        models = models_for(segment, series)
        items = []
        for _, r in models.iterrows():
            subbits = []
            eu_c = (r.get("eu_class_marking") or "").strip()
            uk_c = (r.get("uk_class_marking") or "").strip()
            if eu_c or uk_c:
                subbits.append(f"Class: EU {eu_c if eu_c else '—'} • UK {uk_c if uk_c else '—'}")
            yr = r.get("year_released", "")
            if yr:
                subbits.append(f"Released: {yr}")
            sub = " • ".join(subbits)
            items.append(
                card_link(
                    f"segment={segment}&series={series}&model={r['model_key']}",
                    r.get("marketing_name", ""),
                    sub=sub,
                    img_url=resolve_img(r.get("image_url", "")),
                )
            )
        st.markdown(
            f"<div style='display:flex;gap:14px;flex-wrap:wrap'>{''.join(items)}</div>",
            unsafe_allow_html=True,
        )
