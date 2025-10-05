# dronify.py — working UI + flags + badges + enriched 3-column compliance matrix
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
        "image_url","segment","series",
        "class_marking","weight_band",
        "marketing_name","mtom_g_nominal",
        "eu_class_marking","uk_class_marking",
        "remote_id_builtin","year_released",
        "notes","operator_id_required","geo_awareness",
        "has_camera" # optional override
    ):
        if col not in df.columns:
            df[col] = ""

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

# ---------- Image resolver ----------
RAW_BASE = "https://raw.githubusercontent.com/JonathanGreen79/dronify/main/images/"
def resolve_img(url: str) -> str:
    url = (url or "").strip()
    if not url: return ""
    low = url.lower()
    if low.startswith(("http://","https://","data:")): return url
    if low.startswith("images/"): return RAW_BASE + url.split("/",1)[1]
    return RAW_BASE + url.lstrip("/")

SEGMENT_HERO = {
    "consumer": resolve_img("images/consumer.jpg"),
    "pro":       resolve_img("images/professional.jpg"),
    "enterprise":resolve_img("images/enterprise.jpg"),
}
EU_FLAG = resolve_img("images/eu.png")
UK_FLAG = resolve_img("images/uk.png")

# ---------- Helpers (lists / sorting / random image) ----------
def series_defs_for(segment_key: str):
    seg = next(s for s in taxonomy["segments"] if s["key"] == segment_key)
    seg_l = str(segment_key).strip().lower()
    present = set(df.loc[df["segment_norm"] == seg_l, "series_norm"].dropna().unique())
    return [s for s in seg["series"] if s["key"].strip().lower() in present]

def pad_digits_for_natural(s: pd.Series, width: int=6) -> pd.Series:
    s = s.astype(str).str.lower()
    return s.str.replace(r"\d+", lambda m: f"{int(m.group(0)):0{width}d}", regex=True)

def models_for(segment_key: str, series_key: str):
    seg_l = str(segment_key).strip().lower()
    ser_l = str(series_key).strip().lower()
    subset = df[(df["segment_norm"]==seg_l)&(df["series_norm"]==ser_l)].copy()
    subset["series_key"]=pad_digits_for_natural(subset["series"])
    subset["name_key"]=pad_digits_for_natural(subset["marketing_name"])
    subset = subset.sort_values(by=["series_key","name_key","marketing_name"], kind="stable", ignore_index=True)
    return subset.drop(columns=["series_key","name_key"])

def random_image_for_series(segment_key: str, series_key: str) -> str:
    seg_l = str(segment_key).strip().lower()
    ser_l = str(series_key).strip().lower()
    subset = df[(df["segment_norm"]==seg_l)&(df["series_norm"]==ser_l)]
    subset = subset[subset["image_url"].astype(str).str.strip()!=""]
    if subset.empty: return SEGMENT_HERO.get(segment_key,"")
    return resolve_img(str(subset.sample(1)["image_url"].iloc[0]))

