import streamlit as st
import pandas as pd
import math
import os
import random
from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go

st.set_page_config(page_title="Celestial Logbook", page_icon="⚓", layout="wide", initial_sidebar_state="collapsed")

KST = timezone(timedelta(hours=9))
LOG_FILE = "log.csv"
NAUTICAL_MILES_PER_MINUTE = 1.0
BUSAN_LAT, BUSAN_LON = 35.1796, 129.0756

DESTINATIONS = {
    "도쿄": {"country": "일본", "lat": 35.6762, "lon": 139.6503},
    "상하이": {"country": "중국", "lat": 31.2304, "lon": 121.4737},
    "싱가포르": {"country": "싱가포르", "lat": 1.3521, "lon": 103.8198},
    "시드니": {"country": "호주", "lat": -33.8688, "lon": 151.2093},
    "호놀룰루": {"country": "미국", "lat": 21.3069, "lon": -157.8583},
    "밴쿠버": {"country": "캐나다", "lat": 49.2827, "lon": -123.1207},
    "로스앤젤레스": {"country": "미국", "lat": 34.0522, "lon": -118.2437},
    "런던": {"country": "영국", "lat": 51.5074, "lon": -0.1278},
    "파리": {"country": "프랑스", "lat": 48.8566, "lon": 2.3522},
    "뉴욕": {"country": "미국", "lat": 40.7128, "lon": -74.0060},
}

POMODORO_ROUTE = ["부산", "울산", "포항", "동해", "속초"]
POMODORO_DESTINATION = {"lat": 38.2070, "lon": 128.5918}

CONSTELLATIONS = {
    1: "오리온자리", 2: "큰개자리", 3: "쌍둥이자리", 4: "사자자리",
    5: "처녀자리", 6: "목동자리", 7: "전갈자리", 8: "궁수자리",
    9: "백조자리", 10: "페가수스자리", 11: "황소자리", 12: "마차부자리"
}


def get_kst_now():
    return datetime.now(KST)


def haversine_nm(lat1, lon1, lat2, lon2):
    """두 위치 사이의 거리를 해리로 계산"""
    earth_radius_km = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_km * c / 1.852


def get_destination_distance(destination):
    info = DESTINATIONS[destination]
    return haversine_nm(BUSAN_LAT, BUSAN_LON, info["lat"], info["lon"])


def get_moon_phase(date_value):
    reference = datetime(2000, 1, 6)
    target = datetime(date_value.year, date_value.month, date_value.day)
    days = (target - reference).days
    phase = (days % 29.53058867) / 29.53058867
    if phase < 0.03:
        return "🌑 신월"
    if phase < 0.22:
        return "🌒 초승달"
    if phase < 0.28:
        return "🌓 상현달"
    if phase < 0.47:
        return "🌔 차오르는 달"
    if phase < 0.53:
        return "🌕 보름달"
    if phase < 0.72:
        return "🌖 기우는 달"
    if phase < 0.78:
        return "🌗 하현달"
    return "🌘 그믐달"


def initialize_log_file():
    if not os.path.exists(LOG_FILE):
        pd.DataFrame(columns=["날짜", "모드", "시작시각", "종료시각", "소요시간(분)", "전진거리(해리)"]).to_csv(
            LOG_FILE, index=False, encoding="utf-8-sig"
        )


def save_session(start_time, end_time, mode):
    if start_time is None:
        return
    minutes = round(max(0, (end_time - start_time).total_seconds() / 60), 1)
    new_row = pd.DataFrame([{
        "날짜": start_time.strftime("%Y-%m-%d"),
        "모드": mode,
        "시작시각": start_time.strftime("%H:%M:%S"),
        "종료시각": end_time.strftime("%H:%M:%S"),
        "소요시간(분)": minutes,
        "전진거리(해리)": round(minutes * NAUTICAL_MILES_PER_MINUTE, 1),
    }])
    initialize_log_file()
    new_row.to_csv(LOG_FILE, mode="a", header=False, index=False, encoding="utf-8-sig")


# =========================================================
# 세션 상태
# =========================================================

