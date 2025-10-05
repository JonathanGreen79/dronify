# dronify.py — UI + compliance board
# - Keeps your “last good” navigation & cards
# - Adds: sidebar legend, fixed headers, vertical dividers, wording tweak
# - Leaves your brick logic intact

import random
from pathlib import Path
import pandas as pd
import streamlit as st
import yaml

st.set_page_config(page_title="Dronify", layout="wide")

DATASET_PATH = Path("dji_drones_v3.yaml")
TAXONOMY_PATH = Path("taxonomy.yaml")

# -------------------- Load --------------------
def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@st.cache_data
def load_data():
    dataset = load_yaml(DATASET_PATH)
    taxonomy = load_yaml(TAXONOMY_PATH)
    df = pd.DataFrame(dataset["data"])

    # Columns that must exist for UI not to break
    must_cols = [
        "image_url","segment","series","marketing_name","model_key",
        "mtom_g_nominal","eu_class_marking","uk_class_marking",
        "remote_id_builtin","geo_awareness","has_camera",
        "operator_id_required","year_released","notes"
    ]
    for c in must_cols:
        if c not in df.columns:
            df[c] = ""

    # normalized helpers
    df["segment_norm"] = df["segment"].astype(str).str.strip().str.lower()
    df["series_norm"]  = df["series"].astype(str).str.strip().str.lower()
    return df, taxonomy

df, taxonomy = load_data()

# -------------------- Query params --------------------
def get_qp():
    try:
        return dict(st.query_params)  # Streamlit ≥ 1.32
    except Exception:
        return {k: (v[0] if isinstance(v, list) else v)
                for k, v in st.experimental_get_query_params().items()}

qp = get_qp()
segment = qp.get("segment")
series   = qp.get("series")
model    = qp.get("model")

# -------------------- Image resolver --------------------
RAW_BASE = "https://raw.githubusercontent.com/JonathanGreen79/dronify/main/images/"

def resolve_img(url: str) -> str:
    """
    - Absolute URLs passed through
    - 'images/...' → GH raw path
    - bare filenames → assumed under /images
    """
    u = (url or "").strip()
    if not u:
        return ""
    low = u.lower()
    if low.startswith("http://") or low.startswith("https://") or low.startswith("data:"):
        return u
    if low.startswith("images/"):
        return RAW_BASE + u.split("/", 1)[1]
    return RAW_BASE + u.lstrip("/")

SEGMENT_HERO = {
    "consumer": resolve_img("images/consumer.jpg"),
    "pro":       resolve_img("images/professional.jpg"),
    "enterprise":resolve_img("images/enterprise.jpg"),
}

# -------------------- Helpers --------------------
def series_defs_for(segment_key: str):
    seg = next(s for s in taxonomy["segments"] if s["key"] == segment_key)
    seg_l = str(segment_key).strip().lower()
    present = set(
        df.loc[df["segment_norm"] == seg_l, "series_norm"].dropna().unique().tolist()
    )
    return [s for s in seg["series"] if s["key"].strip().lower() in present]

def pad_digits_for_natural(s: pd.Series, width: int = 6) -> pd.Series:
    return (
        s.astype(str).str.lower()
         .str.replace(r"\d+", lambda m: f"{int(m.group(0)):0{width}d}", regex=True)
    )

def models_for(segment_key: str, series_key: str):
    seg_l = str(segment_key).strip().lower()
    ser_l = str(series_key).strip().lower()
    subset = df[(df["segment_norm"] == seg_l) & (df["series_norm"] == ser_l)].copy()
    subset["series_key"] = pad_digits_for_natural(subset["series"])
    subset["name_key"]   = pad_digits_for_natural(subset["marketing_name"])
    subset = subset.sort_values(
        by=["series_key", "name_key", "marketing_name"],
        kind="stable", ignore_index=True
    )
    return subset.drop(columns=["series_key", "name_key"])

def random_image_for_series(segment_key: str, series_key: str) -> str:
    seg_l = str(segment_key).strip().lower()
    ser_l = str(series_key).strip().lower()
    subset = df[(df["segment_norm"] == seg_l) & (df["series_norm"] == ser_l)]
    subset = subset[subset["image_url"].astype(str).str.strip() != ""]
    if subset.empty:
        return SEGMENT_HERO.get(segment_key, "")
    raw = str(subset.sample(1, random_state=None)["image_url"].iloc[0])
    return resolve_img(raw)

# -------------------- Styles --------------------
POSSIBLE_LABEL = "Possible (additional requirements)"