# ---------- Styles ----------
st.markdown("""
<style>
.block-container { padding-top: 1.1rem; }

/* cards */
.card{
  width:260px;height:240px;border:1px solid #E5E7EB;border-radius:14px;background:#fff;
  text-decoration:none!important;color:#111827!important;display:block;padding:12px;
  transition:box-shadow .15s, transform .15s, border-color .15s; cursor:pointer;
}
.card:hover{border-color:#D1D5DB;box-shadow:0 6px 18px rgba(0,0,0,.08);transform:translateY(-2px);}
.img{width:100%;height:150px;border-radius:10px;background:#F3F4F6;overflow:hidden;display:flex;align-items:center;justify-content:center;}
.img>img{width:100%;height:100%;object-fit:cover;}
.title{margin-top:10px;text-align:center;font-weight:700;font-size:.98rem;}
.sub{margin-top:4px;text-align:center;font-size:.8rem;color:#6B7280;}
.strip{display:flex;flex-wrap:nowrap;gap:14px;overflow-x:auto;padding:8px 2px;margin:0;}
.strip2{display:grid;grid-auto-flow:column;grid-auto-columns:260px;grid-template-rows:repeat(2,1fr);gap:14px;overflow-x:auto;padding:8px 2px;margin:0;}
.h1{font-weight:800;font-size:1.2rem;color:#1F2937;margin:0 0 12px 0;}

/* sidebar */
.sidebar-title{font-weight:800;font-size:1.05rem;margin-top:.6rem;}
.sidebar-kv{margin:.15rem 0;color:#374151;font-size:.93rem;}
.sidebar-back{margin-top:.5rem;display:inline-block;text-decoration:none;color:#2563EB;font-weight:600;}
.sidebar-back:hover{text-decoration:underline;}
.badge{display:inline-block;padding:6px 10px;border-radius:999px;background:#EEF2FF;color:#111827;font-weight:600;font-size:.82rem;}
.badge-red{background:#FEE2E2;color:#991B1B;}
.badge-green{background:#DCFCE7;color:#14532D;}
.badge-gray{background:#F3F4F6;color:#374151;}
.flag-row{display:flex;align-items:center;gap:10px;margin:4px 0 2px 0;}
.flag{width:20px;height:20px;object-fit:contain;border-radius:3px;}
.flag-text{font-weight:700;color:#1F2937;}
.kv-icon{font-size:1.05rem;display:inline-block;width:1.35rem;text-align:center;}

/* rule matrix */
.rule-grid{
  display:grid;
  grid-template-columns: repeat(3, minmax(280px, 1fr));
  gap:16px; margin-top:14px;
}
.rule-card{
  border:1px solid #E5E7EB; border-radius:14px; padding:14px; background:#fff;
  box-shadow:0 4px 14px rgba(0,0,0,.04);
}
.rule-title{font-weight:800;color:#111827;margin-bottom:8px;}
.rule-chip{display:inline-block;padding:4px 10px;border-radius:999px;background:#F3F4F6;color:#374151;font-weight:700;font-size:.8rem;margin-right:6px;margin-bottom:8px;}
.rule-table{width:100%;border-collapse:separate;border-spacing:0 6px;}
.rule-row{display:grid;grid-template-columns: 120px 1fr;align-items:center;gap:10px;padding:6px 8px;border-radius:10px;background:#F9FAFB;}
.rule-row .rlabel{font-weight:700;color:#374151;}
.rule-row .rval{display:flex;flex-wrap:wrap;gap:8px;align-items:center;}
.tick{font-weight:900;color:#16A34A;}  /* ✔ */
.warn{font-weight:900;color:#D97706;}   /* ! */
.nope{font-weight:900;color:#DC2626;}   /* ✖ */
.pill{display:inline-block;padding:3px 8px;border-radius:999px;font-weight:700;font-size:.78rem;}
.p-ok{background:#DCFCE7;color:#14532D;}
.p-warn{background:#FEF3C7;color:#92400E;}
.p-no{background:#FEE2E2;color:#991B1B;}
.small{color:#6B7280;font-size:.85rem;}
.hr{height:1px;background:#E5E7EB;margin:10px 0;}
</style>
""", unsafe_allow_html=True)

# ---------- Card markup ----------
def card_link(qs: str, title: str, sub: str="", img_url: str="") -> str:
    img = f"<div class='img'><img src='{img_url}' alt=''/></div>" if img_url else "<div class='img'></div>"
    sub_html = f"<div class='sub'>{sub}</div>" if sub else ""
    return f"<a class='card' href='?{qs}' target='_self' rel='noopener'>{img}<div class='title'>{title}</div>{sub_html}</a>"

def render_row(title: str, items: list[str]):
    st.markdown(f"<div class='h1'>{title}</div><div class='strip'>{''.join(items)}</div>", unsafe_allow_html=True)

def render_two_rows(title: str, items: list[str]):
    st.markdown(f"<div class='h1'>{title}</div><div class='strip2'>{''.join(items)}</div>", unsafe_allow_html=True)

# ---------- Tiny rule engine ----------
def _float(v):
    try: return float(v)
    except: return None

def weight_g(row):
    return _float(row.get("mtom_g_nominal"))

def weight_band(row):
    g = weight_g(row)
    if g is None: return None
    if g < 250: return "sub250"
    if g < 900: return "250to900"
    if g < 4000: return "900to4kg"
    return "over4kg"

def has_camera(row):
    v = str(row.get("has_camera","")).strip().lower()
    if v in ("yes","true","1"): return True
    if v in ("no","false","0"): return False
    # default: DJI consumer/pro/enterprise have cameras
    return True

