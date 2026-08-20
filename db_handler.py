import sqlite3
import json
import os

# 🎯 DB 절대 경로 설정
DB_FILE = "chat.db"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, DB_FILE)

# ==========================================
# 🛠️ [수정] init_db 함수 안의 테이블명도 chat_history로 변경!
# ==========================================
def init_db():
    """데이터베이스와 필요한 3대 테이블(config, token_usage, chat_history)을 강제 생성합니다."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1️⃣ config 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # 2️⃣ token_usage 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO token_usage (id, input_tokens, output_tokens) VALUES (1, 0, 0)")
    
    # 3️⃣ [🚨 이름 변경!] messages -> chat_history 테이블로 생성!
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

# ==========================================
# ⚙️ 시스템 프롬프트 관련 함수 (config 테이블 제어)
# ==========================================

def get_system_prompt(default_prompt=""):
    """DB에서 시스템 프롬프트를 안전하게 가져옵니다."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key = 'system_prompt'")
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0]
        else:
            # 기존에 값이 없으면 기본값으로 저장하고 반환
            save_system_prompt(default_prompt)
            return default_prompt
    except Exception:
        return default_prompt

def save_system_prompt(prompt_text):
    """DB에 시스템 프롬프트를 덮어씌워 영구 저장합니다."""
    init_db() # 테이블이 혹시나 없을 때를 대비해 강제 생성 실행
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO config (key, value)
        VALUES ('system_prompt', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (prompt_text,))
    conn.commit()
    conn.close()

# ==========================================
# 📊 토큰 사용량 관련 함수 (token_usage 테이블 제어)
# ==========================================

def load_tokens():
    """누적 토큰을 가져옵니다."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT input_tokens, output_tokens FROM token_usage WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0], row[1]
        return 0, 0
    except Exception:
        return 0, 0

def update_tokens(input_delta, output_delta):
    """누적 토큰 수치를 안전하게 갱신하고 누적치를 반환합니다."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE token_usage 
        SET input_tokens = input_tokens + ?, 
            output_tokens = output_tokens + ? 
        WHERE id = 1
    """, (input_delta, output_delta))
    conn.commit()
    
    # 반영 후 최신 데이터 다시 로드
    cursor.execute("SELECT input_tokens, output_tokens FROM token_usage WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0], row[1]
    return 0, 0

# ==========================================
# 💬 [🚨 이름 변경!] 대화 기록 관련 함수 (chat_history 테이블 제어)
# ==========================================

def save_chat(messages_list):
    """현재 세션의 대화 상태를 DB와 완전히 동기화합니다."""

    init_db()

    conn = sqlite3.connect(DB_PATH)

    try:
        cursor = conn.cursor()

        # 현재 DB 대화를 제거
        cursor.execute("DELETE FROM chat_history")

        # 현재 세션 상태만 다시 저장
        cursor.executemany(
            "INSERT INTO chat_history (role, content) VALUES (?, ?)",
            [
                (msg["role"], msg["content"])
                for msg in messages_list
            ]
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def save_message(role, content):
    """새로운 단일 대화 메시지를 DB에 저장합니다."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat_history (role, content) VALUES (?, ?)", (role, content))
    conn.commit()
    conn.close()


def load_messages():
    """DB에 저장된 모든 대화 기록을 순서대로 리스트로 가져옵니다."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT role, content FROM chat_history ORDER BY id ASC") # 👈 chat_history 조회!
        rows = cursor.fetchall()
        conn.close()
        return [{"role": r, "content": c} for r, c in rows]
    except Exception:
        return []


def clear_messages():
    """대화 기록을 싹 다 비웁니다."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_history") # 👈 chat_history 삭제!
        conn.commit()
        conn.close()
    except Exception:
        pass


# 프로필 사진 업데이트 관련
def save_avatar(image_bytes):
    """업로드된 프로필 이미지 바이너리를 DB에 저장합니다 (기존 이미지 덮어쓰기)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # 이미지를 저장할 테이블이 없으면 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value BLOB
            )
        """)
        # 기존 설정이 있으면 덮어쓰고 없으면 삽입
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('avatar', ?)",
            (image_bytes,)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"아바타 저장 실패: {e}")

