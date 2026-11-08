import time
import threading
from collections import deque
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from openpyxl import Workbook, load_workbook

try:
    from streamlit_shortcuts import add_shortcuts
    SHORTCUTS_AVAILABLE = True
except ImportError:
    add_shortcuts = None
    SHORTCUTS_AVAILABLE = False


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="ESP32 Smart Rover",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# ESP32 CONFIGURATION
# Change this IP address to the IP shown in your ESP32 Serial
# Monitor. The ESP32 and computer must be on the same network.
# ============================================================

ESP32_IP = "172.24.229.237"
BASE_URL = f"http://{ESP32_IP}"
REQUEST_TIMEOUT = 2.0
MAX_POINTS = 100

EXCEL_FILE = Path(__file__).resolve().parent / "rover_data.xlsx"
EXCEL_LOCK = threading.Lock()


# ============================================================
# SESSION STATE
# ============================================================

def initialize_session_state():
    defaults = {
        "time_data": deque(maxlen=MAX_POINTS),
        "temperature_data": deque(maxlen=MAX_POINTS),
        "gas_data": deque(maxlen=MAX_POINTS),
        "light_data": deque(maxlen=MAX_POINTS),
        "start_time": time.time(),
        "temperature": None,
        "gas": None,
        "light": None,
        "status": "Not connected",
        "last_command": "STOP",
        "speed": 180,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_session_state()


# ============================================================
# EXCEL LOGGING
# ============================================================

def setup_excel():
    with EXCEL_LOCK:
        if not EXCEL_FILE.exists():
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.title = "Rover Data"
            worksheet.append([
                "Timestamp",
                "Elapsed Time (s)",
                "Data Type",
                "Command",
                "Speed",
                "Temperature (°C)",
                "Gas",
                "Light",
                "Status",
            ])
            workbook.save(EXCEL_FILE)
            workbook.close()


def log_to_excel(
    data_type,
    command="",
    speed="",
    temperature="",
    gas="",
    light="",
    status="",
):
    try:
        setup_excel()
        elapsed = round(time.time() - st.session_state.start_time, 2)

        with EXCEL_LOCK:
            workbook = load_workbook(EXCEL_FILE)
            worksheet = workbook["Rover Data"]
            worksheet.append([
                time.strftime("%Y-%m-%d %H:%M:%S"),
                elapsed,
                data_type,
                command,
                speed,
                temperature,
                gas,
                light,
                status,
            ])
            workbook.save(EXCEL_FILE)
            workbook.close()
    except Exception as error:
        print(f"Excel logging error: {error}")


setup_excel()


# ============================================================
# ESP32 COMMUNICATION
# ============================================================

def send_command(command):
    try:
        response = requests.get(
            f"{BASE_URL}/{command}",
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        st.session_state.status = "ESP32 Connected"
        return True
    except requests.RequestException as error:
        st.session_state.status = "ESP32 Disconnected"
        print(f"ESP32 communication error: {error}")
        return False


def movement(command, description):
    success = send_command(command.lower())
    st.session_state.last_command = command.upper()

    log_to_excel(
        "Movement",
        command=command.upper(),
        status=description if success else "Command failed",
    )


def move_forward():
    movement("forward", "Moving Forward")


def move_backward():
    movement("backward", "Moving Backward")


def move_left():
    movement("left", "Turning Left")


def move_right():
    movement("right", "Turning Right")


def stop_rover():
    movement("stop", "Stopped")


# ============================================================
# MOTOR SPEED
# ============================================================

def change_speed(speed):
    speed = int(speed)

    try:
        response = requests.get(
            f"{BASE_URL}/speed",
            params={"value": speed},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        st.session_state.speed = speed
        st.session_state.status = "ESP32 Connected"

        log_to_excel(
            "Speed",
            speed=speed,
            status=f"Speed set to {speed}",
        )
        return True
    except requests.RequestException as error:
        st.session_state.status = "ESP32 Disconnected"
        print(f"Speed control error: {error}")
        return False


# ============================================================
# SENSOR READING
# Expected ESP32 JSON format:
# {"temperature": 25.5, "gas": 120, "light": 650}
# ============================================================

def read_sensors():
    try:
        response = requests.get(
            f"{BASE_URL}/sensors",
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        temperature = float(data["temperature"])
        gas = float(data["gas"])
        light = float(data["light"])

        elapsed = time.time() - st.session_state.start_time

        st.session_state.time_data.append(elapsed)
        st.session_state.temperature_data.append(temperature)
        st.session_state.gas_data.append(gas)
        st.session_state.light_data.append(light)

        st.session_state.temperature = temperature
        st.session_state.gas = gas
        st.session_state.light = light
        st.session_state.status = "ESP32 Connected"

        log_to_excel(
            "Sensor",
            temperature=temperature,
            gas=gas,
            light=light,
            status="ESP32 Connected",
        )
        return True

    except (
        requests.RequestException,
        ValueError,
        KeyError,
        TypeError,
    ) as error:
        st.session_state.status = "ESP32 Disconnected"
        print(f"Sensor reading error: {error}")
        return False


# ============================================================
# CUSTOM DARK THEME
# ============================================================

st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        background-color: #0b1120;
        color: #e2e8f0;
    }
    [data-testid="stHeader"] {
        background-color: #0b1120;
    }
    .block-container {
        max-width: 1500px;
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    [data-testid="stSidebar"] {
        background-color: #111c30;
        border-right: 1px solid #263750;
    }
    [data-testid="stSidebar"] * {
        color: #e2e8f0;
    }
    .stApp, .stApp p, .stApp label,
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
        color: #e2e8f0;
    }
    .hero {
        padding: 25px;
        border-radius: 18px;
        background: linear-gradient(135deg, #172554, #075985, #0891b2);
        margin-bottom: 25px;
        box-shadow: 0 8px 30px rgba(0,180,255,0.15);
    }
    .hero h1 {
        color: #ffffff !important;
        font-size: 2.3rem;
        margin: 0;
    }
    .hero p {
        color: #bae6fd !important;
        margin-top: 8px;
    }
    [data-testid="stMetric"] {
        background-color: #172338;
        border: 1px solid #29415f;
        padding: 18px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    [data-testid="stMetricLabel"] {
        color: #93c5fd !important;
    }
    [data-testid="stMetricValue"] {
        color: #38bdf8 !important;
    }
    .stButton > button {
        background-color: #172c46;
        color: #ffffff !important;
        border: 1px solid #0ea5e9;
        border-radius: 12px;
        min-height: 65px;
        font-weight: bold;
        transition: 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #0369a1;
        border-color: #38bdf8;
        color: white !important;
        box-shadow: 0 0 15px rgba(14,165,233,0.4);
    }
    .stButton > button[kind="primary"] {
        background-color: #dc2626;
        border: 1px solid #f87171;
        color: white !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #991b1b;
    }
    [data-testid="stSlider"] {
        color: #38bdf8;
    }
    [data-testid="stProgressBar"] > div > div {
        background-color: #06b6d4;
    }
    .stTextInput input {
        background-color: #172338;
        color: white !important;
        border: 1px solid #334e68;
    }
    .status-card {
        background-color: #172338;
        border: 1px solid #29415f;
        padding: 18px;
        border-radius: 15px;
        color: #e2e8f0;
    }
    .status-card b {
        color: #38bdf8;
    }
    .small-note, [data-testid="stCaption"] {
        color: #94a3b8 !important;
    }
    hr {
        border-color: #334155;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="hero">
        <h1>🤖 ESP32 SMART ROVER</h1>
        <p>
            Wireless Rover Control |
            Live Sensor Monitoring |
            Excel Data Logging
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("⚙️ Rover Settings")
    st.text_input(
        "ESP32 IP Address",
        value=ESP32_IP,
        disabled=True,
    )
    st.write(f"**Base URL:** `{BASE_URL}`")
    st.write(f"**Excel File:** `{EXCEL_FILE.name}`")

    if st.button("🔌 Test ESP32 Connection", use_container_width=True):
        if send_command("stop"):
            st.success("ESP32 is reachable.")
        else:
            st.error("ESP32 is not reachable. Check its IP and Wi-Fi.")

    st.divider()
    st.subheader("⌨️ Keyboard Controls")

    if SHORTCUTS_AVAILABLE:
        st.success("Arrow-key support available")
        st.caption("↑ Forward | ↓ Backward | ← Left | → Right | SPACE Stop")
    else:
        st.warning("Optional keyboard shortcuts are not installed.")
        st.code("python -m pip install streamlit-shortcuts")

    st.divider()
    st.subheader("📁 Excel Data")

    if EXCEL_FILE.exists():
        st.download_button(
            "📥 Download Excel Log",
            data=EXCEL_FILE.read_bytes(),
            file_name="rover_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


# ============================================================
# ROVER MOVEMENT CONTROL
# ============================================================

st.subheader("🎮 Rover Movement Control")

left_col, center_col, right_col = st.columns([1, 2, 1])

with center_col:
    top = st.columns(3)
    with top[1]:
        forward_btn = st.button(
            "⬆️ FORWARD",
            key="forward_btn",
            use_container_width=True,
        )

    middle = st.columns(3)
    with middle[0]:
        left_btn = st.button(
            "⬅️ LEFT",
            key="left_btn",
            use_container_width=True,
        )
    with middle[1]:
        stop_btn = st.button(
            "🛑 STOP",
            key="stop_btn",
            type="primary",
            use_container_width=True,
        )
    with middle[2]:
        right_btn = st.button(
            "➡️ RIGHT",
            key="right_btn",
            use_container_width=True,
        )

    bottom = st.columns(3)
    with bottom[1]:
        backward_btn = st.button(
            "⬇️ BACKWARD",
            key="backward_btn",
            use_container_width=True,
        )

if forward_btn:
    move_forward()
if backward_btn:
    move_backward()
if left_btn:
    move_left()
if right_btn:
    move_right()
if stop_btn:
    stop_rover()

if SHORTCUTS_AVAILABLE:
    try:
        add_shortcuts(
            forward_btn="arrowup",
            backward_btn="arrowdown",
            left_btn="arrowleft",
            right_btn="arrowright",
            stop_btn="space",
        )
    except Exception as error:
        st.sidebar.warning(f"Keyboard shortcut setup failed: {error}")


# ============================================================
# MOTOR SPEED CONTROL
# ============================================================

st.divider()
st.subheader("⚡ Motor Speed Control")

speed = st.slider(
    "Adjust Motor Speed",
    min_value=0,
    max_value=255,
    value=int(st.session_state.speed),
    step=1,
    key="speed_slider",
)

if speed != st.session_state.speed:
    change_speed(speed)

st.progress(speed / 255)
st.caption(f"Current Motor Speed: {speed} / 255")


# ============================================================
# SYSTEM STATUS
# ============================================================

st.divider()
st.subheader("📊 Rover System Status")

status_left, status_mid, status_right = st.columns(3)

with status_left:
    st.metric("Connection", st.session_state.status)
with status_mid:
    st.metric("Current Command", st.session_state.last_command)
with status_right:
    st.metric("Motor Speed", st.session_state.speed)


# ============================================================
# LIVE SENSOR DASHBOARD
# Requires Streamlit 1.37 or newer for st.fragment.
# ============================================================

st.divider()
st.subheader("📡 Live Sensor Monitoring")


@st.fragment(run_every="1s")
def live_dashboard():
    read_sensors()

    col1, col2, col3 = st.columns(3)

    with col1:
        temperature = st.session_state.temperature
        st.metric(
            "🌡️ Temperature",
            "-- °C" if temperature is None else f"{temperature:.1f} °C",
        )

    with col2:
        gas = st.session_state.gas
        st.metric(
            "🫁 Gas Sensor",
            "--" if gas is None else f"{gas:.0f}",
        )

    with col3:
        light = st.session_state.light
        st.metric(
            "💡 Light Sensor",
            "--" if light is None else f"{light:.0f}",
        )

    st.caption(
        f"Connection: {st.session_state.status} | "
        f"Last Command: {st.session_state.last_command}"
    )

    if st.session_state.time_data:
        graph_data = pd.DataFrame({
            "Time (s)": list(st.session_state.time_data),
            "Temperature (°C)": list(st.session_state.temperature_data),
            "Gas": list(st.session_state.gas_data),
            "Light": list(st.session_state.light_data),
        }).set_index("Time (s)")

        st.divider()
        st.subheader("📈 Live Sensor Graphs")

        graph1, graph2, graph3 = st.columns(3)

        with graph1:
            st.caption("🌡️ Temperature")
            st.line_chart(graph_data[["Temperature (°C)"]], height=260)

        with graph2:
            st.caption("🫁 Gas Sensor")
            st.line_chart(graph_data[["Gas"]], height=260)

        with graph3:
            st.caption("💡 Light Sensor")
            st.line_chart(graph_data[["Light"]], height=260)
    else:
        st.info("Waiting for sensor readings from the ESP32...")


live_dashboard()


# ============================================================
# EXCEL LOGGING INFORMATION
# ============================================================

st.divider()
st.subheader("📁 Automatic Data Logging")

st.markdown(
    """
    <div class="status-card">
        <b>Excel Logging Active</b>
        <p>
            Movement commands, motor speed changes, and sensor readings
            are automatically stored in rover_data.xlsx.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

if EXCEL_FILE.exists():
    file_size = EXCEL_FILE.stat().st_size / 1024
    st.info(
        f"Excel File: {EXCEL_FILE.name} | "
        f"File Size: {file_size:.2f} KB"
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()
st.markdown(
    """
    <p class="small-note">
        ESP32 SMART ROVER DASHBOARD |
        Streamlit UI |
        Wireless Motor Control |
        Temperature + Gas + Light Monitoring |
        Excel Data Logging
    </p>
    """,
    unsafe_allow_html=True,
)
