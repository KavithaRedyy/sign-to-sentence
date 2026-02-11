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

# =====================================================
# BACKGROUND FIX (BASE64 – ALWAYS WORKS)
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
            background-attachment: fixed;
        }}
        .card {{
            background: rgba(0,0,0,0.65);
            padding: 35px;
            border-radius: 18px;
            color: white;
            width: 420px;
            margin: auto;
            box-shadow: 0 0 40px rgba(0,255,255,0.45);
        }}
        section[data-testid="stSidebar"] {{
            background: rgba(0,0,0,0.7);
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
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.title("🔐 Login")

    email = st.text_input("📧 Email")
    password = st.text_input("🔑 Password", type="password")

    if st.button("Login"):
        cur.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cur.fetchone()
        if user:
            st.session_state.page = "app"
            cur.execute("INSERT INTO logins VALUES(NULL,?,?)", (email, datetime.now()))
            db.commit()
        else:
            st.error("Invalid credentials")

    st.button("📝 Register", on_click=lambda: st.session_state.update(page="signup"))
    st.button("🛡 Admin Login", on_click=lambda: st.session_state.update(page="admin"))
    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# SIGNUP PAGE
# =====================================================
def signup_page():
    set_bg("assets/bg_signup.png")
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.title("📝 Register")

    name = st.text_input("👤 Name")
    email = st.text_input("📧 Email")
    password = st.text_input("🔑 Password", type="password")

    if st.button("Create Account"):
        try:
            cur.execute(
                "INSERT INTO users VALUES(NULL,?,?,?,?)",
                (name, email, password, "user")
            )
            db.commit()
            st.success("Account created successfully")
            st.session_state.page = "login"
        except:
            st.error("Email already exists")

    st.button("⬅ Back to Login", on_click=lambda: st.session_state.update(page="login"))
    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# ADMIN LOGIN
# =====================================================
def admin_login():
    set_bg("assets/adminbg.png")
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.title("🛡 Admin Login")

    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if user == "admin" and pwd == "admin123":
            st.session_state.page = "admin_dashboard"
        else:
            st.error("Invalid admin credentials")

    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# ADMIN DASHBOARD
# =====================================================
def admin_dashboard():
    set_bg("assets/addashboard.png")
    st.sidebar.title("Admin Panel")

    nav = st.sidebar.radio("Navigation", ["Dashboard", "Users", "Logs", "Logout"])

    if nav == "Dashboard":
        st.header("📊 Admin Dashboard")
        c1, c2 = st.columns(2)
        c1.markdown("<div class='card'>👥 Users Overview</div>", unsafe_allow_html=True)
        c2.markdown("<div class='card'>📈 System Activity</div>", unsafe_allow_html=True)

    elif nav == "Users":
        st.header("👥 Registered Users")
        cur.execute("SELECT name,email,role FROM users")
        st.table(cur.fetchall())

    elif nav == "Logs":
        st.header("🕒 Login History")
        cur.execute("SELECT email,login_time FROM logins")
        st.table(cur.fetchall())

    else:
        st.session_state.page = "login"

# =====================================================
# SIGN TO SPEECH DASHBOARD (YOUR EXACT LOGIC)
# =====================================================
def sign_to_speech():
    set_bg("assets/addashboard.png")
    st.sidebar.title("Sign & Speech")

    section = st.sidebar.radio("Navigation", ["Dashboard", "Sign to Speech", "Logout"])

    if section == "Dashboard":
        st.header("📌 System Overview")
        a, b, c = st.columns(3)
        a.markdown("<div class='card'>📷 Live Camera</div>", unsafe_allow_html=True)
        b.markdown("<div class='card'>🧠 Sentence Builder</div>", unsafe_allow_html=True)
        c.markdown("<div class='card'>🔊 Voice Output</div>", unsafe_allow_html=True)
        return

    if section == "Logout":
        st.session_state.page = "login"
        st.stop()

    # ---------------- YOUR ORIGINAL CODE ----------------
    st.header("🤟 Sign to Speech – Sentence Level System")

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
    speak_btn = col1.button("🔊 Speak Sentence")
    restart_btn = col2.button("🔄 Restart")

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
        st.session_state.last_letter = None
        st.session_state.stable_count = 0
        st.session_state.last_hand_time = time.time()
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
            f"**Sentence Buffer:** {' '.join(st.session_state.words)}"
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