def load_avatar():
    """DB에서 저장된 프로필 이미지 바이너리를 불러옵니다."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'avatar'")
        row = cursor.fetchone()
        conn.close()
        if row:
            return row[0]  # 이미지 바이너리 데이터 반환
        return None
    except Exception:
        return None
    
def save_summary(summary_text):
    """누적 줄거리 요약을 config 테이블에 저장합니다."""
    init_db()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO config (key, value)
            VALUES ('story_summary', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (summary_text,),
        )


def load_summary():
    """저장된 누적 줄거리 요약을 불러옵니다."""
    init_db()

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT value FROM config WHERE key = 'story_summary'"
        ).fetchone()

    return row[0] if row else ""


def reset_tokens():
    """누적 토큰 수치를 0으로 초기화합니다."""
    init_db()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE token_usage
        SET input_tokens = 0,
            output_tokens = 0
        WHERE id = 1
    """)

    conn.commit()
    conn.close()

# =======================================================
# 🌐 Supabase 멀티 채팅방 기능
# =======================================================

from datetime import datetime, timezone

import streamlit as st
from supabase import create_client


# =======================================================
# 🔌 Supabase 연결
# =======================================================

def get_supabase():
    """
    Streamlit Secrets에 저장된 Supabase 정보로 연결합니다.
    """

    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]

        return create_client(url, key)

    except Exception as e:
        raise Exception(f"Supabase 연결 실패: {e}")


# =======================================================
# 💬 채팅방 관련
# =======================================================

def create_room():
    """
    새 채팅방 생성

    현재 사용되지 않는 가장 작은 번호를 찾아
    채팅방 1, 채팅방 2 ... 형식으로 생성합니다.

    예:
    기존 채팅
    채팅방 3

    → 새로 만들면 '채팅방 1'
    """

    supabase = get_supabase()

    # 현재 모든 채팅방 제목 가져오기
    result = (
        supabase
        .table("chat_rooms")
        .select("title")
        .execute()
    )

    rooms = result.data or []

    # 현재 사용 중인 '채팅방 N' 번호 수집
    used_numbers = set()

    for room in rooms:
        title = room.get("title", "")

        if title.startswith("채팅방 "):
            try:
                number = int(title.replace("채팅방 ", "").strip())
                used_numbers.add(number)
            except ValueError:
                pass

    # 사용되지 않는 가장 작은 번호 찾기
    next_number = 1

    while next_number in used_numbers:
        next_number += 1

    title = f"채팅방 {next_number}"

    # 새 채팅방 생성
    result = (
        supabase
        .table("chat_rooms")
        .insert({
            "title": title
        })
        .execute()
    )

    if not result.data:
        raise Exception("채팅방 생성 실패")

    return result.data[0]["id"]


def get_rooms():
    """
    전체 채팅방 목록 불러오기

    최근 사용한 채팅방이 위에 표시됩니다.
    """

    supabase = get_supabase()

    result = (
        supabase
        .table("chat_rooms")
        .select("*")
        .order("updated_at", desc=True)
        .execute()
    )

    return result.data or []


def get_room(room_id):
    """
    특정 채팅방 정보 가져오기
    """

    supabase = get_supabase()

    result = (
        supabase
        .table("chat_rooms")
        .select("*")
        .eq("id", room_id)
        .limit(1)
        .execute()
    )

    if not result.data:
        return None

    return result.data[0]


