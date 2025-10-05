import random
import streamlit as st
import pandas as pd
import yaml
from pathlib import Path

st.set_page_config(page_title="Dronify", layout="wide")

# ---------------- Load YAML ---------------- #
DATASET_PATH = Path("dji_drones_v3.yaml")
TAXONOMY_PATH = Path("taxonomy.yaml")

def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@st.cache_data
def load_data():
    dataset = load_yaml(DATASET_PATH)
    taxonomy = load_yaml(TAXONOMY_PATH)
    df = pd.DataFrame(dataset["data"])
    return df, taxonomy

df, taxonomy = load_data()

# ---------------- Image Handling ---------------- #
RAW_BASE = "https://raw.githubusercontent.com/JonathanGreen79/dronify/main/images/"

def resolve_img(filename: str):
    if not filename:
        return ""
    if filename.startswith("images/"):
        filename = filename.split("/", 1)[1]
    return f"{RAW_BASE}{filename}"

SEGMENT_IMAGES = {
    "consumer": resolve_img("consumer.jpg"),
    "pro": resolve_img("professional.jpg"),
    "enterprise": resolve_img("enterprise.jpg"),
}

# ---------------- Style ---------------- #
st.markdown("""
<style>
    .stApp {
        background-color: #fafafa;
    }
    .card-container {
        display: flex;
        justify-content: center;
        align-items: center;
        flex-wrap: wrap;
        gap: 25px;
        margin-top: 20px;
    }
    .card {
        background-color: white;
        border: 1px solid #ddd;
        border-radius: 12px;
        padding: 10px;
        text-align: center;
        width: 280px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        transition: all 0.2s ease-in-out;
        cursor: pointer;
    }
    .card:hover {
        box-shadow: 0 3px 8px rgba(0,0,0,0.2);
        transform: translateY(-2px);
    }
    .card img {
        width: 200px;
        height: 130px;
        object-fit: contain;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .card-title {
        font-weight: 600;
        color: #222;
        text-decoration: none !important;
        margin-bottom: 6px;
    }
    .card-sub {
        font-size: 13px;
        color: #666;
    }
    button[title="button"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- Step Logic ---------------- #
if "stage" not in st.session_state:
    st.session_state.stage = 1
if "segment" not in st.session_state:
    st.session_state.segment = None
if "series" not in st.session_state:
    st.session_state.series = None

def reset_to_stage(stage):
    st.session_state.stage = stage

# ---------------- Step 1 ---------------- #
if st.session_state.stage == 1:
    st.subheader("Choose your drone category")

    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    for seg, img in SEGMENT_IMAGES.items():
        st.markdown(
            f"""
            <div class="card" onclick="window.location.reload(); 
            fetch('/_stcore/update', {{method:'POST',headers:{{'Content-Type':'application/json'}},
            body:JSON.stringify({{'segment':'{seg}','stage':2}})}})">
                <img src="{img}" alt="{seg}">
                <div class="card-title">{seg.capitalize()}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Step 2 ---------------- #
elif st.session_state.stage == 2:
    seg = st.session_state.segment
    st.subheader(f"Choose a series ({seg.capitalize()})")

    series_list = sorted(df.loc[df["segment"] == seg, "series"].dropna().unique())

    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    for s in series_list:
        subset = df[(df["segment"] == seg) & (df["series"] == s)]
        img = resolve_img(subset.sample(1).iloc[0].get("image_url", "")) if not subset.empty else resolve_img("consumer.jpg")
        st.markdown(
            f"""
            <div class="card" onclick="window.location.reload(); 
            fetch('/_stcore/update', {{method:'POST',headers:{{'Content-Type':'application/json'}},
            body:JSON.stringify({{'series':'{s}','stage':3}})}})">
                <img src="{img}" alt="{s}">
                <div class="card-title">{s.title()} Series</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Step 3 ---------------- #
elif st.session_state.stage == 3:
    seg = st.session_state.segment
    ser = st.session_state.series
    st.subheader(f"Choose a drone ({seg.capitalize()} → {ser.title()} Series)")

    models = df[(df["segment"] == seg) & (df["series"] == ser)]

    st.markdown('<div class="card-container">', unsafe_allow_html=True)
    for _, row in models.iterrows():
        img = resolve_img(row.get("image_url", ""))
        name = row.get("marketing_name", "")
        weight = row.get("weight_band", "unknown")
        cls = row.get("class_marking", "unknown")

        st.markdown(
            f"""
            <div class="card">
                <img src="{img}" alt="{name}">
                <div class="card-title">{name}</div>
                <div class="card-sub">Class: {cls} • Weight: {weight}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("← Back"):
        reset_to_stage(2)
