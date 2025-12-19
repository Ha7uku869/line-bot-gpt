import os
import json
from sqlalchemy import create_engine, text

# ==========================================
# データベース接続設定
# ==========================================
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

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
            # 1. 会話履歴用のテーブル
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS conversations (
                    user_id TEXT PRIMARY KEY,
                    history TEXT
                )
            """))
            
            # 2. 【New】抽出データ（ナレッジグラフの元）用のテーブル
            # 論文にある time, where, who, emotion, stress を保存します
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS knowledge_store (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT,
                    extracted_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            print("✅ データベース初期化完了（ナレッジ用テーブル作成）")
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
            return [] # 初回は空リストを返す（システムプロンプトはai_handlerで付与するため）

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

def save_extracted_data(user_id, data_dict):
    """
    【New】抽出されたメンタルヘルスデータを保存する
    """
    if not engine: return
    try:
        data_json = json.dumps(data_dict, ensure_ascii=False)
        with engine.connect() as conn:
            # どんどん追記していく（上書きしない）
            sql = text("""
                INSERT INTO knowledge_store (user_id, extracted_data)
                VALUES (:uid, :data)
            """)
            conn.execute(sql, {"uid": user_id, "data": data_json})
            conn.commit()
            print(f"💾 データ抽出保存完了: {data_dict}")
    except Exception as e:
        print(f"❌ データ保存エラー: {e}")