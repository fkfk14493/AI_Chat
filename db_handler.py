import sqlite3
import json

DB_FILE = "sogo_chat.db"

def init_db():
    """데이터베이스 파일과 대화 테이블을 생성하는 함수"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # messages 열에 대화 기록 리스트를 TEXT(JSON 문자열) 형태로 통째로 저장합니다.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            messages TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_chat(messages):
    """현재까지의 대화 배열을 JSON으로 말아서 DB에 쑤셔 넣기"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 기존 데이터가 있으면 덮어씌우기 위해 지우고 새로 저장
    cursor.execute("DELETE FROM chat_history")
    json_messages = json.dumps(messages, ensure_ascii=False)
    cursor.execute("INSERT INTO chat_history (messages) VALUES (?)", (json_messages,))
    
    conn.commit()
    conn.close()

def load_chat():
    """DB에서 이전 대화 기록을 불러오기"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT messages FROM chat_history ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return json.loads(row[0])
    return []

# db_handler.py에 추가할 코드

def init_db():
    """기존 테이블 생성 코드에 줄거리 테이블 추가"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. 대화 기록 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            messages TEXT
        )
    ''')
    
    # 2. [추가] 줄거리 요약 저장 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS story_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_summary(summary_text):
    """요약된 줄거리를 DB에 저장"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # 기존 요약은 지우고 최신 요약 하나만 남기거나 누적해서 기록
    cursor.execute("INSERT INTO story_summary (summary) VALUES (?)", (summary_text,))
    conn.commit()
    conn.close()

def load_summary():
    """가장 최신 줄거리 요약 불러오기"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT summary FROM story_summary ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "저장된 줄거리가 없습니다."

# db_handler.py 맨 아래에 추가

def save_prompt(prompt_text):
    """수정된 프롬프트를 DB 파일에 영구 저장합니다."""
    conn = sqlite3.connect("sogo_chat.db")
    cursor = conn.cursor()
    # 설정값을 보관하는 전용 테이블 생성
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("""
        INSERT OR REPLACE INTO settings (key, value)
        VALUES ('system_prompt', ?)
    """, (prompt_text,))
    conn.commit()
    conn.close()

def load_prompt(default_val):
    """저장된 프롬프트를 불러옵니다. 없으면 기본값을 반환합니다."""
    conn = sqlite3.connect("sogo_chat.db")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT value FROM settings WHERE key = 'system_prompt'")
        row = cursor.fetchone()
        if row:
            return row[0]
    except sqlite3.OperationalError:
        # 테이블이 아직 안 만들어졌다면 기본값 반환
        pass
    finally:
        conn.close()
    return default_val