st.markdown("""
<style>
/* keep page tidy */
.block-container { padding-top: 1.05rem; }

/* Card grid — unchanged from your "last good" */
.card {
  width: 260px; height: 240px; border: 1px solid #E5E7EB; border-radius: 14px;
  background: #fff; text-decoration: none !important; color: #111827 !important;
  display: block; padding: 12px; transition: box-shadow .15s ease, transform .15s ease, border-color .15s ease;
}
.card:hover { border-color: #D1D5DB; box-shadow: 0 6px 18px rgba(0,0,0,.08); transform: translateY(-2px); }

.img { width: 100%; height: 150px; border-radius: 10px; background: #F3F4F6;
       overflow: hidden; display:flex; align-items:center; justify-content:center; }
.img > img { width: 100%; height: 100%; object-fit: cover; }
.title { margin-top: 10px; text-align: center; font-weight: 700; font-size: 0.98rem; }
.sub   { margin-top: 4px;  text-align: center; font-size: .8rem; color: #6B7280; }
.strip { display:flex; flex-wrap:nowrap; gap:14px; overflow-x:auto; padding:8px 2px; margin:0; }
.strip2{ display:grid; grid-auto-flow:column; grid-auto-columns:260px; grid-template-rows:repeat(2,1fr);
         gap:14px; overflow-x:auto; padding:8px 2px; margin:0; }
.h1 { font-weight:800; font-size:1.2rem; color:#1F2937; margin:0 0 12px 0; }

/* Sidebar visuals */
.sidebar-title{ font-weight:800; font-size:1.05rem; margin:.6rem 0 .2rem; }
.badge { display:inline-block; padding:3px 10px; border-radius:999px; background:#EEF2FF; color:#3730A3; font-weight:600; font-size:.78rem; }
.badge-red{ background:#FEE2E2; color:#991B1B; }
.badge-green{ background:#DCFCE7; color:#14532D; }
.flagline { display:flex; align-items:center; gap:8px; margin:.25rem 0; }
.flagline img{ width:20px; height:20px; border-radius:3px; }

/* Brick layout */
.brick{ border:1px solid #E5E7EB; border-radius:12px; padding:16px; background:#fff; margin-bottom:16px; box-shadow:0 1px 0 rgba(0,0,0,.02); }
.brick h4{ margin:0 0 6px 0; font-size:1rem; }
.brick .ex{ color:#374151; font-size:.92rem; margin-bottom:.25rem; }
.kv{ display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }
.kv .pill{ padding:6px 10px; border-radius:999px; font-weight:600; font-size:.78rem; border:1px solid #E5E7EB; background:#F9FAFB; }

.ok    { background:#DCFCE7; border-color:#BBF7D0; color:#14532D; }
.warn  { background:#FEF9C3; border-color:#FDE68A; color:#854D0E; }
.deny  { background:#FEE2E2; border-color:#FECACA; color:#991B1B; }
.info  { background:#EEF2FF; border-color:#E0E7FF; color:#3730A3; }

/* Column headers */
.section-h { font-weight:800; font-size:1.15rem; margin:0 0 8px 2px; color:#111827; }

/* Vertical dividers between the three columns */
div[data-testid="column"]:nth-child(2),
div[data-testid="column"]:nth-child(3){
  border-left: 1px solid #E5E7EB;
  padding-left: 18px;
}

/* Small label on each brick for the top-right overall chip */
.chip{ float:right; margin-top:-2px; }
</style>
""", unsafe_allow_html=True)

# -------------------- Card link helpers --------------------
def card_link(qs: str, title: str, sub: str = "", img_url: str = "") -> str:
    img = f"<div class='img'><img src='{img_url}' alt=''/></div>" if img_url else "<div class='img'></div>"
    sub_html = f"<div class='sub'>{sub}</div>" if sub else ""
    return f"<a class='card' href='?{qs}' target='_self' rel='noopener'>{img}<div class='title'>{title}</div>{sub_html}</a>"

def render_row(title: str, items: list[str]):
    st.markdown(f"<div class='h1'>{title}</div><div class='strip'>{''.join(items)}</div>", unsafe_allow_html=True)

def render_two_rows(title: str, items: list[str]):
    st.markdown(f"<div class='h1'>{title}</div><div class='strip2'>{''.join(items)}</div>", unsafe_allow_html=True)

# -------------------- Brick rendering --------------------
def pill(text, klass="info", tooltip=None):
    t = f" title='{tooltip}'" if tooltip else ""
    return f"<span class='pill {klass}'{t}>{text}</span>"

def chip(text, color="info"):
    return f"<span class='pill {color} chip'>{text}</span>"

def brick(title, summary, pills, top_chip=None, tone="info"):
    chip_html = chip(top_chip, "ok" if top_chip=="Allowed" else ("deny" if top_chip=="Not applicable" else "info")) if top_chip else ""
    return st.markdown(
        f"""
        <div class='brick'>
          <h4>{title}{chip_html}</h4>
          <div class='ex'>{summary}</div>
          <div class='kv'>{' '.join(pills)}</div>
        </div>
        """, unsafe_allow_html=True
    )

