import streamlit as st
import db_handler as db
from config import init_app_state
from sidebar import render_sidebar
from chat_room import render_chat_history, handle_user_input
import streamlit.components.v1 as components

from room_list import render_room_list


# =======================================================
# 0. 레이아웃 세팅
# =======================================================
st.set_page_config(
    page_title="Chatting",
    layout="centered"
)

st.markdown(
    '<div id="top-anchor"></div>',
    unsafe_allow_html=True
)

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
    </style>
    """,
    unsafe_allow_html=True
)


# =======================================================
# 1. DB 초기화
# =======================================================
try:
    db.init_db()

except Exception as e:
    st.error(
        f"❌ 데이터베이스 연동 실패: {e}"
    )


# =======================================================
# 2. 현재 들어가 있는 채팅방
# =======================================================
if "current_room_id" not in st.session_state:
    st.session_state.current_room_id = None


# =======================================================
# 3. 화면 분기
# =======================================================

# -------------------------------------------------------
# 채팅방을 선택하지 않은 상태
# -------------------------------------------------------
if st.session_state.current_room_id is None:

    render_room_list()


# -------------------------------------------------------
# 채팅방에 들어간 상태
# -------------------------------------------------------
else:

    # ===================================================
    # 채팅방 처음 들어올 때
    # 렌더링 중인 화면을 잠깐 숨김
    # ===================================================
    if st.session_state.get(
        "auto_scroll_to_bottom",
        False
    ):

        components.html(
            """
            <script>
                const doc = window.parent.document;

                const main =
                    doc.querySelector(
                        '[data-testid="stMain"]'
                    )
                    ||
                    doc.querySelector(
                        'section.main'
                    )
                    ||
                    doc.querySelector(
                        '.main'
                    );

                if (main) {
                    main.style.opacity = "0";
                    main.style.pointerEvents = "none";
                }
            </script>
            """,
            height=0
        )


    # ===================================================
    # 기존 세션 초기화
    # ===================================================
    init_app_state()


    # ===================================================
    # 사이드바
    # ===================================================
    render_sidebar()


    # ===================================================
    # 채팅 화면
    # ===================================================
    render_chat_history()

    handle_user_input()


    # ===================================================
    # 페이지 최하단 앵커
    # ===================================================
    st.markdown(
        '<div id="bottom-anchor"></div>',
        unsafe_allow_html=True
    )


    # ===================================================
    # 채팅방 입장 시
    # 모든 메시지가 그려진 뒤 최하단 고정
    # ===================================================
    if st.session_state.get(
        "auto_scroll_to_bottom",
        False
    ):

        components.html(
            """
            <script>
                const doc = window.parent.document;

                const main =
                    doc.querySelector(
                        '[data-testid="stMain"]'
                    )
                    ||
                    doc.querySelector(
                        'section.main'
                    )
                    ||
                    doc.querySelector(
                        '.main'
                    );

                const app =
                    doc.querySelector(
                        '[data-testid="stAppViewContainer"]'
                    );

                const scrolling =
                    doc.scrollingElement
                    ||
                    doc.documentElement;


                // ==========================================
                // 부드러운 스크롤 완전 비활성화
                // ==========================================
                if (scrolling) {
                    scrolling.style.scrollBehavior = "auto";
                }

                if (main) {
                    main.style.scrollBehavior = "auto";
                }

                if (app) {
                    app.style.scrollBehavior = "auto";
                }


                // ==========================================
                // Streamlit 렌더링 완료될 때까지
                // 계속 맨 아래로 고정
                // ==========================================
                let count = 0;


                function forceBottom() {

                    if (scrolling) {
                        scrolling.scrollTop =
                            scrolling.scrollHeight;
                    }

                    if (main) {
                        main.scrollTop =
                            main.scrollHeight;
                    }

                    if (app) {
                        app.scrollTop =
                            app.scrollHeight;
                    }

                    window.parent.scrollTo(
                        0,
                        doc.body.scrollHeight
                    );


                    count++;


                    // 약 35프레임 동안 계속 하단 고정
                    if (count < 35) {

                        requestAnimationFrame(
                            forceBottom
                        );

                    } else {

                        // ==================================
                        // 렌더링 끝난 후
                        // 맨 아래에서 화면 표시
                        // ==================================
                        if (main) {
                            main.style.opacity = "1";
                            main.style.pointerEvents = "auto";
                        }
                    }
                }


                requestAnimationFrame(
                    forceBottom
                );

            </script>
            """,
            height=0
        )


        # 이번 채팅방 입장 자동스크롤 완료
        st.session_state.auto_scroll_to_bottom = False