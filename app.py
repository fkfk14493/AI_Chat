import streamlit as st
import db_handler as db

from config import init_app_state
from sidebar import render_sidebar
from chat_room import render_chat_history, handle_user_input
from room_list import render_room_list


# =======================================================
# 0. 페이지 설정
# =======================================================
st.set_page_config(
    page_title="Chatting",
    layout="centered"
)


# =======================================================
# 1. 기본 스타일
# =======================================================
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }

        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }

        html {
            scroll-behavior: auto !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# =======================================================
# 2. DB 초기화
# =======================================================
try:
    db.init_db()

except Exception as e:
    st.error(
        f"❌ 데이터베이스 연동 실패: {e}"
    )


# =======================================================
# 3. 현재 채팅방 상태
# =======================================================
if "current_room_id" not in st.session_state:
    st.session_state.current_room_id = None


# =======================================================
# 4. 채팅방 목록 화면
# =======================================================
if st.session_state.current_room_id is None:

    render_room_list()


# =======================================================
# 5. 실제 채팅방 화면
# =======================================================
else:

    # -----------------------------------------------
    # 앱 상태 초기화
    # -----------------------------------------------
    init_app_state()


    # -----------------------------------------------
    # 사이드바
    # -----------------------------------------------
    render_sidebar()


    # -----------------------------------------------
    # 채팅 기록
    # -----------------------------------------------
    render_chat_history()


    # -----------------------------------------------
    # 입력창
    # -----------------------------------------------
    handle_user_input()


    # -----------------------------------------------
    # 맨 아래 위치
    # -----------------------------------------------
    st.markdown(
        '<div id="bottom-anchor"></div>',
        unsafe_allow_html=True
    )


    # ===================================================
    # 채팅방에 처음 들어왔을 때만
    # 마지막 대화 위치로 이동
    # ===================================================
    if st.session_state.get(
        "auto_scroll_to_bottom",
        False
    ):

        st.markdown(
            """
            <script>
                (() => {
                    const parentWindow = window.parent;
                    const parentDocument = parentWindow.document;

                    function goBottom() {

                        const target =
                            parentDocument.getElementById(
                                "bottom-anchor"
                            );

                        if (target) {

                            target.scrollIntoView({
                                behavior: "auto",
                                block: "end"
                            });

                            return;
                        }

                        parentWindow.scrollTo({
                            top:
                                parentDocument.documentElement.scrollHeight,
                            behavior: "auto"
                        });
                    }


                    // Streamlit 렌더가 끝나는 시점을 여러 번 잡음
                    requestAnimationFrame(() => {

                        goBottom();

                        requestAnimationFrame(() => {

                            goBottom();

                            setTimeout(
                                goBottom,
                                50
                            );

                            setTimeout(
                                goBottom,
                                150
                            );

                            setTimeout(
                                goBottom,
                                300
                            );
                        });
                    });

                })();
            </script>
            """,
            unsafe_allow_html=True
        )

        st.session_state.auto_scroll_to_bottom = False