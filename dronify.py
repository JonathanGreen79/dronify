# dronify.py — 3-column compliance view with era-aware badges + hover tooltips
# (Updated: Current-era Remote ID/Geo show green if the drone has them;
#           explicit NOW/2026/2028 headers; improved legend wording)

import streamlit as st
import pandas as pd
import yaml
from pathlib import Path

st.set_page_config(page_title="Dronify", layout="wide")

DATASET_PATH = Path("dji_drones_v3.yaml")
TAXONOMY_PATH = Path("taxonomy.yaml")

# -------------------- Data loading --------------------
def load_yaml(p: Path):
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@st.cache_data
def load_data():
    dataset = load_yaml(DATASET_PATH)
    taxonomy = load_yaml(TAXONOMY_PATH)
    df = pd.DataFrame(dataset["data"])
    for col in [
        "model_key","marketing_name","segment","series","mtom_g_nominal",
        "eu_class_marking","uk_class_marking","year_released",
        "has_camera","geo_awareness","remote_id_builtin","operator_id_required",
        "image_url","notes"
    ]:
        if col not in df.columns:
            df[col] = ""
    df["mtom_g_nominal"] = pd.to_numeric(df["mtom_g_nominal"], errors="coerce")
    return df, taxonomy

df, taxonomy = load_data()

# -------------------- Query params --------------------
def get_qp():
    try:
        return dict(st.query_params)
    except Exception:
        return {k: (v[0] if isinstance(v, list) else v)
                for k, v in st.experimental_get_query_params().items()}

qp = get_qp()
segment = qp.get("segment")
series  = qp.get("series")
model   = qp.get("model")

# -------------------- Image resolver --------------------
RAW_BASE = "https://raw.githubusercontent.com/JonathanGreen79/dronify/main/images/"

