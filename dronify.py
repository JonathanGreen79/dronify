# dronify.py — Navigation (stage 1/2/3) + robust image resolver + sidebar
# + 3x4 compliance grid (Current / 2026 / 2028 × A1/A2/A3/Specific bricks)
# Bricks now reflect tech compliance (Remote ID, Geo-awareness) from YAML.

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

    # Ensure all columns exist
    for col in (
        "image_url", "segment", "series", "marketing_name", "model_key",
        "mtom_g_nominal",
        "eu_class_marking", "uk_class_marking",
        "has_camera", "geo_awareness", "remote_id_builtin", "operator_id_required",
        "year_released", "notes"
    ):
        if col not in df.columns:
            df[col] = ""

    # Normalized for filtering
    df["segment_norm"] = df["segment"].astype(str).str.strip().str.lower()
    df["series_norm"]  = df["series"].astype(str).str.strip().str.lower()

    return df, taxonomy

df, taxonomy = load_data()

# ------------------------------- Query params -------------------------------

def get_qp():
    try:
        return dict(st.query_params)  # Streamlit ≥1.32
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
    Robustly resolve image references:
    - absolute http(s)/data: returned as-is
    - 'images/...' -> RAW_BASE + path
    - bare filename -> 'images/<filename>'
    - trims duplicate/leading slashes
    """
    u = (url or "").strip()
    if not u:
        return ""
    low = u.lower()
    if low.startswith("http://") or low.startswith("https://") or low.startswith("data:"):
        return u
    # normalise
    p = u.replace("\\", "/").lstrip("/")
    # if already starts with images/, keep only one images/ segment
    while p.lower().startswith("images/"):
        p = p.split("/", 1)[1] if "/" in p else ""
    if not p:
        return ""
    return RAW_BASE + "images/" + p

SEGMENT_HERO = {
    "consumer": resolve_img("images/consumer.jpg"),
    "pro":       resolve_img("images/professional.jpg"),
    "enterprise":resolve_img("images/enterprise.jpg"),
}
EU_FLAG = resolve_img("images/eu.png")
UK_FLAG = resolve_img("images/uk.png")

# ------------------------------- Helpers -------------------------------

def series_defs_for(segment_key: str):
    seg = next(s for s in taxonomy["segments"] if s["key"] == segment_key)
    present = set(
        df.loc[df["segment_norm"] == segment_key, "series_norm"].dropna().unique().tolist()
    )
    return [s for s in seg["series"] if s["key"] in present]

def pad_digits_for_natural(s: pd.Series, width: int = 6) -> pd.Series:
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

def coalesce(*vals, default=""):
    for v in vals:
        s = str(v or "").strip()
        if s:
            return s
    return default

def _to_int(x):
    try: return int(str(x).strip())
    except Exception: return None

# ------------------------------- Styles -------------------------------

st.markdown("""
<style>
.block-container { padding-top: 1.0rem; }

