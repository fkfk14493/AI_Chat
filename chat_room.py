#chat_room.py
import streamlit as st
from google.genai import types
from google.genai import errors  # 🚨 구글 SDK 전용 에러 처리를 위해 임포트!
import db_handler as db  # 형씨의 원래 DB 핸들러 파일 호출
import os
import sqlite3
import io

def render_chat_history():
    """웹 화면에 대화 기록만 순수하게 출력 (중복 출력 원천 차단)"""
    rendered_keys = set()

    for idx, msg in enumerate(st.session_state.messages):
        # 역할(role)과 대화 내용(content)을 하나로 묶어 고유한 키(Key)로 만듭니다.
        msg_key = (msg["role"], msg.get("content", ""))
        
        # 🚨 이미 화면에 그린 적이 있는 메시지라면 가차 없이 패스합니다! (2배 출력 원천 차단)
        if msg_key in rendered_keys:
            continue
        rendered_keys.add(msg_key)
        
        avatar_image = None
        if msg["role"] == "assistant":
            if "custom_avatar" in st.session_state and st.session_state.custom_avatar is not None:
                # 🚨 생 바이트 데이터를 스트림릿용 이미지 객체로 변환!
                avatar_image = io.BytesIO(st.session_state.custom_avatar)
            else:
                avatar_image = "🤖"
        
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
                                    # 🚨 구글 전용 429 / 403 / 503 에러 철벽 감지 및 우회
                                    is_quota_error = False
                                    if isinstance(e, errors.ClientError) or isinstance(e, errors.ServerError):
                                        if e.code in [429, 403, 503]:
                                            is_quota_error = True
                                    
                                    if is_quota_error or any(kw in str(e).upper() for kw in ["EXHAUSTED", "QUOTA", "LIMIT", "429"]):
                                        st.toast("3.5 모델 한도 도달! 3.1 Flash로 우회합니다.")
                                        
                                        # 🛡️ get_history() 안전하게 호출하도록 방어막 세팅!
                                        chat_history = (
                                            st.session_state.chat.get_history() 
                                            if hasattr(st.session_state.chat, "get_history") 
                                            else None
                                        )
                                        
                                        st.session_state.chat = st.session_state.client.chats.create(
                                            model="gemini-3.1-flash-lite", 
                                            history=chat_history, 
                                            config=types.GenerateContentConfig(
                                                system_instruction=st.session_state.system_prompt,
                                                temperature=0.95
                                            )
                                        )
                                        response = st.session_state.chat.send_message(edited_text)
                                        response_text = response.text
                                
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
                    refined_text = st.text_area("수정 내용:", value=msg["content"], key=f"refine_{idx}", height=150)
                    
                    if st.button("확인", key=f"btn_refine_{idx}", use_container_width=True):
                        if refined_text.strip() and refined_text.strip() != msg["content"]:
                            st.session_state.messages[idx]["content"] = refined_text
                            
                            if hasattr(st.session_state.chat, "history") and st.session_state.chat.history:
                                st.session_state.chat.history[-1].parts[0].text = refined_text
                            
                            if hasattr(st.session_state.chat, "_history") and st.session_state.chat._history:
                                st.session_state.chat._history[-1].parts[0].text = refined_text
                            
                            db.save_chat(st.session_state.messages)
                            st.toast("수정이 완료되었습니다.")
                            st.rerun()