# -------------------- Compliance-ish helpers --------------------
def has_yes(x):  # helper for yaml values yes/no/unknown
    return str(x).strip().lower() in ("yes","true","1")

def label_remote_geo(row, year):
    """
    Returns pill set for Remote ID & Geo-awareness across different years.
    Uses the model's onboard capabilities from YAML, not user credentials.
    """
    geo_ok = has_yes(row.get("geo_awareness"))
    rid_ok_now = has_yes(row.get("remote_id_builtin"))

    # 2026: new UK classes require built-in RID
    # 2028: legacy ≥100g + camera → RID required
    mtom = float(row.get("mtom_g_nominal") or 0)
    cam  = has_yes(row.get("has_camera"))

    if year == "now":
        rid_ok = rid_ok_now
    elif year == "2026":
        # Treat as "RID OK" if device already has built-in RID
        rid_ok = rid_ok_now
    else:  # 2028 planned
        rid_ok = rid_ok_now if (mtom >= 100 and cam) else rid_ok_now

    rid_pill  = pill("Remote ID: OK" if rid_ok else "Remote ID: Required", "ok" if rid_ok else "deny")
    geo_pill  = pill("Geo-awareness: Onboard" if geo_ok else "Geo-awareness: Required", "ok" if geo_ok else "deny")
    return rid_pill, geo_pill

def a1_summary():  # short line kept consistent
    return "Fly close to people; avoid assemblies/crowds. TOAL: sensible separation; follow local restrictions."

def a3_summary():
    return "Keep ≥ 150 m from residential/commercial/recreational areas. TOAL: well away from uninvolved people and built-up areas."

def a2_summary():
    return "A2 mainly for C2 drones (sometimes C1 by nuance). This model cannot use A2; consider A1 or A3/Specific."

def spec_summary():
    return "Risk-assessed operations per OA; distances per ops manual. TOAL & mitigations defined by your approved procedures."

def operator_flyer_pills(show_op, show_flyer):
    op = pill("Operator ID: Required", "deny") if show_op else pill("Operator ID: Have", "ok")
    fy = pill("Flyer ID: Required", "deny") if show_flyer else pill("Flyer ID: Have", "ok")
    return op, fy

# -------------------- Sidebar: model details + controls + legend --------------------
def sidebar_for_model(row, seg_label, ser_label):
    st.sidebar.markdown(f"**{seg_label} → {ser_label}**")

    back_qs = f"segment={segment}&series={series}"
    st.sidebar.markdown(f"<a class='badge' href='?{back_qs}' target='_self'>← Back to models</a>", unsafe_allow_html=True)

    # Thumbnail
    img = resolve_img(row.get("image_url",""))
    if img:
        st.sidebar.image(img, use_container_width=True, caption=row.get("marketing_name",""))

    # EU / UK dotted with flags
    eu = (row.get("eu_class_marking") or "unknown").strip() or "unknown"
    uk = (row.get("uk_class_marking") or "unknown").strip() or "unknown"
    st.sidebar.markdown(
        f"""
        <div class="flagline"><img src="{resolve_img('images/eu.png')}" /> <b>EU:</b> {eu}</div>
        <div class="flagline"><img src="{resolve_img('images/uk.png')}" /> <b>UK:</b> {uk}</div>
        """, unsafe_allow_html=True
    )

    # Key specs list
    st.sidebar.markdown("<div class='sidebar-title'>Key specs</div>", unsafe_allow_html=True)
    mtom = row.get("mtom_g_nominal","—")
    st.sidebar.markdown(f"- **Model**: {row.get('marketing_name','—')}")
    st.sidebar.markdown(f"- **MTOW**: {mtom if mtom else '—'} g")
    st.sidebar.markdown(f"- **Remote ID**: {'yes' if has_yes(row.get('remote_id_builtin')) else 'no/unknown'}")
    st.sidebar.markdown(f"- **Geo-awareness**: {'yes' if has_yes(row.get('geo_awareness')) else 'no/unknown'}")
    st.sidebar.markdown(f"- **Released**: {row.get('year_released','—')}")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Your credentials")
    have_op   = st.sidebar.checkbox("I have an Operator ID", value=False)
    have_fly  = st.sidebar.checkbox("I have a Flyer ID (basic test)", value=False)
    have_a1a3 = st.sidebar.checkbox("I have A1/A3 training (optional)", value=False)
    have_a2   = st.sidebar.checkbox("I have A2 CofC", value=False)
    have_gvc  = st.sidebar.checkbox("I have GVC", value=False)
    have_oa   = st.sidebar.checkbox("I have an OA (Operational Authorisation)", value=False)

    # Legend (moved to sidebar bottom)
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Legend")
    st.sidebar.markdown(
        """
        <div class='kv'>
          <span class='pill ok'>Allowed</span>
          <span class='pill info'>Possible (additional requirements)</span>
          <span class='pill warn'>Available via OA/GVC</span>
          <span class='pill deny'>Not applicable</span>
        </div>
        """, unsafe_allow_html=True
    )

    return {
        "op": have_op, "fly": have_fly, "a1a3": have_a1a3, "a2": have_a2, "gvc": have_gvc, "oa": have_oa
    }

