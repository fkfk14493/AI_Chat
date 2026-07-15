import streamlit as st
from google import genai
from google.genai import types
import db_handler as db

# 데이터베이스 초기화 및 기존 대화 기록 불러오기
db.init_db()
if "messages" not in st.session_state:
    st.session_state.messages = db.load_chat()

# [수정] 브라우저 기본 레이아웃에서 불필요한 여백을 줄이고 깔끔하게 세팅
st.set_page_config(page_title="Chatting", layout="centered")

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

# 1. 스트림릿 Secrets 금고에서 안전하게 API 키 로드
if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# 2. 실행 시 DB에서 프롬프트 가져와서 세션에 얹기 (기본값 빈 문자열 설정으로 에러 차단!)
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = db.get_system_prompt("")

# 3. 제미나이 대화 세션 연결 (이중 중복 생성 방지 및 통합)
if "chat" not in st.session_state:
    history_contents = []
    for m in st.session_state.messages:
        # 🚨 [추가] 시스템 메시지(요약본)는 API 대화 히스토리에 직접 주입하지 않고 패스합니다!
        # (시스템 지침은 아래 GenerateContentConfig의 system_instruction으로만 들어가는 게 안전합니다.)
        if m["role"] == "system":
            continue
            
        role = "model" if m["role"] == "assistant" else "user"
        history_contents.append(
            types.Content(
                role=role, 
                parts=[types.Part.from_text(text=m["content"])]
            )
        )
        
    st.session_state.chat = st.session_state.client.chats.create(
        model="gemini-3.5-flash", # 3.5 Flash로 안전하게 빌드!
        history=history_contents if history_contents else None,
        config=types.GenerateContentConfig(
            system_instruction=st.session_state.system_prompt, # 🧠 DB에서 가져온 뇌 주입!
            temperature=0.95,
        )
    )
# ── [기존 출력 영역 교체] ──
# 웹 화면에 대화 기록만 순수하게 출력
for idx, msg in enumerate(st.session_state.messages):
    # role이 assistant일 때만 sogo.jpg 사진을 아이콘으로 지정
    avatar_image = "sogo.jpg" if msg["role"] == "assistant" else None
    
    # 🎯 [순간이동 포인트 심기] HTML div를 사용해 각 메시지에 고유 ID(번호표)를 부여합니다.
    st.markdown(f'<div id="message-{idx}"></div>', unsafe_allow_html=True)
    
    with st.chat_message(msg["role"], avatar=avatar_image):
        st.write(msg["content"])


