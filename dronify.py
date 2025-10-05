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


# ---------- Helpers: data & images ----------
def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@st.cache_data(show_spinner=False)
def load_data():
    dataset = load_yaml(DATASET_PATH)
    taxonomy = load_yaml(TAXONOMY_PATH)
    df = pd.DataFrame(dataset["data"])

    # Ensure columns (robustness)
    needed = [
        "image_url", "segment", "series", "marketing_name", "model_key",
        "mtom_g_nominal", "eu_class_marking", "uk_class_marking",
        "has_camera", "geo_awareness", "remote_id_builtin", "year_released"
    ]
    for col in needed:
        if col not in df.columns:
            df[col] = ""

    # Normalized
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
    # bare filename -> assume images/
    return RAW_BASE + url.lstrip("/")


# ---------- UI CSS ----------
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

/* Legend */
.legend { margin-top: 8px; border-top:1px solid #E5E7EB; padding-top:6px; }
.legend .badge { margin-right:6px; }

/* Three-cell GRID per row so all bricks align (same row height) */
.grid3 { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 16px; align-items: stretch; }
.grid3 > div { display:flex; }

/* Column headers row + dividers (matches grid3) */
.grid3-headers { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 16px; margin: 4px 0 10px; }
.grid3-headers .hdrcell { font-weight:800; font-size:1.15rem; color:#111827; }

/* Vertical dividers between columns */
.divided.grid3 > div:not(:first-child),
.divided.grid3-headers > div:not(:first-child) {
  border-left: 1px solid #EDEFF3;
  padding-left: 12px;
}
</style>
""",
    unsafe_allow_html=True,
)


# ---------- Query params ----------
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

df, taxonomy = load_data()


# ---------- Taxonomy helpers ----------
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


# ---------- Brick rendering ----------
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
    return "C2: 30 m from uninvolved people (5 m in low-speed)."


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


def compute_bricks(row: pd.Series, creds: dict, year: int):
    """
    Returns (html_a1, html_a2, html_a3, html_specific)
    """
    has_cam = yesish(row.get("has_camera", "yes"))
    geo_ok  = yesish(row.get("geo_awareness", "unknown"))
    rid_ok  = yesish(row.get("remote_id_builtin", "unknown"))
    eu      = str(row.get("eu_class_marking", "")).strip().lower()

    # Credentials
    have_op   = creds.get("op", False)
    have_fl   = creds.get("flyer", False)
    have_a1a3 = creds.get("a1a3", False)
    have_a2   = creds.get("a2", False)
    have_gvc  = creds.get("gvc", False)
    have_oa   = creds.get("oa", False)

    # ---------- A1 ----------
    pills_a1 = []
    if has_cam and not have_op:
        pills_a1.append(pill_need("Operator ID: Required",
                         "Required for all drones with a camera (registration of the operator)."))
    else:
        pills_a1.append(pill_ok("Operator ID: OK"))

    if has_cam and not have_fl:
        pills_a1.append(pill_need("Flyer ID: Required", "Basic test for camera drones."))
    else:
        pills_a1.append(pill_ok("Flyer ID: OK"))

    pills_a1.append(pill_ok("Remote ID: OK") if rid_ok else pill_need("Remote ID: Required"))
    pills_a1.append(pill_ok("Geo-awareness: Onboard") if geo_ok else pill_need("Geo-awareness: Required"))
    pills_a1.append(pill_info("A1/A3: Optional"))

    a1_all_ok = all(("Required" not in x) for x in pills_a1)
    a1_kind   = "allowed" if a1_all_ok else "possible"
    a1_badge  = badge("Allowed" if a1_kind == "allowed" else "Possible (additional requirements)", a1_kind)
    a1_body   = f"<div class='small'>{rule_text_a1()}</div><div>{''.join(pills_a1)}</div>"
    html_a1   = card("A1 — Close to people", a1_badge, a1_body, a1_kind)

    # ---------- A2 ----------
    is_c2 = (eu == "c2")
    pills_a2 = []
    if is_c2:
        pills_a2.append(pill_need("Operator ID: Required") if not have_op else pill_ok("Operator ID: OK"))
        pills_a2.append(pill_need("Flyer ID: Required") if not have_fl else pill_ok("Flyer ID: OK"))
        pills_a2.append(pill_need("A2 CofC: Required") if not have_a2 else pill_ok("A2 CofC: OK"))
        pills_a2.append(pill_ok("Remote ID: OK") if rid_ok else pill_need("Remote ID: Required"))
        pills_a2.append(pill_ok("Geo-awareness: Onboard") if geo_ok else pill_need("Geo-awareness: Required"))

        a2_all_ok = all(("Required" not in x) for x in pills_a2)
        a2_kind   = "allowed" if a2_all_ok else "possible"
        a2_badge  = badge("Allowed" if a2_kind == "allowed" else "Possible (additional requirements)", a2_kind)
        a2_body   = f"<div class='small'>{rule_text_a2(year)}</div><div>{''.join(pills_a2)}</div>"
        html_a2   = card("A2 — Close with A2 CofC", a2_badge, a2_body, a2_kind)
    else:
        pills_a2.append(pill_info("A2 CofC: N/A"))
        pills_a2.append(pill_ok("Remote ID: OK") if rid_ok else pill_need("Remote ID: Required"))
        pills_a2.append(pill_ok("Geo-awareness: Onboard") if geo_ok else pill_need("Geo-awareness: Required"))
        a2_badge = badge("Not applicable", "na")
        a2_body  = f"<div class='small'>{rule_text_a2(year)}</div><div>{''.join(pills_a2)}</div>"
        html_a2  = card("A2 — Close with A2 CofC", a2_badge, a2_body, "na")

    # ---------- A3 ----------
    pills_a3 = []
    pills_a3.append(pill_need("Operator ID: Required") if not have_op else pill_ok("Operator ID: OK"))
    pills_a3.append(pill_need("Flyer ID: Required") if not have_fl else pill_ok("Flyer ID: OK"))
    pills_a3.append(pill_ok("Remote ID: OK") if rid_ok else pill_need("Remote ID: Required"))
    pills_a3.append(pill_ok("Geo-awareness: Onboard") if geo_ok else pill_need("Geo-awareness: Required"))

    a3_all_ok = all(("Required" not in x) for x in pills_a3)
    a3_kind   = "allowed" if a3_all_ok else "possible"
    a3_badge  = badge("Allowed" if a3_kind == "allowed" else "Possible (additional requirements)", a3_kind)
    a3_body   = f"<div class='small'>{rule_text_a3()}</div><div>{''.join(pills_a3)}</div>"
    html_a3   = card("A3 — Far from people", a3_badge, a3_body, a3_kind)

    # ---------- Specific (OA / GVC) ----------
    pills_sp = []
    pills_sp.append(pill_need("Operator ID: Required") if not have_op else pill_ok("Operator ID: OK"))
    pills_sp.append(pill_need("Flyer ID: Required")   if not have_fl else pill_ok("Flyer ID: OK"))
    pills_sp.append(pill_need("GVC: Required")        if not have_gvc else pill_ok("GVC: OK"))
    pills_sp.append(pill_need("OA: Required")         if not have_oa else pill_ok("OA: OK"))
    pills_sp.append(pill_ok("Remote ID: OK")          if rid_ok else pill_need("Remote ID: Required"))
    pills_sp.append(pill_ok("Geo-awareness: Onboard") if geo_ok else pill_need("Geo-awareness: Required"))

    sp_all_ok = all(("Required" not in x) for x in pills_sp)
    sp_kind   = "allowed" if sp_all_ok else "oagvc"
    sp_lbl    = "Allowed" if sp_kind == "allowed" else "Available via OA/GVC"
    sp_badge  = badge(sp_lbl, "allowed" if sp_kind == "allowed" else "oagvc")
    sp_body   = f"<div class='small'>{rule_text_specific()}</div><div>{''.join(pills_sp)}</div>"
    html_sp   = card("Specific — OA / GVC", sp_badge, sp_body, sp_kind)

    return html_a1, html_a2, html_a3, html_sp


# ---------- STAGE 1 & 2 ----------
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


# ---------- PAGE FLOW ----------
if not segment:
    # Stage 1: choose group
    items = []
    for seg in taxonomy["segments"]:
        img = SEGMENT_HERO.get(seg["key"], "")
        items.append(card_link(f"segment={seg['key']}", seg["label"], img_url=img))
    render_row("Choose your drone category", items)

elif not series:
    # Stage 2: choose series (random image)
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
    # Stage 3: models grid and detail view
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    ser_label = next(s["label"] for s in series_defs_for(segment) if s["key"] == series)

    # Sidebar back
    st.sidebar.markdown(f"[← Back to models](?segment={segment}&series={series})")

    if model:
        sel = df[df["model_key"] == model]
    else:
        sel = None

    if sel is not None and not sel.empty:
        row = sel.iloc[0]

        # Thumbnail + caption
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

        # Key specs
        st.sidebar.markdown("<div class='sidebar-title'>Key specs</div>", unsafe_allow_html=True)
        st.sidebar.markdown(
            f"<div class='sidebar-kv'><b>Model</b>: {row.get('marketing_name','—')}</div>"
            f"<div class='sidebar-kv'><b>MTOW</b>: {row.get('mtom_g_nominal','—')} g</div>"
            f"<div class='sidebar-kv'><b>Remote ID</b>: {row.get('remote_id_builtin','unknown')}</div>"
            f"<div class='sidebar-kv'><b>Geo-awareness</b>: {row.get('geo_awareness','unknown')}</div>"
            f"<div class='sidebar-kv'><b>Released</b>: {row.get('year_released','—')}</div>",
            unsafe_allow_html=True,
        )

        # Credentials (compact)
        st.sidebar.markdown("<div class='sidebar-title'>Your credentials</div>", unsafe_allow_html=True)
        have_op   = st.sidebar.checkbox("Operator ID", value=False, key="c_op")
        have_fl   = st.sidebar.checkbox("Flyer ID (basic test)", value=False, key="c_fl")
        have_a1a3 = st.sidebar.checkbox("A1/A3 training (optional)", value=False, key="c_a1a3")
        have_a2   = st.sidebar.checkbox("A2 CofC", value=False, key="c_a2")
        have_gvc  = st.sidebar.checkbox("GVC", value=False, key="c_gvc")
        have_oa   = st.sidebar.checkbox("OA (Operational Authorisation)", value=False, key="c_oa")
        creds = dict(op=have_op, flyer=have_fl, a1a3=have_a1a3, a2=have_a2, gvc=have_gvc, oa=have_oa)

        # Legend in sidebar
        st.sidebar.markdown(
            """
<div class='legend'>
  <div class='sidebar-title' style='margin:0 0 6px'>Legend</div>
  <span class='badge badge-allowed'>Allowed</span>
  <span class='badge badge-possible'>Possible (additional requirements)</span>
  <span class='badge badge-oagvc'>Available via OA/GVC</span>
  <span class='badge badge-na'>Not applicable</span>
</div>
""",
            unsafe_allow_html=True,
        )

        # --------- Compute all bricks ---------
        a_now = compute_bricks(row, creds, 2025)
        a_26  = compute_bricks(row, creds, 2026)
        a_28  = compute_bricks(row, creds, 2028)

        # ---------- HEADERS (NOW | 2026 | 2028) with column dividers ----------
        st.markdown(
            "<div class='grid3-headers divided'>"
            "<div class='hdrcell'>NOW</div>"
            "<div class='hdrcell'>2026</div>"
            "<div class='hdrcell'>2028 (planned)</div>"
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
        # Row 2: A2 across 3 cells
        st.markdown(
            "<div class='grid3 divided'>"
            f"<div>{a_now[1]}</div>"
            f"<div>{a_26[1]}</div>"
            f"<div>{a_28[1]}</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        # Row 3: A3 across 3 cells
        st.markdown(
            "<div class='grid3 divided'>"
            f"<div>{a_now[2]}</div>"
            f"<div>{a_26[2]}</div>"
            f"<div>{a_28[2]}</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        # Row 4: Specific across 3 cells
        st.markdown(
            "<div class='grid3 divided'>"
            f"<div>{a_now[3]}</div>"
            f"<div>{a_26[3]}</div>"
            f"<div>{a_28[3]}</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    else:
        # No model selected -> models grid
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
