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

# ---------------------------------------------------------------------
# Restart
# ---------------------------------------------------------------------
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

df, taxonomy = load_data()

# ---------------------------------------------------------------------
# UI CSS
# ---------------------------------------------------------------------
st.markdown(
    """
<style>
.block-container { padding-top: .7rem; }

/* Titles */
.h1 { font-weight: 800; font-size: 1.2rem; color: #1F2937; margin: 6px 0 12px 0; }
.hdr { font-weight: 800; font-size: 1.35rem; margin: 6px 0 12px; }

/* Sidebar tweaks (more compact) */
section[data-testid="stSidebar"] .block-container { padding-top: .4rem; }
.sidebar-title { font-weight:800; font-size:1.02rem; margin:.35rem 0 .2rem; }
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
.card-outer { border:1px solid #E5E7EB; border-radius:12px; padding:14px; margin-bottom:12px; width:100%;
              display:flex; flex-direction:column; }
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

/* Three-column GRID */
.grid3 { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 16px; align-items: stretch; }
.grid3 > div { display:flex; }

/* Header cells */
.hdrcell { font-weight:800; font-size:1.05rem; color:#111827; }

/* Vertical dividers */
.divided.grid3 > div:not(:first-child) {
  border-left: 1px solid #EDEFF3;
  padding-left: 12px;
}

/* Report tags */
.tag { display:inline-block; padding:2px 8px; border-radius:999px; background:#EFF6FF; color:#1E40AF; font-weight:700; font-size:.75rem; margin-left:6px; }
.result-pill { display:inline-block; padding:6px 10px; border-radius:10px; background:#F3F4F6; margin:4px 0; }

/* Row of action buttons on top pages */
.top-actions { display:flex; gap: 10px; justify-content:flex-end; margin:8px 0 12px; }

/* Mini spacer above "Your credentials" in sidebar */
.sidebar-spacer { height: 6px; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# Query params
# ---------------------------------------------------------------------
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
series  = qp.get("series")
model   = qp.get("model")
show_report = qp.get("report", "") == "1"

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
# Brick helpers & rules
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

# --- util
def _lc(x): return str(x or "").strip().lower()

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

# --- rule text
def rule_text_a1():
    return "Fly close to people; avoid assemblies/crowds. TOAL: sensible separation; follow local restrictions."

def rule_text_a2(year: int):
    if year < 2026:
        return "A2 mainly for C2 drones (sometimes C1 by nuance). Transitional (≤2 kg) until Jan 2026: keep ≥50 m from uninvolved people."
    return "C2/UK2: keep 30 m from uninvolved people (5 m in low-speed)."

def rule_text_a3():
    return "Keep ≥150 m from residential/commercial/industrial/recreational areas. TOAL: well away from uninvolved people and built-up areas."

def rule_text_specific():
    return "Risk-assessed operations per OA; distances per ops manual. TOAL & mitigations per your approved procedures (e.g., PDRA-01)."

# --- eligibility gating
def eligible_open_subcats(row: pd.Series, year: int, jurisdiction: str = "UK") -> dict:
    eu = _lc(row.get("eu_class_marking", ""))
    uk = _lc(row.get("uk_class_marking", ""))
    mtow = _parse_mtow_g(row)
    is_classed = eu in {"c0","c1","c2","c3","c4"} or uk in {"uk0","uk1","uk2","uk3","uk4"}
    bridge = (jurisdiction.upper() == "UK" and year <= 2027)

    # sub-100 g -> A1 + A3, no IDs
    if mtow is not None and mtow < 100:
        return {"a1": True, "a2": False, "a3": True}

    a1 = False
    if mtow is not None and mtow <= 250: a1 = True
    if uk in {"uk0", "uk1"}: a1 = True
    if bridge and year >= 2026 and eu in {"c0","c1"}: a1 = True

    a2 = False
    if uk == "uk2" or (bridge and eu == "c2"):
        if mtow is None or mtow <= 4000:
            a2 = True
    if (jurisdiction.upper() == "UK" and year < 2026 and not is_classed
        and mtow is not None and mtow <= 2000):
        a2 = True

    a3 = False
    if mtow is not None and mtow < 25000: a3 = True
    if uk in {"uk3","uk4"} or (bridge and eu in {"c2","c3","c4"}): a3 = True

    return {"a1": a1, "a2": a2, "a3": a3}

# --- Remote ID timeline (UK)
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

# --- compute bricks (single model)
def compute_bricks(row: pd.Series, creds: dict, year: int, jurisdiction: str = "UK"):
    has_cam = yesish(row.get("has_camera", "yes"))
    geo_ok  = yesish(row.get("geo_awareness", "unknown"))
    rid_ok  = yesish(row.get("remote_id_builtin", "unknown"))
    elig = eligible_open_subcats(row, year, jurisdiction)

    have_op, have_fl = creds.get("op", False), creds.get("flyer", False)
    have_a2, have_gvc, have_oa = creds.get("a2", False), creds.get("gvc", False), creds.get("oa", False)

    mtow = _parse_mtow_g(row) or 0.0
    sub100 = mtow < 100

    # A1
    if not elig["a1"]:
        html_a1 = card("A1 — Close to people", badge("Not applicable","na"),
            f"<div class='small'>{rule_text_a1()}</div><div>{pill_info('Not eligible by class/weight')}</div>", "na")
    else:
        pills_a1 = []
        if has_cam and not sub100 and not have_op: pills_a1.append(pill_need("Operator ID: Required"))
        else: pills_a1.append(pill_ok("Operator ID: OK" if not sub100 else "Operator ID: Not required"))
        if has_cam and not sub100 and not have_fl: pills_a1.append(pill_need("Flyer ID: Required"))
        else: pills_a1.append(pill_ok("Flyer ID: OK" if not sub100 else "Flyer ID: Not required"))
        pills_a1.append(rid_pill(row, year, rid_ok))
        pills_a1.append(pill_ok("Geo-awareness: Onboard") if geo_ok else pill_need("Geo-awareness: Required"))
        a1_kind = "allowed" if pills_all_ok(pills_a1) else "possible"
        html_a1 = card("A1 — Close to people", badge("Allowed" if a1_kind=="allowed" else "Possible (additional requirements)", a1_kind),
                       f"<div class='small'>{rule_text_a1()}</div><div>{''.join(pills_a1)}</div>", a1_kind)

    # A2
    if not elig["a2"]:
        html_a2 = card("A2 — Close with A2 CofC", badge("Not applicable","na"),
                       f"<div class='small'>{rule_text_a2(year)}</div><div>{pill_info('Not eligible by class/weight for A2')}</div>", "na")
    else:
        pills_a2 = [
            pill_need("Operator ID: Required") if not have_op else pill_ok("Operator ID: OK"),
            pill_need("Flyer ID: Required") if not have_fl else pill_ok("Flyer ID: OK"),
            pill_need("A2 CofC: Required") if not have_a2 else pill_ok("A2 CofC: OK"),
            rid_pill(row, year, rid_ok),
            pill_ok("Geo-awareness: Onboard") if geo_ok else pill_need("Geo-awareness: Required"),
        ]
        a2_kind = "allowed" if pills_all_ok(pills_a2) else "possible"
        html_a2 = card("A2 — Close with A2 CofC", badge("Allowed" if a2_kind=="allowed" else "Possible (additional requirements)", a2_kind),
                       f"<div class='small'>{rule_text_a2(year)}</div><div>{''.join(pills_a2)}</div>", a2_kind)

    # A3
    if not elig["a3"]:
        html_a3 = card("A3 — Far from people", badge("Not applicable","na"),
                       f"<div class='small'>{rule_text_a3()}</div><div>{pill_info('Not eligible by class/weight for A3')}</div>", "na")
    else:
        pills_a3 = [
            pill_need("Operator ID: Required") if not have_op else pill_ok("Operator ID: OK"),
            pill_need("Flyer ID: Required") if not have_fl else pill_ok("Flyer ID: OK"),
            rid_pill(row, year, rid_ok),
            pill_ok("Geo-awareness: Onboard") if geo_ok else pill_need("Geo-awareness: Required"),
        ]
        a3_kind = "allowed" if pills_all_ok(pills_a3) else "possible"
        html_a3 = card("A3 — Far from people", badge("Allowed" if a3_kind=="allowed" else "Possible (additional requirements)", a3_kind),
                       f"<div class='small'>{rule_text_a3()}</div><div>{''.join(pills_a3)}</div>", a3_kind)

    # Specific
    pills_sp = [
        pill_need("Operator ID: Required") if not have_op else pill_ok("Operator ID: OK"),
        pill_need("Flyer ID: Required") if not have_fl else pill_ok("Flyer ID: OK"),
        pill_need("GVC: Required") if not have_gvc else pill_ok("GVC: OK"),
        pill_need("OA: Required") if not have_oa else pill_ok("OA: OK"),
        rid_pill(row, year, rid_ok),
        pill_ok("Geo-awareness: Onboard") if geo_ok else pill_need("Geo-awareness: Required"),
    ]
    sp_kind = "allowed" if pills_all_ok(pills_sp) else "oagvc"
    sp_lbl  = "Allowed" if sp_kind == "allowed" else "Available via OA/GVC"
    html_sp = card("Specific — OA / GVC", badge(sp_lbl, "allowed" if sp_kind=="allowed" else "oagvc"),
                   f"<div class='small'>{rule_text_specific()}</div><div>{''.join(pills_sp)}</div>", sp_kind)

    return html_a1, html_a2, html_a3, html_sp

# ---------------------------------------------------------------------
# Report helpers (multi-model)
# ---------------------------------------------------------------------
def category_allowed_for(row, creds, year) -> set[str]:
    """
    Returns set of categories where the final card would be 'Allowed'
    (i.e., all pills OK). Uses the same logic as compute_bricks but
    evaluates booleans only.
    """
    has_cam = yesish(row.get("has_camera", "yes"))
    geo_ok  = yesish(row.get("geo_awareness", "unknown"))
    rid_ok  = yesish(row.get("remote_id_builtin", "unknown"))
    elig = eligible_open_subcats(row, year, "UK")

    have_op, have_fl = creds.get("op", False), creds.get("flyer", False)
    have_a2, have_gvc, have_oa = creds.get("a2", False), creds.get("gvc", False), creds.get("oa", False)
    mtow = _parse_mtow_g(row) or 0.0
    sub100 = mtow < 100

    out = set()

    # A1
    if elig["a1"]:
        ok = True
        if has_cam and not sub100 and not have_op: ok = False
        if has_cam and not sub100 and not have_fl: ok = False
        if rid_is_required(row, year) and not rid_ok: ok = False
        if not geo_ok: ok = False
        if ok: out.add("A1")

    # A2
    if elig["a2"]:
        ok = True
        if not have_op or not have_fl or not have_a2: ok = False
        if rid_is_required(row, year) and not rid_ok: ok = False
        if not geo_ok: ok = False
        if ok: out.add("A2")

    # A3
    if elig["a3"]:
        ok = True
        if not have_op or not have_fl: ok = False
        if rid_is_required(row, year) and not rid_ok: ok = False
        if not geo_ok: ok = False
        if ok: out.add("A3")

    # Specific
    ok = True
    if not have_op or not have_fl or not have_gvc or not have_oa: ok = False
    if rid_is_required(row, year) and not rid_ok: ok = False
    if not geo_ok: ok = False
    if ok: out.add("Specific")

    return out

def render_result_badge(label: str) -> str:
    return f"<span class='tag'>{label}</span>"

def render_result_row(name: str, cats: list[str]) -> str:
    tags = "".join(render_result_badge(c) for c in cats)
    return f"<div class='result-pill'><b>{name}</b>{tags}</div>"

# ---------------------------------------------------------------------
# Stage 1 & 2 cards + “report” card
# ---------------------------------------------------------------------
SEGMENT_HERO = {
    "consumer": resolve_img("images/consumer.jpg"),
    "pro": resolve_img("images/professional.jpg"),
    "enterprise": resolve_img("images/enterprise.jpg"),
}

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
# PAGE FLOW
# ---------------------------------------------------------------------
# Hide sidebar on menus / show only on final model page
def showing_product_page() -> bool:
    return bool(series) and bool(model)

if showing_product_page():
    st.sidebar.markdown("### Navigation")
    if st.sidebar.button("Restart", key="restart_btn_final"):
        _restart_app()
else:
    # Minimal empty sidebar so the layout doesn't jump; no controls
    with st.sidebar:
        st.write("")

if show_report:
    # ---------------- Report page ----------------
    st.markdown("# What/where can I fly?")

    st.markdown(
        "Tell us what credentials you hold; we’ll check **all drones** in the list "
        "and show what’s **Allowed** by year."
    )

    # Credential toggles (top-level, independent of sidebar)
    colc1, colc2, colc3, colc4, colc5 = st.columns(5)
    with colc1:
        r_op = st.checkbox("Operator ID", value=False, key="r_op")
    with colc2:
        r_fl = st.checkbox("Flyer ID", value=False, key="r_fl")
    with colc3:
        r_a2 = st.checkbox("A2 CofC", value=False, key="r_a2")
    with colc4:
        r_gv = st.checkbox("GVC", value=False, key="r_gvc")
    with colc5:
        r_oa = st.checkbox("OA", value=False, key="r_oa")

    report_creds = dict(op=r_op, flyer=r_fl, a2=r_a2, gvc=r_gv, oa=r_oa)

    # Category filter toggles
    st.write("")
    filt_cols = st.columns(4)
    with filt_cols[0]: f_a1 = st.checkbox("Filter A1", value=True, key="f_a1")
    with filt_cols[1]: f_a2 = st.checkbox("Filter A2", value=True, key="f_a2")
    with filt_cols[2]: f_a3 = st.checkbox("Filter A3", value=True, key="f_a3")
    with filt_cols[3]: f_sp = st.checkbox("Filter Specific", value=True, key="f_sp")
    active_filters = {cat for cat, keep in zip(["A1","A2","A3","Specific"], [f_a1,f_a2,f_a3,f_sp]) if keep}

    # Build three columns of results + counts
    years = [
        ("Now – 31 Dec 2025", 2025),
        ("1 Jan 2026 – 31 Dec 2027 (UK–EU bridge)", 2026),
        ("From 1 Jan 2028 (planned)", 2028),
    ]

    colA, colB, colC = st.columns(3)
    col_map = {2025: colA, 2026: colB, 2028: colC}

    # We’ll accumulate counts per year
    counts = {2025: 0, 2026: 0, 2028: 0}

    # Precompute for all drones
    rows = []
    for _, r in df.iterrows():
        name = r.get("marketing_name","")
        rows.append((name, r))

    rows.sort(key=lambda x: x[0].lower())

    for title, yr in years:
        # Render a placeholder for a dynamic header with count
        holder = col_map[yr].empty()
        container = col_map[yr].container()
        # Build content
        allowed_here = []
        for name, r in rows:
            cats = sorted(list(category_allowed_for(r, report_creds, yr)))
            if not cats:
                continue
            # Respect active filters
            if not (set(cats) & active_filters):
                continue
            allowed_here.append(render_result_row(name, [c for c in cats if c in active_filters]))
        counts[yr] = len(allowed_here)

        # Heading with live count
        holder.markdown(f"## {title} <span style='color:#6B7280;font-weight:600'>({counts[yr]})</span>", unsafe_allow_html=True)
        if allowed_here:
            container.markdown("<div style='margin-top:8px'>" + "".join(allowed_here) + "</div>", unsafe_allow_html=True)
        else:
            container.info("Nothing matches your credentials and filters.")

    st.divider()
    st.markdown(
        "<div class='top-actions'>"
        "<a href='?'>Back to start</a>"
        "</div>",
        unsafe_allow_html=True,
    )

else:
    # ---------------- Normal flow (menus + product page) ----------------
    if not segment:
        # Home: choose segment + report tile under the row
        items = []
        for seg in taxonomy["segments"]:
            img = SEGMENT_HERO.get(seg["key"], "")
            items.append(card_link(f"segment={seg['key']}", seg["label"], img_url=img))
        render_row("Choose your drone category", items)

        # Report tile row
        report_card = card_link(
            "report=1",
            "What/where can I fly?",
            sub="Tell us your credentials and we’ll scan all drones by year.",
            img_url=resolve_img("images/uk.jpg"),
        )
        st.markdown(
            f"<div style='margin-top:12px'></div>"
            f"<div class='h1'>Or…</div>"
            f"<div style='display:flex;gap:14px;flex-wrap:wrap'>{report_card}</div>",
            unsafe_allow_html=True,
        )

    elif not series:
        # Choose series
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

        # Also show the report tile here, for convenience
        report_card = card_link(
            "report=1",
            "What/where can I fly?",
            sub="Tell us your credentials and we’ll scan all drones by year.",
            img_url=resolve_img("images/uk.jpg"),
        )
        st.markdown(
            f"<div style='margin-top:12px'></div>"
            f"<div style='display:flex;gap:14px;flex-wrap:wrap'>{report_card}</div>",
            unsafe_allow_html=True,
        )

    else:
        # Product page (sidebar is active here)
        seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
        ser_label = next(s["label"] for s in series_defs_for(segment) if s["key"] == series)

        sel = df[df["model_key"] == model] if model else None

        if sel is not None and not sel.empty:
            row = sel.iloc[0]

            # Sidebar: image + flags + specs
            img_url = resolve_img(row.get("image_url", ""))
            if img_url:
                st.sidebar.image(img_url, use_container_width=True, caption=row.get("marketing_name", ""))

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

            # Spacer before creds, as requested
            st.sidebar.markdown("<div class='sidebar-spacer'></div>", unsafe_allow_html=True)
            st.sidebar.markdown("<div class='sidebar-title'>Your credentials</div>", unsafe_allow_html=True)
            have_op   = st.sidebar.checkbox("Operator ID", value=False, key="c_op")
            have_fl   = st.sidebar.checkbox("Flyer ID", value=False, key="c_fl")
            have_a2   = st.sidebar.checkbox("A2 CofC", value=False, key="c_a2")
            have_gvc  = st.sidebar.checkbox("GVC", value=False, key="c_gvc")
            have_oa   = st.sidebar.checkbox("OA (Operational Authorisation)", value=False, key="c_oa")
            creds = dict(op=have_op, flyer=have_fl, a2=have_a2, gvc=have_gvc, oa=have_oa)

            # Top-right actions moved into body (no cropping)
            act = st.columns([1,1,8])
            with act[0]:
                st.link_button("My permissions report", "?report=1")
            with act[1]:
                if st.button("Restart"):
                    _restart_app()

            a_now = compute_bricks(row, creds, 2025, jurisdiction="UK")
            a_26  = compute_bricks(row, creds, 2026, jurisdiction="UK")
            a_28  = compute_bricks(row, creds, 2028, jurisdiction="UK")

            # Headers row
            st.markdown(
                "<div class='grid3 divided' style='margin:0 0 8px 0;'>"
                "<div style='text-align:center;font-weight:600;font-size:.95rem;color:#374151;margin-bottom:4px;'>Now – 31 Dec 2025</div>"
                "<div style='text-align:center;font-weight:600;font-size:.95rem;color:#374151;margin-bottom:4px;'>1 Jan 2026 – 31 Dec 2027 (UK–EU bridge)</div>"
                "<div style='text-align:center;font-weight:600;font-size:.95rem;color:#374151;margin-bottom:4px;'>From 1 Jan 2028 (planned)</div>"
                "</div>",
                unsafe_allow_html=True,
            )

            # Rows
            st.markdown(
                "<div class='grid3 divided'>"
                f"<div>{a_now[0]}</div>"
                f"<div>{a_26[0]}</div>"
                f"<div>{a_28[0]}</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<div class='grid3 divided'>"
                f"<div>{a_now[1]}</div>"
                f"<div>{a_26[1]}</div>"
                f"<div>{a_28[1]}</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<div class='grid3 divided'>"
                f"<div>{a_now[2]}</div>"
                f"<div>{a_26[2]}</div>"
                f"<div>{a_28[2]}</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<div class='grid3 divided'>"
                f"<div>{a_now[3]}</div>"
                f"<div>{a_26[3]}</div>"
                f"<div>{a_28[3]}</div>"
                "</div>",
                unsafe_allow_html=True,
            )

        else:
            # Model list for chosen series
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
                if yr: subbits.append(f"Released: {yr}")
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
