import sqlite3
import json

# 🎯 모든 데이터베이스 파일명을 'chat.db'로 단일화합니다!
DB_FILE = "chat.db"

# ==========================================
# 1. 🗄️ 데이터베이스 및 모든 테이블 통합 초기화
# ==========================================
def init_db():
    """챗봇 운영에 필요한 모든 테이블을 'chat.db' 안에 원샷으로 생성합니다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # [A] 대화 기록 테이블 (JSON 문자열 통째로 저장)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            messages TEXT
        )
    ''')
    
    # [B] 줄거리 요약 저장 테이블 (슬라이딩 윈도우 및 /저장 용)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS story_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # [C] 설정값 보관 전용 테이블 (시스템 프롬프트 영구 저장용)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    conn.commit()
    conn.close()


# ==========================================
# 2. 💬 대화 기록 (Messages) 제어 함수
# ==========================================
def save_chat(messages):
    """현재까지의 대화 배열을 JSON으로 말아서 DB에 덮어씁니다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM chat_history")
    json_messages = json.dumps(messages, ensure_ascii=False)
    cursor.execute("INSERT INTO chat_history (messages) VALUES (?)", (json_messages,))
    
    conn.commit()
    conn.close()

def load_chat():
    """DB에서 가장 최신의 대화 기록을 역직렬화하여 불러옵니다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT messages FROM chat_history ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return json.loads(row[0])
    return []


# ==========================================
# 3. 📝 줄거리 요약 (Summary) 제어 함수
# ==========================================
def save_summary(summary_text):
    """요약된 줄거리를 DB에 한 줄씩 새로 누적하여 저장합니다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO story_summary (summary) VALUES (?)", (summary_text,))
    conn.commit()
    conn.close()

def load_summary():
    """가장 최신화된 하나의 줄거리 요약본을 불러옵니다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT summary FROM story_summary ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "저장된 줄거리가 없습니다."


# ==========================================
# 4. ⚙️ 프롬프트 설정 (System Prompt) 제어 함수
# ==========================================
def save_system_prompt(prompt_text):
    """수정된 시스템 프롬프트를 DB config 테이블에 영구 저장 및 업데이트합니다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO config (key, value) 
        VALUES ('system_prompt', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (prompt_text,))
    conn.commit()
    conn.close()

def get_system_prompt(default_prompt):
    """DB에서 시스템 프롬프트를 가져오고, 없으면 기본값(default_prompt)으로 세팅합니다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 만약 config 테이블이 작동하지 않는 예외 상황 방어용 예외처리
    try:
        cursor.execute("SELECT value FROM config WHERE key = 'system_prompt'")
        row = cursor.fetchone()
        if row:
            conn.close()
            return row[0]
    except sqlite3.OperationalError:
        pass
        
    # 최초 실행 등의 이유로 DB에 프롬프트가 저장된 적이 없다면 기본값 저장 후 반환
    conn.close()
    save_system_prompt(default_prompt)
    return default_prompt


# [DB 초기화 시 테이블 생성 영역에 추가]
def init_db():
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    # ... 기존 대화 저장 테이블 생성 코드 ...
    
    # 📊 토큰 저장용 테이블 추가 (없으면 생성)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0
        )
    """)
    # 기본값 행 1개 삽입 (최초 1회만)
    cursor.execute("INSERT OR IGNORE INTO token_usage (id, input_tokens, output_tokens) VALUES (1, 0, 0)")

    # 🚨 2. [여기에 추가!] 토큰 테이블이 없으면 만들어줍니다.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0
        )
    """)
    
    # 🚨 3. [여기에 추가!] 기본값 행 1개 삽입 (id가 1인 행이 이미 없으면 기본 0, 0으로 생성)
    cursor.execute("INSERT OR IGNORE INTO token_usage (id, input_tokens, output_tokens) VALUES (1, 0, 0)")
    
    conn.commit()
    conn.close()

# 📊 토큰 사용량 업데이트 함수
def update_tokens(input_tokens, output_tokens):
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE token_usage 
        SET input_tokens = ?, output_tokens = ? 
        WHERE id = 1
    """, (input_tokens, output_tokens))
    conn.commit()
    conn.close()

# 📊 토큰 사용량 불러오기 함수
def load_tokens():
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("SELECT input_tokens, output_tokens FROM token_usage WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0], row[1]
    return 0, 0