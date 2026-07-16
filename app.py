# app.py
import streamlit as st
import db_handler as db  # 기존 DB 핸들러 파일 호출
from config import render_backup_tools, init_app_state  # ⚙️ 설정 및 초기화 도구 가져오기
from sidebar import render_sidebar  # 🧭 사이드바 조종실 가져오기
from chat_room import render_chat_history, handle_user_input  # 💬 메인 채팅 렌더러 및 입력기 가져오기

# =======================================================
# 0. 레이아웃 세팅 및 기본 스타일 주입
# =======================================================
st.set_page_config(page_title="Chatting", layout="centered")

# 순간이동 앵커 포인트를 위한 맨 위 천장 닻 설치
st.markdown('<div id="top-anchor"></div>', unsafe_allow_html=True)

# [수정] 스트림릿 특유의 상단 여백(헤더 공백)을 강제로 제거하는 CSS 주입
st.markdown("""
    <style>
        /* 상단 공백 제거 */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }
        /* 우측 상단 스트림릿 메뉴 숨기기 */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# =======================================================
# 1. 💾 DB 파일 및 스키마 자동 초기화
# =======================================================
try:
    db.init_db()
except Exception as e:
    st.error(f"❌ 데이터베이스 연동 실패: {e}")

# =======================================================
# 🛠️ [1단계] 즉시 반영형 무적의 복원 도구 그리기
# =======================================================
# config.py 내부에 포장해둔 DB 다운로드 및 백업 업로더 UI를 최상단에 배치합니다.
render_backup_tools()

# =======================================================
# 🤖 [2단계] 메인 가동 영역 및 세션 초기화
# =======================================================
# 클라이언트 생성, 프롬프트 로드, 대화 상태 복원, 제미나이 뇌세포(3.5 ↔ 3.1 우회) 가동을 원터치로 진행합니다.
init_app_state()

# =======================================================
# 🧭 [사이드바] 설정 조종실 렌더링
# =======================================================
# 순간이동 닻, 실시간 토큰 계기판, 다운로드, 검색 기능이 들어있는 사이드바를 가동합니다.
render_sidebar()

# =======================================================
# 💬 [3단계] 웹 화면에 대화 기록 출력 (중복 방어막)
# =======================================================
st.title("AI Chatroom")
render_chat_history()

# =======================================================
# 🤖 [4단계] 사용자 입력창 및 통합 대화 처리 구역
# =======================================================
# 실시간 429 감지 및 3.1 우회, 10턴 슬라이딩 윈도우 압축 기능이 내장된 입력창을 가동합니다.
handle_user_input()

# 순간이동 앵커 포인트를 위한 맨 아래 바닥 닻 설치
st.markdown('<div id="bottom-anchor"></div>', unsafe_allow_html=True)