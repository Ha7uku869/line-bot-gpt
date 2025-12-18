import os
import json
from sqlalchemy import create_engine, text

# ==========================================
# データベース接続設定
# ==========================================
DATABASE_URL = os.environ.get("DATABASE_URL")

# Render対策: postgres:// を postgresql:// に変換
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# エンジンの作成（接続エラーを防ぐため、存在しない場合はNoneにする）
if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
else:
    engine = None
    print("⚠️ 警告: DATABASE_URLが設定されていません。")

def init_db():
    """テーブルが存在しない場合に作成する"""
    if not engine: return
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS conversations (
                    user_id TEXT PRIMARY KEY,
                    history TEXT
                )
            """))
            conn.commit()
            print("✅ データベース初期化完了")
    except Exception as e:
        print(f"❌ DB初期化エラー: {e}")

def get_history(user_id):
    """DBから会話履歴を取得する"""
    if not engine: return []
    with engine.connect() as conn:
        result = conn.execute(text("SELECT history FROM conversations WHERE user_id = :uid"), {"uid": user_id}).fetchone()
        if result:
            return json.loads(result[0])
        else:
            # 初期プロンプト（AIの人格）
            return [{"role": "system", "content": "あなたは親身な心理カウンセラーです。ユーザーの悩みを傾聴し、解決策を急がず、優しく共感してください。返信は短めに、友人のような距離感で。"}]

def save_history(user_id, history_list):
    """会話履歴をDBに保存(上書き)する"""
    if not engine: return
    try:
        history_json = json.dumps(history_list, ensure_ascii=False)
        with engine.connect() as conn:
            sql = text("""
                INSERT INTO conversations (user_id, history)
                VALUES (:uid, :hist)
                ON CONFLICT (user_id) 
                DO UPDATE SET history = :hist
            """)
            conn.execute(sql, {"uid": user_id, "hist": history_json})
            conn.commit()
    except Exception as e:
        print(f"❌ DB保存エラー: {e}")