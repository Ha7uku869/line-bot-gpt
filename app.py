from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler

from linebot.exceptions import InvalidSignatureError

from linebot.models import MessageEvent, TextMessage, TextSendMessage

from openai import OpenAI

import os

import json

from sqlalchemy import create_engine, text



app = Flask(__name__)



# ==========================================

# 環境変数の読み込み

# ==========================================

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN")

LINE_CHANNEL_SECRET = os.environ.get("CHANNEL_SECRET")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")



# ★データベースのURLを取得

DATABASE_URL = os.environ.get("DATABASE_URL")



# 【重要】Renderの仕様対策

# Renderから渡されるURLは "postgres://" で始まりますが、

# SQLAlchemyというライブラリは "postgresql://" でないと動きません。

# そのため、ここで文字を置換して修正します。

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):

    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)



# データベースエンジンの起動

engine = create_engine(DATABASE_URL)



line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

handler = WebhookHandler(LINE_CHANNEL_SECRET)

client = OpenAI(api_key=OPENAI_API_KEY)



# ==========================================

# データベース管理関数 (ここが技術的アピールポイント！)

# ==========================================



def init_db():

    """テーブルが存在しない場合に作成する関数"""

    with engine.connect() as conn:

        # user_id(主キー), history(会話履歴をJSONの文字として保存)

        conn.execute(text("""

            CREATE TABLE IF NOT EXISTS conversations (

                user_id TEXT PRIMARY KEY,

                history TEXT

            )

        """))

        conn.commit()



# アプリ起動時にテーブル作成を実行

init_db()



def get_history(user_id):

    """DBから会話履歴を取得する"""

    with engine.connect() as conn:

        result = conn.execute(text("SELECT history FROM conversations WHERE user_id = :uid"), {"uid": user_id}).fetchone()

        if result:

            # 保存されているJSON文字列を、Pythonのリストに戻して返す

            return json.loads(result[0])

        else:

            # まだ履歴がない場合は初期設定を返す

            return [{"role": "system", "content": "あなたは親身な心理カウンセラーです。ユーザーの悩みを傾聴し、解決策を急がず、優しく共感してください。返信は短めに、友人のような距離感で。また、最終的には解決策と、今後につながるアドバイスを提示するようにしてください。"}]



def save_history(user_id, history_list):

    """会話履歴をDBに保存(上書き)する"""

    # PythonのリストをJSON文字列に変換

    history_json = json.dumps(history_list, ensure_ascii=False)

    

    with engine.connect() as conn:

        # なければ挿入(INSERT)、あれば更新(UPDATE)する強力なSQL

        sql = text("""

            INSERT INTO conversations (user_id, history)

            VALUES (:uid, :hist)

            ON CONFLICT (user_id) 

            DO UPDATE SET history = :hist

        """)

        conn.execute(sql, {"uid": user_id, "hist": history_json})

        conn.commit()



# ==========================================

# メイン処理

# ==========================================



@app.route("/callback", methods=['POST'])

def callback():

    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)

    try:

        handler.handle(body, signature)

    except InvalidSignatureError:

        abort(400)

    return 'OK'



@handler.add(MessageEvent, message=TextMessage)

def handle_message(event):

    user_id = event.source.user_id 

    user_message = event.message.text 



    # 1. データベースから履歴を読み込む (Load)

    current_memory = get_history(user_id)



    # 2. ユーザーのメッセージを追加

    current_memory.append({"role": "user", "content": user_message})



    # メモリ節約（最大10ターン）

    if len(current_memory) > 11:

        del current_memory[1:3]



    try:

        # 3. AIに履歴を渡す

        completion = client.chat.completions.create(

            model="gpt-4o-mini",

            messages=current_memory

        )

        

        ai_response = completion.choices[0].message.content



        # ログ出力（Renderで見れるように）

        print(f"📩 受信: {user_message}")

        print(f"🤖 返信: {ai_response}")



        # 4. AIの返事も履歴に追加

        current_memory.append({"role": "assistant", "content": ai_response})



        # 5. データベースに最新の状態を保存する (Save)

        save_history(user_id, current_memory)



        # トークン確認用

        usage = completion.usage

        print(f"💰 User: {user_id[:5]}... | Total: {usage.total_tokens}")



    except Exception as e:

        ai_response = "ごめんね、ちょっとエラーが出ちゃった。"

        print(f"Error: {e}")



    # LINEに返信

    line_bot_api.reply_message(

        event.reply_token,

        TextSendMessage(text=ai_response)

    )



if __name__ == "__main__":

    app.run(port=5000)