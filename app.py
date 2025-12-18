from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

# 作成したモジュールをインポート
import database
import ai_handler

app = Flask(__name__)

# ==========================================
# LINE Bot設定
# ==========================================
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 起動時にDBテーブルを作成
database.init_db()

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

    # 1. データベースから履歴を取得 (database.pyにお任せ)
    history = database.get_history(user_id)

    # 2. ユーザーのメッセージを追加
    history.append({"role": "user", "content": user_message})

    # メモリ節約（最大10ターン）
    if len(history) > 11:
        del history[1:3]

    # 3. AIに返信を生成してもらう (ai_handler.pyにお任せ)
    ai_response, tokens = ai_handler.get_chat_response(history)

    # ログ出力
    print(f"📩 受信: {user_message}")
    print(f"🤖 返信: {ai_response}")
    print(f"💰 User: {user_id[:5]}... | Total: {tokens}")

    # 4. AIの返信を履歴に追加
    history.append({"role": "assistant", "content": ai_response})

    # 5. データベースに保存 (database.pyにお任せ)
    database.save_history(user_id, history)

    # LINEに返信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=ai_response)
    )

if __name__ == "__main__":
    app.run(port=5000)