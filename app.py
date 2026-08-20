# app.py
import streamlit as st
import db_handler as db

from config import render_backup_tools, init_app_state
from sidebar import render_sidebar
from chat_room import render_chat_history, handle_user_input

# ✅ 새로 추가
from room_list import render_room_list


# =======================================================
# 0. 레이아웃 세팅
# =======================================================
st.set_page_config(
    page_title="Chatting",
    layout="centered"
)

st.markdown('<div id="top-anchor"></div>', unsafe_allow_html=True)

st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)


# =======================================================
# 1. DB 초기화
# =======================================================
try:
    db.init_db()
except Exception as e:
    st.error(f"❌ 데이터베이스 연동 실패: {e}")


# =======================================================
# 2. 현재 들어가 있는 채팅방
# =======================================================
if "current_room_id" not in st.session_state:
    st.session_state.current_room_id = None


# =======================================================
# 3. 화면 분기
# =======================================================

# -----------------------------
# 채팅방을 선택하지 않은 상태
# -----------------------------
if st.session_state.current_room_id is None:

    render_room_list()


# -----------------------------
# 채팅방에 들어간 상태
# -----------------------------
else:

    # 백업 / 복원 도구
    render_backup_tools()

    # 기존 세션 초기화
    init_app_state()

    # 기존 사이드바
    render_sidebar()

    # 기존 채팅 화면
    st.subheader("Chatting")
    render_chat_history()

    # 기존 채팅 입력창
    handle_user_input()

    # 하단 앵커
    st.markdown(
        '<div id="bottom-anchor"></div>',
        unsafe_allow_html=True
    )