def flyer_operator_by_phase(row, phase):
    """Return strings for Flyer ID / Operator ID per phase (now/2026/2028)."""
    g = weight_g(row) or 0
    cam = has_camera(row)

    if phase == "now":
        flyer = (cam or g >= 250)
        operator = cam or g >= 250  # operator ID effectively required for camera drones
    else:
        # 2026 and 2028: Flyer ID threshold lowered to 100 g with camera
        flyer = (g >= 100 and cam) or (g >= 250)  # keep ≥250 safety net
        operator = cam or g >= 250

    return ("Yes" if flyer else "No"), ("Yes" if operator else "No")

def class_in_effect_by_phase(row, phase):
    eu = (row.get("eu_class_marking") or row.get("class_marking") or "").upper().strip()
    uk = (row.get("uk_class_marking") or "").upper().strip()
    if phase == "now":
        return uk or eu or "—"
    if phase == "2026":
        # EU recognised until 31 Dec 2027; prefer UK if present
        return uk or (eu if eu else "Legacy / —")
    if phase == "2028":
        # EU no longer recognised automatically
        return uk or "Legacy / —"
    return "—"

def allow_map(symbol_ok=True, symbol_warn=True, symbol_no=True):
    return {
        "ok": "<span class='tick'>✔︎</span>",
        "warn": "<span class='warn'>!</span>",
        "no": "<span class='nope'>✖</span>",
    }

def capability_by_phase(row, phase):
    """Return per subcategory: 'ok' | 'warn' | 'no', with notes list."""
    wb = weight_band(row)
    eu = (row.get("eu_class_marking") or row.get("class_marking") or "").upper().strip()
    uk = (row.get("uk_class_marking") or "").upper().strip()
    out = {"A1":"no","A2":"no","A3":"no","Specific":"no", "notes":[]}

    if phase == "now":
        # current transitional
        if eu == "C0" or wb == "sub250":
            out.update(A1="ok", A2="no", A3="ok")  # A3 always permissible if away from people
        elif eu == "C1":
            out.update(A1="ok", A2="warn", A3="ok")  # A2 needs A2 CofC
        elif eu in ("C2","C3","C4"):
            out.update(A1="no", A2="warn", A3="ok")
        else:
            # legacy/unmarked
            if wb == "sub250":
                out.update(A1="ok", A2="no", A3="ok")
            else:
                out.update(A1="no", A2="no", A3="ok")
                out["notes"].append("Legacy: typically A3 only.")
        return out

    if phase == "2026":
        if uk.startswith("UK"):
            if uk == "UK0":
                out.update(A1="ok", A2="no", A3="ok")
            elif uk == "UK1":
                out.update(A1="ok", A2="warn", A3="ok")
            elif uk == "UK2":
                out.update(A1="no", A2="warn", A3="ok")
            elif uk in ("UK3","UK4","UK5","UK6"):
                out.update(A1="no", A2="no", A3="ok", Specific="warn")
            return out
        # EU still recognised through 2027
        if eu == "C0" or wb == "sub250":
            out.update(A1="ok", A2="no", A3="ok")
        elif eu == "C1":
            out.update(A1="ok", A2="warn", A3="ok")
        elif eu in ("C2","C3","C4"):
            out.update(A1="no", A2="warn", A3="ok")
        else:
            # legacy extended
            if wb == "sub250":
                out.update(A1="ok", A2="no", A3="ok")
            else:
                out.update(A1="no", A2="no", A3="ok")
                out["notes"].append("Legacy: transitional limits continue.")
        return out

    if phase == "2028":
        if uk.startswith("UK"):
            if uk == "UK0":
                out.update(A1="ok", A2="no", A3="ok")
            elif uk == "UK1":
                out.update(A1="ok", A2="warn", A3="ok")
            elif uk == "UK2":
                out.update(A1="no", A2="warn", A3="ok")
            elif uk in ("UK3","UK4","UK5","UK6"):
                out.update(A1="no", A2="no", A3="ok", Specific="warn")
            return out
        # No UK class (legacy): EU not recognised
        if wb == "sub250":
            out.update(A1="ok", A2="no", A3="ok")
            out["notes"].append("Legacy: check added 2028 Remote ID / geo-awareness for ≥100 g with camera.")
        else:
            out.update(A1="no", A2="no", A3="ok", Specific="warn")
            out["notes"].append("EU class not recognised; legacy likely A3 or Specific.")
        return out

    return out

