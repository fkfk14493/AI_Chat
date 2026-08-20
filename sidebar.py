# sidebar.py

import io

import streamlit as st
from google.genai import types
from google.genai import errors

import db_handler as db
from config import BASE_ROLEPLAY_PROMPT


def render_sidebar():

    # =======================================================
    # 현재 채팅방 확인
    # =======================================================
    room_id = st.session_state.get("current_room_id")

    if room_id is None:
        return


    # =======================================================
    # 방이 바뀌었으면 해당 방 설정 다시 불러오기
    # =======================================================
    if st.session_state.get("settings_room_id") != room_id:

        try:
            # 현재 방 프롬프트 / 프로필 불러오기
            room_settings = db.get_room_settings(room_id)

            st.session_state.system_prompt = (
                room_settings["system_prompt"]
            )

            st.session_state.custom_avatar = (
                room_settings["avatar"]
            )

            # 현재 방 누적 토큰 불러오기
            room_input_tokens, room_output_tokens = (
                db.load_room_tokens(room_id)
            )

            st.session_state.total_input_tokens = (
                room_input_tokens
            )

            st.session_state.total_output_tokens = (
                room_output_tokens
            )

        except Exception as e:
            st.error(
                f"채팅방 설정 불러오기 실패: {e}"
            )

            st.session_state.system_prompt = ""
            st.session_state.custom_avatar = None
            st.session_state.total_input_tokens = 0
            st.session_state.total_output_tokens = 0

        # 현재 방 설정 로딩 완료 표시
        st.session_state.settings_room_id = room_id


    # =======================================================
    # 사이드바
    # =======================================================
    with st.sidebar:

        # ===================================================
        # ← 채팅방 목록으로 돌아가기
        # ===================================================
        if st.button(
            "← 채팅방 목록",
            key=f"back_to_room_list_{room_id}",
            type="tertiary"
        ):
            st.session_state.current_room_id = None
            st.session_state.room_messages_loaded = False
            st.session_state.settings_room_id = None

            # 현재 Gemini 대화 객체 제거
            if "chat" in st.session_state:
                del st.session_state["chat"]

            st.rerun()


        st.title("⚙️ 설정 및 관리")

        st.markdown("---")


        # ===================================================
        # 📸 AI 프로필
        # ===================================================
        st.subheader("📸 AI 프로필 설정")

        uploaded_avatar = st.file_uploader(
            "AI 프로필 사진 업로드 (.png, .jpg)",
            type=["png", "jpg", "jpeg"],
            key=f"avatar_upload_{room_id}"
        )

        if uploaded_avatar is not None:

            avatar_bytes = uploaded_avatar.read()

            st.session_state.custom_avatar = avatar_bytes

            try:
                db.save_room_avatar(
                    room_id,
                    avatar_bytes
                )

                st.success(
                    "이 채팅방의 프로필 이미지가 저장되었습니다!"
                )

            except Exception as e:
                st.error(
                    f"❌ 프로필 저장 실패: {e}"
                )


        # ===================================================
        # 현재 프로필 표시
        # ===================================================
        if st.session_state.get("custom_avatar") is not None:

            st.image(
                st.session_state.custom_avatar,
                width=80,
                caption="현재 프로필"
            )

            if st.button(
                "기본 프로필로 리셋",
                key=f"reset_avatar_{room_id}",
                use_container_width=True
            ):

                st.session_state.custom_avatar = None

                try:
                    db.save_room_avatar(
                        room_id,
                        None
                    )

                    st.toast(
                        "이 채팅방의 프로필을 기본값으로 변경했습니다."
                    )

                    st.rerun()

                except Exception as e:
                    st.error(
                        f"❌ 프로필 초기화 실패: {e}"
                    )


        # ===================================================
        # 🧭 화면 순간이동
        # ===================================================
        st.markdown("---")

        st.subheader("🧭 화면 순간이동")

        nav_col1, nav_col2 = st.columns(2)

        with nav_col1:
            st.markdown(
                """
                <a href="#top-anchor" target="_self" style="
                    display:block;
                    padding:0.5rem;
                    color:white;
                    background-color:#4B90FF;
                    text-decoration:none;
                    border-radius:5px;
                    font-size:0.85rem;
                    font-weight:bold;
                    text-align:center;
                ">⬆️ 맨 위로</a>
                """,
                unsafe_allow_html=True
            )

        with nav_col2:
            st.markdown(
                """
                <a href="#bottom-anchor" target="_self" style="
                    display:block;
                    padding:0.5rem;
                    color:white;
                    background-color:#4B90FF;
                    text-decoration:none;
                    border-radius:5px;
                    font-size:0.85rem;
                    font-weight:bold;
                    text-align:center;
                ">⬇️ 맨 아래로</a>
                """,
                unsafe_allow_html=True
            )


        # ===================================================
        # 📝 프롬프트 설정
        # ===================================================
        st.markdown("---")

        st.subheader("📝 프롬프트 설정")

        user_prompt = st.text_area(
            "프롬프트를 수정하고 아래 [변경 적용]을 누르세요:",
            value=st.session_state.get(
                "system_prompt",
                ""
            ),
            height=200,
            key=f"prompt_input_{room_id}"
        )


        # ===================================================
        # 글자 수 표시
        # ===================================================
        prompt_length = len(user_prompt)

        st.caption(
            f"공백 포함: {prompt_length:,} 자"
            )


        # ===================================================
        # 💾 프롬프트 변경 적용
        # ===================================================
        if st.button(
            "💾 프롬프트 변경 적용",
            key=f"save_prompt_{room_id}",
            use_container_width=True
        ):

            st.session_state.system_prompt = user_prompt

            try:
                db.save_room_prompt(
                    room_id,
                    user_prompt
                )

            except Exception as e:
                st.error(
                    f"❌ 프롬프트 저장 실패: {e}"
                )


            # ===============================================
            # 현재 방 메시지 기반 Gemini history 재구성
            # ===============================================
            new_history = []

            if st.session_state.get("messages"):

                for msg in st.session_state.messages:

                    if msg["role"] == "system":
                        continue

                    role_name = (
                        "model"
                        if msg["role"] == "assistant"
                        else "user"
                    )

                    new_history.append(
                        types.Content(
                            role=role_name,
                            parts=[
                                types.Part.from_text(
                                    text=msg["content"]
                                )
                            ]
                        )
                    )


            # ===============================================
            # Gemini 세션 재생성
            # ===============================================
            try:

                st.session_state.chat = (
                    st.session_state.client.chats.create(
                        model="gemini-3.5-flash",
                        history=(
                            new_history
                            if new_history
                            else None
                        ),
                        config=types.GenerateContentConfig(
                            system_instruction=(
                                BASE_ROLEPLAY_PROMPT
                                + "\n"
                                + st.session_state.system_prompt
                            ),
                            temperature=0.95,
                        )
                    )
                )

            except Exception as e:

                is_quota_or_server_error = False

                if (
                    isinstance(e, errors.ClientError)
                    or isinstance(e, errors.ServerError)
                ):
                    if e.code in [429, 403, 503]:
                        is_quota_or_server_error = True

                error_msg = str(e).upper()

                if (
                    is_quota_or_server_error
                    or any(
                        kw in error_msg
                        for kw in [
                            "EXHAUSTED",
                            "QUOTA",
                            "LIMIT",
                            "429",
                            "UNAVAILABLE"
                        ]
                    )
                ):

                    st.session_state.chat = (
                        st.session_state.client.chats.create(
                            model="gemini-3.1-flash-lite",
                            history=(
                                new_history
                                if new_history
                                else None
                            ),
                            config=types.GenerateContentConfig(
                                system_instruction=(
                                    BASE_ROLEPLAY_PROMPT
                                    + "\n"
                                    + st.session_state.system_prompt
                                ),
                                temperature=0.95,
                            )
                        )
                    )

                    st.toast(
                        "3.1 Flash-lite 모델로 임시 우회했습니다."
                    )

                else:
                    raise e


            st.success(
                "이 채팅방의 프롬프트가 저장되었습니다."
            )

            st.rerun()


        # ===================================================
        # 🛠️ 추가 편의 기능
        # ===================================================
        st.markdown("---")

        st.subheader("🛠️ 추가 편의 기능")


        # ===================================================
        # 📥 현재 방 TXT 다운로드
        # ===================================================
        if st.session_state.get("messages"):

            export_text = ""

            for msg in st.session_state.messages:

                role_name = (
                    "나"
                    if msg["role"] == "user"
                    else "상대"
                )

                export_text += (
                    f"[{role_name}]\n"
                    f"{msg['content']}\n\n"
                )

            st.download_button(
                label="📥 현재 대화 TXT 다운로드",
                data=export_text,
                file_name=f"chat_room_{room_id}.txt",
                mime="text/plain",
                use_container_width=True
            )

        else:
            st.caption(
                "대화 기록이 없어서 다운로드할 수 없습니다."
            )


        # ===================================================
        # 🔍 현재 방 대화 검색
        # ===================================================
        st.markdown("---")

        search_query = st.text_input(
            "🔍 과거 대화 검색 (단어 입력):",
            placeholder="찾을 단어를 입력하고 Enter...",
            key=f"search_{room_id}"
        )

        if (
            search_query
            and st.session_state.get("messages")
        ):

            st.write(
                f"**'{search_query}' 검색 결과:**"
            )

            found_any = False

            for idx, msg in enumerate(
                st.session_state.messages
            ):

                if (
                    search_query.lower()
                    in msg["content"].lower()
                ):

                    found_any = True

                    role_name = (
                        "나"
                        if msg["role"] == "user"
                        else "상대"
                    )

                    with st.expander(
                        f"💬 [{role_name}]의 대화에서 발견"
                    ):

                        st.write(
                            msg["content"]
                        )

                        st.markdown(
                            f"""
                            <a
                                href="#message-{idx}"
                                target="_self"
                                style="
                                    display:inline-block;
                                    padding:0.4rem 0.8rem;
                                    color:white;
                                    background-color:#FF4B4B;
                                    text-decoration:none;
                                    border-radius:5px;
                                    font-size:0.85rem;
                                    font-weight:bold;
                                    text-align:center;
                                    margin-top:5px;
                                "
                            >
                                해당 위치로 이동
                            </a>
                            """,
                            unsafe_allow_html=True
                        )

            if not found_any:
                st.warning(
                    "검색 결과가 없습니다."
                )


        # ===================================================
        # 📊 토큰 계기판
        # ===================================================
        st.divider()

        st.subheader("📊 실시간 토큰 계기판")

        total_in = st.session_state.get(
            "total_input_tokens",
            0
        )

        total_out = st.session_state.get(
            "total_output_tokens",
            0
        )

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                label="입력 토큰 (누적)",
                value=f"{total_in:,}",
                help="내가 보낸 질문과 과거 기억을 합친 토큰 수입니다."
            )

        with col2:
            st.metric(
                label="출력 토큰 (누적)",
                value=f"{total_out:,}",
                help="AI가 생성한 출력 토큰 수입니다."
            )


        estimated_cost = (
            total_in * 0.000000075
        ) + (
            total_out * 0.00000030
        )

        st.caption(
            f"💰 현재 세션 예상 요금: "
            f"약 {estimated_cost * 1350:.2f}원"
        )


        if st.button(
            "토큰 집계 초기화",
            key=f"reset_tokens_{room_id}",
            use_container_width=True
        ):

            db.reset_room_tokens(room_id)

            st.session_state.total_input_tokens = 0
            st.session_state.total_output_tokens = 0

            st.toast(
                "누적 토큰 집계가 0으로 초기화되었습니다."
            )

            st.rerun()


        # ===================================================
        # ⚠️ 위험 구역
        # ===================================================
        st.markdown("---")

        st.subheader("위험 구역")

        if st.button(
            "이 채팅방 대화 기록 초기화",
            key=f"clear_room_{room_id}",
            type="primary",
            use_container_width=True
        ):

            try:

                # 현재 방 메시지만 삭제
                db.clear_room_messages(
                    room_id
                )

                st.session_state.messages = []

                if "chat" in st.session_state:
                    del st.session_state["chat"]

                st.success(
                    "현재 채팅방의 대화만 초기화되었습니다."
                )

                st.rerun()

            except Exception as e:
                st.error(
                    f"❌ 대화 초기화 실패: {e}"
                )