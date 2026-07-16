# sidebar.py
import db_handler as db
import streamlit as st
from google import genai
from google.genai import types
from google.genai import errors  # 🚨 429 및 구글 API 에러 우회용 임포트
import os
import sqlite3


def render_sidebar():
    
    with st.sidebar:
        st.title("⚙️ 설정 및 관리")
        st.markdown("---")

        # ==========================================
        # 📸 실시간 AI 프로필 이미지 업로더 추가!
        # ==========================================
        st.subheader("📸 AI 프로필 설정")
        
        # 1. 현재 세션에 업로드된 이미지가 있는지 확인 (없으면 기본값 None)
        if "custom_avatar" not in st.session_state:
            st.session_state.custom_avatar = None
            
        uploaded_avatar = st.file_uploader(
            "AI 프로필 사진 업로드 (.png, .jpg)", 
            type=["png", "jpg", "jpeg"]
        )
        
        # sidebar.py 내부의 이미지 업로드 구역 수정
        if uploaded_avatar is not None:
            avatar_bytes = uploaded_avatar.read()
            st.session_state.custom_avatar = avatar_bytes
            db.save_avatar(avatar_bytes)  # 👈 DB에 영구 저장!
            st.success("프로필 이미지가 업로드되었습니다!")
            st.rerun()
            
        if st.session_state.custom_avatar is not None:
            st.image(st.session_state.custom_avatar, width=80, caption="현재 프로필")
            if st.button("기본 프로필로 리셋", use_container_width=True):
                st.session_state.custom_avatar = None
                db.save_avatar(None)  # 👈 DB에서도 지우기!
                st.toast("기본 프로필로 되돌아갑니다.")
                st.rerun()

        st.markdown("---")
        st.subheader("🧭 화면 순간이동")
        
        # 가로로 정렬된 예쁜 버튼 2개 배치
        nav_col1, nav_col2 = st.columns(2)
        with nav_col1:
            st.markdown(
                """
                <a href="#top-anchor" target="_self" style="
                    display: block;
                    padding: 0.5rem;
                    color: white;
                    background-color: #4B90FF;
                    text-decoration: none;
                    border-radius: 5px;
                    font-size: 0.85rem;
                    font-weight: bold;
                    text-align: center;
                ">⬆️ 맨 위로</a>
                """,
                unsafe_allow_html=True
            )
        with nav_col2:
            st.markdown(
                """
                <a href="#bottom-anchor" target="_self" style="
                    display: block;
                    padding: 0.5rem;
                    color: white;
                    background-color: #4B90FF;
                    text-decoration: none;
                    border-radius: 5px;
                    font-size: 0.85rem;
                    font-weight: bold;
                    text-align: center;
                ">⬇️ 맨 아래로</a>
                """,
                unsafe_allow_html=True
            )
        
        st.markdown("---")
        st.subheader("📝 프롬프트 설정")
        
        # 1. 세션 프롬프트 확보 (없다면 DB에서 로드)
        if "system_prompt" not in st.session_state:
            try:
                st.session_state.system_prompt = db.get_system_prompt("")
            except Exception:
                st.session_state.system_prompt = ""

        # 2. 웹 화면에 실시간으로 수정 가능한 대형 텍스트 박스 배치
        user_prompt = st.text_area(
            "프롬프트를 수정하고 아래 [변경 적용]을 누르세요:",
            value=st.session_state.system_prompt,
            height=200
        )
        
        # 🎯 [실시간 글자 수 표시기]
        prompt_length = len(user_prompt)
        st.markdown(
            f"""
            <div style="text-align: right; margin-top: -10px; margin-bottom: 15px;">
                <span style="font-size: 0.85rem; color: #888888;">공백 포함: </span>
                <strong style="font-size: 0.95rem; color: #FF4B4B;">{prompt_length:,}</strong>
                <span style="font-size: 0.85rem; color: #888888;"> 자</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # 3. 변경 적용 버튼 (안전한 예외 우회 로직 장착)
        if st.button("💾 프롬프트 변경 적용", use_container_width=True):
            st.session_state.system_prompt = user_prompt
            db.save_system_prompt(user_prompt)
            
            # 과거 대화 히스토리 포맷 규격에 맞춰 조립
            new_history = []
            if "messages" in st.session_state and st.session_state.messages:
                for msg in st.session_state.messages:
                    if msg["role"] == "system":
                        continue
                    role_name = "model" if msg["role"] == "assistant" else "user"
                    new_history.append(
                        types.Content(
                            role=role_name,
                            parts=[types.Part.from_text(text=msg["content"])]
                        )
                    )
            
            # 🚨 새 프롬프트로 제미나이 세션 재생성 시도 (에러 발생 시 즉각 대피!)
            try:
                st.session_state.chat = st.session_state.client.chats.create(
                    model="gemini-3.5-flash",
                    history=new_history if new_history else None,
                    config=types.GenerateContentConfig(
                        system_instruction=st.session_state.system_prompt,
                        temperature=0.95,
                    )
                )
            except Exception as e:
                # 429(Rate Limit) 또는 503(Overloaded) 감지
                is_quota_or_server_error = False
                if isinstance(e, errors.ClientError) or isinstance(e, errors.ServerError):
                    if e.code in [429, 403, 503]:
                        is_quota_or_server_error = True
                
                error_msg = str(e).upper()
                if is_quota_or_server_error or any(kw in error_msg for kw in ["EXHAUSTED", "QUOTA", "LIMIT", "429", "UNAVAILABLE"]):
                    # 3.1 Flash-lite 우회로 안심 전환!
                    st.session_state.chat = st.session_state.client.chats.create(
                        model="gemini-3.1-flash-lite",
                        history=new_history if new_history else None,
                        config=types.GenerateContentConfig(
                            system_instruction=st.session_state.system_prompt,
                            temperature=0.95,
                        )
                    )
                    st.toast("3.1 Flash-lite 모델로 임시 우회 변경 적용되었습니다.")
                else:
                    raise e
            
            st.success("프롬프트가 성공적으로 반영되었습니다.")
            st.rerun()

        st.markdown("---")
        st.subheader("🛠️ 추가 편의 기능")

        # ==========================================
        # 1. 📥 TXT 파일 내보내기 (다운로드) 기능
        # ==========================================
        if "messages" in st.session_state and st.session_state.messages:
            export_text = ""
            for msg in st.session_state.messages:
                role_name = "나" if msg["role"] == "user" else "상대"
                export_text += f"[{role_name}]\n{msg['content']}\n\n"
                
            st.download_button(
                label="📥 전체 대화 TXT 다운로드",
                data=export_text,
                file_name="chat_backup.txt",
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.caption("대화 기록이 없어서 다운로드할 수 없습니다.")

        st.markdown("---")

        # ==========================================
        # 2. 🔍 과거 대화 검색 기능 (순간이동 링크 버전)
        # ==========================================
        search_query = st.text_input("🔍 과거 대화 검색 (단어 입력):", placeholder="찾을 단어를 입력하고 Enter...")

        if search_query and "messages" in st.session_state:
            st.write(f"**'{search_query}' 검색 결과:**")
            found_any = False
            
            for idx, msg in enumerate(st.session_state.messages):
                if search_query.lower() in msg["content"].lower():
                    found_any = True
                    role_name = "나" if msg["role"] == "user" else "상대"
                    
                    with st.expander(f"💬 [{role_name}]의 대화에서 발견"):
                        st.write(msg["content"])
                        st.markdown(
                            f"""
                            <a href="#message-{idx}" target="_self" style="
                                display: inline-block;
                                padding: 0.4rem 0.8rem;
                                color: white;
                                background-color: #FF4B4B;
                                text-decoration: none;
                                border-radius: 5px;
                                font-size: 0.85rem;
                                font-weight: bold;
                                text-align: center;
                                margin-top: 5px;
                            ">해당 위치로 이동</a>
                            """,
                            unsafe_allow_html=True
                        )

            if not found_any:
                st.warning("검색 결과가 없습니다.")

        st.divider()

        st.subheader("📊 실시간 토큰 계기판")
        
        # 세션 초기화 상태 대비 안전 장치
        total_in = st.session_state.get("total_input_tokens", 0)
        total_out = st.session_state.get("total_output_tokens", 0)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label="입력 토큰 (누적)", 
                value=f"{total_in:,}", 
                help="내가 보낸 질문과 과거 기억을 합친 글자 수입니다."
            )
        with col2:
            st.metric(
                label="출력 토큰 (누적)", 
                value=f"{total_out:,}", 
                help="AI가 나에게 뱉어낸 장문 소설 대사의 글자 수입니다."
            )
            
        estimated_cost = (total_in * 0.000000075) + (total_out * 0.00000030)
        st.caption(f"💰 현재 세션 예상 요금: 약 {estimated_cost * 1350:.2f}원")

        if st.button("토큰 집계 초기화", use_container_width=True):
            db.reset_tokens()
            
            st.session_state.total_input_tokens = 0
            st.session_state.total_output_tokens = 0
            
            st.toast("누적 토큰 집계가 0으로 초기화되었습니다.")
            st.rerun()

        st.markdown("---")
        st.subheader("위험 구역")
        
        if st.button("대화 기록 초기화", type="primary", use_container_width=True):
            st.session_state.messages = []
            if "chat" in st.session_state:
                if hasattr(st.session_state.chat, "history"):
                    st.session_state.chat.history = []
                elif hasattr(st.session_state.chat, "_history"):
                    st.session_state.chat._history = []
            try:
                db.save_chat([])
            except Exception:
                pass
            st.success("대화 기록이 완벽하게 초기화되었습니다!")
            st.rerun()