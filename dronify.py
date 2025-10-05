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
    .card {
        background-color: white;
        border: 1px solid #ddd;
        border-radius: 12px;
        padding: 10px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        transition: all 0.2s ease-in-out;
    }
    .card:hover {
        box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        transform: translateY(-2px);
    }
    .card img {
        width: 180px;
        height: 120px;
        object-fit: contain;
        margin-bottom: 8px;
    }
    .card-title {
        font-weight: 600;
        color: #222 !important;
        text-decoration: none !important;
    }
    .card-sub {
        font-size: 13px;
        color: #666;
    }
    .center {
        display: flex;
        justify-content: center;
        align-items: center;
        flex-wrap: wrap;
        gap: 20px;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- Step 1: Select Segment ---------------- #
if "stage" not in st.session_state:
    st.session_state.stage = 1
if "segment" not in st.session_state:
    st.session_state.segment = None
if "series" not in st.session_state:
    st.session_state.series = None

def reset_to_stage(stage):
    st.session_state.stage = stage

if st.session_state.stage == 1:
    st.subheader("Choose your drone category")

    cols = st.columns(3, gap="large")
    for idx, (seg, img) in enumerate(SEGMENT_IMAGES.items()):
        with cols[idx]:
            if st.button("", key=f"seg_btn_{seg}"):
                st.session_state.segment = seg
                st.session_state.stage = 2
            st.markdown(f"""
                <div class="card" onclick="document.querySelector('[data-testid=stButton][key=seg_btn_{seg}] button').click()">
                    <img src="{img}" alt="{seg}">
                    <div class="card-title">{seg.capitalize()}</div>
                </div>
            """, unsafe_allow_html=True)

# ---------------- Step 2: Select Series ---------------- #
elif st.session_state.stage == 2:
    seg = st.session_state.segment
    st.subheader(f"Choose a series ({seg.capitalize()})")

    series_list = sorted(df.loc[df["segment"] == seg, "series"].dropna().unique())

    st.markdown('<div class="center">', unsafe_allow_html=True)
    for s in series_list:
        subset = df[(df["segment"] == seg) & (df["series"] == s)]
        if not subset.empty:
            chosen = subset.sample(1).iloc[0]
            img_file = chosen.get("image_url", "")
            img = resolve_img(img_file)
        else:
            img = resolve_img("consumer.jpg")

        st.markdown(f"""
        <div class="card" onclick="fetch('/?series={s}')">
            <img src="{img}" alt="{s}">
            <div class="card-title">{s.title()} Series</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    for s in series_list:
        if st.button(f"Select {s}", key=f"series_{s}"):
            st.session_state.series = s
            st.session_state.stage = 3

# ---------------- Step 3: Select Model ---------------- #
elif st.session_state.stage == 3:
    seg = st.session_state.segment
    ser = st.session_state.series
    st.subheader(f"Choose a drone ({seg.capitalize()} → {ser.title()} Series)")

    models = df[(df["segment"] == seg) & (df["series"] == ser)]

    st.markdown('<div class="center">', unsafe_allow_html=True)
    for _, row in models.iterrows():
        img = resolve_img(row.get("image_url", ""))
        name = row.get("marketing_name", "")
        weight = row.get("weight_band", "unknown")
        cls = row.get("class_marking", "unknown")

        st.markdown(f"""
        <div class="card">
            <img src="{img}" alt="{name}">
            <div class="card-title">{name}</div>
            <div class="card-sub">Class: {cls} • Weight: {weight}</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("← Back"):
        reset_to_stage(2)