def rename_room(room_id, new_title):
    """
    채팅방 제목 수정
    """

    new_title = new_title.strip()

    if not new_title:
        return

    supabase = get_supabase()

    supabase.table("chat_rooms").update({
        "title": new_title,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq(
        "id", room_id
    ).execute()


def delete_room(room_id):
    """
    채팅방 삭제

    Supabase에서 chat_messages의 room_id 외래키에
    ON DELETE CASCADE를 설정하면
    해당 채팅방의 메시지도 같이 삭제됩니다.
    """

    supabase = get_supabase()

    supabase.table("chat_rooms").delete().eq(
        "id", room_id
    ).execute()


# =======================================================
# 📨 채팅 메시지 관련
# =======================================================

def get_messages(room_id):
    """
    특정 채팅방의 메시지만 불러옵니다.

    반환 예:
    [
        {"role": "user", "content": "안녕"},
        {"role": "assistant", "content": "안녕하세요"}
    ]
    """

    supabase = get_supabase()

    result = (
        supabase
        .table("chat_messages")
        .select("role, content")
        .eq("room_id", room_id)
        .order("id")
        .execute()
    )

    return result.data or []


def add_message(room_id, role, content):
    """
    특정 채팅방에 메시지 하나 저장
    """

    supabase = get_supabase()

    # 메시지 저장
    supabase.table("chat_messages").insert({
        "room_id": room_id,
        "role": role,
        "content": content
    }).execute()

    # 해당 방을 최근 사용 목록 위로 올림
    supabase.table("chat_rooms").update({
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq(
        "id", room_id
    ).execute()


def clear_room_messages(room_id):
    """
    특정 채팅방의 대화 내용만 삭제
    채팅방 자체는 남겨둡니다.
    """

    supabase = get_supabase()

    supabase.table("chat_messages").delete().eq(
        "room_id", room_id
    ).execute()


def save_room_messages(room_id, messages):
    """
    해당 채팅방 메시지 전체를 다시 저장합니다.

    기존 네 코드의 save_chat(messages)와 비슷하게
    사용할 수 있도록 만든 호환용 함수입니다.
    """

    supabase = get_supabase()

    # 해당 방 메시지만 삭제
    supabase.table("chat_messages").delete().eq(
        "room_id", room_id
    ).execute()

    # 다시 저장
    rows = []

    for message in messages:
        rows.append({
            "room_id": room_id,
            "role": message["role"],
            "content": message["content"]
        })

    if rows:
        supabase.table("chat_messages").insert(rows).execute()

    # 최근 수정 시간 갱신
    supabase.table("chat_rooms").update({
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq(
        "id", room_id
    ).execute()

# =======================================================
# 🚚 기존 SQLite 채팅 → Supabase 이전
# =======================================================

def migrate_old_chat_to_supabase():
    """
    기존 SQLite의 채팅 + 프롬프트 + 프로필 이미지를
    Supabase의 '기존 채팅' 방으로 한 번만 복사합니다.

    기존 SQLite 데이터는 삭제하지 않습니다.
    """

    # =======================================================
    # 1. 기존 SQLite 채팅 불러오기
    # =======================================================
    old_messages = load_messages()

    if not old_messages:
        return {
            "success": False,
            "message": "기존 SQLite에 옮길 채팅이 없습니다."
        }


    supabase = get_supabase()


    # =======================================================
    # 2. 이미 '기존 채팅' 방이 있는지 확인
    # =======================================================
    existing = (
        supabase
        .table("chat_rooms")
        .select("id, title")
        .eq("title", "기존 채팅")
        .execute()
    )

    if existing.data:
        return {
            "success": False,
            "message": "이미 '기존 채팅' 방이 존재합니다."
        }


    # =======================================================
    # 3. 기존 SQLite 프롬프트 불러오기
    # =======================================================
    old_prompt = ""

    try:
        old_prompt = get_system_prompt("")
    except Exception:
        old_prompt = ""


    # =======================================================
    # 4. 기존 SQLite 프로필 사진 불러오기
    # =======================================================
    old_avatar = None

    try:
        old_avatar = load_avatar()
    except Exception:
        old_avatar = None


    # =======================================================
    # 5. 프로필 이미지를 base64 문자열로 변환
    # =======================================================
    avatar_data = None

    if old_avatar:
        try:
            import base64

            avatar_data = base64.b64encode(
                old_avatar
            ).decode("utf-8")

        except Exception:
            avatar_data = None


    # =======================================================
    # 6. '기존 채팅' 방 생성
    #    프롬프트 / 프로필도 같이 저장
    # =======================================================
    room_result = (
        supabase
        .table("chat_rooms")
        .insert({
            "title": "기존 채팅",
            "system_prompt": old_prompt,
            "avatar_data": avatar_data
        })
        .execute()
    )

    if not room_result.data:
        return {
            "success": False,
            "message": "기존 채팅방 생성에 실패했습니다."
        }


    room_id = room_result.data[0]["id"]


    # =======================================================
    # 7. 기존 메시지를 Supabase용으로 변환
    # =======================================================
    rows = []

    for msg in old_messages:

        role = msg.get("role")
        content = msg.get("content", "")

        if not role or not content:
            continue

        rows.append({
            "room_id": room_id,
            "role": role,
            "content": content
        })


    # =======================================================
    # 8. 유효한 메시지가 없으면 방 삭제
    # =======================================================
    if not rows:

        supabase.table("chat_rooms").delete().eq(
            "id",
            room_id
        ).execute()

        return {
            "success": False,
            "message": "이전할 유효한 메시지가 없습니다."
        }


    # =======================================================
    # 9. 메시지 전체 Supabase에 저장
    # =======================================================
    supabase.table("chat_messages").insert(
        rows
    ).execute()


    # =======================================================
    # 10. 실제 저장된 메시지 수 확인
    # =======================================================
    check = (
        supabase
        .table("chat_messages")
        .select("id")
        .eq("room_id", room_id)
        .execute()
    )

    saved_count = len(check.data or [])


    # =======================================================
    # 11. 완료
    # =======================================================
    return {
        "success": True,
        "room_id": room_id,
        "saved_count": saved_count,
        "prompt_migrated": bool(old_prompt),
        "avatar_migrated": bool(old_avatar),
        "message": (
            f"기존 채팅 {saved_count}개와 "
            f"프롬프트/프로필 설정을 이전했습니다."
        )
    }

# =======================================================
# 🎭 채팅방별 프롬프트 / 프로필
# =======================================================

import base64
from datetime import datetime, timezone


def get_room_settings(room_id):
    """
    현재 채팅방의 프롬프트와 프로필 사진을 불러옵니다.
    """

    supabase = get_supabase()

    result = (
        supabase
        .table("chat_rooms")
        .select("system_prompt, avatar_data")
        .eq("id", room_id)
        .limit(1)
        .execute()
    )

    if not result.data:
        return {
            "system_prompt": "",
            "avatar": None
        }

    room = result.data[0]

    avatar = None

    if room.get("avatar_data"):
        try:
            avatar = base64.b64decode(
                room["avatar_data"]
            )
        except Exception:
            avatar = None

    return {
        "system_prompt": room.get("system_prompt") or "",
        "avatar": avatar
    }


def save_room_prompt(room_id, prompt):
    """
    현재 채팅방에만 프롬프트 저장
    """

    supabase = get_supabase()

    supabase.table("chat_rooms").update({
        "system_prompt": prompt,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq(
        "id", room_id
    ).execute()


def save_room_avatar(room_id, avatar_bytes):
    """
    현재 채팅방에만 프로필 이미지 저장
    """

    supabase = get_supabase()

    if avatar_bytes is None:
        avatar_data = None
    else:
        avatar_data = base64.b64encode(
            avatar_bytes
        ).decode("utf-8")

    supabase.table("chat_rooms").update({
        "avatar_data": avatar_data,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq(
        "id", room_id
    ).execute()

    # =======================================================
# 🚚 기존 SQLite 설정 → Supabase 채팅방 설정 이전
# =======================================================

def migrate_old_settings_to_existing_room():
    """
    기존 SQLite의 값이 실제로 존재할 때만
    Supabase의 '기존 채팅' 방에 이전합니다.

    빈 문자열 / None / 0으로 기존 Supabase 값을
    덮어쓰지 않습니다.
    """

    supabase = get_supabase()

    # 기존 채팅방 찾기
    result = (
        supabase
        .table("chat_rooms")
        .select(
            "id, system_prompt, avatar_data, summary, "
            "input_tokens, output_tokens"
        )
        .eq("title", "기존 채팅")
        .limit(1)
        .execute()
    )

    if not result.data:
        return {
            "success": False,
            "message": "'기존 채팅' 방을 찾지 못했습니다."
        }

    room = result.data[0]
    room_id = room["id"]

    # -------------------------------------------------------
    # 기존 SQLite 값 읽기
    # -------------------------------------------------------
    try:
        old_prompt = get_system_prompt("")
    except Exception:
        old_prompt = ""

    try:
        old_avatar = load_avatar()
    except Exception:
        old_avatar = None

    try:
        old_summary = load_summary()
    except Exception:
        old_summary = ""

    try:
        old_input_tokens, old_output_tokens = load_tokens()
    except Exception:
        old_input_tokens = 0
        old_output_tokens = 0

    # -------------------------------------------------------
    # 실제 값이 존재하는 것만 업데이트
    # -------------------------------------------------------
    update_data = {}

    if old_prompt:
        update_data["system_prompt"] = old_prompt

    if old_avatar:
        update_data["avatar_data"] = base64.b64encode(
            old_avatar
        ).decode("utf-8")

    if old_summary:
        update_data["summary"] = old_summary

    # 둘 중 하나라도 실제 누적치가 있을 때만 이전
    if old_input_tokens > 0 or old_output_tokens > 0:
        update_data["input_tokens"] = old_input_tokens
        update_data["output_tokens"] = old_output_tokens

    if not update_data:
        return {
            "success": False,
            "message": (
                "현재 SQLite에서 이전할 기존 설정을 찾지 못했습니다. "
                "Supabase 값은 건드리지 않았습니다."
            )
        }

    update_data["updated_at"] = (
        datetime.now(timezone.utc).isoformat()
    )

    supabase.table("chat_rooms").update(
        update_data
    ).eq(
        "id",
        room_id
    ).execute()

    return {
        "success": True,
        "room_id": room_id,
        "message": "존재하는 기존 데이터만 안전하게 이전했습니다."
    }

# =======================================================
# 🧠 방별 장기 요약
# =======================================================

def load_room_summary(room_id):
    supabase = get_supabase()

    result = (
        supabase
        .table("chat_rooms")
        .select("summary")
        .eq("id", room_id)
        .limit(1)
        .execute()
    )

    if not result.data:
        return ""

    return result.data[0].get("summary") or ""


def save_room_summary(room_id, summary_text):
    supabase = get_supabase()

    supabase.table("chat_rooms").update({
        "summary": summary_text,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq(
        "id", room_id
    ).execute()


# =======================================================
# 📊 방별 토큰
# =======================================================

def load_room_tokens(room_id):
    supabase = get_supabase()

    result = (
        supabase
        .table("chat_rooms")
        .select("input_tokens, output_tokens")
        .eq("id", room_id)
        .limit(1)
        .execute()
    )

    if not result.data:
        return 0, 0

    room = result.data[0]

    return (
        room.get("input_tokens") or 0,
        room.get("output_tokens") or 0
    )


def update_room_tokens(room_id, input_delta, output_delta):
    """
    현재 방의 기존 누적값을 읽고 증가시킵니다.
    개인용 앱 기준으로 충분한 방식입니다.
    """

    current_input, current_output = load_room_tokens(room_id)

    new_input = current_input + input_delta
    new_output = current_output + output_delta

    supabase = get_supabase()

    supabase.table("chat_rooms").update({
        "input_tokens": new_input,
        "output_tokens": new_output,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq(
        "id", room_id
    ).execute()

    return new_input, new_output


def reset_room_tokens(room_id):
    supabase = get_supabase()

    supabase.table("chat_rooms").update({
        "input_tokens": 0,
        "output_tokens": 0,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq(
        "id", room_id
    ).execute()