import streamlit as st
import pandas as pd
import math
import os
import random
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone


# =========================================================
# 페이지 기본 설정
# =========================================================

st.set_page_config(
    page_title="Celestial Logbook",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# =========================================================
# 한국 시간
# =========================================================

KST = timezone(timedelta(hours=9))


def get_kst_now():
    return datetime.now(KST)


# =========================================================
# 기본 설정
# =========================================================

LOG_FILE = "log.csv"

# 공부 1분 = 1해리
NAUTICAL_MILES_PER_MINUTE = 1.0

BUSAN_LAT = 35.1796
BUSAN_LON = 129.0756


# =========================================================
# 목적지
# =========================================================

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

POMODORO_DESTINATION = {
    "lat": 38.2070,
    "lon": 128.5918,
}

POMODORO_ROUTE = ["부산", "울산", "포항", "동해", "속초"]


# =========================================================
# 별자리
# =========================================================

CONSTELLATIONS = {
    1: "오리온자리",
    2: "큰개자리",
    3: "쌍둥이자리",
    4: "사자자리",
    5: "처녀자리",
    6: "목동자리",
    7: "전갈자리",
    8: "궁수자리",
    9: "백조자리",
    10: "페가수스자리",
    11: "황소자리",
    12: "마차부자리",
}


# =========================================================
# 거리 계산
# =========================================================

def haversine_nm(lat1, lon1, lat2, lon2):
    earth_radius_km = 6371.0

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    km = earth_radius_km * c

    return km / 1.852


def get_destination_distance(destination):
    if destination == "뽀모도로":
        return haversine_nm(
            BUSAN_LAT,
            BUSAN_LON,
            POMODORO_DESTINATION["lat"],
            POMODORO_DESTINATION["lon"],
        )

    info = DESTINATIONS[destination]

    return haversine_nm(
        BUSAN_LAT,
        BUSAN_LON,
        info["lat"],
        info["lon"],
    )


# =========================================================
# 달의 위상
# =========================================================

def get_moon_phase(date_value):
    reference = datetime(2000, 1, 6)
    target = datetime(
        date_value.year,
        date_value.month,
        date_value.day,
    )

    days = (target - reference).days
    synodic_month = 29.53058867
    phase = (days % synodic_month) / synodic_month

    if phase < 0.03:
        return "🌑 신월"
    elif phase < 0.22:
        return "🌒 초승달"
    elif phase < 0.28:
        return "🌓 상현달"
    elif phase < 0.47:
        return "🌔 차오르는 달"
    elif phase < 0.53:
        return "🌕 보름달"
    elif phase < 0.72:
        return "🌖 기우는 달"
    elif phase < 0.78:
        return "🌗 하현달"
    else:
        return "🌘 그믐달"


# =========================================================
# log.csv
# =========================================================

def initialize_log_file():
    if not os.path.exists(LOG_FILE):
        empty_df = pd.DataFrame(
            columns=[
                "날짜",
                "모드",
                "시작시각",
                "종료시각",
                "소요시간(분)",
                "전진거리(해리)",
            ]
        )

        empty_df.to_csv(
            LOG_FILE,
            index=False,
            encoding="utf-8-sig",
        )


def save_session(start_time, end_time, mode):
    if start_time is None:
        return

    seconds = max(
        0,
        (end_time - start_time).total_seconds(),
    )

    minutes = round(seconds / 60, 1)
    distance = round(
        minutes * NAUTICAL_MILES_PER_MINUTE,
        1,
    )

    new_row = pd.DataFrame(
        [{
            "날짜": start_time.strftime("%Y-%m-%d"),
            "모드": mode,
            "시작시각": start_time.strftime("%H:%M:%S"),
            "종료시각": end_time.strftime("%H:%M:%S"),
            "소요시간(분)": minutes,
            "전진거리(해리)": distance,
        }]
    )

    initialize_log_file()

    new_row.to_csv(
        LOG_FILE,
        mode="a",
        header=False,
        index=False,
        encoding="utf-8-sig",
    )


def get_today_total_minutes():
    initialize_log_file()

    try:
        df = pd.read_csv(
            LOG_FILE,
            encoding="utf-8-sig",
        )

        if df.empty:
            return 0.0

        today = get_kst_now().strftime("%Y-%m-%d")
        today_df = df[df["날짜"].astype(str) == today]

        return pd.to_numeric(
            today_df["소요시간(분)"],
            errors="coerce",
        ).fillna(0).sum()

    except Exception:
        return 0.0


# =========================================================
# 세션 상태
# =========================================================

if "timer_running" not in st.session_state:
    st.session_state.timer_running = False

if "start_time" not in st.session_state:
    st.session_state.start_time = None

if "elapsed_seconds" not in st.session_state:
    st.session_state.elapsed_seconds = 0

if "selected_mode" not in st.session_state:
    st.session_state.selected_mode = "자유항해"

if "selected_destination" not in st.session_state:
    st.session_state.selected_destination = "도쿄"

if "free_destination" not in st.session_state:
    st.session_state.free_destination = None

if "voyage_saved" not in st.session_state:
    st.session_state.voyage_saved = False


# =========================================================
# 현재 경과 시간
# =========================================================

def get_elapsed_seconds():
    if not st.session_state.timer_running:
        return st.session_state.elapsed_seconds

    if st.session_state.start_time is None:
        return st.session_state.elapsed_seconds

    now = get_kst_now()

    current = int(
        (now - st.session_state.start_time).total_seconds()
    )

    return st.session_state.elapsed_seconds + max(0, current)


def format_time(seconds):
    seconds = max(0, int(seconds))

    minutes = seconds // 60
    seconds = seconds % 60

    return f"{minutes:02d}:{seconds:02d}"


# =========================================================
# 현재 목적지
# =========================================================

def get_current_destination():
    mode = st.session_state.selected_mode

    if mode == "지정 항로":
        return st.session_state.selected_destination

    if mode == "뽀모도로":
        return "뽀모도로"

    if st.session_state.free_destination is not None:
        return st.session_state.free_destination

    return "도쿄"


def get_destination_coordinates():
    destination = get_current_destination()

    if destination == "뽀모도로":
        return (
            POMODORO_DESTINATION["lat"],
            POMODORO_DESTINATION["lon"],
        )

    info = DESTINATIONS[destination]

    return info["lat"], info["lon"]


# =========================================================
# 대권항로상의 현재 위치
# =========================================================

def interpolate_great_circle(
    lat1,
    lon1,
    lat2,
    lon2,
    fraction,
):
    fraction = max(0.0, min(1.0, fraction))

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    x1 = math.cos(lat1_rad) * math.cos(lon1_rad)
    y1 = math.cos(lat1_rad) * math.sin(lon1_rad)
    z1 = math.sin(lat1_rad)

    x2 = math.cos(lat2_rad) * math.cos(lon2_rad)
    y2 = math.cos(lat2_rad) * math.sin(lon2_rad)
    z2 = math.sin(lat2_rad)

    dot = max(-1.0, min(1.0, x1 * x2 + y1 * y2 + z1 * z2))
    angle = math.acos(dot)

    if angle < 1e-10:
        return lat1, lon1

    sin_angle = math.sin(angle)

    a = math.sin((1 - fraction) * angle) / sin_angle
    b = math.sin(fraction * angle) / sin_angle

    x = a * x1 + b * x2
    y = a * y1 + b * y2
    z = a * z1 + b * z2

    lat = math.degrees(math.atan2(z, math.sqrt(x * x + y * y)))
    lon = math.degrees(math.atan2(y, x))

    return lat, lon


def get_voyage_status():
    elapsed = get_elapsed_seconds()

    destination_lat, destination_lon = get_destination_coordinates()

    total_distance = haversine_nm(
        BUSAN_LAT,
        BUSAN_LON,
        destination_lat,
        destination_lon,
    )

    traveled_distance = min(
        elapsed * NAUTICAL_MILES_PER_MINUTE / 60,
        total_distance,
    )

    progress = (
        traveled_distance / total_distance
        if total_distance > 0
        else 0
    )

    current_lat, current_lon = interpolate_great_circle(
        BUSAN_LAT,
        BUSAN_LON,
        destination_lat,
        destination_lon,
        progress,
    )

    remaining_distance = max(
        0,
        total_distance - traveled_distance,
    )

    return {
        "destination_lat": destination_lat,
        "destination_lon": destination_lon,
        "total_distance": total_distance,
        "traveled_distance": traveled_distance,
        "remaining_distance": remaining_distance,
        "progress": progress,
        "current_lat": current_lat,
        "current_lon": current_lon,
    }


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
<style>

.stApp {
    background-color: #07111f;
    color: #f4efe2;
}

.block-container {
    max-width: 1100px;
    padding-top: 2.5rem;
    padding-bottom: 4rem;
}

section[data-testid="stSidebar"] {
    background-color: #091827;
    border-right: 1px solid #b99a55;
}

.main-title {
    color: #d8b66a;
    font-size: 3.2rem;
    font-weight: 700;
    letter-spacing: 0.06em;
}

.subtitle {
    color: #9daaba;
    margin-bottom: 25px;
}

.info-card {
    background-color: #0d1b2a;
    border: 1px solid #33485e;
    border-radius: 15px;
    padding: 18px;
    margin-bottom: 15px;
}

.card-title {
    color: #9daaba;
    font-size: 0.8rem;
    letter-spacing: 0.1em;
    margin-bottom: 8px;
}

.card-value {
    color: #f1d58b;
    font-size: 1.35rem;
    font-weight: 700;
}

.timer-box {
    background-color: #081522;
    border: 1px solid #8e743d;
    border-radius: 18px;
    padding: 42px 20px;
    margin: 20px 0;
    text-align: center;
}

.timer-label {
    color: #9daaba;
    font-size: 0.9rem;
    letter-spacing: 0.18em;
    margin-bottom: 15px;
}

.timer-number {
    color: #f1d58b;
    font-size: 5rem;
    font-weight: 700;
    line-height: 1;
    font-variant-numeric: tabular-nums;
}

.section-title {
    color: #d8b66a;
    font-size: 1.3rem;
    font-weight: 700;
    margin-top: 28px;
    margin-bottom: 12px;
}

div[data-testid="stButton"] button {
    border-radius: 10px;
}

</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# 사이드바
# - 항해 모드는 여기서 선택하지 않음
# - 하늘 정보만 표시
# =========================================================

with st.sidebar:
    st.markdown(
        """
        <div style="
            color:#d8b66a;
            font-size:1.35rem;
            font-weight:700;
            margin-bottom:10px;
        ">
            CELESTIAL LOGBOOK
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="
            color:#9daaba;
            line-height:1.6;
            margin-bottom:20px;
        ">
        공부한 시간을 항해 거리로 바꾸어
        나만의 항해일지를 만들어보세요.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    today = get_kst_now().date()

    st.markdown("### 오늘의 하늘")

    st.markdown(
        f"""
        <div style="
            color:#f4efe2;
            line-height:1.9;
        ">
        📅 {today.strftime("%Y년 %m월 %d일")}<br>
        ✦ {CONSTELLATIONS[today.month]}<br>
        {get_moon_phase(today)}
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 제목
# =========================================================

st.markdown(
    '<div class="main-title">CELESTIAL LOGBOOK</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">공부를 항해로 바꾸는 나만의 항해일지</div>',
    unsafe_allow_html=True,
)


# =========================================================
# 메인 항해 모드 선택
# =========================================================

st.markdown("### 항해 모드")

mode1, mode2, mode3 = st.columns(3)

with mode1:
    free_clicked = st.button(
        "⚓ 자유항해",
        use_container_width=True,
        type=(
            "primary"
            if st.session_state.selected_mode == "자유항해"
            else "secondary"
        ),
    )

with mode2:
    route_clicked = st.button(
        "🧭 지정 항로",
        use_container_width=True,
        type=(
            "primary"
            if st.session_state.selected_mode == "지정 항로"
            else "secondary"
        ),
    )

with mode3:
    pomodoro_clicked = st.button(
        "🍅 뽀모도로",
        use_container_width=True,
        type=(
            "primary"
            if st.session_state.selected_mode == "뽀모도로"
            else "secondary"
        ),
    )


if free_clicked:
    if st.session_state.timer_running:
        st.warning("항해 중에는 항해 모드를 변경할 수 없습니다.")
    else:
        st.session_state.selected_mode = "자유항해"
        st.session_state.free_destination = None
        st.rerun()

if route_clicked:
    if st.session_state.timer_running:
        st.warning("항해 중에는 항해 모드를 변경할 수 없습니다.")
    else:
        st.session_state.selected_mode = "지정 항로"
        st.rerun()

if pomodoro_clicked:
    if st.session_state.timer_running:
        st.warning("항해 중에는 항해 모드를 변경할 수 없습니다.")
    else:
        st.session_state.selected_mode = "뽀모도로"
        st.session_state.free_destination = None
        st.rerun()


# =========================================================
# 지정 항로 목적지 선택
# =========================================================

if st.session_state.selected_mode == "지정 항로":
    destination = st.selectbox(
        "목적지",
        list(DESTINATIONS.keys()),
        index=list(DESTINATIONS.keys()).index(
            st.session_state.selected_destination
        ),
        disabled=st.session_state.timer_running,
    )

    if destination != st.session_state.selected_destination:
        st.session_state.selected_destination = destination

    distance = get_destination_distance(destination)

    st.caption(
        f"부산 → {destination} 약 {distance:,.0f} NM"
    )


# =========================================================
# 상단 정보
# =========================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        f"""
        <div class="info-card">
            <div class="card-title">TODAY'S TOTAL VOYAGE</div>
            <div class="card-value">
                {get_today_total_minutes():,.1f}분
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    if st.session_state.selected_mode == "지정 항로":
        destination_text = st.session_state.selected_destination
    elif st.session_state.selected_mode == "뽀모도로":
        destination_text = "속초"
    else:
        destination_text = "무작위 목적지"

    st.markdown(
        f"""
        <div class="info-card">
            <div class="card-title">DESTINATION</div>
            <div class="card-value">
                {destination_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    if st.session_state.timer_running:
        voyage_text = "UNDERWAY"
    elif st.session_state.elapsed_seconds > 0:
        voyage_text = "ANCHORED"
    else:
        voyage_text = "READY"

    st.markdown(
        f"""
        <div class="info-card">
            <div class="card-title">STATUS</div>
            <div class="card-value">
                {voyage_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 타이머 + 항해 지도
#
# JavaScript 없음.
# Streamlit + Plotly만 사용.
# =========================================================

@st.fragment(run_every=1)
def show_live_voyage():

    elapsed = get_elapsed_seconds()

    if st.session_state.selected_mode == "뽀모도로":
        remaining = max(0, 25 * 60 - elapsed)
        timer_text = format_time(remaining)
        timer_label = "POMODORO REMAINING"
    else:
        timer_text = format_time(elapsed)
        timer_label = "CURRENT VOYAGE"

    st.markdown(
        f"""
        <div class="timer-box">
            <div class="timer-label">{timer_label}</div>
            <div class="timer-number">{timer_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    voyage = get_voyage_status()

    # ---------------------------------------------
    # 현재 항해 정보
    # ---------------------------------------------

    info1, info2, info3, info4 = st.columns(4)

    with info1:
        st.metric(
            "현재 위치",
            f"{voyage['current_lat']:.2f}°, "
            f"{voyage['current_lon']:.2f}°",
        )

    with info2:
        st.metric(
            "전진 거리",
            f"{voyage['traveled_distance']:,.1f} NM",
        )

    with info3:
        st.metric(
            "남은 거리",
            f"{voyage['remaining_distance']:,.1f} NM",
        )

    with info4:
        st.metric(
            "진행률",
            f"{voyage['progress'] * 100:.1f}%",
        )

    # ---------------------------------------------
    # 지도
    # ---------------------------------------------

    destination_lat = voyage["destination_lat"]
    destination_lon = voyage["destination_lon"]

    current_lat = voyage["current_lat"]
    current_lon = voyage["current_lon"]

    fig = go.Figure()

    # 부산 → 목적지 항로
    fig.add_trace(
        go.Scattergeo(
            lat=[
                BUSAN_LAT,
                destination_lat,
            ],
            lon=[
                BUSAN_LON,
                destination_lon,
            ],
            mode="lines",
            line=dict(
                color="#8e743d",
                width=2,
            ),
            name="항로",
        )
    )

    # 현재까지 이동한 항적
    if voyage["progress"] > 0:
        fig.add_trace(
            go.Scattergeo(
                lat=[
                    BUSAN_LAT,
                    current_lat,
                ],
                lon=[
                    BUSAN_LON,
                    current_lon,
                ],
                mode="lines",
                line=dict(
                    color="#d8b66a",
                    width=4,
                ),
                name="항적",
            )
        )

    # 부산
    fig.add_trace(
        go.Scattergeo(
            lat=[BUSAN_LAT],
            lon=[BUSAN_LON],
            mode="markers+text",
            marker=dict(
                size=8,
                color="#f4efe2",
            ),
            text=["부산"],
            textposition="bottom center",
            textfont=dict(
                size=11,
                color="#f4efe2",
            ),
            name="출발지",
        )
    )

    # 목적지
    fig.add_trace(
        go.Scattergeo(
            lat=[destination_lat],
            lon=[destination_lon],
            mode="markers+text",
            marker=dict(
                size=10,
                color="#d8b66a",
            ),
            text=[get_current_destination()],
            textposition="top center",
            textfont=dict(
                size=12,
                color="#f1d58b",
            ),
            name="목적지",
        )
    )

    # 현재 선박
    fig.add_trace(
        go.Scattergeo(
            lat=[current_lat],
            lon=[current_lon],
            mode="text",
            text=["🚢"],
            textfont=dict(
                size=24,
            ),
            name="현재 선박",
            showlegend=False,
        )
    )

    # 지도가 매번 새로 만들어져도 화면 상태가 최대한 유지되도록 설정
    fig.update_layout(
        height=520,
        margin=dict(
            l=0,
            r=0,
            t=0,
            b=0,
        ),
        paper_bgcolor="#07111f",
        plot_bgcolor="#07111f",
        font=dict(
            color="#f4efe2",
        ),
        uirevision="celestial-voyage-map",
        transition=dict(
            duration=500,
            easing="linear",
        ),
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
        legend=dict(
            bgcolor="#081522",
            font=dict(
                color="#f4efe2",
            ),
        ),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": False,
        },
        key="celestial_voyage_map",
    )

    # ---------------------------------------------
    # 뽀모도로 25분 자동 종료
    # ---------------------------------------------

    if (
        st.session_state.selected_mode == "뽀모도로"
        and st.session_state.timer_running
        and elapsed >= 25 * 60
    ):
        now = get_kst_now()

        if st.session_state.start_time is not None:
            save_session(
                st.session_state.start_time,
                now,
                "뽀모도로",
            )

        st.session_state.elapsed_seconds = 25 * 60
        st.session_state.start_time = None
        st.session_state.timer_running = False
        st.session_state.voyage_saved = True

        st.rerun(scope="fragment")


show_live_voyage()


# =========================================================
# 버튼
# =========================================================

button1, button2, button3 = st.columns(3)

with button1:
    start_clicked = st.button(
        "🚢 출항",
        key="start_voyage_button",
        use_container_width=True,
        disabled=st.session_state.timer_running,
    )

with button2:
    stop_clicked = st.button(
        "⏸ 정박",
        key="stop_voyage_button",
        use_container_width=True,
        disabled=not st.session_state.timer_running,
    )

with button3:
    reset_clicked = st.button(
        "↻ 초기화",
        key="reset_voyage_button",
        use_container_width=True,
    )


# =========================================================
# 출항
# =========================================================

if start_clicked:

    if st.session_state.selected_mode == "자유항해":
        st.session_state.free_destination = random.choice(
            list(DESTINATIONS.keys())
        )

    st.session_state.start_time = get_kst_now()
    st.session_state.timer_running = True
    st.session_state.voyage_saved = False

    st.rerun()


# =========================================================
# 정박
# =========================================================

if stop_clicked:

    now = get_kst_now()
    start = st.session_state.start_time

    if start is not None:
        segment_seconds = max(
            0,
            int((now - start).total_seconds()),
        )

        st.session_state.elapsed_seconds += segment_seconds

        save_session(
            start,
            now,
            st.session_state.selected_mode,
        )

    st.session_state.start_time = None
    st.session_state.timer_running = False
    st.session_state.voyage_saved = True

    st.rerun()


# =========================================================
# 초기화
# =========================================================

if reset_clicked:

    st.session_state.timer_running = False
    st.session_state.start_time = None
    st.session_state.elapsed_seconds = 0
    st.session_state.free_destination = None
    st.session_state.voyage_saved = False

    st.rerun()


# =========================================================
# 상태 안내
# =========================================================

if st.session_state.timer_running:
    st.info("🚢 항해 중입니다. 공부한 시간이 실시간으로 항해 거리로 변환됩니다.")

elif st.session_state.elapsed_seconds > 0:
    st.success("⏸ 정박했습니다. 현재 시간이 유지됩니다. 다시 출항하면 이어서 진행합니다.")

else:
    st.caption("출항 버튼을 누르면 항해가 시작됩니다.")


# =========================================================
# 지정 항로 진행도
# =========================================================

if st.session_state.selected_mode == "지정 항로":

    voyage = get_voyage_status()

    st.markdown(
        '<div class="section-title">🧭 항로 진행도</div>',
        unsafe_allow_html=True,
    )

    st.progress(voyage["progress"])

    p1, p2 = st.columns(2)

    with p1:
        st.metric(
            "현재까지 전진",
            f"{voyage['traveled_distance']:,.1f} NM",
        )

    with p2:
        st.metric(
            "목적지까지",
            f"{voyage['remaining_distance']:,.1f} NM",
        )


# =========================================================
# 뽀모도로 안내
# =========================================================

if st.session_state.selected_mode == "뽀모도로":

    st.markdown(
        '<div class="section-title">🍅 뽀모도로 항해</div>',
        unsafe_allow_html=True,
    )

    route = " → ".join(POMODORO_ROUTE)

    st.markdown(
        f"""
        <div class="info-card">
            <div class="card-title">CURRENT ROUTE</div>
            <div style="
                color:#f4efe2;
                font-size:1.15rem;
                margin-bottom:10px;
            ">
                {route}
            </div>
            <div style="
                color:#9daaba;
                line-height:1.7;
            ">
                25분 집중하면 하나의 항해 기록이 저장됩니다.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 안내
# =========================================================

st.divider()

st.markdown(
    '<div class="section-title">✦ 항해 안내</div>',
    unsafe_allow_html=True,
)

if st.session_state.selected_mode == "자유항해":
    st.write(
        "자유롭게 공부하고 정박하면 해당 시간이 항해일지에 기록됩니다. "
        "출항할 때마다 목적지가 무작위로 정해집니다."
    )

elif st.session_state.selected_mode == "지정 항로":
    st.write(
        f"부산에서 {st.session_state.selected_destination}까지의 "
        "가상 항로를 따라 공부합니다."
    )

else:
    st.write(
        "25분 동안 집중하면 자동으로 항해가 종료되고 기록됩니다."
    )