def toel_guidance_by_phase(row, phase):
    """Return short TOAL (take-off/landing) separation guidance per phase."""
    # These are concise advisories for Open category:
    if phase == "now":
        return "TOAL: keep ≤50 m from uninvolved people only if unavoidable & safe."
    if phase == "2026":
        return "TOAL: ≤50 m permitted when necessary & safe; follow class limits."
    if phase == "2028":
        return "TOAL: as per UK class; ≤50 m only if unavoidable & safe."
    return ""

def quals_by_phase(row, phase):
    """Return qualification summary for A1/A2/A3/Specific."""
    caps = capability_by_phase(row, phase)
    parts = []
    if caps["A2"] in ("ok","warn"):
        parts.append("A2 CofC for A2")
    if caps["Specific"] in ("ok","warn"):
        parts.append("GVC + Operational Authorisation for Specific")
    if not parts:
        parts.append("Basic flyer competency (Flyer ID)")
    return " • ".join(parts)

# ---------- Matrix render ----------
def render_rule_matrix(row):
    phases = [
        ("Now", "now"),
        ("From 1 Jan 2026", "2026"),
        ("From 1 Jan 2028 (planned)", "2028"),
    ]
    cols_html = []
    ticks = allow_map()

    for title, key in phases:
        caps = capability_by_phase(row, key)
        flyer, oper = flyer_operator_by_phase(row, key)
        class_effective = class_in_effect_by_phase(row, key)
        toel = toel_guidance_by_phase(row, key)
        quals = quals_by_phase(row, key)

        # Row builder helpers
        def line_row(label, content_html):
            return f"<div class='rule-row'><div class='rlabel'>{label}</div><div class='rval'>{content_html}</div></div>"

        def state_pill(state, note=None):
            cls = "p-ok" if state=="ok" else ("p-warn" if state=="warn" else "p-no")
            lab = "Permitted" if state=="ok" else ("Conditional" if state=="warn" else "Not allowed")
            extra = f" <span class='small'>({note})</span>" if note else ""
            return f"<span class='pill {cls}'>{lab}</span>{extra}"

        # A1/A2/A3/Specific rows
        a1 = state_pill(caps["A1"], "Avoid crowds / be considerate" if caps["A1"]!="no" else None)
        a2 = state_pill(caps["A2"], "A2 CofC; 5–30 m" if caps["A2"]!="no" else None)
        a3 = state_pill(caps["A3"], "≥150 m built-up areas" if caps["A3"]!="no" else None)
        sp = state_pill(caps["Specific"], "GVC + OA" if caps["Specific"]!="no" else None)

        # Flyer/Operator
        flyer_p = f"<span class='pill {'p-ok' if flyer=='Yes' else 'p-no'}'>Flyer ID: {flyer}</span>"
        oper_p  = f"<span class='pill {'p-ok' if oper =='Yes' else 'p-no'}'>Operator ID: {oper}</span>"

        # Class in effect
        class_chip = f"<span class='rule-chip'>Class in effect: {class_effective}</span>"

        # Build card
        card = (
            f"<div class='rule-card'>"
            f"<div class='rule-title'>{title}</div>"
            f"{class_chip}"
            f"<div class='hr'></div>"
            f"<div class='rule-table'>"
            f"{line_row('A1', a1)}"
            f"{line_row('A2', a2)}"
            f"{line_row('A3', a3)}"
            f"{line_row('Specific', sp)}"
            + line_row("TOAL", f"<span class='small'>{toel}</span>")
            + line_row("Qualifications", f"<span class='small'>{quals}</span>")
            + line_row("IDs", flyer_p + " " + oper_p)
            + "</div>"
        )

        # Notes (if any)
        notes = caps.get("notes", [])
        if notes:
            notes_html = " ".join(f"<div class='small'>• {n}</div>" for n in notes)
            card += f"<div class='hr'></div>{notes_html}"

        card += "</div>"
        cols_html.append(card)

    st.markdown("<div class='rule-grid'>" + "".join(cols_html) + "</div>", unsafe_allow_html=True)

# ---------- Screens ----------
if not segment:
    items=[]
    for seg in taxonomy["segments"]:
        img = SEGMENT_HERO.get(seg["key"], "")
        items.append(card_link(f"segment={seg['key']}", seg["label"], img_url=img))
    render_row("Choose your drone category", items)

elif not series:
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    items=[]
    for s in series_defs_for(segment):
        rnd_img = random_image_for_series(segment, s["key"])
        items.append(card_link(f"segment={segment}&series={s['key']}", f"{s['label']}", img_url=rnd_img))
    render_row(f"Choose a series ({seg_label})", items)