def resolve_img(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    low = url.lower()
    if low.startswith(("http://","https://","data:")):
        return url
    if low.startswith("images/"):
        return RAW_BASE + url.split("/",1)[1]
    return RAW_BASE + url.lstrip("/")

SEGMENT_HERO = {
    "consumer": resolve_img("images/consumer.jpg"),
    "pro":       resolve_img("images/professional.jpg"),
    "enterprise":resolve_img("images/enterprise.jpg"),
}

# -------------------- Styles --------------------
st.markdown("""
<style>
.block-container { padding-top: 1rem; }

/* cards in stages 1/2/3 */
.card {
  width: 260px; height: 240px; border: 1px solid #E5E7EB; border-radius: 14px;
  background: #fff; text-decoration: none !important; color: #111827 !important;
  display: block; padding: 12px; transition:.15s; cursor: pointer;
}
.card:hover { border-color:#D1D5DB; box-shadow:0 6px 18px rgba(0,0,0,.08); transform:translateY(-2px); }
.img { width:100%; height:150px; border-radius:10px; background:#F3F4F6; overflow:hidden; display:flex; align-items:center; justify-content:center; }
.img>img { width:100%; height:100%; object-fit:cover; }
.title { margin-top:10px; text-align:center; font-weight:700; font-size:.98rem; }
.sub { margin-top:4px; text-align:center; font-size:.8rem; color:#6B7280; }

.strip { display:flex; gap:14px; overflow-x:auto; padding:8px 2px; }
.strip2 { display:grid; grid-auto-flow:column; grid-auto-columns:260px; grid-template-rows:repeat(2,1fr); gap:14px; overflow-x:auto; padding:8px 2px; }
.h1 { font-weight:800; font-size:1.2rem; color:#1F2937; margin:0 0 12px 0; }

/* sidebar */
.sidebar-title { font-weight:800; font-size:1.05rem; margin-top:.6rem; }
.sidebar-kv { margin:.15rem 0; color:#374151; font-size:.93rem; }
.sidebar-muted { color:#6B7280; font-size:.85rem; }
.sidebar-back { margin-top:.35rem; display:inline-block; text-decoration:none; color:#2563EB; font-weight:600; }
.sidebar-back:hover { text-decoration:underline; }

/* status chip */
.chip { display:inline-block; padding:3px 8px; border-radius:999px; font-weight:700; font-size:.80rem; }
.chip-ok { background:#DCFCE7; color:#14532D; }
.chip-info { background:#DBEAFE; color:#1E3A8A; }
.chip-warn { background:#FEF3C7; color:#92400E; }
.chip-na { background:#E5E7EB; color:#374151; }

/* bricks */
.brick { border-radius:14px; padding:14px; border:1px solid #E5E7EB; margin-bottom:14px; }
.brick-ok   { background:#F0FDF4; border-color:#A7F3D0; }
.brick-info { background:#EFF6FF; border-color:#BFDBFE; }
.brick-warn { background:#FFFBEB; border-color:#FDE68A; }
.brick-na   { background:#F3F4F6; border-color:#E5E7EB; }

.line { border-top:1px dashed #E5E7EB; margin:8px 0 12px 0; }

/* badges inside bricks */
.badge { display:inline-block; margin:4px 6px 0 0; padding:4px 8px; border-radius:999px; font-size:.80rem; border:1px solid transparent; }
.badge-ok { background:#ECFDF5; color:#065F46; border-color:#A7F3D0; }
.badge-missing { background:#FEE2E2; color:#7F1D1D; border-color:#FCA5A5; }
.badge-neutral { background:#F3F4F6; color:#374151; border-color:#E5E7EB; }

/* legend */
.legend { display:flex; gap:10px; flex-wrap:wrap; margin-top:.75rem; }
.legend .chip { font-weight:600; }
.small { font-size:.86em; color:#4B5563; }
</style>
""", unsafe_allow_html=True)

# -------------------- Helpers --------------------
def card_link(qs: str, title: str, sub: str = "", img_url: str = "") -> str:
    img = f"<div class='img'><img src='{img_url}' alt=''/></div>" if img_url else "<div class='img'></div>"
    sub_html = f"<div class='sub'>{sub}</div>" if sub else ""
    return f"<a class='card' href='?{qs}' target='_self'>{img}<div class='title'>{title}</div>{sub_html}</a>"

def render_row(title: str, items: list[str]):
    st.markdown(f"<div class='h1'>{title}</div><div class='strip'>{''.join(items)}</div>", unsafe_allow_html=True)

def render_two_rows(title: str, items: list[str]):
    st.markdown(f"<div class='h1'>{title}</div><div class='strip2'>{''.join(items)}</div>", unsafe_allow_html=True)

def chip(label, tone="info"):
    cls = {"ok":"chip-ok","info":"chip-info","warn":"chip-warn","na":"chip-na"}[tone]
    return f"<span class='chip {cls}'>{label}</span>"

def badge(label, state="ok", tooltip:str|None=None):
    cls = {"ok":"badge-ok","missing":"badge-missing","neutral":"badge-neutral"}[state]
    title = f" title='{tooltip}'" if tooltip else ""
    return f"<span class='badge {cls}'{title}>{label}</span>"

# -------------------- Stage 1/2 helpers --------------------
def series_defs_for(segment_key: str):
    seg = next(s for s in taxonomy["segments"] if s["key"] == segment_key)
    present = set(df.loc[df["segment"]==segment_key, "series"].dropna().unique().tolist())
    return [s for s in seg["series"] if s["key"] in present]

def models_for(segment_key: str, series_key: str):
    subset = df[(df["segment"]==segment_key) & (df["series"]==series_key)].copy()
    subset["name_key"] = subset["marketing_name"].str.lower().str.replace(
        r"\d+", lambda m: f"{int(m.group(0)):06d}", regex=True
    )
    subset = subset.sort_values(by=["name_key","marketing_name"], kind="stable", ignore_index=True)
    return subset.drop(columns=["name_key"])

import random
def random_image_for_series(segment_key: str, series_key: str) -> str:
    subset = df[(df["segment"]==segment_key)&(df["series"]==series_key)]
    subset = subset[subset["image_url"].astype(str).str.strip()!=""]
    if subset.empty: return SEGMENT_HERO.get(segment_key,"")
    return resolve_img(str(subset.sample(1)["image_url"].iloc[0]))

# -------------------- Era rules + tooltips --------------------
ERA_LIST = [
    ("current","Now"),
    ("2026","2026"),
    ("2028","2028 (planned)"),
]

def needs_rid(era: str) -> bool:
    return era in ("2026","2028")

def needs_geo(era: str, mtom_g: float|None, has_cam: bool) -> bool:
    if era=="current": return False
    if era=="2026":    return True
    if era=="2028":    return True
    return False

def tooltip_operator(era:str) -> str:
    if era=="current":
        return "UK: Operator ID is required for any drone with a camera (including sub-250 g)."
    if era=="2026":
        return "From 2026: Operator ID continues to be required for camera drones (Open Category)."
    return "Planned 2028: Operator ID remains required; legacy camera drones also in scope."

def tooltip_flyer(era:str) -> str:
    if era=="current":
        return "UK: Flyer ID is required for anyone flying a drone with a camera, regardless of weight (non-toy)."
    if era=="2026":
        return "From 2026: Flyer ID required for camera drones over 100 g."
    return "Planned 2028: Requirement extends to legacy drones ≥100 g with a camera."

def tooltip_rid(era:str) -> str:
    if era=="current":
        return "Remote ID not generally required in UK Open Category (today). If your drone has it, great."
    return "Remote ID (Direct) must broadcast drone & operator info in flight."

def tooltip_geo(era:str) -> str:
    if era=="current":
        return "Geo-awareness not mandatory in UK Open Category (today). If your drone has it, even better."
    if era=="2026":
        return "From 2026: Geo-awareness is required (e.g., map-based restricted airspace warnings)."
    return "Planned 2028: Geo-awareness also required for some smaller (UK0) drones (≥100 g with camera)."

# -------------------- Brick computation --------------------
def class_allows_a2(eu_class:str) -> bool:
    return str(eu_class or "").strip().upper()=="C2"

def cred_badges(era:str, row:pd.Series, user:dict):
    """
    Return badges + requirement flags.
    In 'current' era, RID/Geo are not required, but if the drone HAS them,
    we show them green (ok); otherwise grey (neutral).
    """
    mtom = float(row.get("mtom_g_nominal") or 0)
    has_cam = str(row.get("has_camera") or "yes").lower()=="yes"

    rid_req  = needs_rid(era)
    geo_req  = needs_geo(era, mtom, has_cam)

    out = []

    # Operator/Flyer simple (we keep required across eras per current UK notes)
    op_required   = True
    flyer_needed  = True

    # Operator ID
    op_state = "ok" if user.get("op_id") else ("missing" if op_required else "neutral")
    out.append(badge("Operator ID: " + ("Have" if op_state=="ok" else "Required" if op_state=="missing" else "—"),
                     op_state, tooltip_operator(era)))

    # Flyer ID
    fly_state = "ok" if user.get("flyer_id") else ("missing" if flyer_needed else "neutral")
    out.append(badge("Flyer ID: " + ("Have" if fly_state=="ok" else "Required" if fly_state=="missing" else "—"),
                     fly_state, tooltip_flyer(era)))

    # Remote ID
    drone_has_rid = str(row.get("remote_id_builtin") or "unknown").lower()=="yes"
    if rid_req:
        rid_state = "ok" if drone_has_rid else "missing"
    else:
        rid_state = "ok" if drone_has_rid else "neutral"  # <<< show green if drone has it now
    rid_label = "Remote ID: " + ("OK" if rid_state in ("ok","neutral") and drone_has_rid else ("OK" if rid_state=="ok" else "Required" if rid_req else "—"))
    out.append(badge(rid_label, rid_state, tooltip_rid(era)))

    # Geo-awareness
    drone_geo = str(row.get("geo_awareness") or "unknown").lower()=="yes"
    if geo_req:
        geo_state = "ok" if drone_geo else "missing"
    else:
        geo_state = "ok" if drone_geo else "neutral"     # <<< show green if drone has it now
    geo_label = "Geo-awareness: " + ("Onboard" if (drone_geo or geo_state=="ok") else ("Required" if geo_req else "—"))
    out.append(badge(geo_label, geo_state, tooltip_geo(era)))

    return out, {
        "op_ok": (op_state=="ok"),
        "fly_ok": (fly_state=="ok"),
        "rid_ok": (rid_state in ("ok","neutral") if not rid_req else rid_state=="ok"),
        "geo_ok": (geo_state in ("ok","neutral") if not geo_req else geo_state=="ok"),
    }

def brick_status_allowed(requirements:dict):
    all_ok = requirements["op_ok"] and requirements["fly_ok"] and requirements["rid_ok"] and requirements["geo_ok"]
    return ("ok" if all_ok else "info"), ("Allowed" if all_ok else "Possible (needs credentials/tech)")

def render_brick(title:str, desc:str, cred_html:list[str], tone:str, status_label:str, right_tag:str|None=None):
    tone_cls = {"ok":"brick-ok","info":"brick-info","warn":"brick-warn","na":"brick-na"}[tone]
    chip_tone = {"ok":"ok","info":"info","warn":"warn","na":"na"}[tone]
    head = f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
    head += f"<div style='font-weight:800'>{title}</div>"
    head += chip(status_label, chip_tone)
    if right_tag:
        head += chip(right_tag, "na")
    head += "</div>"
    st.markdown(f"<div class='brick {tone_cls}'>{head}<div class='line'></div><div class='small'>{desc}</div><div style='margin-top:6px'>{''.join(cred_html)}</div></div>", unsafe_allow_html=True)

def section_for_era(era_key:str, era_label:str, row:pd.Series, user:dict):
    # VERY explicit column headers so they can't be missed
    st.markdown(f"### {era_label}")

    # --- A1
    cred_html, req_flags = cred_badges(era_key, row, user)
    tone, label = brick_status_allowed(req_flags)
    desc = "Fly close to people; avoid assemblies/crowds. TOAL: sensible separation; follow local restrictions."
    render_brick("A1 — Close to people", desc, cred_html, tone, label)

    # --- A2
    can_a2 = class_allows_a2(row.get("eu_class_marking",""))
    if not can_a2:
        cred_html, req_flags = cred_badges(era_key, row, user)
        render_brick("A2 — Close with A2 CofC",
                     "A2 mainly for C2 drones (sometimes C1 by nuance). This model cannot use A2; consider A1 or A3/Specific.",
                     cred_html, "na", "Not applicable", right_tag="A2 CofC: N/A")
    else:
        cred_html, req_flags = cred_badges(era_key, row, user)
        if req_flags["op_ok"] and req_flags["fly_ok"] and req_flags["rid_ok"] and req_flags["geo_ok"] and user.get("a2_cofc"):
            tone, label = "ok", "Allowed (A2 CofC)"
        else:
            tone, label = "info", "Needs A2 CofC"
        desc = "Stand off from people (C2); keep within A2 limits. TOAL: observe local restrictions."
        render_brick("A2 — Close with A2 CofC", desc, cred_html, tone, label, right_tag=("A2 CofC: Have" if user.get("a2_cofc") else "A2 CofC: Needed"))

    # --- A3
    cred_html, req_flags = cred_badges(era_key, row, user)
    tone, label = brick_status_allowed(req_flags)
    desc = "Keep ≥ 150 m from residential/commercial/recreational areas. TOAL: well away from uninvolved people and built-up areas."
    render_brick("A3 — Far from people", desc, cred_html, tone, label)

    # --- Specific (OA/GVC)
    cred_html, req_flags = cred_badges(era_key, row, user)
    has_all = req_flags["op_ok"] and req_flags["fly_ok"] and req_flags["rid_ok"] and req_flags["geo_ok"] and user.get("gvc") and user.get("oa")
    tone = "ok" if has_all else "warn"
    label = "Allowed (OA/GVC)" if has_all else "Available via OA/GVC"
    cred_html.append(badge("GVC: " + ("Have" if user.get("gvc") else "Required"), "ok" if user.get("gvc") else "missing"))
    cred_html.append(badge("OA: " + ("Have" if user.get("oa") else "Required"), "ok" if user.get("oa") else "missing"))
    desc = "Risk-assessed operations per OA; distances per ops manual. TOAL & mitigations defined by your approved procedures."
    render_brick("Specific — OA / GVC", desc, cred_html, tone, label)

# -------------------- Screen routing --------------------
if not segment:
    items = []
    for seg in taxonomy["segments"]:
        items.append(card_link(f"segment={seg['key']}", seg["label"], img_url=SEGMENT_HERO.get(seg["key"], "")))
    render_row("Choose your drone category", items)

elif not series:
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    items = []
    for s in series_defs_for(segment):
        items.append(card_link(f"segment={segment}&series={s['key']}", s["label"], img_url=random_image_for_series(segment, s["key"])))
    render_row(f"Choose a series ({seg_label})", items)

else:
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    ser_label = next(s["label"] for s in series_defs_for(segment) if s["key"] == series)

    if model:
        sel = df[df["model_key"] == model]
        if not sel.empty:
            row = sel.iloc[0]

            # ----- Sidebar -----
            st.sidebar.markdown(f"<a class='sidebar-back' href='?segment={segment}&series={series}' target='_self'>← Back to models</a>", unsafe_allow_html=True)
            img_url = resolve_img(row.get("image_url",""))
            if img_url:
                st.sidebar.image(img_url, caption=row.get("marketing_name",""), use_container_width=True)

            # EU/UK badges with flags
            eu = (row.get("eu_class_marking") or "unknown")
            uk = (row.get("uk_class_marking") or "unknown")
            eu_flag = resolve_img("images/eu.png")
            uk_flag = resolve_img("images/uk.png")
            st.sidebar.markdown(f"<div><img src='{eu_flag}' width='20' style='vertical-align:middle;margin-right:6px'> EU: <b>{eu}</b></div>", unsafe_allow_html=True)
            st.sidebar.markdown(f"<div><img src='{uk_flag}' width='20' style='vertical-align:middle;margin-right:6px'> UK: <b>{uk}</b></div>", unsafe_allow_html=True)

            # Key specs
            st.sidebar.markdown("<div class='sidebar-title'>Key specs</div>", unsafe_allow_html=True)
            kv = [
                ("Model", row.get("marketing_name","—")),
                ("MTOW", f"{int(row['mtom_g_nominal'])} g" if pd.notna(row["mtom_g_nominal"]) else "—"),
                ("Remote ID", row.get("remote_id_builtin","unknown")),
                ("Geo-awareness", row.get("geo_awareness","unknown")),
                ("Released", int(row["year_released"]) if str(row["year_released"]).strip().isdigit() else row.get("year_released","—")),
            ]
            for k,v in kv:
                st.sidebar.markdown(f"<div class='sidebar-kv'><b>{k}</b> : {v}</div>", unsafe_allow_html=True)

            # Credentials checkboxes
            st.sidebar.markdown("<div class='sidebar-title'>Your credentials</div>", unsafe_allow_html=True)
            op_id  = st.sidebar.checkbox("I have an Operator ID", value=False, key="op_id")
            flyer  = st.sidebar.checkbox("I have a Flyer ID (basic test)", value=False, key="flyer_id")
            a1a3   = st.sidebar.checkbox("I have A1/A3 training (optional)", value=False, key="a1a3_train")
            a2     = st.sidebar.checkbox("I have A2 CofC", value=False, key="a2_cofc")
            gvc    = st.sidebar.checkbox("I have GVC", value=False, key="gvc")
            oa     = st.sidebar.checkbox("I have an OA (Operational Authorisation)", value=False, key="oa")

            user = {"op_id": op_id, "flyer_id": flyer, "a1a3": a1a3, "a2_cofc": a2, "gvc": gvc, "oa": oa}

            # ----- Main columns -----
            c1, c2, c3 = st.columns([1,1,1], gap="large")
            for (ek, el), col in zip(ERA_LIST, [c1,c2,c3]):
                with col:
                    section_for_era(ek, el, row, user)

            # Legend
            st.markdown(
                "<div class='legend'>"
                f"{chip('Allowed','ok')}"
                f"{chip('Possible (needs credentials/tech)','info')}"
                f"{chip('Available via OA/GVC','warn')}"
                f"{chip('Not applicable','na')}"
                "</div>",
                unsafe_allow_html=True
            )

        else:
            model = None

    if not model:
        models = models_for(segment, series)
        items = []
        for _, r in models.iterrows():
            subparts = []
            eu_c = (r.get("eu_class_marking") or "").strip()
            uk_c = (r.get("uk_class_marking") or "").strip()
            if eu_c or uk_c:
                subparts.append(f"Class: EU {eu_c or '—'} • UK {uk_c or '—'}")
            yr = str(r.get("year_released","")).strip()
            if yr: subparts.append(f"Released: {yr}")
            sub = " • ".join(subparts)
            items.append(card_link(
                f"segment={segment}&series={series}&model={r['model_key']}",
                r.get("marketing_name",""),
                sub=sub,
                img_url=resolve_img(str(r.get("image_url","")))
            ))
        render_two_rows(f"Choose a drone ({seg_label} → {ser_label})", items)