defaults = {
    "timer_running": False,
    "start_time": None,
    "elapsed_seconds": 0,
    "selected_mode": "자유형",
    "selected_destination": "도쿄",
    "free_destination": None,
    "current_session_saved": False,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
<style>
.stApp { background-color:#07111f; color:#f4efe2; }
.block-container { max-width:1100px; padding-top:3rem; padding-bottom:4rem; }
section[data-testid="stSidebar"] { background-color:#091827; border-right:1px solid #b99a55; }
.main-title { color:#d8b66a; font-size:3.2rem; font-weight:700; letter-spacing:.06em; }
.subtitle { color:#9daaba; margin-bottom:30px; }
.info-card { background-color:#0d1b2a; border:1px solid #33485e; border-radius:15px; padding:20px; margin-bottom:15px; }
.card-title { color:#9daaba; font-size:.8rem; letter-spacing:.1em; margin-bottom:8px; }
.card-value { color:#f1d58b; font-size:1.4rem; font-weight:700; }
.section-title { color:#d8b66a; font-size:1.3rem; font-weight:700; margin-top:30px; margin-bottom:15px; }
</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# 사이드바
# =========================================================

with st.sidebar:
    st.markdown(
        """
        <div style="color:#d8b66a;font-size:1.35rem;font-weight:700;margin-bottom:10px;">
            ⚓ CELESTIAL LOGBOOK
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div style="color:#9daaba;line-height:1.6;margin-bottom:20px;">
            공부한 시간을 항해 거리로 바꾸어<br>나만의 항해일지를 만들어보세요.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("### ⚓ 항해 모드")

    modes = ["자유형", "지정 항로", "뽀모도로"]
    mode = st.radio(
        "공부 방식을 선택하세요.",
        modes,
        index=modes.index(st.session_state.selected_mode),
        label_visibility="collapsed",
    )
    st.session_state.selected_mode = mode

    if mode == "지정 항로":
        destination_options = list(DESTINATIONS.keys())
        destination = st.selectbox(
            "목적지",
            destination_options,
            index=destination_options.index(st.session_state.selected_destination),
        )
        st.session_state.selected_destination = destination
        st.caption(f"부산 → {destination} 약 {get_destination_distance(destination):,.0f} NM")

    st.divider()
    today = get_kst_now().date()
    st.markdown("### 오늘의 하늘")
    st.markdown(
        f"""
        <div style="color:#f4efe2;line-height:1.8;">
        📅 {today.strftime('%Y년 %m월 %d일')}<br>
        ✦ {CONSTELLATIONS[today.month]}<br>
        {get_moon_phase(today)}
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 제목
# =========================================================

st.markdown('<div class="main-title">CELESTIAL LOGBOOK</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">공부를 항해로 바꾸는 나만의 항해일지</div>', unsafe_allow_html=True)


# =========================================================
# 오늘 누적 항해 시간
# =========================================================

initialize_log_file()
try:
    log_df = pd.read_csv(LOG_FILE, encoding="utf-8-sig")
    today_text = get_kst_now().strftime("%Y-%m-%d")
    today_minutes = pd.to_numeric(
        log_df.loc[log_df["날짜"].astype(str) == today_text, "소요시간(분)"],
        errors="coerce",
    ).fillna(0).sum() if len(log_df) else 0
except Exception:
    today_minutes = 0


# =========================================================
# 상단 정보
# =========================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f'<div class="info-card"><div class="card-title">CURRENT MODE</div><div class="card-value">{mode}</div></div>',
        unsafe_allow_html=True,
    )

with col2:
    if mode == "지정 항로":
        destination_text = st.session_state.selected_destination
    elif mode == "뽀모도로":
        destination_text = "25분 항해"
    else:
        destination_text = "자유 항해"
    st.markdown(
        f'<div class="info-card"><div class="card-title">DESTINATION</div><div class="card-value">{destination_text}</div></div>',
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f'<div class="info-card"><div class="card-title">오늘 누적 항해 시간</div><div class="card-value">{today_minutes:.1f}분</div></div>',
        unsafe_allow_html=True,
    )

with col4:
    voyage_text = "25 MIN" if mode == "뽀모도로" else "FREE"
    st.markdown(
        f'<div class="info-card"><div class="card-title">VOYAGE</div><div class="card-value">{voyage_text}</div></div>',
        unsafe_allow_html=True,
    )


# =========================================================
# 경과 시간
# =========================================================

def get_elapsed_seconds():
    if not st.session_state.timer_running:
        return st.session_state.elapsed_seconds
    if st.session_state.start_time is None:
        return st.session_state.elapsed_seconds
    current_seconds = int((get_kst_now() - st.session_state.start_time).total_seconds())
    return st.session_state.elapsed_seconds + max(0, current_seconds)


def format_time(seconds):
    seconds = max(0, int(seconds))
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


# =========================================================
# 타이머
# =========================================================

@st.fragment(run_every=1)
def show_timer():
    elapsed = get_elapsed_seconds()
    if st.session_state.selected_mode == "뽀모도로":
        timer_text = format_time(max(0, 25 * 60 - elapsed))
    else:
        timer_text = format_time(elapsed)

    st.markdown(
        f"""
        <div style="background:#081522;border:1px solid #8e743d;border-radius:18px;padding:40px 20px;margin:25px 0 15px;text-align:center;">
            <div style="color:#9daaba;font-size:14px;letter-spacing:3px;margin-bottom:12px;">CURRENT VOYAGE</div>
            <div style="color:#f1d58b;font-size:72px;font-weight:700;line-height:1.1;font-family:monospace;">{timer_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

show_timer()


# =========================================================
# 버튼
# =========================================================

button1, button2, button3 = st.columns(3)

with button1:
    start_clicked = st.button(
        "⚓ 출항",
        key="start_timer_button",
        use_container_width=True,
        disabled=st.session_state.timer_running,
    )

with button2:
    stop_clicked = st.button(
        "⏸ 정박",
        key="stop_timer_button",
        use_container_width=True,
        disabled=not st.session_state.timer_running,
    )

with button3:
    reset_clicked = st.button(
        "↻ 초기화",
        key="reset_timer_button",
        use_container_width=True,
    )


# =========================================================
# 출항
# =========================================================

if start_clicked:
    # 자유형은 한 번 출항할 때 목적지를 하나 정하고 끝까지 유지
    if mode == "자유형" and st.session_state.free_destination is None:
        st.session_state.free_destination = random.choice(list(DESTINATIONS.keys()))

    st.session_state.start_time = get_kst_now()
    st.session_state.timer_running = True
    st.session_state.current_session_saved = False
    st.rerun()


# =========================================================
# 정박
# =========================================================

if stop_clicked:
    now = get_kst_now()
    start = st.session_state.start_time

    if start is not None:
        segment_seconds = max(0, int((now - start).total_seconds()))
        st.session_state.elapsed_seconds += segment_seconds
        save_session(start, now, st.session_state.selected_mode)

    st.session_state.start_time = None
    st.session_state.timer_running = False
    st.session_state.current_session_saved = True
    st.rerun()


# =========================================================
# 초기화
# =========================================================

if reset_clicked:
    st.session_state.timer_running = False
    st.session_state.start_time = None
    st.session_state.elapsed_seconds = 0
    st.session_state.free_destination = None
    st.session_state.current_session_saved = False
    st.rerun()


# =========================================================
# 상태 표시
# =========================================================

if st.session_state.timer_running:
    st.info("⚓ 항해 중입니다.")
elif st.session_state.elapsed_seconds > 0:
    st.success("⏸ 정박 중입니다. 다시 출항하면 이어서 진행합니다.")
else:
    st.caption("출항 버튼을 누르면 항해가 시작됩니다.")


# =========================================================
# 대권항로 계산
# =========================================================

def great_circle_point(lat1, lon1, lat2, lon2, fraction):
    fraction = max(0.0, min(1.0, fraction))
    p1, l1 = math.radians(lat1), math.radians(lon1)
    p2, l2 = math.radians(lat2), math.radians(lon2)

    x1, y1, z1 = math.cos(p1) * math.cos(l1), math.cos(p1) * math.sin(l1), math.sin(p1)
    x2, y2, z2 = math.cos(p2) * math.cos(l2), math.cos(p2) * math.sin(l2), math.sin(p2)
    dot = max(-1.0, min(1.0, x1 * x2 + y1 * y2 + z1 * z2))
    omega = math.acos(dot)

    if omega < 1e-10:
        return lat1, lon1

    sin_omega = math.sin(omega)
    a = math.sin((1 - fraction) * omega) / sin_omega
    b = math.sin(fraction * omega) / sin_omega
    x = a * x1 + b * x2
    y = a * y1 + b * y2
    z = a * z1 + b * z2

    return math.degrees(math.atan2(z, math.sqrt(x * x + y * y))), math.degrees(math.atan2(y, x))


def get_voyage_destination():
    if mode == "지정 항로":
        name = st.session_state.selected_destination
        return name, DESTINATIONS[name]

    if mode == "자유형":
        name = st.session_state.free_destination or "도쿄"
        return name, DESTINATIONS[name]

    return "속초", {"country": "대한민국", "lat": POMODORO_DESTINATION["lat"], "lon": POMODORO_DESTINATION["lon"]}


def get_current_voyage():
    destination_name, destination_info = get_voyage_destination()
    total_distance = haversine_nm(BUSAN_LAT, BUSAN_LON, destination_info["lat"], destination_info["lon"])
    elapsed = get_elapsed_seconds()
    distance = min(elapsed * NAUTICAL_MILES_PER_MINUTE / 60, total_distance)
    progress = distance / total_distance if total_distance else 0
    current_lat, current_lon = great_circle_point(
        BUSAN_LAT, BUSAN_LON,
        destination_info["lat"], destination_info["lon"],
        progress,
    )
    return destination_name, destination_info, total_distance, elapsed, distance, progress, current_lat, current_lon


def create_voyage_map():
    destination_name, destination_info, total_distance, elapsed, distance, progress, current_lat, current_lon = get_current_voyage()

    point_count = max(2, min(100, int(progress * 100) + 2))
    track_lat = []
    track_lon = []

    for i in range(point_count):
        fraction = progress * i / (point_count - 1)
        lat, lon = great_circle_point(
            BUSAN_LAT, BUSAN_LON,
            destination_info["lat"], destination_info["lon"],
            fraction,
        )
        track_lat.append(lat)
        track_lon.append(lon)

    fig = go.Figure()

    # 전체 예정 항로
    route_lat = []
    route_lon = []
    route_points = 80
    for i in range(route_points):
        fraction = i / (route_points - 1)
        lat, lon = great_circle_point(
            BUSAN_LAT, BUSAN_LON,
            destination_info["lat"], destination_info["lon"],
            fraction,
        )
        route_lat.append(lat)
        route_lon.append(lon)

    fig.add_trace(go.Scattergeo(
        lat=route_lat,
        lon=route_lon,
        mode="lines",
        line=dict(color="#31485d", width=1, dash="dot"),
        name="예정 항로",
    ))

    # 지금까지 이동한 항적
    fig.add_trace(go.Scattergeo(
        lat=track_lat,
        lon=track_lon,
        mode="lines",
        line=dict(color="#d8b66a", width=4),
        name="현재 항적",
    ))

    # 부산 출항지
    fig.add_trace(go.Scattergeo(
        lat=[BUSAN_LAT],
        lon=[BUSAN_LON],
        mode="markers+text",
        marker=dict(size=9, color="#f1d58b"),
        text=["부산"],
        textposition="bottom center",
        name="출항지",
    ))

    # 목적지
    fig.add_trace(go.Scattergeo(
        lat=[destination_info["lat"]],
        lon=[destination_info["lon"]],
        mode="markers+text",
        marker=dict(size=12, symbol="star", color="#d8b66a"),
        text=[destination_name],
        textposition="top center",
        name="목적지",
    ))

    # 현재 선박
    fig.add_trace(go.Scattergeo(
        lat=[current_lat],
        lon=[current_lon],
        mode="markers+text",
        marker=dict(size=14, symbol="triangle-up", color="#ffffff"),
        text=["⚓"],
        textposition="middle center",
        name="현재 선박",
    ))

    fig.update_layout(
        height=520,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#07111f",
        plot_bgcolor="#07111f",
        font=dict(color="#f4efe2"),
        geo=dict(
            showland=True,
            landcolor="#122235",
            showocean=True,
            oceancolor="#06101d",
            showlakes=True,
            lakecolor="#06101d",
            showcoastlines=True,
            coastlinecolor="#52667a",
            showframe=False,
            projection_type="natural earth",
        ),
        legend=dict(bgcolor="#081522", font=dict(color="#f4efe2")),
    )

    return fig


# =========================================================
# 지도 + 현재 항해 정보
# =========================================================

@st.fragment(run_every=1)
def show_voyage_map():
    destination_name, destination_info, total_distance, elapsed, distance, progress, current_lat, current_lon = get_current_voyage()

    st.markdown('<div class="section-title">🗺️ CURRENT VOYAGE</div>', unsafe_allow_html=True)
    st.plotly_chart(
        create_voyage_map(),
        use_container_width=True,
        config={"displayModeBar": False},
        key="celestial_voyage_map",
    )

    info1, info2, info3, info4 = st.columns(4)

    with info1:
        st.metric("현재 위치", f"{current_lat:.2f}°, {current_lon:.2f}°")
    with info2:
        st.metric("항해 거리", f"{distance:,.1f} NM")
    with info3:
        st.metric("남은 거리", f"{max(0, total_distance - distance):,.1f} NM")
    with info4:
        st.metric("진행률", f"{progress * 100:.1f}%")

    status = "UNDERWAY · 항해 중" if st.session_state.timer_running else "ANCHORED · 정박"
    st.caption(f"상태: {status}  |  목적지: {destination_name}")

show_voyage_map()


# =========================================================
# 지정 항로 진행도
# =========================================================

if mode == "지정 항로":
    initialize_log_file()

    try:
        log_df = pd.read_csv(LOG_FILE, encoding="utf-8-sig")
        total_distance = pd.to_numeric(
            log_df["전진거리(해리)"], errors="coerce"
        ).fillna(0).sum() if len(log_df) else 0
    except Exception:
        total_distance = 0

    destination_distance = get_destination_distance(st.session_state.selected_destination)
    progress = min(total_distance / destination_distance, 1.0) if destination_distance else 0

    st.markdown('<div class="section-title">🧭 항로 진행도</div>', unsafe_allow_html=True)
    st.progress(progress)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("현재까지 전진", f"{total_distance:,.1f} NM")
    with col2:
        st.metric("목적지까지", f"{destination_distance:,.0f} NM")


# =========================================================
# 뽀모도로 안내
# =========================================================

if mode == "뽀모도로":
    st.markdown('<div class="section-title">🍅 뽀모도로 항해</div>', unsafe_allow_html=True)
    route = " → ".join(POMODORO_ROUTE)
    st.markdown(
        f"""
        <div class="info-card">
            <div class="card-title">CURRENT ROUTE</div>
            <div style="color:#f4efe2;font-size:1.15rem;margin-bottom:10px;">{route}</div>
            <div style="color:#9daaba;line-height:1.7;">25분 집중하면 하나의 항해 기록이 저장됩니다.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 안내
# =========================================================

st.markdown("---")
st.markdown('<div class="section-title">✦ 항해 안내</div>', unsafe_allow_html=True)

if mode == "자유형":
    st.write("자유롭게 공부하고 정박하면 해당 시간이 항해일지에 기록됩니다.")
elif mode == "지정 항로":
    st.write(f"부산에서 {st.session_state.selected_destination}까지의 가상 항로를 따라 공부합니다.")
else:
    st.write("25분 동안 집중하면 자동으로 항해가 종료되고 기록됩니다.")
import streamlit as st
import pandas as pd
import math
import os
import random
from datetime import datetime, timedelta, timezone
import plotly.graph_objects as go

st.set_page_config(page_title="Celestial Logbook", page_icon="⚓", layout="wide", initial_sidebar_state="collapsed")

KST = timezone(timedelta(hours=9))
LOG_FILE = "log.csv"
NAUTICAL_MILES_PER_MINUTE = 1.0
BUSAN_LAT, BUSAN_LON = 35.1796, 129.0756

DESTINATIONS = {
    "도쿄": {"country": "일본", "lat": 35.6762, "lon": 139.6503},
    "상하이": {"country": "중국", "lat": 31.2304, "lon": 121.4737},
    "싱가포르": {"country": "싱가포르", "lat": 1.3521, "lon": 103.8198},
    "시드니": {"country": "호주", "lat": -33.8688, "lon": 151.2093},
    "호놀룰루": {"country": "미국", "lat": 21.3069, "lon": -157.8583},
    "밴쿠버": {"country": "캐나다", "lat": 49.2827, "lon": -123.1207},
    "로스앤젤레스": {"country": "미국", "lat": 34.0522, "lon": -118.2437},
    "런던": {"country": "영국", "lat": 51.5074, "lon": -0.1278},
    "파리": {"country": "프랑스", "lat": 48.8566, "lon": 2.3522},
    "뉴욕": {"country": "미국", "lat": 40.7128, "lon": -74.0060},
}

POMODORO_ROUTE = ["부산", "울산", "포항", "동해", "속초"]
POMODORO_DESTINATION = {"lat": 38.2070, "lon": 128.5918}

CONSTELLATIONS = {
    1: "오리온자리", 2: "큰개자리", 3: "쌍둥이자리", 4: "사자자리",
    5: "처녀자리", 6: "목동자리", 7: "전갈자리", 8: "궁수자리",
    9: "백조자리", 10: "페가수스자리", 11: "황소자리", 12: "마차부자리"
}


def get_kst_now():
    return datetime.now(KST)


def haversine_nm(lat1, lon1, lat2, lon2):
    """두 위치 사이의 거리를 해리로 계산"""
    earth_radius_km = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_km * c / 1.852


def get_destination_distance(destination):
    info = DESTINATIONS[destination]
    return haversine_nm(BUSAN_LAT, BUSAN_LON, info["lat"], info["lon"])


def get_moon_phase(date_value):
    reference = datetime(2000, 1, 6)
    target = datetime(date_value.year, date_value.month, date_value.day)
    days = (target - reference).days
    phase = (days % 29.53058867) / 29.53058867
    if phase < 0.03:
        return "🌑 신월"
    if phase < 0.22:
        return "🌒 초승달"
    if phase < 0.28:
        return "🌓 상현달"
    if phase < 0.47:
        return "🌔 차오르는 달"
    if phase < 0.53:
        return "🌕 보름달"
    if phase < 0.72:
        return "🌖 기우는 달"
    if phase < 0.78:
        return "🌗 하현달"
    return "🌘 그믐달"


def initialize_log_file():
    if not os.path.exists(LOG_FILE):
        pd.DataFrame(columns=["날짜", "모드", "시작시각", "종료시각", "소요시간(분)", "전진거리(해리)"]).to_csv(
            LOG_FILE, index=False, encoding="utf-8-sig"
        )


def save_session(start_time, end_time, mode):
    if start_time is None:
        return
    minutes = round(max(0, (end_time - start_time).total_seconds() / 60), 1)
    new_row = pd.DataFrame([{
        "날짜": start_time.strftime("%Y-%m-%d"),
        "모드": mode,
        "시작시각": start_time.strftime("%H:%M:%S"),
        "종료시각": end_time.strftime("%H:%M:%S"),
        "소요시간(분)": minutes,
        "전진거리(해리)": round(minutes * NAUTICAL_MILES_PER_MINUTE, 1),
    }])
    initialize_log_file()
    new_row.to_csv(LOG_FILE, mode="a", header=False, index=False, encoding="utf-8-sig")


# =========================================================
# 세션 상태
# =========================================================

defaults = {
    "timer_running": False,
    "start_time": None,
    "elapsed_seconds": 0,
    "selected_mode": "자유형",
    "selected_destination": "도쿄",
    "free_destination": None,
    "current_session_saved": False,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
<style>
.stApp { background-color:#07111f; color:#f4efe2; }
.block-container { max-width:1100px; padding-top:3rem; padding-bottom:4rem; }
section[data-testid="stSidebar"] { background-color:#091827; border-right:1px solid #b99a55; }
.main-title { color:#d8b66a; font-size:3.2rem; font-weight:700; letter-spacing:.06em; }
.subtitle { color:#9daaba; margin-bottom:30px; }
.info-card { background-color:#0d1b2a; border:1px solid #33485e; border-radius:15px; padding:20px; margin-bottom:15px; }
.card-title { color:#9daaba; font-size:.8rem; letter-spacing:.1em; margin-bottom:8px; }
.card-value { color:#f1d58b; font-size:1.4rem; font-weight:700; }
.section-title { color:#d8b66a; font-size:1.3rem; font-weight:700; margin-top:30px; margin-bottom:15px; }
</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# 사이드바
# =========================================================

with st.sidebar:
    st.markdown(
        """
        <div style="color:#d8b66a;font-size:1.35rem;font-weight:700;margin-bottom:10px;">
            ⚓ CELESTIAL LOGBOOK
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div style="color:#9daaba;line-height:1.6;margin-bottom:20px;">
            공부한 시간을 항해 거리로 바꾸어<br>나만의 항해일지를 만들어보세요.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("### ⚓ 항해 모드")

    modes = ["자유형", "지정 항로", "뽀모도로"]
    mode = st.radio(
        "공부 방식을 선택하세요.",
        modes,
        index=modes.index(st.session_state.selected_mode),
        label_visibility="collapsed",
    )
    st.session_state.selected_mode = mode

    if mode == "지정 항로":
        destination_options = list(DESTINATIONS.keys())
        destination = st.selectbox(
            "목적지",
            destination_options,
            index=destination_options.index(st.session_state.selected_destination),
        )
        st.session_state.selected_destination = destination
        st.caption(f"부산 → {destination} 약 {get_destination_distance(destination):,.0f} NM")

    st.divider()
    today = get_kst_now().date()
    st.markdown("### 오늘의 하늘")
    st.markdown(
        f"""
        <div style="color:#f4efe2;line-height:1.8;">
        📅 {today.strftime('%Y년 %m월 %d일')}<br>
        ✦ {CONSTELLATIONS[today.month]}<br>
        {get_moon_phase(today)}
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 제목
# =========================================================

st.markdown('<div class="main-title">CELESTIAL LOGBOOK</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">공부를 항해로 바꾸는 나만의 항해일지</div>', unsafe_allow_html=True)


# =========================================================
# 오늘 누적 항해 시간
# =========================================================

initialize_log_file()
try:
    log_df = pd.read_csv(LOG_FILE, encoding="utf-8-sig")
    today_text = get_kst_now().strftime("%Y-%m-%d")
    today_minutes = pd.to_numeric(
        log_df.loc[log_df["날짜"].astype(str) == today_text, "소요시간(분)"],
        errors="coerce",
    ).fillna(0).sum() if len(log_df) else 0
except Exception:
    today_minutes = 0


# =========================================================
# 상단 정보
# =========================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f'<div class="info-card"><div class="card-title">CURRENT MODE</div><div class="card-value">{mode}</div></div>',
        unsafe_allow_html=True,
    )

with col2:
    if mode == "지정 항로":
        destination_text = st.session_state.selected_destination
    elif mode == "뽀모도로":
        destination_text = "25분 항해"
    else:
        destination_text = "자유 항해"
    st.markdown(
        f'<div class="info-card"><div class="card-title">DESTINATION</div><div class="card-value">{destination_text}</div></div>',
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f'<div class="info-card"><div class="card-title">오늘 누적 항해 시간</div><div class="card-value">{today_minutes:.1f}분</div></div>',
        unsafe_allow_html=True,
    )

with col4:
    voyage_text = "25 MIN" if mode == "뽀모도로" else "FREE"
    st.markdown(
        f'<div class="info-card"><div class="card-title">VOYAGE</div><div class="card-value">{voyage_text}</div></div>',
        unsafe_allow_html=True,
    )


# =========================================================
# 경과 시간
# =========================================================

def get_elapsed_seconds():
    if not st.session_state.timer_running:
        return st.session_state.elapsed_seconds
    if st.session_state.start_time is None:
        return st.session_state.elapsed_seconds
    current_seconds = int((get_kst_now() - st.session_state.start_time).total_seconds())
    return st.session_state.elapsed_seconds + max(0, current_seconds)


def format_time(seconds):
    seconds = max(0, int(seconds))
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


# =========================================================
# 타이머
# =========================================================

@st.fragment(run_every=1)
def show_timer():
    elapsed = get_elapsed_seconds()
    if st.session_state.selected_mode == "뽀모도로":
        timer_text = format_time(max(0, 25 * 60 - elapsed))
    else:
        timer_text = format_time(elapsed)

    st.markdown(
        f"""
        <div style="background:#081522;border:1px solid #8e743d;border-radius:18px;padding:40px 20px;margin:25px 0 15px;text-align:center;">
            <div style="color:#9daaba;font-size:14px;letter-spacing:3px;margin-bottom:12px;">CURRENT VOYAGE</div>
            <div style="color:#f1d58b;font-size:72px;font-weight:700;line-height:1.1;font-family:monospace;">{timer_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

show_timer()


# =========================================================
# 버튼
# =========================================================

button1, button2, button3 = st.columns(3)

with button1:
    start_clicked = st.button(
        "⚓ 출항",
        key="start_timer_button",
        use_container_width=True,
        disabled=st.session_state.timer_running,
    )

with button2:
    stop_clicked = st.button(
        "⏸ 정박",
        key="stop_timer_button",
        use_container_width=True,
        disabled=not st.session_state.timer_running,
    )

with button3:
    reset_clicked = st.button(
        "↻ 초기화",
        key="reset_timer_button",
        use_container_width=True,
    )


# =========================================================
# 출항
# =========================================================

if start_clicked:
    # 자유형은 한 번 출항할 때 목적지를 하나 정하고 끝까지 유지
    if mode == "자유형" and st.session_state.free_destination is None:
        st.session_state.free_destination = random.choice(list(DESTINATIONS.keys()))

    st.session_state.start_time = get_kst_now()
    st.session_state.timer_running = True
    st.session_state.current_session_saved = False
    st.rerun()


# =========================================================
# 정박
# =========================================================

if stop_clicked:
    now = get_kst_now()
    start = st.session_state.start_time

    if start is not None:
        segment_seconds = max(0, int((now - start).total_seconds()))
        st.session_state.elapsed_seconds += segment_seconds
        save_session(start, now, st.session_state.selected_mode)

    st.session_state.start_time = None
    st.session_state.timer_running = False
    st.session_state.current_session_saved = True
    st.rerun()


# =========================================================
# 초기화
# =========================================================

if reset_clicked:
    st.session_state.timer_running = False
    st.session_state.start_time = None
    st.session_state.elapsed_seconds = 0
    st.session_state.free_destination = None
    st.session_state.current_session_saved = False
    st.rerun()


# =========================================================
# 상태 표시
# =========================================================

if st.session_state.timer_running:
    st.info("⚓ 항해 중입니다.")
elif st.session_state.elapsed_seconds > 0:
    st.success("⏸ 정박 중입니다. 다시 출항하면 이어서 진행합니다.")
else:
    st.caption("출항 버튼을 누르면 항해가 시작됩니다.")


# =========================================================
# 대권항로 계산
# =========================================================

def great_circle_point(lat1, lon1, lat2, lon2, fraction):
    fraction = max(0.0, min(1.0, fraction))
    p1, l1 = math.radians(lat1), math.radians(lon1)
    p2, l2 = math.radians(lat2), math.radians(lon2)

    x1, y1, z1 = math.cos(p1) * math.cos(l1), math.cos(p1) * math.sin(l1), math.sin(p1)
    x2, y2, z2 = math.cos(p2) * math.cos(l2), math.cos(p2) * math.sin(l2), math.sin(p2)
    dot = max(-1.0, min(1.0, x1 * x2 + y1 * y2 + z1 * z2))
    omega = math.acos(dot)

    if omega < 1e-10:
        return lat1, lon1

    sin_omega = math.sin(omega)
    a = math.sin((1 - fraction) * omega) / sin_omega
    b = math.sin(fraction * omega) / sin_omega
    x = a * x1 + b * x2
    y = a * y1 + b * y2
    z = a * z1 + b * z2

    return math.degrees(math.atan2(z, math.sqrt(x * x + y * y))), math.degrees(math.atan2(y, x))


def get_voyage_destination():
    if mode == "지정 항로":
        name = st.session_state.selected_destination
        return name, DESTINATIONS[name]

    if mode == "자유형":
        name = st.session_state.free_destination or "도쿄"
        return name, DESTINATIONS[name]

    return "속초", {"country": "대한민국", "lat": POMODORO_DESTINATION["lat"], "lon": POMODORO_DESTINATION["lon"]}


def get_current_voyage():
    destination_name, destination_info = get_voyage_destination()
    total_distance = haversine_nm(BUSAN_LAT, BUSAN_LON, destination_info["lat"], destination_info["lon"])
    elapsed = get_elapsed_seconds()
    distance = min(elapsed * NAUTICAL_MILES_PER_MINUTE / 60, total_distance)
    progress = distance / total_distance if total_distance else 0
    current_lat, current_lon = great_circle_point(
        BUSAN_LAT, BUSAN_LON,
        destination_info["lat"], destination_info["lon"],
        progress,
    )
    return destination_name, destination_info, total_distance, elapsed, distance, progress, current_lat, current_lon


def create_voyage_map():
    destination_name, destination_info, total_distance, elapsed, distance, progress, current_lat, current_lon = get_current_voyage()

    point_count = max(2, min(100, int(progress * 100) + 2))
    track_lat = []
    track_lon = []

    for i in range(point_count):
        fraction = progress * i / (point_count - 1)
        lat, lon = great_circle_point(
            BUSAN_LAT, BUSAN_LON,
            destination_info["lat"], destination_info["lon"],
            fraction,
        )
        track_lat.append(lat)
        track_lon.append(lon)

    fig = go.Figure()

    # 전체 예정 항로
    route_lat = []
    route_lon = []
    route_points = 80
    for i in range(route_points):
        fraction = i / (route_points - 1)
        lat, lon = great_circle_point(
            BUSAN_LAT, BUSAN_LON,
            destination_info["lat"], destination_info["lon"],
            fraction,
        )
        route_lat.append(lat)
        route_lon.append(lon)

    fig.add_trace(go.Scattergeo(
        lat=route_lat,
        lon=route_lon,
        mode="lines",
        line=dict(color="#31485d", width=1, dash="dot"),
        name="예정 항로",
    ))

    # 지금까지 이동한 항적
    fig.add_trace(go.Scattergeo(
        lat=track_lat,
        lon=track_lon,
        mode="lines",
        line=dict(color="#d8b66a", width=4),
        name="현재 항적",
    ))

    # 부산 출항지
    fig.add_trace(go.Scattergeo(
        lat=[BUSAN_LAT],
        lon=[BUSAN_LON],
        mode="markers+text",
        marker=dict(size=9, color="#f1d58b"),
        text=["부산"],
        textposition="bottom center",
        name="출항지",
    ))

    # 목적지
    fig.add_trace(go.Scattergeo(
        lat=[destination_info["lat"]],
        lon=[destination_info["lon"]],
        mode="markers+text",
        marker=dict(size=12, symbol="star", color="#d8b66a"),
        text=[destination_name],
        textposition="top center",
        name="목적지",
    ))

    # 현재 선박
    fig.add_trace(go.Scattergeo(
        lat=[current_lat],
        lon=[current_lon],
        mode="markers+text",
        marker=dict(size=14, symbol="triangle-up", color="#ffffff"),
        text=["⚓"],
        textposition="middle center",
        name="현재 선박",
    ))

    fig.update_layout(
        height=520,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#07111f",
        plot_bgcolor="#07111f",
        font=dict(color="#f4efe2"),
        geo=dict(
            showland=True,
            landcolor="#122235",
            showocean=True,
            oceancolor="#06101d",
            showlakes=True,
            lakecolor="#06101d",
            showcoastlines=True,
            coastlinecolor="#52667a",
            showframe=False,
            projection_type="natural earth",
        ),
        legend=dict(bgcolor="#081522", font=dict(color="#f4efe2")),
    )

    return fig


# =========================================================
# 지도 + 현재 항해 정보
# =========================================================

@st.fragment(run_every=1)
def show_voyage_map():
    destination_name, destination_info, total_distance, elapsed, distance, progress, current_lat, current_lon = get_current_voyage()

    st.markdown('<div class="section-title">🗺️ CURRENT VOYAGE</div>', unsafe_allow_html=True)
    st.plotly_chart(
        create_voyage_map(),
        use_container_width=True,
        config={"displayModeBar": False},
        key="celestial_voyage_map",
    )

    info1, info2, info3, info4 = st.columns(4)

    with info1:
        st.metric("현재 위치", f"{current_lat:.2f}°, {current_lon:.2f}°")
    with info2:
        st.metric("항해 거리", f"{distance:,.1f} NM")
    with info3:
        st.metric("남은 거리", f"{max(0, total_distance - distance):,.1f} NM")
    with info4:
        st.metric("진행률", f"{progress * 100:.1f}%")

    status = "UNDERWAY · 항해 중" if st.session_state.timer_running else "ANCHORED · 정박"
    st.caption(f"상태: {status}  |  목적지: {destination_name}")

show_voyage_map()


# =========================================================
# 지정 항로 진행도
# =========================================================

if mode == "지정 항로":
    initialize_log_file()

    try:
        log_df = pd.read_csv(LOG_FILE, encoding="utf-8-sig")
        total_distance = pd.to_numeric(
            log_df["전진거리(해리)"], errors="coerce"
        ).fillna(0).sum() if len(log_df) else 0
    except Exception:
        total_distance = 0

    destination_distance = get_destination_distance(st.session_state.selected_destination)
    progress = min(total_distance / destination_distance, 1.0) if destination_distance else 0

    st.markdown('<div class="section-title">🧭 항로 진행도</div>', unsafe_allow_html=True)
    st.progress(progress)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("현재까지 전진", f"{total_distance:,.1f} NM")
    with col2:
        st.metric("목적지까지", f"{destination_distance:,.0f} NM")


# =========================================================
# 뽀모도로 안내
# =========================================================

if mode == "뽀모도로":
    st.markdown('<div class="section-title">🍅 뽀모도로 항해</div>', unsafe_allow_html=True)
    route = " → ".join(POMODORO_ROUTE)
    st.markdown(
        f"""
        <div class="info-card">
            <div class="card-title">CURRENT ROUTE</div>
            <div style="color:#f4efe2;font-size:1.15rem;margin-bottom:10px;">{route}</div>
            <div style="color:#9daaba;line-height:1.7;">25분 집중하면 하나의 항해 기록이 저장됩니다.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 안내
# =========================================================

st.markdown("---")
st.markdown('<div class="section-title">✦ 항해 안내</div>', unsafe_allow_html=True)

if mode == "자유형":
    st.write("자유롭게 공부하고 정박하면 해당 시간이 항해일지에 기록됩니다.")
elif mode == "지정 항로":
    st.write(f"부산에서 {st.session_state.selected_destination}까지의 가상 항로를 따라 공부합니다.")
else:
    st.write("25분 동안 집중하면 자동으로 항해가 종료되고 기록됩니다.")