else:
    seg_label = next(s["label"] for s in taxonomy["segments"] if s["key"] == segment)
    ser_label = next(s["label"] for s in series_defs_for(segment) if s["key"] == series)

    if model:
        sel = df[df["model_key"] == model]
        if not sel.empty:
            row = sel.iloc[0]

            # Sidebar (unchanged except breadcrumb removed)
            back_qs = f"segment={segment}&series={series}"
            st.sidebar.markdown(
                f"<a class='sidebar-back' href='?{back_qs}' target='_self'>← Back to models</a>",
                unsafe_allow_html=True
            )
            img_url = resolve_img(row.get("image_url",""))
            if img_url:
                st.sidebar.image(img_url, use_container_width=True, caption=row.get("marketing_name",""))

            eu = (row.get("eu_class_marking") or row.get("class_marking") or "unknown") or "unknown"
            uk = (row.get("uk_class_marking") or row.get("class_marking") or "unknown") or "unknown"
            st.sidebar.markdown(
                f"<div class='flag-row'><img class='flag' src='{EU_FLAG}' alt='EU flag'><span class='flag-text'>EU:</span> <span class='badge'>{eu}</span></div>",
                unsafe_allow_html=True
            )
            st.sidebar.markdown(
                f"<div class='flag-row'><img class='flag' src='{UK_FLAG}' alt='UK flag'><span class='flag-text'>UK:</span> <span class='badge'>{uk}</span></div>",
                unsafe_allow_html=True
            )

            op = str(row.get("operator_id_required","")).strip().lower()
            if op in ("yes","true","1"):
                st.sidebar.markdown("<span class='badge badge-red'>Operator ID: Required</span>", unsafe_allow_html=True)
            elif op in ("no","false","0"):
                st.sidebar.markdown("<span class='badge badge-green'>Operator ID: Not required</span>", unsafe_allow_html=True)
            else:
                st.sidebar.markdown("<span class='badge badge-gray'>Operator ID: Unknown</span>", unsafe_allow_html=True)

            st.sidebar.markdown("<div style='margin-top:6px'><span class='badge badge-gray'>Flyer ID</span></div>", unsafe_allow_html=True)

            st.sidebar.markdown("<div class='sidebar-title'>Key specs</div>", unsafe_allow_html=True)
            mtow = str(row.get("mtom_g_nominal","")).strip()
            mtow_display = (mtow+" g") if mtow else "—"
            remote_id = str(row.get("remote_id_builtin","")).strip() or "unknown"
            geo_awareness = str(row.get("geo_awareness","")).strip() or "—"
            st.sidebar.markdown(
                f"""
                <div class='sidebar-kv'><span class='kv-icon'>🏷️</span><b>Model</b> : {row.get('marketing_name','—')}</div>
                <div class='sidebar-kv'><span class='kv-icon'>⚖️</span><b>MTOW</b> : {mtow_display}</div>
                <div class='sidebar-kv'><span class='kv-icon'>🛰️</span><b>Remote ID</b> : {remote_id}</div>
                <div class='sidebar-kv'><span class='kv-icon'>🗺️</span><b>Geo-awareness</b> : {geo_awareness}</div>
                <div class='sidebar-kv'><span class='kv-icon'>📅</span><b>Released</b> : {row.get('year_released','—')}</div>
                """,
                unsafe_allow_html=True
            )

            # ---- Main body: compliance matrix ----
            render_rule_matrix(row)

        else:
            model = None

    if not model:
        models = models_for(segment, series)
        items=[]
        for _, r in models.iterrows():
            eu_c = (r.get("eu_class_marking") or r.get("class_marking") or "").strip()
            uk_c = (r.get("uk_class_marking") or r.get("class_marking") or "").strip()
            parts=[]
            if eu_c or uk_c:
                parts.append(f"Class: EU {eu_c or '—'} • UK {uk_c or '—'}")
            wb = r.get("weight_band","")
            if isinstance(wb,str) and wb:
                parts.append(f"Weight: {wb}")
            sub = " • ".join(parts)
            items.append(
                card_link(
                    f"segment={segment}&series={series}&model={r['model_key']}",
                    r.get("marketing_name",""),
                    sub=sub,
                    img_url=resolve_img(str(r.get("image_url","")))
                )
            )
        render_two_rows(f"Choose a drone ({seg_label} → {ser_label})", items)

