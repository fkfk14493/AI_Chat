# config.py
import db_handler as db
import streamlit as st
from google import genai
from google.genai import types
from google.genai import errors  # 🚨 429 및 구글 전용 에러 처리를 위해 임포트!
import os
import sqlite3

# 🎯 DB 절대 경로 설정
DB_FILE = "chat.db"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, DB_FILE)


def render_backup_tools():
    """📥 [1단계] 데이터 백업 및 복원 도구 UI를 그립니다."""
    # 🚨 맨 위에 물리적인 빈 여백을 줘서 상자가 안 잘리게 내립니다!
    st.write("")
    st.write("")
    
    with st.expander("🛠️ 데이터 백업 및 복원", expanded=False):
        col1, col2 = st.columns(2)
        
        # 1. 백업 다운로드
        with col1:
            if os.path.exists(DB_PATH):
                with open(DB_PATH, "rb") as f:
                    st.download_button(
                        label="📥 현재 DB 다운로드",
                        data=f,
                        file_name=DB_FILE,
                        mime="application/octet-stream"
                    )
            else:
                st.info("백업할 DB가 없습니다.")

        # 2. 즉시 반영 업로드 (메모리 강제 주입식)
        with col2:
            uploaded_db = st.file_uploader("📤 백업본 업로드", type=["db"], label_visibility="collapsed")
            
            if uploaded_db is not None:
                try:
                    # 기존 SQLite 연결 정리
                    import gc
                    gc.collect()
                    
                    # 파일 강제 덮어쓰기
                    db_bytes = uploaded_db.getbuffer()
                    with open(DB_PATH, "wb") as f:
                        f.write(db_bytes)
                    
                    # 덮어쓴 DB가 정상적인지 테스트 연결
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    
                    # 테이블이 없을 경우를 대비해 토큰용 테이블 강제 생성
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS token_usage (
                            id INTEGER PRIMARY KEY,
                            input_tokens INTEGER DEFAULT 0,
                            output_tokens INTEGER DEFAULT 0
                        )
                    """)
                    cursor.execute("SELECT input_tokens, output_tokens FROM token_usage WHERE id = 1")
                    row = cursor.fetchone()
                    
                    # chat_history 조회
                    try:
                        cursor.execute("SELECT role, content FROM chat_history ORDER BY id ASC")
                        db_messages = [{"role": r, "content": c} for r, c in cursor.fetchall()]
                    except Exception:
                        db_messages = []
                    
                    conn.close()
                    
                    st.success("🎉 복원 성공! 연결 복구 완료.")
                    
                    # 🚨 [중복 차단 치트키 개조!] 대화와 토큰 세션만 쏙 비워줍니다.
                    st.session_state.messages = []
                    st.session_state.total_input_tokens = 0
                    st.session_state.total_output_tokens = 0
                    
                    if row:
                        st.session_state.total_input_tokens = row[0]
                        st.session_state.total_output_tokens = row[1]
                    
                    # 🚨 세션에 빈 껍데기만 남겨서 2단계에 새로고침 신호를 정확히 송신합니다!
                    st.session_state.messages_uploaded = True
                    
                    # 완전히 강제 주입된 깨끗한 상태로 새로고침!
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ 오류: {e}")

    st.markdown("---")


def init_app_state():
    """🤖 [2단계] 메인 가동 영역 및 세션 초기화 (429 한도 초과 및 우회 보완판)"""

    if "custom_avatar" not in st.session_state:
        db_avatar = db.load_avatar()
        st.session_state.custom_avatar = db_avatar if db_avatar else None
    
    # 1. 🚨 [최우선] 제미나이 API 클라이언트(client)를 가장 먼저 초기화합니다!
    if "client" not in st.session_state:
        st.session_state.client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

    # 2. 🚨 [핵심 보안] 세션 프롬프트(system_prompt)를 챗 세션 빌드 전에 무조건 먼저 확보합니다!
    if "system_prompt" not in st.session_state:
        try:
            st.session_state.system_prompt = db.get_system_prompt("")
        except Exception:
            st.session_state.system_prompt = ""

    # 3. [메모리-DB 완벽 동기화] 세션에 메시지가 없거나 비어있다면, 새로고침 시 무조건 DB에서 안전하게 로드합니다!
    if "messages" not in st.session_state or not st.session_state.messages:
        db_messages = db.load_messages()
        st.session_state.messages = db_messages if db_messages else []

    # 4. 토큰 및 업로드 신호등 플래그 초기화
    if "messages_uploaded" not in st.session_state:
        st.session_state.messages_uploaded = False

    if "total_input_tokens" not in st.session_state:
        st.session_state.total_input_tokens = 0
    if "total_output_tokens" not in st.session_state:
        st.session_state.total_output_tokens = 0

    # 5. 제미나이 대화 세션 생성 (이중 생성 방지 및 자동 백업 우회 적용)
    if "chat" not in st.session_state:
        history_contents = []
        for m in st.session_state.messages:
            # 시스템 메시지는 API 대화 히스토리에 주입하지 않고 패스
            if m["role"] == "system":
                continue
                
            role = "model" if m["role"] == "assistant" else "user"
            history_contents.append(
                types.Content(
                    role=role, 
                    parts=[types.Part.from_text(text=m["content"])]
                )
            )
            
        try:
            # 1. 3.5 Flash로 접속 시도!
            st.session_state.chat = st.session_state.client.chats.create(
                model="gemini-3.5-flash",
                history=history_contents if history_contents else None,
                config=types.GenerateContentConfig(
                    system_instruction=st.session_state.system_prompt,
                    temperature=0.95,
                )
            )
        except Exception as e:
            # 🚨 [중요] 429 한도 초과 또는 503 서버 혼잡 모두 감지하기!
            is_quota_or_server_error = False
            if isinstance(e, errors.ClientError) or isinstance(e, errors.ServerError):
                if e.code in [429, 403, 503]:
                    is_quota_or_server_error = True
            
            error_msg = str(e).upper()
            if is_quota_or_server_error or any(kw in error_msg for kw in ["EXHAUSTED", "QUOTA", "LIMIT", "429", "UNAVAILABLE"]):
                # 즉시 3.1 Flash-lite로 우회해서 재시도!
                st.session_state.chat = st.session_state.client.chats.create(
                    model="gemini-3.1-flash-lite",
                    history=history_contents if history_contents else None,
                    config=types.GenerateContentConfig(
                        system_instruction=st.session_state.system_prompt,
                        temperature=0.95,
                    )
                )
                st.toast("3.1 Flash-lite 모델로 임시 우회 가동됩니다.")
            else:
                raise e