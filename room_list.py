# room_list.py

import streamlit as st
import db_handler as db


def render_room_list():

    # =======================================================
    # 🎨 채팅방 목록 전용 스타일
    # =======================================================
    st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem !important;
        }

        div[data-testid="stButton"] > button {
            transition: all 0.15s ease;
        }

        div[data-testid="stButton"] > button:hover {
            transform: translateY(-1px);
        }
    </style>
    """, unsafe_allow_html=True)


    # =======================================================
    # 💬 제목 + 새 채팅 버튼
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

                # 이 방의 메시지는 이미 빈 상태로 준비됨
                st.session_state.room_messages_loaded = True

                # 이전 방에서 쓰던 Gemini 대화 객체 제거
                if "chat" in st.session_state:
                    del st.session_state.chat

                st.rerun()

            except Exception as e:
                st.error(f"❌ 새 채팅방 생성 실패: {e}")


    st.divider()


    # =======================================================
    # 📂 기존 채팅방 목록 불러오기
    # =======================================================
    try:
        rooms = db.get_rooms()

    except Exception as e:
        st.error(f"❌ 채팅방 목록 불러오기 실패: {e}")
        return


    # =======================================================
    # 채팅방이 없을 때
    # =======================================================
    if not rooms:
        st.info(
            "아직 만들어진 채팅방이 없습니다.\n\n"
            "오른쪽 위 ＋ 버튼을 눌러 새 채팅을 만들어보세요."
        )
        return


    # =======================================================
    # 💬 채팅방 목록
    # =======================================================
    for room in rooms:

        room_id = room["id"]
        title = room.get("title") or "새 채팅"

        room_col, edit_col, delete_col = st.columns(
            [7, 1, 1]
        )


        # ===================================================
        # 🚪 채팅방 입장
        # ===================================================
        with room_col:

            if st.button(
                title,
                key=f"room_{room_id}",
                use_container_width=True
            ):

                try:
                    messages = db.get_messages(room_id)

                    st.session_state.current_room_id = room_id
                    st.session_state.messages = messages

                    # 이미 해당 방 메시지를 불러왔다는 표시
                    st.session_state.room_messages_loaded = True

                    # 이전 방에서 쓰던 Gemini 대화 객체 제거
                    if "chat" in st.session_state:
                        del st.session_state.chat

                    st.rerun()

                except Exception as e:
                    st.error(
                        f"❌ 채팅방 불러오기 실패: {e}"
                    )


        # ===================================================
        # ✏️ 이름 수정
        # ===================================================
        with edit_col:

            if st.button(
                "✏️",
                key=f"edit_{room_id}",
                help="채팅방 이름 수정",
                use_container_width=True
            ):
                st.session_state.editing_room_id = room_id


        # ===================================================
        # 🗑️ 채팅방 삭제
        # ===================================================
        with delete_col:

            if st.button(
                "🗑️",
                key=f"delete_{room_id}",
                help="채팅방 삭제",
                use_container_width=True
            ):

                try:
                    db.delete_room(room_id)

                    if (
                        st.session_state.get(
                            "editing_room_id"
                        )
                        == room_id
                    ):
                        st.session_state.editing_room_id = None

                    st.rerun()

                except Exception as e:
                    st.error(
                        f"❌ 채팅방 삭제 실패: {e}"
                    )


        # ===================================================
        # ✏️ 제목 편집창
        # ===================================================
        if (
            st.session_state.get("editing_room_id")
            == room_id
        ):

            new_title = st.text_input(
                "채팅방 이름",
                value=title,
                key=f"title_input_{room_id}",
                label_visibility="collapsed",
                placeholder="채팅방 이름"
            )

            save_col, cancel_col = st.columns(2)


            # 저장
            with save_col:

                if st.button(
                    "저장",
                    key=f"save_title_{room_id}",
                    use_container_width=True
                ):

                    new_title = new_title.strip()

                    if not new_title:
                        st.warning(
                            "채팅방 이름을 입력해주세요."
                        )

                    else:
                        try:
                            db.rename_room(
                                room_id,
                                new_title
                            )

                            st.session_state.editing_room_id = None
                            st.rerun()

                        except Exception as e:
                            st.error(
                                f"❌ 이름 수정 실패: {e}"
                            )


            # 취소
            with cancel_col:

                if st.button(
                    "취소",
                    key=f"cancel_title_{room_id}",
                    use_container_width=True
                ):

                    st.session_state.editing_room_id = None
                    st.rerun()


        st.divider()