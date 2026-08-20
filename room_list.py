# room_list.py
import streamlit as st
import db_handler as db


def render_room_list():
    st.subheader("💬 채팅방")

    # =======================================================
    # + 새 채팅방 만들기
    # =======================================================
    if st.button(
        "＋ 새 채팅",
        use_container_width=True
    ):
        room_id = db.create_room()

        st.session_state.current_room_id = room_id
        st.session_state.messages = []

        st.rerun()

    st.divider()

    # =======================================================
    # 기존 채팅방 목록 불러오기
    # =======================================================
    try:
        rooms = db.get_rooms()
    except Exception as e:
        st.error(f"❌ 채팅방 목록 불러오기 실패: {e}")
        return

    if not rooms:
        st.info("아직 만들어진 채팅방이 없습니다.")
        return

    # =======================================================
    # 채팅방 목록 출력
    # =======================================================
    for room in rooms:
        room_id = room["id"]
        title = room.get("title", "새 채팅")

        # 방마다 3칸 구성
        col1, col2, col3 = st.columns([6, 1, 1])

        # -----------------------------
        # 채팅방 입장
        # -----------------------------
        with col1:
            if st.button(
                title,
                key=f"room_{room_id}",
                use_container_width=True
            ):
                st.session_state.current_room_id = room_id
                st.session_state.messages = db.get_messages(room_id)

                st.rerun()

        # -----------------------------
        # 제목 수정 버튼
        # -----------------------------
        with col2:
            if st.button(
                "✏️",
                key=f"edit_{room_id}"
            ):
                st.session_state.editing_room_id = room_id

        # -----------------------------
        # 삭제 버튼
        # -----------------------------
        with col3:
            if st.button(
                "🗑️",
                key=f"delete_{room_id}"
            ):
                db.delete_room(room_id)

                # 수정 중이던 방이 삭제되면 상태 초기화
                if st.session_state.get("editing_room_id") == room_id:
                    st.session_state.editing_room_id = None

                st.rerun()

        # ===================================================
        # 제목 편집 모드
        # ===================================================
        if st.session_state.get("editing_room_id") == room_id:

            new_title = st.text_input(
                "채팅방 이름",
                value=title,
                key=f"title_input_{room_id}",
                label_visibility="collapsed"
            )

            save_col, cancel_col = st.columns(2)

            with save_col:
                if st.button(
                    "저장",
                    key=f"save_title_{room_id}",
                    use_container_width=True
                ):
                    if new_title.strip():
                        db.rename_room(
                            room_id,
                            new_title.strip()
                        )

                        st.session_state.editing_room_id = None
                        st.rerun()

            with cancel_col:
                if st.button(
                    "취소",
                    key=f"cancel_title_{room_id}",
                    use_container_width=True
                ):
                    st.session_state.editing_room_id = None
                    st.rerun()

        st.divider()