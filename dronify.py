# dronify.py
# Three-column compliance view (Now • 2026 • 2028), compact sidebar, crisp badges,
# A2 truly not-applicable, OA/GVC turns Allowed when both ticked.

import random
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

st.set_page_config(page_title="Dronify", layout="wide")

DATASET_PATH = Path("dji_drones_v3.yaml")
TAXONOMY_PATH = Path("taxonomy.yaml")

# ----------------------------- Loaders -----------------------------
def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@st.cache_data
def load_data():
    dataset = load_yaml(DATASET_PATH)
    taxonomy = load_yaml(TAXONOMY_PATH)
    df = pd.DataFrame(dataset["data"])

    # Ensure expected columns exist
    for c in [
        "image_url", "segment", "series", "marketing_name", "model_key",
        "eu_class_marking", "uk_class_marking", "mtom_g_nominal",
        "remote_id_builtin", "geo_awareness", "has_camera", "year_released",
        "notes"
    ]:
        if c not in df.columns:
            df[c] = ""

    # Normalize
    df["segment_norm"] = df["segment"].astype(str).str.strip().str.lower()
    df["series_norm"] = df["series"].astype(str).str.strip().str.lower()

    return df, taxonomy

df, taxonomy = load_data()

# ----------------------------- Query params -----------------------------
def get_qp():
    try:
        return dict(st.query_params)
    except Exception:
        return {k: (v[0] if isinstance(v, list) else v)
                for k, v in st.experimental_get_query_params().items()}

qp = get_qp()
segment = qp.get("segment")
series = qp.get("series")
model = qp.get("model")

# ----------------------------- Image resolver -----------------------------
RAW_BASE = "https://raw.githubusercontent.com/JonathanGreen79/dronify/main/images/"