# ==========================================
# 사용자 입력 및 명령어 처리 영역 (들여쓰기 및 모순 완벽 수정본)
# ==========================================
if user_input := st.chat_input("메시지를 입력하세요"):
    
    # ── [특수 기능 1] 사용자가 '/저장' 이라고 입력했을 때 ──
    if user_input.strip() == "/저장":
        with st.chat_message("assistant", avatar="sogo.jpg"):
            with st.spinner("지금까지의 소설 줄거리를 요약하는 중..."):
                summary_prompt = (
                    "지금까지 나눈 대화 기록을 바탕으로, "
                    "소설의 현재 상황과 줄거리를 5문장 이내의 깔끔한 시놉시스로 요약해줘."
                )
                summary_response = st.session_state.chat.send_message(summary_prompt)
                summary_text = summary_response.text
                
                db.save_summary(summary_text) # DB에 요약본 저장
                
                st.success("지금까지의 줄거리가 저장되었습니다.")
                st.info(f"**현재 줄거리 요약:**\n{summary_text}")
                
    # ── [특수 기능 2] 사용자가 '/되돌리기' 이라고 입력했을 때 ──
    elif user_input.strip() == "/되돌리기":
        if len(st.session_state.messages) >= 1:
            with st.spinner("대화방을 안전하게 동기화하는 중... "):
                
                # 🚨 [지능형 감지] 마지막 메시지가 유저(user)의 것인지, AI(model)의 것인지 판별합니다.
                last_msg_role = st.session_state.messages[-1]["role"]
                
                if last_msg_role == "user":
                    # 에러 상황: 답장 없이 내 질문만 덜렁 남은 경우 ➡️ 최근 "1개"만 삭제
                    remove_count = 1
                else:
                    # 정상 상황: 티키타카가 다 완료된 경우 ➡️ 최근 "2개(1턴)" 삭제
                    remove_count = 2

                # 1. 메모리(세션 상태)에서 판별된 개수만큼 삭제
                for _ in range(remove_count):
                    if st.session_state.messages:
                        st.session_state.messages.pop()
                
                # 2. 롤백된 기록 DB에 새로 덮어쓰기
                db.save_chat(st.session_state.messages)
                
                # 3. 🔥 제미나이 자체 세션 뇌 구조에서도 동일한 개수만큼 롤백
                if hasattr(st.session_state.chat, "history"):
                    if st.session_state.chat.history:
                        st.session_state.chat.history = st.session_state.chat.history[:-remove_count]
                
                if hasattr(st.session_state.chat, "_history"):
                    if st.session_state.chat._history:
                        st.session_state.chat._history = st.session_state.chat._history[:-remove_count]
                
            # 4. 새로고침으로 깔끔하게 지워진 화면 갱신
            if remove_count == 1:
                st.toast("삭제 되었습니다.")
            else:
                st.toast("직전 대화 1턴을 되돌렸습니다.")
                
            st.rerun()
        else:
            st.warning("되돌릴 대화 기록이 없습니다.")
                    
    # ── 일반 대화인 경우 (티키타카) ──
    else:
        # 1. 사용자가 입력한 메시지 화면에 그리기 및 저장
        with st.chat_message("user"):
            st.write(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        db.save_chat(st.session_state.messages)
        
        # 2. 답변 생성 및 출력 (아바타 장착 및 미니멀 스피너)
        with st.chat_message("assistant", avatar="sogo.jpg"):
            with st.spinner(""):
                response = st.session_state.chat.send_message(user_input)
                st.write(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                db.save_chat(st.session_state.messages)

        # ==========================================
        # 🔥 [새로 탑재된 치트키] 5턴 버퍼 슬라이딩 윈도우 자동 작동 영역
        # ==========================================
        # 메시지가 30개 (나의 대화 15개 + 상대 대화 15개 = 15턴) 쌓였을 때 백그라운드 메모리 정리 작동!
        if len(st.session_state.messages) >= 30:
            with st.spinner("예전 기억들을 줄거리로 알차게 요약하는 중..."):
                
                # A. 보존할 가장 생생한 최신 5턴 (메시지 10개) 분리
                keep_messages = st.session_state.messages[-10:]
                
                # B. 요약할 오래된 과거 10턴 (메시지 20개) 분리
                old_messages = st.session_state.messages[:-10]
                
                # C. 텍스트로 합쳐서 요약용 재료 만들기
                old_chat_text = ""
                for msg in old_messages:
                    role_name = "당신" if msg["role"] == "user" else "나"
                    old_chat_text += f"{role_name}: {msg['content']}\n"
                
                # D. 기존에 저장된 줄거리 요약본이 있다면 DB에서 긁어오기
                existing_summary = ""
                try:
                    # db_handler에 구현된 요약본 불러오기 함수 호출 (함수명이 다르면 맞춰서 수정)
                    existing_summary = db.load_summary() 
                except Exception:
                    existing_summary = ""
                
                # E. 제미나이 플래시를 시켜서 기존 요약본 + 새로 밀려난 10턴 누적 압축하기
                summary_prompt = f"""
                너는 소설의 줄거리를 기록하는 전문 서기다.
                [기존 줄거리]에 [새로 추가된 대화 기록]을 누적으로 반영하여, 전체 맥락과 인물들의 감정선이 자연스럽게 이어지도록 
                하나의 매끄럽고 콤팩트한 3~4줄짜리 시놉시스로 업데이트해라.
                
                [기존 줄거리]
                {existing_summary if existing_summary else "아직 이전 줄거리가 없습니다."}
                
                [새로 추가된 대화 기록 (과거 10턴)]
                {old_chat_text}
                """
                
                # 메인 챗봇의 대화 흐름을 방해하지 않게 조용히 새 API 호출로 요약만 따옵니다.
                summary_response = st.session_state.client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=summary_prompt
                )
                new_cumulative_summary = summary_response.text
                
                # F. 누적 압축된 줄거리를 DB에 안전하게 저장!
                db.save_summary(new_cumulative_summary)
                
                # G. 세션 메시지 리셋: 오직 [최신 5턴]만 화면에 남기기
                st.session_state.messages = keep_messages
                db.save_chat(keep_messages)
                
                # H. 제미나이 실제 뇌(API History)에도 요약본 컨텍스트와 최신 5턴만 주입해서 뇌세포 포맷
                new_history = []
                for msg in keep_messages:
                    role_name = "model" if msg["role"] == "assistant" else "user"
                    new_history.append(
                        types.Content(
                            role=role_name,
                            parts=[types.Part.from_text(text=msg["content"])]
                        )
                    )
                
                # 시스템 프롬프트 업데이트 (시스템 지침에 누적 줄거리를 강제로 얹어줍니다)
                updated_instruction = f"""
                {st.session_state.system_prompt}
                
                [우리가 지금까지 진행한 소설의 줄거리 요약]:
                {new_cumulative_summary}
                
                위의 줄거리를 머릿속에 완벽히 인지하고, 과거 설정을 기억하면서 아래 이어지는 대화에 자연스럽게 반응해라.
                """
                
                # 새 뇌(System Instruction)와 쌩쌩한 최신 5턴 히스토리로 챗 세션 재구축!
                st.session_state.chat = st.session_state.client.chats.create(
                    model="gemini-3.5-flash",
                    history=new_history,
                    config=types.GenerateContentConfig(
                        system_instruction=updated_instruction,
                        temperature=0.95
                    )
                )
                
            st.toast("5턴 슬라이딩 윈도우 가동! 오래된 대화가 줄거리 요약본으로 완벽하게 압축되었습니다.")
            st.rerun()


# ==========================================
# 사이드바 설정 (프롬프트 수정 + 초기화 기능)
# ==========================================
with st.sidebar:
    st.title("⚙️ 설정 및 관리")
    
    st.markdown("---")
    st.subheader("📝 프롬프트 설정")
    
    # [수정] 코드 내에 프롬프트 텍스트를 두지 않고, DB에서만 불러옵니다.
    # 만약 DB가 비어있다면 빈 값("")을 가져오며, 사용자가 사이드바에 입력한 값으로 최초 저장됩니다.
    if "system_prompt" not in st.session_state:
        st.session_state.system_prompt = db.get_system_prompt("") # db_handler 함수명 규격 통일

    # 3. 웹 화면에 실시간으로 수정 가능한 대형 텍스트 박스 배치
    user_prompt = st.text_area(
        "프롬프트를 수정하고 아래 [변경 적용]을 누르세요:",
        value=st.session_state.system_prompt,
        height=200
    )
    
    # 🎯 [실시간 글자 수 표시기 추가!]
    # 입력된 프롬프트의 길이를 구해서 바로 아래에 예쁘게 띄워줍니다.
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
    
    # # 4. 변경 적용 버튼 (수정본)
    if st.button("💾 프롬프트 변경 적용", use_container_width=True):
        st.session_state.system_prompt = user_prompt
        db.save_system_prompt(user_prompt) # db_handler 함수명 규격 통일
        
        # 1. 새 프롬프트로 제미나이 세션 새로 열기
        st.session_state.chat = st.session_state.client.chats.create(
            model="gemini-3.5-flash", # 모델 명 통일
            config=types.GenerateContentConfig(
                system_instruction=st.session_state.system_prompt
            )
        )
        
        # 2. ⭐️ [버전 에러 완벽 차단] 과거 대화 히스토리 주입하기
        if "messages" in st.session_state and st.session_state.messages:
            new_history = []
            for msg in st.session_state.messages:
                # 화면상의 'assistant' 역할을 제미나이 규격인 'model'로 변환하여 주입합니다.
                role_name = "model" if msg["role"] == "assistant" else "user"
                new_history.append(
                    types.Content(
                        role=role_name,
                        parts=[types.Part.from_text(text=msg["content"])]
                    )
                )
            
            # 제미나이 SDK 버전에 따라 history와 _history 양쪽 모두 안전하게 주입
            if hasattr(st.session_state.chat, "_history"):
                st.session_state.chat._history = new_history
            elif hasattr(st.session_state.chat, "history"):
                st.session_state.chat.history = new_history

        st.success("프롬프트가 변경되었습니다.")
        st.rerun()

    st.markdown("---")
    st.subheader("🛠️ 추가 편의 기능")

    # ==========================================
    # 1. 📥 TXT 파일 내보내기 (다운로드) 기능
    # ==========================================
    if st.session_state.messages:
        # 지금까지의 대화 배열을 하나의 기나긴 텍스트 문자열로 조립합니다.
        export_text = ""
        for msg in st.session_state.messages:
            role_name = "나" if msg["role"] == "user" else "상대"
            export_text += f"[{role_name}]\n{msg['content']}\n\n"
            
        # 스트림릿 자체 다운로드 버튼 기능을 이용해 폰/PC로 즉시 다운로드!
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

    if search_query:
        st.write(f"**'{search_query}' 검색 결과:**")
        found_any = False
        
        # 전체 대화 내역을 돌면서 키워드가 포함되어 있는지 샅샅이 뒤집니다.
        for idx, msg in enumerate(st.session_state.messages):
            if search_query.lower() in msg["content"].lower():
                found_any = True
                role_name = "나" if msg["role"] == "user" else "상대"
                
                # 검색된 대화 조각들을 보여줍니다.
                with st.expander(f"💬 [{role_name}]의 대화에서 발견"):
                    st.write(msg["content"])
                    
                    # [순간이동 치트키 버튼]
                    # HTML <a> 태그를 이용해 클릭 시 해당 메시지 ID 위치로 브라우저 스크롤을 이동시킵니다.
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
                        "해당 위치로 이동</a>
                        """,
                        unsafe_allow_html=True
                    )
        
        if not found_any:
            st.warning("검색 결과가 없습니다.")

    st.markdown("---")
    st.subheader("위험 구역")
    
    # 아까 만든 초기화 버튼은 이 아래에 그대로 둡니다.
    if st.button("대화 기록 초기화", type="primary", use_container_width=True):
        st.session_state.messages = []
        if hasattr(st.session_state.chat, "history"):
            st.session_state.chat.history = []
        elif hasattr(st.session_state.chat, "_history"):
            st.session_state.chat._history = []
        db.save_chat([])
        st.success("대화 기록이 완벽하게 초기화되었습니다!")
        st.rerun()