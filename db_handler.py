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
    """app.py의 형식(st.session_state.messages)을 받아와서 DB 테이블을 싹 비우고 완전히 새로 갱신합니다."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 🚨 테이블명을 chat_history로 맞춰서 비우고 저장합니다!
    cursor.execute("DELETE FROM chat_history")
    
    for msg in messages_list:
        cursor.execute("INSERT INTO chat_history (role, content) VALUES (?, ?)", (msg["role"], msg["content"]))
        
    conn.commit()
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