def handle_user_input():
    """[4단계] 사용자 입력창 및 통합 대화 처리 구역 (UI 즉시 반영 및 429 우회 통합)"""
    if user_input := st.chat_input("메시지를 입력하세요..."):
        
        # ── [특수 기능 1] 사용자가 '/저장' 이라고 입력했을 때 ──
        if user_input.strip() == "/저장":
            # 📸 실시간 커스텀 프로필 동기화 (없으면 기본 "🤖" 아이콘 사용)
            if st.session_state.get("custom_avatar") is not None:
                tgt_avatar = io.BytesIO(st.session_state["custom_avatar"])
            else:
                tgt_avatar = "🤖"
            
            with st.chat_message("assistant", avatar=tgt_avatar):
                with st.spinner("지금까지의 소설 줄거리를 요약하는 중..."):
                    summary_prompt = (
                        "지금까지 나눈 대화 기록을 바탕으로, "
                        "소설의 현재 상황과 줄거리를 5문장 이내의 깔끔한 시놉시스로 요약해줘."
                    )
                    summary_response = st.session_state.chat.send_message(summary_prompt)
                    summary_text = summary_response.text
                    
                    db.save_summary(summary_text)  # DB에 요약본 저장
                    
                    st.success("지금까지의 줄거리가 저장되었습니다.")
                    st.info(f"**현재 줄거리 요약:**\n{summary_text}")
                    
        # ── [특수 기능 2] 사용자가 '/되돌리기' 이라고 입력했을 때 ──
        elif user_input.strip() == "/되돌리기":
            if len(st.session_state.messages) >= 1:
                with st.spinner("대화방을 동기화하는 중... "):
                    last_msg_role = st.session_state.messages[-1]["role"]
                    remove_count = 1 if last_msg_role == "user" else 2

                    for _ in range(remove_count):
                        if st.session_state.messages:
                            st.session_state.messages.pop()
                    
                    db.save_chat(st.session_state.messages)
                    
                    if hasattr(st.session_state.chat, "history") and st.session_state.chat.history:
                        st.session_state.chat.history = st.session_state.chat.history[:-remove_count]
                    
                    if hasattr(st.session_state.chat, "_history") and st.session_state.chat._history:
                        st.session_state.chat._history = st.session_state.chat._history[:-remove_count]
                    
                if remove_count == 1:
                    st.toast("삭제 되었습니다.")
                else:
                    st.toast("직전 대화 1턴을 되돌렸습니다.")
                st.rerun()
            else:
                st.warning("되돌릴 대화 기록이 없습니다.")
                
        # ── [일반 대화] 특수 명령어가 아닌 일반 티키타카일 때 ──
        else:
            # 1. 🚨 [UI 즉시 반영] 내 질문을 세션에 넣고 화면에 "즉시" 그려서 답답함 해소!
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.write(user_input)
            
            # 📸 실시간 커스텀 프로필 동기화 (없으면 기본 "🤖" 아이콘 사용)
            if st.session_state.get("custom_avatar") is not None:
                tgt_avatar = io.BytesIO(st.session_state["custom_avatar"])
            else:
                tgt_avatar = "🤖"
            
            # 2. 🚨 [로딩 연출] 대답 대기 및 429 / 403 / 503 완벽 대응 우회막 (커스텀 아바타 반영)
            with st.chat_message("assistant", avatar=tgt_avatar):
                with st.spinner("답장 하는 중..."):
                    try:
                        # [시도 1] 3.5 Flash로 대화 시도
                        response = st.session_state.chat.send_message(user_input)
                        response_text = response.text
                        
                        if response.usage_metadata:
                            st.session_state.total_input_tokens += response.usage_metadata.prompt_token_count
                            st.session_state.total_output_tokens += response.usage_metadata.candidates_token_count
                            db.update_tokens(st.session_state.total_input_tokens, st.session_state.total_output_tokens)
                        
                    except Exception as e:
                        # 🚨 구글 SDK 전용 에러 판별해서 한도(429/403) 초과 시 우회 작동!
                        is_quota_error = False
                        if isinstance(e, errors.ClientError) or isinstance(e, errors.ServerError):
                            if e.code in [429, 403, 503]:
                                is_quota_error = True
                        
                        if is_quota_error or any(kw in str(e).upper() for kw in ["EXHAUSTED", "QUOTA", "LIMIT", "429"]):
                            st.toast("3.5 모델 한도 도달! 즉시 3.1 Flash로 우회합니다.")
                            
                            st.session_state.chat = st.session_state.client.chats.create(
                                model="gemini-3.1-flash-lite", 
                                history=st.session_state.chat.get_history(), 
                                config=types.GenerateContentConfig(
                                    system_instruction=st.session_state.system_prompt,
                                    temperature=0.95
                                )
                            )
                            
                            # [시도 2] 즉시 재요청!
                            response = st.session_state.chat.send_message(user_input)
                            response_text = response.text
                            
                            if response.usage_metadata:
                                st.session_state.total_input_tokens += response.usage_metadata.prompt_token_count
                                st.session_state.total_output_tokens += response.usage_metadata.candidates_token_count
                                db.update_tokens(st.session_state.total_input_tokens, st.session_state.total_output_tokens)
                        else:
                            raise e
            
            # 3. AI의 새 답변도 세션(메모리)에 최종 추가
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            
            # 🚨 제미나이 뇌세포 실제 히스토리 멱살 잡고 동기화 강제 매핑
            if hasattr(st.session_state.chat, "history"):
                new_history = []
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
                st.session_state.chat.history = new_history
            
            # 4. DB에 현재 대화 기록을 통째로 딱 한 번만 저장!
            db.save_chat(st.session_state.messages)

            # ==========================================
            # 🔥 10턴 버퍼 슬라이딩 윈도우 자동 작동 영역 (기억 보정 완료!)
            # ==========================================
            if len(st.session_state.messages) >= 40:
                with st.spinner("예전 기억들을 요약하는 중..."):
                    keep_messages = st.session_state.messages[-20:]
                    old_messages = st.session_state.messages[:-20]
                    
                    old_chat_text = ""
                    for msg in old_messages:
                        role_name = "당신" if msg["role"] == "user" else "나"
                        old_chat_text += f"{role_name}: {msg['content']}\n"
                    
                    existing_summary = ""
                    try:
                        existing_summary = db.load_summary() 
                    except Exception:
                        existing_summary = ""
                    
                    summary_prompt = f"""
                    너는 소설의 줄거리를 기록하는 전문 서기다.
                    [기존 줄거리]에 [새로 추가된 대화 기록]을 누적으로 반영하여, 전체 맥락과 인물들의 감정선이 자연스럽게 이어지도록 
                    하나의 매끄럽고 콤팩트한 3~4줄짜리 시놉시스로 업데이트해라.
                    
                    [기존 줄거리]
                    {existing_summary if existing_summary else "아직 이전 줄거리가 없습니다."}
                    
                    [새로 추가된 대화 기록 (과거 10턴)]
                    {old_chat_text}
                    """
                    
                    summary_response = st.session_state.client.models.generate_content(
                        model="gemini-3.5-flash",
                        contents=summary_prompt
                    )
                    new_cumulative_summary = summary_response.text
                    
                    db.save_summary(new_cumulative_summary)
                    
                    st.session_state.messages = list(keep_messages)
                    db.save_chat(keep_messages)
                    
                    new_history = []
                    for msg in keep_messages:
                        role_name = "model" if msg["role"] == "assistant" else "user"
                        new_history.append(
                            types.Content(
                                role=role_name,
                                parts=[types.Part.from_text(text=msg["content"])]
                            )
                        )
                    
                    updated_instruction = f"""
                    {st.session_state.system_prompt}
                    
                    [우리가 지금까지 진행한 소설의 줄거리 요약]:
                    {new_cumulative_summary}
                    
                    위의 줄거리를 머릿속에 완벽히 인지하고, 과거 설정을 기억하면서 아래 이어지는 대화에 자연스럽게 반응해라.
                    """
                    
                    st.session_state.chat = st.session_state.client.chats.create(
                        model="gemini-3.5-flash",
                        history=new_history,
                        config=types.GenerateContentConfig(
                            system_instruction=updated_instruction,
                            temperature=0.95
                        )
                    )
                    
                st.toast("10턴 기억 최적화 완료!")
            
            st.rerun()