# dronify.py — streamlined compliance view with flags, credentials, and three-column rules

import streamlit as st
import pandas as pd
import yaml
from pathlib import Path

st.set_page_config(page_title="Dronify", layout="wide")

DATASET_PATH = Path("dji_drones_v3.yaml")
TAXONOMY_PATH = Path("taxonomy.yaml")  # not used here but kept for forward-compat

# ---------- Load ----------
def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@st.cache_data
def load_data():
    dataset = load_yaml(DATASET_PATH)
    df = pd.DataFrame(dataset["data"])
    # ensure columns exist (robust if file evolves)
    must = [
        "model_key","marketing_name","segment","series","mtom_g_nominal",
        "eu_class_marking","uk_class_marking","year_released",
        "has_camera","geo_awareness","remote_id_builtin",
        "operator_id_required","image_url","notes"
    ]
    for c in must:
        if c not in df.columns:
            df[c] = ""
    return df

df = load_data()

# ---------- Utilities ----------
RAW_BASE = "https://raw.githubusercontent.com/JonathanGreen79/dronify/main/images/"

def resolve_img(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    low = u.lower()
    if low.startswith("http://") or low.startswith("https://") or low.startswith("data:"):
        return u
    if low.startswith("images/"):
        return RAW_BASE + u.split("/", 1)[1]
    # bare filename
    return RAW_BASE + u.lstrip("/")

def pill(text: str, kind: str="ok", title: str=""):
    # kind: ok (green), need (red), info (blue)
    color = {"ok":"#DCFCE7","need":"#FEE2E2","info":"#DBEAFE"}[kind]
    fg    = {"ok":"#14532D","need":"#991B1B","info":"#1E40AF"}[kind]
    return f"""<span class="pill pill-{kind}" title="{title}" 
        style="display:inline-block;padding:6px 10px;border-radius:999px;background:{color};
        color:{fg};font-weight:600;font-size:.85rem;margin:4px 6px 0 0;border:1px solid rgba(0,0,0,.06);">
        {text}</span>"""

def badge(text: str, kind: str):
    # kind: allowed (green), possible (blue), na (grey), warn (orange)
    cfg = {
        "allowed": ("#E8F7EE", "#166534"),
        "possible": ("#EAF2FF", "#1E40AF"),
        "na": ("#F4F4F5", "#374151"),
        "warn": ("#FFF4E5", "#92400E")
    }[kind]
    return f"""<span class="badge badge-{kind}" 
        style="display:inline-block;padding:6px 10px;border-radius:999px;background:{cfg[0]};
        color:{cfg[1]};font-weight:800;border:1px solid rgba(0,0,0,.06);">{text}</span>"""

def card(title_html: str, badge_html: str, body_html: str, tone: str="possible"):
    # tone: allowed / possible / na / warn (colors for card background)
    bg = {
        "allowed": "#F0FFF4",
        "possible": "#F4F8FF",
        "na": "#F7F7F8",
        "warn": "#FFF9EB"
    }[tone]
    return f"""
    <div class="card {tone}" style="background:{bg};border:1px solid #E5E7EB;border-radius:12px;padding:16px 16px 12px 16px;margin:8px 0 20px 0;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
        <h4 style="margin:0;font-size:1.02rem;font-weight:800;color:#111827;">{title_html}</h4>
        {badge_html}
      </div>
      <div style="font-size:.92rem;color:#374151;line-height:1.35;">
        {body_html}
      </div>
    </div>
    """

# ---------- Styling ----------
st.markdown("""
<style>
/* Reduce sidebar whitespace slightly */
.sidebar .block-container { padding-top: .6rem !important; }
.block-container { padding-top: .9rem; }

/* Column dividers */
.columns-divide > div:not(:last-child) {
  border-right: 1px dashed #E5E7EB;
}
.columns-divide > div { padding-right: 16px; }

/* Compact checkboxes */
div[role="checkbox"] + label { margin-bottom: 0 !important; }

/* Small headings in sidebar */
.sb-h { font-weight:800; font-size: .88rem; color:#111827; margin: 6px 0 6px 0; }
.sb-kv { font-size:.9rem; color:#374151; margin:2px 0; display:flex; align-items:center; gap:8px; }
.sb-muted { color:#6B7280; font-size:.86rem; }

/* Tiny legend pills */
.legend li { margin: 2px 0; }
</style>
""", unsafe_allow_html=True)

# ---------- Query & selected model ----------
# Expect ?segment=...&series=...&model=...
qp = st.query_params
model_key = qp.get("model") or (qp.get("model",[None])[0] if isinstance(qp.get("model"), list) else None)

if not model_key:
    # If opened directly, just pick first model to avoid empty page.
    model_key = df.iloc[0]["model_key"]

row = df[df["model_key"] == model_key].iloc[0].to_dict()

# ---------- Sidebar ----------
with st.sidebar:
    # (Breadcrumb removed)
    st.markdown(f"<a href='?segment={row.get('segment','')}&series={row.get('series','')}' style='text-decoration:none;font-weight:700;'>← Back to models</a>", unsafe_allow_html=True)
    img_url = resolve_img(row.get("image_url", ""))
    if img_url:
        st.image(img_url, use_container_width=True, caption=row.get("marketing_name",""))

    st.markdown(f"<div class='sb-kv'><img src='https://flagcdn.com/w20/eu.png' width='20'> <b>EU:</b> {row.get('eu_class_marking') or 'unknown'}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sb-kv'><img src='https://flagcdn.com/w20/gb.png' width='20'> <b>UK:</b> {row.get('uk_class_marking') or 'unknown'}</div>", unsafe_allow_html=True)

    st.markdown("<div class='sb-h'>Key specs</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sb-kv'><b>Model</b>: {row.get('marketing_name','—')}</div>", unsafe_allow_html=True)
    mtom = row.get("mtom_g_nominal") or ""
    st.markdown(f"<div class='sb-kv'><b>MTOW</b>: {mtom if mtom else '—'} g</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sb-kv'><b>Remote ID</b>: {row.get('remote_id_builtin','unknown')}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sb-kv'><b>Geo-awareness</b>: {row.get('geo_awareness','unknown')}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sb-kv'><b>Released</b>: {row.get('year_released','—')}</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='sb-h'>Your credentials</div>", unsafe_allow_html=True)

    # Compact checkboxes (no "I have")
    st.checkbox("Operator ID", key="cred_opid", value=False)
    st.checkbox("Flyer ID (basic test)", key="cred_flyer", value=False)
    st.checkbox("A1/A3 training (optional)", key="cred_a1a3", value=False)
    st.checkbox("A2 CofC", key="cred_a2cofc", value=False)
    st.checkbox("GVC", key="cred_gvc", value=False)
    st.checkbox("OA (Operational Authorisation)", key="cred_oa", value=False)

    # Legend at bottom
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<div class='sb-h'>Legend</div>", unsafe_allow_html=True)
    st.markdown(
        """
        <ul class='legend' style="list-style:none;padding-left:0;margin:0;">
          <li>🟢 <b>Allowed</b></li>
          <li>🔵 <b>Possible</b> (additional requirements)</li>
          <li>🟡 <b>Available via OA/GVC</b></li>
          <li>⚪ <b>Not applicable</b></li>
        </ul>
        """, unsafe_allow_html=True
    )

# ---------- Compliance logic helpers ----------
def requires_flyer_id(mass_g: int, has_camera: bool, band: str) -> bool:
    # Simple policy that matches the app's current intent:
    # - NOW: Flyer ID required if camera (your own Mini 5 Pro case)
    # - 2026+: Flyer ID required if camera AND mass >= 100 g
    if band == "now":
        return bool(has_camera)
    else:
        return bool(has_camera) and (int(mass_g or 0) >= 100)

def a2_applicable(eu_class: str) -> bool:
    # C2/C3 drones can use A2. C0/C1 minis cannot.
    cls = (eu_class or "").strip().upper()
    return cls in ("C2", "C3", "C2/C3", "C2 / C3")

def pill_ok(text, tip=""):
    return pill(text, "ok", tip)

def pill_need(text, tip=""):
    return pill(text, "need", tip)

def pill_info(text, tip=""):
    return pill(text, "info", tip)

def grid_column(title: str):
    st.markdown(f"<h2 style='margin:.2rem 0 1rem 0;'>{title}</h2>", unsafe_allow_html=True)

# Determine statuses for a given band
def build_cards(band: str):
    # Read YAML attributes
    mass = int(row.get("mtom_g_nominal") or 0)
    has_cam = str(row.get("has_camera","yes")).strip().lower() == "yes"
    geo = str(row.get("geo_awareness","unknown")).strip().lower()
    rid = str(row.get("remote_id_builtin","unknown")).strip().lower()
    eu_cls = (row.get("eu_class_marking") or "").strip().upper()

    need_op = True if has_cam else False  # camera implies operator ID
    need_flyer = requires_flyer_id(mass, has_cam, band)

    # Check user-provided credentials
    has_op = bool(st.session_state.get("cred_opid"))
    has_flyer = bool(st.session_state.get("cred_flyer"))
    has_a1a3 = bool(st.session_state.get("cred_a1a3"))
    has_a2cofc = bool(st.session_state.get("cred_a2cofc"))
    has_gvc = bool(st.session_state.get("cred_gvc"))
    has_oa = bool(st.session_state.get("cred_oa"))

    # Helper pills (RID/Geo logic for 2026+; else use onboard/ok display from yaml)
    if band == "now":
        rid_p = pill_ok("Remote ID: OK" if rid == "yes" else "Remote ID: —",
                        "Remote ID not mandated yet for legacy sub-250, displayed from spec.")
        geo_p = pill_ok("Geo-awareness: Onboard" if geo == "yes" else "Geo-awareness: —",
                        "Geo-awareness displayed from spec.")
    else:
        # Tighten starting 2026/2028: require RID & Geo-awareness
        rid_p = pill_ok("Remote ID: OK","") if rid == "yes" else pill_need("Remote ID: Required","Direct Remote ID required for class-marked drones.")
        geo_p = pill_ok("Geo-awareness: OK","") if geo == "yes" else pill_need("Geo-awareness: Required","Geo-awareness required from 2026/2028.")

    # common “A1/A3 optional” info pill
    a1a3_info = pill_info("A1/A3: Optional", "Suggested for familiarisation.")

    # --- A1 Close to people ---
    a1_pills = []
    a1_pills.append(pill_need("Operator ID: Required", "Required for any camera drone.") if need_op and not has_op else pill_ok("Operator ID: Have",""))
    a1_pills.append(pill_need("Flyer ID: Required", "UK basic test") if need_flyer and not has_flyer else pill_ok("Flyer ID: Have",""))
    a1_pills.append(rid_p)
    a1_pills.append(geo_p)
    a1_pills.append(a1a3_info)

    a1_ok = True
    if need_op and not has_op: a1_ok = False
    if need_flyer and not has_flyer: a1_ok = False
    # RID/Geo can block from 2026+
    if band != "now":
        if "Required" in rid_p: a1_ok = False
        if "Required" in geo_p: a1_ok = False

    a1_badge = badge("Allowed","allowed") if a1_ok else badge("Possible (additional requirements)","possible")
    a1_tone = "allowed" if a1_ok else "possible"
    a1_body = f"""
      Fly close to people; avoid assemblies/crowds. TOAL: sensible separation; follow local restrictions.
      <div class="pills" style="margin-top:6px;">{''.join(a1_pills)}</div>
    """
    a1 = card("A1 — Close to people", a1_badge, a1_body, a1_tone)

    # --- A2 Close with A2 CofC ---
    if a2_applicable(eu_cls):
        a2_pills = []
        # A2 needs Operator + Flyer + A2 CofC (+RID/Geo 2026+)
        a2_need = []
        a2_pills.append(pill_need("Operator ID: Required") if need_op and not has_op else pill_ok("Operator ID: Have"))
        a2_pills.append(pill_need("Flyer ID: Required") if need_flyer and not has_flyer else pill_ok("Flyer ID: Have"))
        a2_pills.append(pill_need("A2 CofC: Required") if not has_a2cofc else pill_ok("A2 CofC: Have"))
        a2_pills.append(rid_p)
        a2_pills.append(geo_p)

        a2_ok = True
        if need_op and not has_op: a2_ok = False
        if need_flyer and not has_flyer: a2_ok = False
        if not has_a2cofc: a2_ok = False
        if band != "now":
            if "Required" in rid_p: a2_ok = False
            if "Required" in geo_p: a2_ok = False

        a2_badge = badge("Allowed","allowed") if a2_ok else badge("Possible (additional requirements)","possible")
        a2_tone = "allowed" if a2_ok else "possible"
        a2_body = f"""
          A2 mainly for C2 drones (sometimes C1 by nuance). This model may use A2 where permitted.
          <div class="pills" style="margin-top:6px;">{''.join(a2_pills)}</div>
        """
    else:
        a2_badge = badge("Not applicable","na")
        a2_tone = "na"
        a2_body = f"""
           A2 mainly for C2 drones (sometimes C1 by nuance). This model cannot use A2;
           consider A1 or A3/Specific.
           <div class="pills" style="margin-top:6px;">
             {pill_need("Operator ID: Required") if (need_op and not has_op) else pill_ok("Operator ID: Have")}
             {pill_need("Flyer ID: Required") if (need_flyer and not has_flyer) else pill_ok("Flyer ID: Have")}
             {pill_info("A2 CofC: N/A")}
             {rid_p}{geo_p}
           </div>
        """
    a2 = card("A2 — Close with A2 CofC", a2_badge, a2_body, a2_tone)

    # --- A3 Far from people ---
    a3_pills = []
    a3_pills.append(pill_need("Operator ID: Required") if need_op and not has_op else pill_ok("Operator ID: Have"))
    a3_pills.append(pill_need("Flyer ID: Required") if need_flyer and not has_flyer else pill_ok("Flyer ID: Have"))
    a3_pills.append(rid_p)
    a3_pills.append(geo_p)
    a3_pills.append(pill_info("A1/A3: Optional"))

    a3_ok = True
    if need_op and not has_op: a3_ok = False
    if need_flyer and not has_flyer: a3_ok = False
    if band != "now":
        if "Required" in rid_p: a3_ok = False
        if "Required" in geo_p: a3_ok = False

    a3_badge = badge("Allowed","allowed") if a3_ok else badge("Possible (additional requirements)","possible")
    a3_tone = "allowed" if a3_ok else "possible"
    a3_body = f"""
      Keep ≥ 150 m from residential/commercial/recreational areas.
      <div class="pills" style="margin-top:6px;">{''.join(a3_pills)}</div>
    """
    a3 = card("A3 — Far from people", a3_badge, a3_body, a3_tone)

    # --- Specific (OA/GVC) ---
    spec_pills = []
    spec_pills.append(pill_need("Operator ID: Required") if need_op and not has_op else pill_ok("Operator ID: Have"))
    spec_pills.append(pill_need("Flyer ID: Required") if need_flyer and not has_flyer else pill_ok("Flyer ID: Have"))
    spec_pills.append(pill_need("GVC: Required") if not has_gvc else pill_ok("GVC: Have"))
    spec_pills.append(pill_need("OA: Required") if not has_oa else pill_ok("OA: Have"))
    # For Specific, from 2026+ also enforce RID/Geo:
    spec_rid = rid_p if band != "now" else (pill_ok("Remote ID: OK") if rid == "yes" else pill_info("Remote ID: —"))
    spec_geo = geo_p if band != "now" else (pill_ok("Geo-awareness: Onboard") if geo == "yes" else pill_info("Geo-awareness: —"))
    spec_pills.append(spec_rid)
    spec_pills.append(spec_geo)

    spec_ok = has_gvc and has_oa and (not need_op or has_op) and (not need_flyer or has_flyer)
    if band != "now":
        if "Required" in spec_rid: spec_ok = False
        if "Required" in spec_geo: spec_ok = False

    if spec_ok:
        spec_badge = badge("Allowed","allowed")
        spec_tone = "allowed"
        spec_hdr = "Specific — OA / GVC"
    else:
        spec_badge = badge("Available via OA/GVC","warn")
        spec_tone = "warn"
        spec_hdr = "Specific — OA / GVC"

    spec_body = f"""
      Risk-assessed operations per OA; distances per ops manual.
      TOAL & mitigations defined by your approved procedures.
      <div class="pills" style="margin-top:6px;">{''.join(spec_pills)}</div>
    """
    spec = card(spec_hdr, spec_badge, spec_body, spec_tone)

    return a1, a2, a3, spec

# ---------- Body ----------
st.markdown(
    """
    <style>
      .hdr { font-weight:900; font-size:1.25rem; margin:.1rem 0 .6rem 0; }
    </style>
    """,
    unsafe_allow_html=True
)

cols = st.columns(3, gap="large")
for i, (title, band) in enumerate([("NOW", "now"), ("2026", "2026"), ("2028 (planned)", "2028")]):
    with cols[i]:
        grid_column(title)
        a1, a2, a3, spec = build_cards(band)
        # render cards (wrapped; no code leakage)
        st.markdown(a1, unsafe_allow_html=True)
        st.markdown(a2, unsafe_allow_html=True)
        st.markdown(a3, unsafe_allow_html=True)
        st.markdown(spec, unsafe_allow_html=True)
