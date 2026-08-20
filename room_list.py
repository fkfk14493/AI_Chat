# room_list.py

import streamlit as st
import db_handler as db


def render_room_list():

    # =======================================================
    # 🎨 스타일
    # =======================================================
    st.markdown("""
    <style>
        div[data-testid="stButton"] > button {
            transition: all 0.15s ease;
        }

        div[data-testid="stButton"] > button:hover {
            transform: translateY(-1px);
        }
    </style>
    """, unsafe_allow_html=True)


    # =======================================================
    # 💬 제목 + 새 채팅
    # =======================================================
    title_col, add_col = st.columns([8, 1])

    with title_col:
        st.subheader("💬 채팅방")

    with add_col:
        if st.button(
            "＋",
            key="new_chat",
            help="새 채팅",
            use_container_width=True
        ):
            try:
                room_id = db.create_room()

                st.session_state.current_room_id = room_id
                st.session_state.messages = []
                st.session_state.room_messages_loaded = True

                if "chat" in st.session_state:
                    del st.session_state.chat

                st.rerun()

            except Exception as e:
                st.error(f"❌ 새 채팅방 생성 실패: {e}")


        # =======================================================
    # 📦 기존 SQLite 데이터 가져오기
    # =======================================================
    with st.expander("📦 기존 데이터 가져오기"):

        st.caption(
            "기존 SQLite DB에 저장된 채팅, 프롬프트, 프로필을 "
            "Supabase의 '기존 채팅' 방으로 옮깁니다."
        )

        # ---------------------------------------------------
        # 기존 채팅 가져오기
        # ---------------------------------------------------
        if st.button(
            "기존 채팅 가져오기",
            key="migrate_old_chat",
            use_container_width=True
        ):
            try:
                result = db.migrate_old_chat_to_supabase()

                if result["success"]:
                    st.success(
                        f"✅ {result['saved_count']}개의 메시지를 옮겼습니다."
                    )
                    st.rerun()

                else:
                    st.warning(result["message"])

            except Exception as e:
                st.error(
                    f"❌ 기존 채팅 이전 실패: {e}"
                )

        # ---------------------------------------------------
        # 기존 프롬프트 / 프로필 가져오기
        # ---------------------------------------------------
        if st.button(
            "기존 프롬프트 / 프로필 가져오기",
            key="migrate_old_settings",
            use_container_width=True
        ):
            try:
                result = db.migrate_old_settings_to_existing_room()

                if result["success"]:

                    prompt_status = (
                        "✅ 프롬프트"
                        if result["prompt_migrated"]
                        else "➖ 프롬프트 없음"
                    )

                    avatar_status = (
                        "✅ 프로필"
                        if result["avatar_migrated"]
                        else "➖ 프로필 없음"
                    )

                    st.success(
                        f"기존 설정 이전 완료!\n\n"
                        f"{prompt_status}\n\n"
                        f"{avatar_status}"
                    )

                    # 기존 채팅방을 다시 들어갈 때
                    # 설정을 새로 읽도록 초기화
                    st.session_state.settings_room_id = None

                else:
                    st.warning(
                        result["message"]
                    )

            except Exception as e:
                st.error(
                    f"❌ 기존 프롬프트 / 프로필 이전 실패: {e}"
                )

    st.divider()


    # =======================================================
    # 📂 채팅방 목록 불러오기
    # =======================================================
    rooms = []

    try:
        rooms = db.get_rooms()

    except Exception as e:
        st.error(f"❌ 채팅방 목록 불러오기 실패: {e}")


    # =======================================================
    # 💬 채팅방이 없을 때
    # =======================================================
    if not rooms:

        st.info(
            "아직 만들어진 채팅방이 없습니다.\n\n"
            "오른쪽 위 ＋ 버튼을 눌러 새 채팅을 만들어보세요."
        )


    # =======================================================
    # 💬 채팅방 목록 출력
    # =======================================================
    else:

        for room in rooms:

            room_id = room["id"]
            title = room.get("title") or f"채팅방 {room_id}"

            # ===============================================
            # 💬 채팅방 이름 + ⋯ 메뉴
            # ===============================================
            room_col, menu_col = st.columns(
                [10, 1],
                vertical_alignment="center"
            )


            # ===============================================
            # 🚪 방 입장
            # ===============================================
            with room_col:

                if st.button(
                    title,
                    key=f"room_{room_id}",
                    use_container_width=True,
                    type="tertiary"
                ):
                    try:
                        messages = db.get_messages(room_id)

                        st.session_state.current_room_id = room_id
                        st.session_state.messages = messages
                        st.session_state.room_messages_loaded = True

                        # 채팅방 들어가면 맨 아래로 이동
                        st.session_state.auto_scroll_to_bottom = True

                        # 기존 Gemini 객체 제거
                        if "chat" in st.session_state:
                            del st.session_state.chat

                        st.rerun()

                    except Exception as e:
                        st.error(
                            f"❌ 채팅방 불러오기 실패: {e}"
                        )


            # ===============================================
            # ⋯ 채팅방 관리 메뉴
            # ===============================================
            with menu_col:

                with st.popover(
                    "⋯",
                    use_container_width=False
                ):

                    st.markdown("##### 채팅방 관리")

                    # ---------------------------------------
                    # ✏️ 이름 수정
                    # ---------------------------------------
                    new_title = st.text_input(
                        "채팅방 이름",
                        value=title,
                        key=f"title_input_{room_id}"
                    )

                    if st.button(
                        "이름 변경",
                        key=f"save_title_{room_id}",
                        use_container_width=True
                    ):

                        new_title = new_title.strip()

                        if new_title:

                            if new_title != title:

                                try:
                                    db.rename_room(
                                        room_id,
                                        new_title
                                    )

                                    st.rerun()

                                except Exception as e:
                                    st.error(
                                        f"❌ 이름 수정 실패: {e}"
                                    )

                        else:
                            st.warning(
                                "채팅방 이름을 입력해주세요."
                            )


                    st.divider()


                    # ---------------------------------------
                    # 🗑️ 삭제
                    # ---------------------------------------
                    if st.button(
                        "🗑️ 채팅방 삭제",
                        key=f"delete_{room_id}",
                        use_container_width=True,
                        type="primary"
                    ):

                        try:
                            db.delete_room(room_id)

                            st.rerun()

                        except Exception as e:
                            st.error(
                                f"❌ 채팅방 삭제 실패: {e}"
                            )


            st.divider()