def resolve_img(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    low = url.lower()
    if low.startswith("http://") or low.startswith("https://") or low.startswith("data:"):
        return url
    if low.startswith("images/"):
        return RAW_BASE + url.split("/", 1)[1]
    return RAW_BASE + url.lstrip("/")

SEGMENT_HERO = {
    "consumer": resolve_img("images/consumer.jpg"),
    "pro":       resolve_img("images/professional.jpg"),
    "enterprise":resolve_img("images/enterprise.jpg"),
}

# ----------------------------- Styles -----------------------------
st.markdown("""
<style>
/* ------- Layout & columns ------- */
.block-container { padding-top: 0.8rem; }
.columns-3 { display:grid; grid-template-columns: 1fr 1fr 1fr; gap: 18px; }
.col { padding: 2px 8px; border-left: 1px solid #E5E7EB; }
.col:first-child { border-left:none; }
.hdr { font-weight:900; font-size:1.05rem; letter-spacing:.02em; margin: 4px 0 10px 2px; }

/* ------- Sidebar compaction ------- */
section[data-testid="stSidebar"] .block-container { padding: 0.6rem 0.6rem 0.9rem; }
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: .35rem !important; }
.sidebar-compact .stCheckbox > label { font-size: 0.89rem; line-height: 1.2; }
.sidebar-compact .stMarkdown p { margin: .15rem 0 .25rem 0; }

/* ------- Cards & badges ------- */
.card {
  background: #fff; border: 1px solid #E5E7EB; border-radius: 14px;
  padding: 14px 14px 12px; margin-bottom: 14px;
  box-shadow: 0 2px 0 rgba(0,0,0,.02);
}

.card.allowed      { background:#ECFDF5; border-color:#A7F3D0; }   /* green */
.card.possible     { background:#EFF6FF; border-color:#BFDBFE; }   /* blue */
.card.available    { background:#FFFBEB; border-color:#FDE68A; }   /* amber */
.card.na           { background:#F9FAFB; border-color:#E5E7EB; }   /* grey */
.card.blocked      { background:#FEF2F2; border-color:#FECACA; }   /* red */

.card h4 { margin: 0 0 8px 0; font-size: 1.02rem; }

/* status badge top-right */
.badge {
  float:right; font-size:.78rem; font-weight:800; padding:4px 10px; border-radius:999px;
}
.badge-allowed   { background:#10B981; color:white; }
.badge-possible  { background:#FFFFFF; color:#1D4ED8; border:1px solid #93C5FD; } /* distinct */
.badge-available { background:#D97706; color:white; }
.badge-na        { background:#9CA3AF; color:white; }
.badge-blocked   { background:#EF4444; color:white; }

/* pills inside cards */
.pills { display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }
.pill {
  font-size:.78rem; border-radius:999px; padding:6px 10px; border:1px solid;
}
.pill-ok      { background:#ECFDF5; border-color:#A7F3D0; color:#065F46; }
.pill-need    { background:#FEF2F2; border-color:#FECACA; color:#991B1B; }
.pill-info    { background:#F3F4F6; border-color:#E5E7EB; color:#374151; }

.legend { display:flex; gap:8px; flex-wrap:wrap; margin-top:.5rem; }
.legend .chip { font-size:.76rem; border-radius:999px; padding:5px 8px; border:1px solid #E5E7EB; }
</style>
""", unsafe_allow_html=True)

# ----------------------------- Helpers -----------------------------
def series_defs_for(segment_key: str):
    seg = next(s for s in taxonomy["segments"] if s["key"] == segment_key)
    seg_l = str(segment_key).strip().lower()
    present = set(df.loc[df["segment_norm"] == seg_l, "series_norm"].dropna().unique())
    return [s for s in seg["series"] if s["key"].strip().lower() in present]

def models_for(segment_key: str, series_key: str):
    seg_l = str(segment_key).strip().lower()
    ser_l = str(series_key).strip().lower()
    subset = df[(df["segment_norm"] == seg_l) & (df["series_norm"] == ser_l)].copy()
    # natural-ish sorting
    def pad_digits(s: pd.Series, w=6):
        x = s.astype(str).str.lower()
        return x.str.replace(r"\d+", lambda m: f"{int(m.group(0)):0{w}d}", regex=True)
    subset["k1"] = pad_digits(subset["series"])
    subset["k2"] = pad_digits(subset["marketing_name"])
    subset = subset.sort_values(by=["k1","k2","marketing_name"], kind="stable", ignore_index=True)
    return subset.drop(columns=["k1","k2"])

def random_image_for_series(segment_key: str, series_key: str) -> str:
    seg_l = str(segment_key).strip().lower()
    ser_l = str(series_key).strip().lower()
    subset = df[(df["segment_norm"] == seg_l) & (df["series_norm"] == ser_l)]
    subset = subset[subset["image_url"].astype(str).str.strip() != ""]
    if subset.empty:
        return SEGMENT_HERO.get(segment_key, "")
    raw = str(subset.sample(1)["image_url"].iloc[0])
    return resolve_img(raw)

# ----------------------------- Brick logic -----------------------------
def class_is_c0(row) -> bool:
    return str(row.get("eu_class_marking","")).strip().upper() == "C0" or (str(row.get("mtom_g_nominal","")).strip().isdigit() and int(row["mtom_g_nominal"]) < 250)

def pill(text, kind="ok", tooltip=""):
    cls = {"ok":"pill-ok","need":"pill-need","info":"pill-info"}.get(kind,"pill-info")
    tt = f' title="{tooltip}"' if tooltip else ""
    return f'<span class="pill {cls}"{tt}>{text}</span>'

def badge(text, kind):
    cls = {
        "allowed":"badge-allowed",
        "possible":"badge-possible",
        "available":"badge-available",
        "na":"badge-na",
        "blocked":"badge-blocked"
    }[kind]
    return f'<span class="badge {cls}">{text}</span>'

def card_html(title, status_kind, status_label, body, pills_html=""):
    return f"""
    <div class="card {status_kind}">
      <h4>{title} {badge(status_label, status_kind)}</h4>
      <div>{body}</div>
      <div class="pills">{pills_html}</div>
    </div>
    """

def remote_geo_pills(row, require_remote=False, require_geo=False):
    pills = []
    # Remote ID
    rid = str(row.get("remote_id_builtin","")).strip().lower()
    if require_remote:
        if rid == "yes":
            pills.append(pill("Remote ID: OK", "ok"))
        else:
            pills.append(pill("Remote ID: Required", "need", "Needed for 2026+ where applicable"))
    else:
        pills.append(pill("Remote ID: OK" if rid == "yes" else "Remote ID: Not required", "ok" if rid == "yes" else "info"))
    # Geo
    geo = str(row.get("geo_awareness","")).strip().lower()
    if require_geo:
        if geo == "yes":
            pills.append(pill("Geo-awareness: Onboard","ok"))
        else:
            pills.append(pill("Geo-awareness: Required","need","Needed for UK1–3 in Open category"))
    else:
        pills.append(pill("Geo-awareness: Onboard" if geo == "yes" else "Geo-awareness: Not required", "ok" if geo=="yes" else "info"))
    return pills

def a1_a3_bricks(row, creds, era):
    """Return A1 and A3 bricks list for given era: 'now' | '2026' | '2028'."""
    bricks = []

    # requirements per era
    require_remote = (era in ("2026","2028")) and not class_is_c0(row)
    require_geo    = (era in ("2026","2028")) and not class_is_c0(row)

    # A1
    pills = []
    # Operator & Flyer always needed for A1 close
    pills += [pill(("Operator ID: Have" if creds["opid"] else "Operator ID: Required"), "ok" if creds["opid"] else "need",
                   "Required for all drones with a camera (registration of the operator)."),
              pill(("Flyer ID: Have" if creds["flyer"] else "Flyer ID: Required"), "ok" if creds["flyer"] else "need",
                   "Online theory test (basic). Required to fly a camera drone in the UK.")]
    pills += remote_geo_pills(row, require_remote, require_geo)

    if creds["opid"] and creds["flyer"]:
        status_kind, status_label = ("allowed","Allowed")
    else:
        status_kind, status_label = ("possible","Possible (additional requirements)")

    bricks.append(card_html(
        "A1 — Close to people",
        status_kind, status_label,
        "Fly close to people; avoid assemblies/crowds. TOAL: sensible separation; follow local restrictions.",
        "".join(pills)
    ))

    # A3
    pills = []
    pills += [pill(("Operator ID: Have" if creds["opid"] else "Operator ID: Required"), "ok" if creds["opid"] else "need"),
              pill(("Flyer ID: Have" if creds["flyer"] else "Flyer ID: Required"), "ok" if creds["flyer"] else "need")]
    # A1/A3 training is optional, but show it as info
    pills += [pill(("A1/A3: Have" if creds["a1a3"] else "A1/A3: Optional"), "ok" if creds["a1a3"] else "info")]
    pills += remote_geo_pills(row, require_remote, require_geo)

    if creds["opid"] and creds["flyer"]:
        status_kind, status_label = ("allowed","Allowed")
    else:
        status_kind, status_label = ("possible","Possible (additional requirements)")

    bricks.append(card_html(
        "A3 — Far from people",
        status_kind, status_label,
        "Keep ≥ 150 m from residential/commercial/recreational areas. TOAL: well away from uninvolved people and built-up areas.",
        "".join(pills)
    ))

    return bricks

def a2_brick(row, era):
    """A2 is not applicable for C0 / sub-250 g minis; grey card."""
    pills = []
    pills += [pill("A2 CofC: N/A", "info")]
    require_remote = (era in ("2026","2028")) and not class_is_c0(row)
    require_geo = (era in ("2026","2028")) and not class_is_c0(row)
    pills += remote_geo_pills(row, require_remote, require_geo)

    return card_html(
        "A2 — Close with A2 CofC",
        "na", "Not applicable",
        "A2 mainly for C2 drones (sometimes C1 by nuance). This model cannot use A2; consider A1 or A3/Specific.",
        "".join(pills)
    )

def specific_brick(row, creds, era):
    """Specific category brick (OA/GVC). Allowed only when both GVC and OA present."""
    require_remote = (era in ("2026","2028")) and not class_is_c0(row)
    require_geo = (era in ("2026","2028")) and not class_is_c0(row)

    has_both = creds["gvc"] and creds["oa"]
    pills = [
        pill(("Operator ID: Have" if creds["opid"] else "Operator ID: Required"), "ok" if creds["opid"] else "need"),
        pill(("Flyer ID: Have" if creds["flyer"] else "Flyer ID: Required"), "ok" if creds["flyer"] else "need"),
        pill(("GVC: Have" if creds["gvc"] else "GVC: Required"), "ok" if creds["gvc"] else "need"),
        pill(("OA: Have" if creds["oa"] else "OA: Required"), "ok" if creds["oa"] else "need"),
    ]
    pills += remote_geo_pills(row, require_remote, require_geo)

    if has_both and creds["opid"] and creds["flyer"]:
        status_kind, status_label = ("allowed","Allowed")
    else:
        status_kind, status_label = ("available","Available via OA/GVC")

    return card_html(
        "Specific — OA / GVC",
        status_kind, status_label,
        "Risk-assessed operations per OA; distances per ops manual. TOAL & mitigations defined by your approved procedures.",
        "".join(pills)
    )

def build_column(row, era_label, era_key, creds):
    """Return complete HTML for one era column."""
    blocks = []
    blocks += a1_a3_bricks(row, creds, era_key)
    blocks.append(a2_brick(row, era_key))
    blocks.append(specific_brick(row, creds, era_key))

    inner = "".join(blocks)
    return f'<div class="col"><div class="hdr">{era_label}</div>{inner}</div>'

# ----------------------------- UI Screens -----------------------------
def card_link(qs: str, title: str, sub: str = "", img_url: str = "") -> str:
    img = f"<div style='width:100%;height:150px;border-radius:10px;background:#F3F4F6;overflow:hidden;display:flex;align-items:center;justify-content:center;'><img src='{img_url}' style='width:100%;height:100%;object-fit:cover;'/></div>" if img_url else "<div style='width:100%;height:150px;border-radius:10px;background:#F3F4F6;'></div>"
    sub_html = f"<div style='margin-top:4px;text-align:center;font-size:.8rem;color:#6B7280'>{sub}</div>" if sub else ""
    return f"<a style='display:block;width:260px;height:240px;border:1px solid #E5E7EB;border-radius:14px;background:#fff;text-decoration:none;color:#111827;padding:12px;transition:box-shadow .15s,transform .15s;border-color:#E5E7EB' href='?{qs}' target='_self'>{img}<div style='margin-top:10px;text-align:center;font-weight:700;font-size:.98rem'>{title}</div>{sub_html}</a>"

def render_row(title: str, items: list[str]):
    st.markdown(f"<div class='hdr'>{title}</div><div style='display:flex;gap:14px;overflow-x:auto;padding:8px 2px;margin:0'>{''.join(items)}</div>", unsafe_allow_html=True)

def render_two_rows(title: str, items: list[str]):
    st.markdown(f"<div class='hdr'>{title}</div><div style='display:grid;grid-auto-flow:column;grid-auto-columns:260px;grid-template-rows:repeat(2,1fr);gap:14px;overflow-x:auto;padding:8px 2px;margin:0'>{''.join(items)}</div>", unsafe_allow_html=True)

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
        items.append(card_link(f"segment={segment}&series={s['key']}", s["label"], img_url=rnd_img))
    render_row(f"Choose a series ({seg_label})", items)

else:
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    ser_label = next(s["label"] for s in series_defs_for(segment) if s["key"] == series)

    # Sidebar selection or model view
    if model:
        sel = df[df["model_key"] == model]
        if not sel.empty:
            row = sel.iloc[0]

            # ----------- SIDEBAR -----------
            st.sidebar.markdown(f"**{seg_label} → {ser_label}**")
            st.sidebar.markdown(f"<a href='?segment={segment}&series={series}' target='_self'>← Back to models</a>", unsafe_allow_html=True)

            # thumbnail
            img_url = resolve_img(row.get("image_url",""))
            if img_url:
                st.sidebar.image(img_url, use_container_width=True, caption=row.get("marketing_name",""))

            # EU/UK flags + classes
            st.sidebar.markdown(
                f"""
                <div style="margin:.25rem 0 .4rem 0">
                  <div>🇪🇺 <b>EU:</b> {row.get('eu_class_marking','unknown')}</div>
                  <div>🇬🇧 <b>UK:</b> {row.get('uk_class_marking','unknown')}</div>
                </div>
                """, unsafe_allow_html=True)

            # key specs
            st.sidebar.markdown("**Key specs**")
            st.sidebar.markdown(
                f"""
                <div class="sidebar-compact">
                  <div>🛠️ <b>Model</b>: {row.get('marketing_name','—')}</div>
                  <div>⚖️ <b>MTOW</b>: {(str(row.get('mtom_g_nominal','')).strip()+' g') if str(row.get('mtom_g_nominal','')).strip() else '—'}</div>
                  <div>📡 <b>Remote ID</b>: {row.get('remote_id_builtin','unknown')}</div>
                  <div>🌐 <b>Geo-awareness</b>: {row.get('geo_awareness','unknown')}</div>
                  <div>📅 <b>Released</b>: {row.get('year_released','—')}</div>
                </div>
                """, unsafe_allow_html=True)

            # credentials block (checklist)
            st.sidebar.markdown("**Your credentials**")
            with st.sidebar.container():
                st.markdown('<div class="sidebar-compact">', unsafe_allow_html=True)
                opid  = st.checkbox("Operator ID", value=False, key="cred_opid")
                flyer = st.checkbox("Flyer ID (basic test)", value=False, key="cred_flyer")
                a1a3  = st.checkbox("A1/A3 training (optional)", value=False, key="cred_a1a3")
                a2    = st.checkbox("A2 CofC", value=False, key="cred_a2")
                gvc   = st.checkbox("GVC", value=False, key="cred_gvc")
                oa    = st.checkbox("OA (Operational Authorisation)", value=False, key="cred_oa")
                st.markdown('</div>', unsafe_allow_html=True)

            creds = {"opid":opid, "flyer":flyer, "a1a3":a1a3, "a2":a2, "gvc":gvc, "oa":oa}

            # ----------- MAIN BODY: three columns -----------
            now_col  = build_column(row, "NOW", "now", creds)
            y26_col  = build_column(row, "2026", "2026", creds)
            y28_col  = build_column(row, "2028 (planned)", "2028", creds)

            st.markdown(f"""<div class="columns-3">{now_col}{y26_col}{y28_col}</div>""", unsafe_allow_html=True)

            # legend at sidebar bottom to save main space
            st.sidebar.markdown("—")
            st.sidebar.markdown("**Legend**")
            st.sidebar.markdown(
                """
                <div class="legend">
                  <span class="chip">🟩 Allowed</span>
                  <span class="chip">🟦 Possible (additional requirements)</span>
                  <span class="chip">🟨 Available via OA/GVC</span>
                  <span class="chip">⬜ Not applicable</span>
                </div>
                """, unsafe_allow_html=True)

        else:
            model = None

    if not model:
        # Model grid
        models = models_for(segment, series)
        items = []
        for _, r in models.iterrows():
            subs = []
            eu = (r.get("eu_class_marking") or r.get("class_marking") or "").strip()
            uk = (r.get("uk_class_marking") or r.get("class_marking") or "").strip()
            if eu or uk:
                subs.append(f"Class: EU {eu or '—'} • UK {uk or '—'}")
            yr = str(r.get("year_released","")).strip()
            if yr:
                subs.append(f"Released: {yr}")
            items.append(card_link(
                f"segment={segment}&series={series}&model={r['model_key']}",
                r.get("marketing_name",""),
                " • ".join(subs),
                img_url=resolve_img(str(r.get("image_url","")))
            ))
        render_two_rows(f"Choose a drone ({seg_label} → {ser_label})", items)