# -------------------- Screens --------------------
if not segment:
    # Stage 1 — choose group
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
        items.append(card_link(f"segment={segment}&series={s['key']}", s["label"], img_url=rnd_img))
    render_row(f"Choose a series ({seg_label})", items)

else:
    # Stage 3 — grid or details
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    ser_label = next(s["label"] for s in series_defs_for(segment) if s["key"] == series)

    if model:
        sel = df[df["model_key"] == model]
        if sel.empty:
            model = None
        else:
            row = sel.iloc[0]

            # ---- Sidebar info & checkboxes & legend ----
            creds = sidebar_for_model(row, seg_label, ser_label)

            # ---- Three compliance columns (NOW / 2026 / 2028 planned) ----
            st.markdown("<div class='section-h'>NOW</div>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3, gap="large")

            # Helper to render A1, A2, A3, Specific bricks for a given column/year
            def render_column(col, year_label):
                # Make badges from model features
                rid_pill, geo_pill = label_remote_geo(row, year_label)

                # A1
                with col:
                    op_p, fly_p = operator_flyer_pills(not creds["op"], not creds["fly"])
                    a1_chip = POSSIBLE_LABEL  # until both creds present
                    if creds["op"] and creds["fly"]:
                        a1_chip = "Allowed"
                    brick(
                        "A1 — Close to people",
                        a1_summary(),
                        [op_p, fly_p, rid_pill, geo_pill],
                        top_chip=a1_chip
                    )
                # A2 (always not applicable with this dataset logic)
                with col:
                    brick(
                        "A2 — Close with A2 CofC",
                        a2_summary(),
                        [
                            pill("Operator ID: Required", "deny"),
                            pill("Flyer ID: Required", "deny"),
                            pill("A2 CofC: N/A","info"),
                            rid_pill, geo_pill
                        ],
                        top_chip="Not applicable"
                    )
                # A3
                with col:
                    op_p, fly_p = operator_flyer_pills(not creds["op"], not creds["fly"])
                    a3_chip = POSSIBLE_LABEL
                    if creds["op"] and creds["fly"]:
                        a3_chip = "Allowed"
                    brick(
                        "A3 — Far from people",
                        a3_summary(),
                        [op_p, fly_p, rid_pill, geo_pill],
                        top_chip=a3_chip
                    )
                # Specific (OA/GVC path)
                with col:
                    spec_chip = "Available via OA/GVC"
                    pills = [
                        pill("Operator ID: Required", "deny" if not creds["op"] else "ok"),
                        pill("Flyer ID: Required", "deny" if not creds["fly"] else "ok"),
                        pill("GVC: Required", "deny" if not creds["gvc"] else "ok"),
                        pill("OA: Required", "deny" if not creds["oa"] else "ok"),
                        rid_pill, geo_pill
                    ]
                    brick(
                        "Specific — OA / GVC",
                        spec_summary(),
                        pills,
                        top_chip=spec_chip
                    )

            render_column(c1, "now")
            st.markdown("<div class='section-h'>2026</div>", unsafe_allow_html=True)
            c4, c5, c6 = st.columns(3, gap="large")
            render_column(c4, "2026")

            st.markdown("<div class='section-h'>2028 (planned)</div>", unsafe_allow_html=True)
            c7, c8, c9 = st.columns(3, gap="large")
            render_column(c7, "2028")

            # pad end
            st.write("")
            st.write("")

    if not model:
        # Show grid for model selection
        models = models_for(segment, series)
        items = []
        for _, r in models.iterrows():
            parts = []
            eu = (r.get("eu_class_marking") or "").strip()
            uk = (r.get("uk_class_marking") or "").strip()
            if eu or uk:
                parts.append(f"Class: EU {eu or '—'} • UK {uk or '—'}")
            yr = str(r.get("year_released") or "").strip()
            if yr:
                parts.append(f"Released: {yr}")
            sub = " • ".join(parts)
            items.append(
                card_link(
                    f"segment={segment}&series={series}&model={r['model_key']}",
                    r.get("marketing_name",""),
                    sub=sub,
                    img_url=resolve_img(r.get("image_url",""))
                )
            )
        render_two_rows(f"Choose a drone ({seg_label} → {ser_label})", items)
