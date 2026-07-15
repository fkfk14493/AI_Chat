import streamlit as st
from google import genai
from google.genai import types
import db_handler as db

# 🚨 [임시 해결 치트키] 기존 DB 살리기용 코드 (한 번 실행 후 지울 것!)
import sqlite3
try:
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    # 기존 DB에 토큰 저장용 테이블이 없으면 생성합니다.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO token_usage (id, input_tokens, output_tokens) VALUES (1, 0, 0)")
    conn.commit()
    conn.close()
    st.toast("✅ 기존 대화 기록을 안전하게 보호하고 토큰 공간을 생성했습니다!")
except Exception as e:
    st.error(f"임시 복구 중 오류 발생: {e}")

# 🚨 [여기 중요!] 1. DB와 테이블을 먼저 확실하게 생성/초기화합니다!
db.init_db()

# 📊 2. 그 다음, 안전하게 기존 토큰 사용량을 불러옵니다.
db_input, db_output = db.load_tokens()

# 3. 세션 상태(Session State)에 값 주입
if "total_input_tokens" not in st.session_state:
    st.session_state.total_input_tokens = db_input
if "total_output_tokens" not in st.session_state:
    st.session_state.total_output_tokens = db_output

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

# 3. 제미나이 대화 세션 연결 (이중 중복 생성 방지 및 자동 백업 우회 적용)
if "chat" not in st.session_state:
    history_contents = []
    for m in st.session_state.messages:
        # 시스템 메시지(요약본)는 API 대화 히스토리에 직접 주입하지 않고 패스합니다.
        if m["role"] == "system":
            continue
            
        role = "model" if m["role"] == "assistant" else "user"
        history_contents.append(
            types.Content(
                role=role, 
                parts=[types.Part.from_text(text=m["content"])]
            )
        )
        
    # 🔥 [핵심 백업 로직] 3.5가 터지면 자동 대피합니다.
    try:
        # 1. 일단 똑똑하고 빠른 3.5 Flash로 접속 시도!
        st.session_state.chat = st.session_state.client.chats.create(
            model="gemini-3.5-flash",
            history=history_contents if history_contents else None,
            config=types.GenerateContentConfig(
                system_instruction=st.session_state.system_prompt,
                temperature=0.95,
            )
        )
    except Exception as e:
        # 2. 만약 구글 서버 과부하(503, UNAVAILABLE 등) 에러가 발생하면?
        error_msg = str(e)
        if "503" in error_msg or "UNAVAILABLE" in error_msg or "high demand" in error_msg:
            # 즉시 2.5 Flash로 우회해서 재시도!
            st.session_state.chat = st.session_state.client.chats.create(
                model="gemini-3.1-flash-lite",  # 안정성 끝판왕 우회로
                history=history_contents if history_contents else None,
                config=types.GenerateContentConfig(
                    system_instruction=st.session_state.system_prompt,
                    temperature=0.95,
                )
            )
            # 화면 우측 하단에 조용히 대피 완료 알림을 띄워줍니다.
            st.toast("3.5 모델 혼잡으로 인해 3.1 Flash-lite 모델로 임시 우회 연결되었습니다.")
        else:
            # 503 이외의 다른 심각한 에러라면 사용자에게 에러를 그대로 보여줍니다.
            raise e

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
        # 🟢 [내 질문 수정 영역] 
        # 내 마지막 질문 말풍선 아래에만 노출 (재전송 및 과거 개편)
        # ==========================================
        if msg["role"] == "user" and idx == len(st.session_state.messages) - 2:
            with st.popover("다시 보내기"):
                edited_text = st.text_area("내용을 입력하세요:", value=msg["content"], key=f"edit_user_{idx}")
                
                if st.button("확인", key=f"btn_user_{idx}", use_container_width=True):
                    if edited_text.strip() and edited_text.strip() != msg["content"]:
                        with st.spinner("수정 중..."):
                            st.session_state.messages.pop()
                            st.session_state.messages.pop()
                            
                            if hasattr(st.session_state.chat, "history") and st.session_state.chat.history:
                                st.session_state.chat.history = st.session_state.chat.history[:-2]
                            if hasattr(st.session_state.chat, "_history") and st.session_state.chat._history:
                                st.session_state.chat._history = st.session_state.chat._history[:-2]
                            
                            st.session_state.messages.append({"role": "user", "content": edited_text})
                            db.save_chat(st.session_state.messages)
                            
                            try:
                                response = st.session_state.chat.send_message(edited_text)
                                response_text = response.text
                                if response.usage_metadata:
                                    st.session_state.total_input_tokens += response.usage_metadata.prompt_token_count
                                    st.session_state.total_output_tokens += response.usage_metadata.candidates_token_count
                                    db.update_tokens(st.session_state.total_input_tokens, st.session_state.total_output_tokens)
                                    
                            except Exception as e:
                                error_msg = str(e)
                                if "503" in error_msg or "UNAVAILABLE" in error_msg or "high demand" in error_msg:
                                    st.toast("3.5 모델 혼잡 감지! 3.1 Flash로 우회합니다.")
                                    st.session_state.chat = st.session_state.client.chats.create(
                                        model="gemini-3.1-flash-lite", 
                                        history=st.session_state.chat.get_history(), 
                                        config=types.GenerateContentConfig(
                                            system_instruction=st.session_state.system_prompt,
                                            temperature=0.95
                                        )
                                    )
                                    response = st.session_state.chat.send_message(edited_text)
                                    response_text = response.text
                                    if response.usage_metadata:
                                        st.session_state.total_input_tokens += response.usage_metadata.prompt_token_count
                                        st.session_state.total_output_tokens += response.usage_metadata.candidates_token_count
                                        db.update_tokens(st.session_state.total_input_tokens, st.session_state.total_output_tokens)
                                else:
                                    raise e
                            
                            st.session_state.messages.append({"role": "assistant", "content": response_text})
                            db.save_chat(st.session_state.messages)
                            st.toast("마지막 대화가 수정 및 갱신되었습니다!")
                            st.rerun()

        # ==========================================
        # 🔴 [신규 추가: 대답 다듬기 영역] 
        # 마지막 대답 말풍선 아래에만 노출 (서버 요청 없이 텍스트만 다듬기)
        # ==========================================
        elif msg["role"] == "assistant" and idx == len(st.session_state.messages) - 1:
            with st.popover("수정하기"):
                # 현재 소고가 뱉은 대사를 텍스트 영역에 띄워줍니다.
                refined_text = st.text_area("수정 내용:", value=msg["content"], key=f"refine_sogo_{idx}", height=150)
                
                if st.button("확인", key=f"btn_refine_{idx}", use_container_width=True):
                    if refined_text.strip() and refined_text.strip() != msg["content"]:
                        # 1️⃣ 세션 메모리에서 기존 소고 대답 갈아끼우기
                        st.session_state.messages[idx]["content"] = refined_text
                        
                        # 2️⃣ 제미나이 뇌세포(history) 내부의 대화 기록도 강제로 수정하기
                        if hasattr(st.session_state.chat, "history") and st.session_state.chat.history:
                            # 제미나이의 마지막 내역(model 역할)의 텍스트 파트를 수정한 텍스트로 치환합니다.
                            st.session_state.chat.history[-1].parts[0].text = refined_text
                        
                        if hasattr(st.session_state.chat, "_history") and st.session_state.chat._history:
                            st.session_state.chat._history[-1].parts[0].text = refined_text
                        
                        # 3️⃣ 동기화된 완벽한 대화 데이터를 DB에 최종 저장
                        db.save_chat(st.session_state.messages)
                        
                        st.toast("수정이 완료되었습니다.")
                        st.rerun()


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
        
        # 2. 답변 생성 및 출력
        with st.chat_message("assistant", avatar="sogo.jpg"):
            with st.spinner(""):
                try:
                    # [시도 1] 3.5 Flash로 대화 시도
                    response = st.session_state.chat.send_message(user_input)
                    response_text = response.text
                    
                    # 📊 [추가] 성공 시 실제 사용된 구글 공식 토큰 수치 가로채기!
                    if response.usage_metadata:
                        st.session_state.total_input_tokens += response.usage_metadata.prompt_token_count
                        st.session_state.total_output_tokens += response.usage_metadata.candidates_token_count

                        # 1) 대화가 무사히 끝나고 토큰이 누적되는 지점들 뒤에 아래 코드 한 줄씩 끼워넣기!
                        db.update_tokens(st.session_state.total_input_tokens, st.session_state.total_output_tokens)
                    
                except Exception as e:
                    error_msg = str(e)
                    if "503" in error_msg or "UNAVAILABLE" in error_msg or "high demand" in error_msg:
                        st.toast("3.5 모델 혼잡 감지! 3.1 Flash로 우회합니다.")
                        
                        st.session_state.chat = st.session_state.client.chats.create(
                            model="gemini-3.1-flash-lite", 
                            history=st.session_state.chat.get_history(), 
                            config=types.GenerateContentConfig(
                                system_instruction=st.session_state.system_prompt,
                                temperature=0.95
                            )
                        )
                        
                        # [시도 2] 이식된 3.1 뇌세포로 즉시 재요청!
                        response = st.session_state.chat.send_message(user_input)
                        response_text = response.text
                        
                        # 📊 [추가] 대피 성공 시에도 실제 사용된 토큰 수 가로채기!
                        if response.usage_metadata:
                            st.session_state.total_input_tokens += response.usage_metadata.prompt_token_count
                            st.session_state.total_output_tokens += response.usage_metadata.candidates_token_count
                    else:
                        raise e
                
                # 최종 답변 화면 출력 및 저장
                st.write(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
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
        
        # 🚨 [수정 완료] 이제 for문과 하위 코드들이 if문 내부(스페이스 8칸 위치)로 올바르게 정렬되었습니다.
        for idx, msg in enumerate(st.session_state.messages):
            if search_query.lower() in msg["content"].lower():
                found_any = True
                role_name = "나" if msg["role"] == "user" else "상대"
                
                # 검색된 대화 조각들을 보여줍니다.
                with st.expander(f"💬 [{role_name}]의 대화에서 발견"):
                    st.write(msg["content"])

                    # [순간이동 치트키 버튼]
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

    st.divider() # 얇은 가로선 하나 그어주기

    st.subheader("📊 실시간 토큰 계기판")
    
    # 2열로 나누어서 깔끔하게 지표 표시 (스트림릿 레이아웃)
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label="입력 토큰 (누적)", 
            value=f"{st.session_state.total_input_tokens:,}", 
            help="내가 보낸 질문과 과거 기억을 합친 글자 수입니다."
        )
    with col2:
        st.metric(
            label="출력 토큰 (누적)", 
            value=f"{st.session_state.total_output_tokens:,}", 
            help="AI가 나에게 뱉어낸 장문 소설 대사의 글자 수입니다."
        )
        
    # 대략적인 예상 요금 계산 (Flash 기준 100만 토큰당 약 $0.075 / $0.30)
    estimated_cost = (st.session_state.total_input_tokens * 0.000000075) + (st.session_state.total_output_tokens * 0.00000030)
    st.caption(f"💰 현재 세션 예상 요금: 약 {estimated_cost * 1350:.2f}원")

    # 🔥 [새로 추가된 토큰 리셋 버튼]
    if st.button("🧹 토큰 집계 초기화", use_container_width=True):
        st.session_state.total_input_tokens = 0
        st.session_state.total_output_tokens = 0
        st.toast("누적 토큰 집계가 0으로 초기화되었습니다.")
        st.rerun() # 화면을 즉시 새로고침해서 0으로 바뀐 지표를 보여줍니다.

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