/* Cards */
.card {
  width: 260px; height: 240px; border: 1px solid #E5E7EB; border-radius: 14px;
  background: #fff; text-decoration: none !important; color: #111827 !important;
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
.h1 { font-weight:800; font-size:1.2rem; color:#1F2937; margin:0 0 12px 0; }

/* Sidebar */
.sidebar-title { font-weight:800; font-size:1.05rem; margin-top:.6rem; }
.sidebar-kv { margin:.18rem 0; color:#374151; font-size:.95rem; }
.sidebar-back { margin-top:0.5rem; display:inline-block; text-decoration:none; color:#2563EB; font-weight:600; }
.sidebar-back:hover { text-decoration: underline; }
.flag-row { display:flex; align-items:center; gap:10px; margin:.25rem 0; }
.flag-row img { width:20px; height:20px; border-radius:3px; object-fit:cover; }

/* Pills */
.badge { display:inline-block; padding:6px 10px; border-radius:999px; font-weight:600; font-size:.82rem; }
.badge-red { background:#FEE2E2; color:#991B1B; }
.badge-green { background:#DCFCE7; color:#14532D; }
.badge-grey { background:#F3F4F6; color:#6B7280; }

/* Bricks grid */
.compliance-row { display:grid; grid-template-columns: 1fr 1fr 1fr; gap: 24px; }
.col-box { padding-right: 16px; border-right: 1px solid #E5E7EB; }
.col-box:last-child { border-right: none; padding-right: 0; }

.col-title { font-weight:800; font-size:1.15rem; margin:0 0 .6rem 0; }

.brick {
  border-radius: 14px; padding: 12px 12px 10px 12px; margin-bottom: 10px; border: 1px solid #E5E7EB;
  box-shadow: 0 4px 10px rgba(0,0,0,.04);
}
.brick-ok   { background:#F0FDF4; }  /* green */
.brick-info { background:#EFF6FF; }  /* blue */
.brick-warn { background:#FFFBEB; }  /* amber */
.brick-na   { background:#F9FAFB; }  /* grey */

.brick-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:6px; }
.brick-title { font-weight:800; font-size:1rem; }
.brick-badge { font-weight:700; font-size:.9rem; padding:6px 10px; border-radius:999px; }

.b-ok   { background:#22C55E; color:white; }
.b-info { background:#2563EB; color:white; }
.b-warn { background:#D97706; color:white; }
.b-na   { background:#9CA3AF; color:white; }

.brick-line { margin:4px 0; color:#374151; font-size:.92rem; }
.brick-sub { color:#6B7280; font-size:.85rem; margin-top:2px; }

.kv-row { display:flex; flex-wrap:wrap; gap:6px; margin-top:6px; }
.kv-pill { padding:4px 8px; border-radius:999px; font-weight:600; font-size:.8rem; }
.kv-red { background:#FEE2E2; color:#991B1B; }
.kv-green { background:#DCFCE7; color:#14532D; }
.kv-grey { background:#F3F4F6; color:#374151; }

/* Legend */
.legend { margin-top: 14px; display:flex; gap:10px; flex-wrap:wrap; color:#374151; font-size:.9rem; }
.legend .chip { padding:4px 10px; border-radius:999px; font-weight:700; }
.legend .ok   { background:#22C55E; color:white; }
.legend .info { background:#2563EB; color:white; }
.legend .warn { background:#D97706; color:white; }
.legend .na   { background:#9CA3AF; color:white; }
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

# ------------------------------- Compliance bricks -------------------------------

def _is_c0(eu_cls: str, weight: int | None) -> bool:
    e = (eu_cls or "").strip().upper()
    return (e == "C0") or (weight is not None and weight < 250)

def _a2_applicable(eu_cls: str) -> bool:
    # Conservative: mainly C2. You may expand to ("C1","C2") if desired.
    e = (eu_cls or "").strip().upper()
    return e == "C2"

def _era_requirements(row: pd.Series, era: str):
    """Return (oper, flyer, rid_required, rid_has, rid_unknown, geo_required, geo_has, geo_unknown)"""
    weight = _to_int(row.get("mtom_g_nominal"))
    has_cam = str(row.get("has_camera", "")).strip().lower() == "yes"

    rid_val = str(row.get("remote_id_builtin", "unknown")).strip().lower()
    geo_val = str(row.get("geo_awareness", "unknown")).strip().lower()

    rid_has = (rid_val == "yes")
    rid_unknown = (rid_val == "unknown")

    geo_has = (geo_val == "yes")
    geo_unknown = (geo_val == "unknown")

    # Operator ID: camera => required (all eras)
    oper = has_cam

    # Flyer ID:
    if era == "current":
        flyer = has_cam or (weight is not None and weight >= 250)
    else:
        flyer = has_cam and (weight is not None and weight > 100)

    # Remote ID requirement per era
    if era == "current":
        rid_required = False  # modern drones often have it; not mandated for all legacy today
    else:
        rid_required = True

    # Geo-awareness requirement per era
    if era == "current":
        geo_required = False
    elif era == "2026":
        geo_required = True
    else:  # 2028 (planned)
        geo_required = has_cam and (weight is not None and weight >= 100)

    return oper, flyer, rid_required, rid_has, rid_unknown, geo_required, geo_has, geo_unknown

def _badge_state(required: bool, has_it: bool, unknown: bool, label: str) -> tuple[str, str]:
    """Return (badge_html, tone_component) where tone_component in {'ok','warn','na'}."""
    if unknown:
        return (f"<span class='kv-pill kv-grey'>{label}: Unknown</span>", "na")
    if required:
        if has_it:
            return (f"<span class='kv-pill kv-green'>{label}: OK</span>", "ok")
        else:
            return (f"<span class='kv-pill kv-red'>{label}: Required</span>", "warn")
    # not required:
    if has_it:
        return (f"<span class='kv-pill kv-green'>{label}: Onboard</span>", "ok")
    else:
        return (f"<span class='kv-pill kv-grey'>{label}: Not required</span>", "ok")

def _badge_required(needed: bool, label: str):
    return f"<span class='kv-pill {'kv-red' if needed else 'kv-green'}'>{label}: {'Required' if needed else 'Not required'}</span>"

def _brick(title: str, status: str, tone: str, separation: str, toel: str,
           quals: list[str], tech: list[str]) -> str:
    tone_cls = {"ok":"brick-ok","info":"brick-info","warn":"brick-warn","na":"brick-na"}.get(tone,"brick-na")
    chip_cls = {"ok":"b-ok","info":"b-info","warn":"b-warn","na":"b-na"}.get(tone,"b-na")
    quals_html = " ".join(quals)
    tech_html  = " ".join(tech)
    return f"""
    <div class="brick {tone_cls}">
      <div class="brick-head">
        <div class="brick-title">{title}</div>
        <div class="brick-badge {chip_cls}">{status}</div>
      </div>
      <div class="brick-line">{separation}</div>
      <div class="brick-sub">{toel}</div>
      <div class="kv-row">{quals_html}</div>
      <div class="kv-row">{tech_html}</div>
    </div>
    """

def _combine_tone(base: str, tech_tones: list[str]) -> str:
    """Escalate tone if any tech check fails. Priority: ok < info < warn < na"""
    order = {"ok":0, "info":1, "warn":2, "na":3}
    t = base
    for tt in tech_tones:
        if order.get(tt,0) > order.get(t,0):
            t = tt
    return t

def _brick_sets(row: pd.Series, era: str):
    """Build A1/A2/A3/Specific bricks for a given era, adjusting tone by tech compliance."""
    eu = coalesce(row.get("eu_class_marking"), row.get("class_marking")).upper()
    weight = _to_int(row.get("mtom_g_nominal"))
    is_c0 = _is_c0(eu, weight)
    a2_ok = _a2_applicable(eu)

    oper, flyer, rid_req, rid_has, rid_unknown, geo_req, geo_has, geo_unknown = _era_requirements(row, era)

    op_b   = _badge_required(oper, "Operator ID")
    fly_b  = _badge_required(flyer, "Flyer ID (basic test)")

    rid_b, rid_tone   = _badge_state(rid_req, rid_has, rid_unknown, "Remote ID")
    geo_b, geo_tone   = _badge_state(geo_req, geo_has, geo_unknown, "Geo-awareness")

    tech_tones = [rid_tone, geo_tone]

    bricks = []

    # A1
    if is_c0 or eu == "C1":
        base_tone = "ok"
        tone = _combine_tone(base_tone, tech_tones)
        bricks.append(_brick(
            "A1 — Close to people",
            "Allowed",
            tone,
            "Fly close to people; avoid assemblies/crowds.",
            "TOAL: sensible separation; follow local restrictions.",
            [op_b, fly_b], [rid_b, geo_b]
        ))
    else:
        bricks.append(_brick(
            "A1 — Close to people",
            "Not applicable",
            "na",
            "A1 primarily for C0/C1 class drones.",
            "Use A3 or Specific instead for heavier classes.",
            [op_b, fly_b], [rid_b, geo_b]
        ))

    # A2
    if a2_ok:
        base_tone = "info"
        tone = _combine_tone(base_tone, tech_tones)
        bricks.append(_brick(
            "A2 — Close with A2 CofC",
            "Allowed with A2 CofC",
            tone,
            "Keep ≥ 50 m from uninvolved people.",
            "TOAL: safe distance; follow manufacturer guidance.",
            [op_b, fly_b, "<span class='kv-pill kv-red'>A2 CofC: Required</span>"],
            [rid_b, geo_b]
        ))
    else:
        bricks.append(_brick(
            "A2 — Close with A2 CofC",
            "Not applicable",
            "na",
            "A2 mainly for C2 drones (sometimes C1 by nuance).",
            "This model cannot use A2; consider A1 or A3/Specific.",
            [op_b, fly_b, "<span class='kv-pill kv-grey'>A2 CofC: N/A</span>"],
            [rid_b, geo_b]
        ))

    # A3
    base_tone = "info"
    tone = _combine_tone(base_tone, tech_tones)
    bricks.append(_brick(
        "A3 — Far from people",
        "Allowed",
        tone,
        "Keep ≥ 150 m from residential/commercial/recreational areas.",
        "TOAL: well away from uninvolved people and built-up areas.",
        [op_b, fly_b], [rid_b, geo_b]
    ))

    # Specific
    base_tone = "warn"
    tone = _combine_tone(base_tone, tech_tones)
    bricks.append(_brick(
        "Specific — OA / GVC",
        "Available via OA/GVC",
        tone,
        "Risk-assessed operations per OA; distances per ops manual.",
        "TOAL & mitigations defined by your approved procedures.",
        [op_b, fly_b, "<span class='kv-pill kv-red'>GVC: Required</span>", "<span class='kv-pill kv-red'>OA: Required</span>"],
        [rid_b, geo_b]
    ))

    return "\n".join(bricks)

def render_compliance_grid(row: pd.Series):
    # Render grid with headers + vertical dividers + legend
    col_html = f"""
    <div class='compliance-row'>
      <div class='col-box'>
        <div class='col-title'>Current</div>
        {_brick_sets(row, "current")}
      </div>
      <div class='col-box'>
        <div class='col-title'>2026</div>
        {_brick_sets(row, "2026")}
      </div>
      <div class='col-box'>
        <div class='col-title'>2028 (planned)</div>
        {_brick_sets(row, "2028")}
      </div>
    </div>
    <div class='legend'>
      <span>Legend:</span>
      <span class='chip ok'>Allowed</span>
      <span class='chip info'>Allowed with additional conditions (e.g., A2 CofC)</span>
      <span class='chip warn'>Available with caveats / tech shortfall to resolve</span>
      <span class='chip na'>Not applicable</span>
    </div>
    """
    st.markdown(col_html, unsafe_allow_html=True)

# ------------------------------- UI flow -------------------------------

if not segment:
    # Stage 1 — categories
    items = []
    for seg in taxonomy["segments"]:
        img = SEGMENT_HERO.get(seg["key"], "")
        items.append(card_link(f"segment={seg['key']}", seg["label"], img_url=img))
    render_row("Choose your drone category", items)

elif not series:
    # Stage 2 — series (random image per series)
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    items = []
    for s in series_defs_for(segment):
        rnd_img = random_image_for_series(segment, s["key"])
        items.append(card_link(f"segment={segment}&series={s['key']}", s["label"], img_url=rnd_img))
    render_row(f"Choose a series ({seg_label})", items)

else:
    # Stage 3 — grid or details
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    ser_label = next(s["label"] for s in series_defs_for(segment) if s["key"] == series)

    if model:
        sel = df[df["model_key"] == model]
        if not sel.empty:
            row = sel.iloc[0]

            # Sidebar
            back_qs = f"segment={segment}&series={series}"
            st.sidebar.markdown(
                f"<a class='sidebar-back' href='?{back_qs}' target='_self'>← Back to models</a>",
                unsafe_allow_html=True
            )

            img_url = resolve_img(row.get("image_url", ""))
            if img_url:
                st.sidebar.image(img_url, use_container_width=True, caption=row.get("marketing_name", ""))

            eu_cls = coalesce(row.get("eu_class_marking"), row.get("class_marking"), default="unknown")
            uk_cls = coalesce(row.get("uk_class_marking"), row.get("class_marking"), default="unknown")
            st.sidebar.markdown(
                f"<div class='flag-row'><img src='{EU_FLAG}' alt='EU'/>"
                f"<span>EU: <b>{eu_cls}</b></span></div>", unsafe_allow_html=True
            )
            st.sidebar.markdown(
                f"<div class='flag-row'><img src='{UK_FLAG}' alt='UK'/>"
                f"<span>UK: <b>{uk_cls}</b></span></div>", unsafe_allow_html=True
            )

            # Quick specs
            st.sidebar.markdown("<div class='sidebar-title'>Key specs</div>", unsafe_allow_html=True)
            mtow = row.get("mtom_g_nominal", "")
            mtow_str = f"{mtow} g" if str(mtow).strip() else "—"
            rid = str(row.get("remote_id_builtin", "unknown")).strip() or "unknown"
            geo = str(row.get("geo_awareness", "unknown")).strip() or "unknown"
            yr  = coalesce(row.get("year_released"), default="—")

            st.sidebar.markdown(
                f"<div class='sidebar-kv'><b>Model</b>: {row.get('marketing_name','—')}</div>"
                f"<div class='sidebar-kv'><b>MTOW</b>: {mtow_str}</div>"
                f"<div class='sidebar-kv'><b>Remote ID</b>: {rid}</div>"
                f"<div class='sidebar-kv'><b>Geo-awareness</b>: {geo}</div>"
                f"<div class='sidebar-kv'><b>Released</b>: {yr}</div>",
                unsafe_allow_html=True
            )

            # Main body — 3×4 bricks with headers, dividers, legend
            render_compliance_grid(row)

        else:
            model = None  # fall back to grid

    # Models grid
    if not model:
        items = []
        models = models_for(segment, series)
        for _, r in models.iterrows():
            eu_c = coalesce(r.get("eu_class_marking"), r.get("class_marking"))
            uk_c = coalesce(r.get("uk_class_marking"), r.get("class_marking"))
            yr = str(r.get("year_released", "") or "").strip()
            parts = []
            if eu_c or uk_c:
                parts.append(f"Class: EU {eu_c if eu_c else '—'} • UK {uk_c if uk_c else '—'}")
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
