import os
os.environ["OPENCV_VIDEOIO_PRIORITY_MSMF"] = "0"

import base64
import streamlit as st
import sqlite3
import cv2
import time
import mediapipe as mp
from ultralytics import YOLO
from datetime import datetime
from tts_edge import speak_sentence
import pandas as pd

# =====================================================
# UI / UX – PROFESSIONAL CSS
# =====================================================
def set_bg(image_path):
    with open(image_path, "rb") as img:
        encoded = base64.b64encode(img.read()).decode()

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        }}

        .glass {{
            background: rgba(15, 25, 40, 0.78);
            padding: 38px;
            border-radius: 20px;
            color: #eaf6ff;
            max-width: 430px;
            margin: auto;
            box-shadow: 0 10px 40px rgba(0,0,0,0.55);
        }}

        h1, h2, h3 {{
            color: #00f7ff;
            text-align: center;
        }}

        label, p {{
            color: #f0f6ff !important;
        }}

        section[data-testid="stSidebar"] {{
            background: rgba(10, 15, 25, 0.9);
        }}

        .metric-box {{
            background: rgba(20, 40, 70, 0.75);
            padding: 25px;
            border-radius: 16px;
            text-align: center;
            box-shadow: 0 8px 25px rgba(0,255,255,0.25);
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# =====================================================
# DATABASE
# =====================================================
db = sqlite3.connect("database.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT UNIQUE,
    password TEXT,
    role TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS logins(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    login_time TEXT
)
""")
db.commit()

# =====================================================
# SESSION STATE
# =====================================================
if "page" not in st.session_state:
    st.session_state.page = "login"

# =====================================================
# LOGIN PAGE
# =====================================================
def login_page():
    set_bg("assets/bg_login.png")

    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.title("Sign-to-Speech Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        cur.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cur.fetchone()
        if user:
            st.session_state.page = "app"
            cur.execute("INSERT INTO logins VALUES(NULL,?,?)", (email, datetime.now()))
            db.commit()
        else:
            st.error("Invalid credentials")

    st.caption("New user?")
    if st.button("Create Account"):
        st.session_state.page = "signup"

    st.caption("Administrator access")
    if st.button("Admin Login"):
        st.session_state.page = "admin"

    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# SIGNUP PAGE
# =====================================================
def signup_page():
    set_bg("assets/bg_signup.png")

    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.title("Create Account")

    name = st.text_input("Full Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Register"):
        try:
            cur.execute("INSERT INTO users VALUES(NULL,?,?,?,?)",
                        (name, email, password, "user"))
            db.commit()
            st.success("Account created successfully")
            st.session_state.page = "login"
        except:
            st.error("Email already exists")

    if st.button("Back to Login"):
        st.session_state.page = "login"

    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# ADMIN LOGIN
# =====================================================
def admin_login():
    set_bg("assets/adminbg.png")

    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.title("Admin Authentication")

    user = st.text_input("Admin Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if user == "admin" and pwd == "admin123":
            st.session_state.page = "admin_dashboard"
        else:
            st.error("Invalid admin credentials")

    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# ADMIN DASHBOARD (WITH GRAPH)
# =====================================================
def admin_dashboard():
    set_bg("assets/addashboard.png")
    st.sidebar.title("Admin Panel")

    nav = st.sidebar.radio("Navigation", ["Dashboard", "Users", "Logout"])

    if nav == "Dashboard":
        st.header("System Activity Overview")

        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]

        cur.execute("SELECT login_time FROM logins")
        logs = cur.fetchall()
        df = pd.DataFrame(logs, columns=["time"])
        df["time"] = pd.to_datetime(df["time"])
        daily = df.groupby(df["time"].dt.date).size()

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<div class='metric-box'>", unsafe_allow_html=True)
            st.metric("Registered Users", total_users)
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown("<div class='metric-box'>", unsafe_allow_html=True)
            st.metric("Total Logins", len(logs))
            st.markdown("</div>", unsafe_allow_html=True)

        if not daily.empty:
            st.subheader("User Login Activity")
            st.line_chart(daily)

    elif nav == "Users":
        st.header("Registered Users")
        cur.execute("SELECT name,email,role FROM users")
        st.dataframe(cur.fetchall(), use_container_width=True)

    else:
        st.session_state.page = "login"

# =====================================================
# SIGN-TO-SPEECH (UNCHANGED CORE LOGIC)
# =====================================================
def sign_to_speech():
    set_bg("assets/addashboard.png")
    st.sidebar.title("Sign-to-Speech")

    section = st.sidebar.radio("Menu", ["Live Translation", "Logout"])

    if section == "Logout":
        st.session_state.page = "login"
        st.stop()

    st.header("Live Sign-to-Speech Translation")

    MODEL_PATH = "runs/classify/train/weights/best.pt"
    CONF_THRESHOLD = 0.85
    STABLE_FRAMES = 10
    SPACE_TIME = 2.0

    model = YOLO(MODEL_PATH)
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(max_num_hands=1)

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    frame_box = st.image([])
    info_box = st.empty()
    sentence_box = st.empty()

    col1, col2 = st.columns(2)
    speak_btn = col1.button("Speak Sentence")
    restart_btn = col2.button("Restart")

    if "letters" not in st.session_state:
        st.session_state.letters = []
    if "words" not in st.session_state:
        st.session_state.words = []
    if "last_letter" not in st.session_state:
        st.session_state.last_letter = None
    if "stable_count" not in st.session_state:
        st.session_state.stable_count = 0
    if "last_hand_time" not in st.session_state:
        st.session_state.last_hand_time = time.time()

    if restart_btn:
        st.session_state.letters.clear()
        st.session_state.words.clear()
        st.stop()

    if speak_btn and st.session_state.words:
        sentence = " ".join(st.session_state.words).capitalize()
        sentence_box.success(sentence)
        speak_sentence(sentence)
        st.stop()

    run = st.checkbox("Start Camera")

    while run:
        ret, frame = cap.read()
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        if not result.multi_hand_landmarks:
            if st.session_state.letters and time.time() - st.session_state.last_hand_time > SPACE_TIME:
                st.session_state.words.append("".join(st.session_state.letters))
                st.session_state.letters.clear()
            frame_box.image(frame, channels="BGR")
            continue

        st.session_state.last_hand_time = time.time()

        h, w, _ = frame.shape
        lm = result.multi_hand_landmarks[0].landmark
        xs = [int(p.x * w) for p in lm]
        ys = [int(p.y * h) for p in lm]

        roi = frame[min(ys):max(ys), min(xs):max(xs)]
        results = model(roi, verbose=False)
        probs = results[0].probs

        if probs and probs.top1conf > CONF_THRESHOLD:
            letter = model.names[probs.top1]
            if letter == st.session_state.last_letter:
                st.session_state.stable_count += 1
            else:
                st.session_state.last_letter = letter
                st.session_state.stable_count = 1

            if st.session_state.stable_count >= STABLE_FRAMES:
                st.session_state.letters.append(letter)
                st.session_state.stable_count = 0

        info_box.markdown(
            f"**Current Word:** {''.join(st.session_state.letters)}  \n"
            f"**Sentence:** {' '.join(st.session_state.words)}"
        )
        frame_box.image(frame, channels="BGR")

# =====================================================
# ROUTER
# =====================================================
if st.session_state.page == "login":
    login_page()
elif st.session_state.page == "signup":
    signup_page()
elif st.session_state.page == "admin":
    admin_login()
elif st.session_state.page == "admin_dashboard":
    admin_dashboard()
elif st.session_state.page == "app":
    sign_to_speech()
