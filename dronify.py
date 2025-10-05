# dronify.py — “last good” UI + flags + badges + three-column rule panel (Now / 2026 / 2028)
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
    for col in (
        "image_url","segment","series",
        "class_marking","weight_band",
        "marketing_name","mtom_g_nominal",
        "eu_class_marking","uk_class_marking",
        "remote_id_builtin","year_released",
        "notes","operator_id_required","geo_awareness",
        "has_camera" # optional; defaults assumed if missing
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

/* rule panel (three columns) */
.rule-grid{
  display:grid;
  grid-template-columns: repeat(3, minmax(260px, 1fr));
  gap:14px; margin-top:12px;
}
.rule-card{
  border:1px solid #E5E7EB; border-radius:14px; padding:14px; background:#fff;
  box-shadow:0 4px 14px rgba(0,0,0,.04);
}
.rule-title{font-weight:800;color:#111827;margin-bottom:6px;}
.rule-head{font-weight:700;margin:2px 0 8px 0;}
.pill{display:inline-block;padding:4px 10px;border-radius:999px;font-weight:700;font-size:.8rem;margin-right:6px;margin-bottom:6px;}
.pill-ok{background:#DCFCE7;color:#14532D;}
.pill-warn{background:#FEF3C7;color:#92400E;}
.pill-bad{background:#FEE2E2;color:#991B1B;}
.rule-note{color:#374151;font-size:.92rem;margin:6px 0;}
.rule-ul{margin:6px 0 0 1rem; padding:0;}
.rule-ul li{margin:.2rem 0;}
.rule-foot{color:#6B7280;font-size:.8rem;margin-top:8px;}
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

def infer_weight_band(row):
    g = _float(row.get("mtom_g_nominal"))
    if g is None: return None
    if g < 250: return "sub250"
    if g < 900: return "250to900"
    if g < 4000: return "900to4kg"
    return "over4kg"

def has_camera(row):
    # Conservative: most DJI consumers have cameras. Allow override via YAML has_camera=yes/no.
    v = str(row.get("has_camera","")).strip().lower()
    if v in ("yes","true","1"): return True
    if v in ("no","false","0"): return False
    # default assumptions
    seg = str(row.get("segment","")).lower()
    series = str(row.get("series","")).lower()
    if seg in ("consumer","pro","enterprise"): return True
    return True

def summarize_now(row):
    """Current (2025) UK Open cat with EU class marks effectively usable; legacy transitional still in effect."""
    wb = infer_weight_band(row)
    eu = (row.get("eu_class_marking") or row.get("class_marking") or "").upper()
    uk = (row.get("uk_class_marking") or "").upper()
    out = {"title":"Now","headline":[],"bullets":[],"notes":[],"status":"ok"}
    # Headline logic
    if eu=="C0" or wb=="sub250":
        out["headline"].append("A1 (close to people; no crowds)")
        out["bullets"] += ["<120 m AGL & VLOS","Avoid assemblies of people"]
    elif eu=="C1":
        out["headline"].append("A1 / A2 (with A2 CofC) / A3")
        out["bullets"] += ["Avoid deliberate overflight of people","A2: 5–30 m with A2 CofC","A3 always permitted away from people"]
    elif eu in ("C2","C3","C4"):
        out["headline"].append("A2 (with A2 CofC) / A3")
        out["bullets"] += ["A2: 5–30 m with A2 CofC","A3: ≥150 m from built-up areas"]
        out["status"]="warn"
    else:
        # Legacy / unknown
        if wb=="sub250":
            out["headline"].append("A1 (legacy sub-250)")
            out["bullets"] += ["No crowds","Be considerate near people"]
        elif wb in ("250to900","900to4kg","over4kg"):
            out["headline"].append("Likely A3 (legacy)")
            out["bullets"] += ["No uninvolved people nearby","≥150 m from residential/industrial/commercial"]
            out["status"]="warn"
        else:
            out["headline"].append("Check category")
            out["bullets"] += ["Provide weight/class to refine"]
            out["status"]="bad"
    out["notes"].append("EU class marks usable in UK at present. Transitional allowances apply.")
    return out

def summarize_2026(row):
    """From 1 Jan 2026 — UK class marks begin; EU marks recognised until 31 Dec 2027; transitional extended."""
    wb = infer_weight_band(row)
    eu = (row.get("eu_class_marking") or row.get("class_marking") or "").upper()
    uk = (row.get("uk_class_marking") or "").upper()
    out = {"title":"From 1 Jan 2026","headline":[],"bullets":[],"notes":[],"status":"ok"}
    # Prefer UK class if present
    if uk.startswith("UK"):
        k = uk
        if k=="UK0":
            out["headline"].append("A1")
            out["bullets"]+=["Close to people; no crowds","Geo-awareness expected","<120 m & VLOS"]
        elif k=="UK1":
            out["headline"].append("A1 / A2")
            out["bullets"]+=["Avoid overflight; 5–30 m in A2","Remote ID & Geo-awareness"]
        elif k=="UK2":
            out["headline"].append("A2 / A3")
            out["bullets"]+=["A2 with 5–30 m","A3 ≥150 m from built-up","Remote ID & Geo-awareness"]
        elif k in ("UK3","UK4","UK5","UK6"):
            out["headline"].append("A3 / Specific")
            out["bullets"]+=["A3: away from people & built-up","Specific category likely for many ops"]
            out["status"]="warn"
        else:
            out["headline"].append("Depends on UK class")
            out["status"]="warn"
    else:
        # EU marks still recognised in UK during 2026–2027
        if eu=="C0" or wb=="sub250":
            out["headline"].append("A1")
            out["bullets"]+=["No crowds","Lights at night"]
        elif eu=="C1":
            out["headline"].append("A1 / A2 / A3")
            out["bullets"]+=["A2: 5–30 m with A2 CofC"]
        elif eu in ("C2","C3","C4"):
            out["headline"].append("A2 (with A2 CofC) / A3")
            out["status"]="warn"
        else:
            # Legacy extended
            if wb=="sub250":
                out["headline"].append("A1 (legacy)")
            else:
                out["headline"].append("Likely A3 (legacy)")
                out["status"]="warn"
            out["bullets"]+=["Transitional rules extended; check limits"]
    # Advisory add-ons
    out["notes"] += ["Remote ID mandatory for many UK1–UK3/5/6.","Geo-awareness required for UK1–UK3."]
    return out

def summarize_2028(row):
    """From 1 Jan 2028 — EU marks no longer recognised; Remote ID expands; Geo for UK0 ≥100g camera."""
    wb = infer_weight_band(row)
    uk = (row.get("uk_class_marking") or "").upper()
    cam = has_camera(row)
    out = {"title":"From 1 Jan 2028 (planned)","headline":[],"bullets":[],"notes":[],"status":"ok"}
    if uk.startswith("UK"):
        if uk=="UK0":
            out["headline"].append("A1")
            out["bullets"]+=["No crowds","Geo-awareness required ≥100 g w/camera"]
        elif uk=="UK1":
            out["headline"].append("A1 / A2")
            out["bullets"]+=["Avoid overflight; A2 5–30 m","Remote ID & Geo-awareness"]
        elif uk=="UK2":
            out["headline"].append("A2 / A3")
            out["bullets"]+=["A2 with A2 CofC","A3 ≥150 m from built-up","Remote ID & Geo-awareness"]
        elif uk in ("UK3","UK4","UK5","UK6"):
            out["headline"].append("A3 / Specific")
            out["bullets"]+=["Specific category likely for many ops"]
            out["status"]="warn"
        else:
            out["headline"].append("Depends on UK class")
            out["status"]="warn"
    else:
        # Legacy without UK class in 2028
        if wb=="sub250":
            out["headline"].append("A1 (legacy)")
            out["bullets"]+=["Geo-awareness likely if ≥100 g & camera","Remote ID may be required if ≥100 g & camera"]
            out["status"]="warn"
        elif wb:
            out["headline"].append("Likely A3 (legacy)")
            out["bullets"]+=["EU class no longer recognised","Remote ID required ≥100 g & camera","Specific category may be needed"]
            out["status"]="bad"
        else:
            out["headline"].append("Insufficient data")
            out["status"]="bad"
    out["notes"]+=["EU class marks not recognised after 31 Dec 2027."]
    return out

def render_rule_card(summary: dict):
    title = summary["title"]
    head  = " • ".join(summary["headline"]) if summary["headline"] else "—"
    bullets = "".join(f"<li>{b}</li>" for b in summary["bullets"])
    notes = " ".join(summary["notes"])
    pill_cls = "pill-ok" if summary["status"]=="ok" else ("pill-warn" if summary["status"]=="warn" else "pill-bad")
    head_html = f"<span class='pill {pill_cls}'>{head}</span>"
    return (
        f"<div class='rule-card'>"
        f"<div class='rule-title'>{title}</div>"
        f"<div class='rule-head'>{head_html}</div>"
        f"<ul class='rule-ul'>{bullets}</ul>"
        f"<div class='rule-foot'>{notes}</div>"
        f"</div>"
    )

def render_rule_panel(row):
    now = summarize_now(row)
    y26 = summarize_2026(row)
    y28 = summarize_2028(row)
    html = (
        "<div class='rule-grid'>"
        f"{render_rule_card(now)}"
        f"{render_rule_card(y26)}"
        f"{render_rule_card(y28)}"
        "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)

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

    # If a model is selected, show sidebar details + MAIN rule panel
    if model:
        sel = df[df["model_key"] == model]
        if not sel.empty:
            row = sel.iloc[0]
            back_qs = f"segment={segment}&series={series}"
            st.sidebar.markdown(f"<a class='sidebar-back' href='?{back_qs}' target='_self'>← Back to models</a>", unsafe_allow_html=True)

            img_url = resolve_img(row.get("image_url",""))
            if img_url:
                st.sidebar.image(img_url, use_container_width=True, caption=row.get("marketing_name",""))

            # EU/UK flag lines
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

            # Operator ID badge + Flyer ID (placeholder)
            op = str(row.get("operator_id_required","")).strip().lower()
            if op in ("yes","true","1"):
                st.sidebar.markdown("<span class='badge badge-red'>Operator ID: Required</span>", unsafe_allow_html=True)
            elif op in ("no","false","0"):
                st.sidebar.markdown("<span class='badge badge-green'>Operator ID: Not required</span>", unsafe_allow_html=True)
            else:
                st.sidebar.markdown("<span class='badge badge-gray'>Operator ID: Unknown</span>", unsafe_allow_html=True)
            st.sidebar.markdown("<div style='margin-top:6px'><span class='badge badge-gray'>Flyer ID</span></div>", unsafe_allow_html=True)

            # Key specs
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

            # ---- NEW: main body rule panel (three columns) ----
            render_rule_panel(row)

        else:
            model = None

    # Model grid if no model selected
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
