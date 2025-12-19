from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

import database
import ai_handler

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 起動時にDBテーブルを作成（抽出用テーブルも作られる）
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

    # 1. 履歴取得
    history = database.get_history(user_id)

    # 2. ユーザーメッセージ追加
    history.append({"role": "user", "content": user_message})
    if len(history) > 11: del history[1:3]

    # 3. AI返信生成
    ai_response, tokens = ai_handler.get_chat_response(history)
    history.append({"role": "assistant", "content": ai_response})

    # 4. 履歴保存
    database.save_history(user_id, history)

    # ==========================================
    # 5. 【New】論文に基づくデータ抽出を実行！
    # ==========================================
    extracted_data = ai_handler.extract_mental_data(user_message, ai_response)
    
    if extracted_data:
        # DBの新しいテーブルに保存
        database.save_extracted_data(user_id, extracted_data)
        
        # ログで確認（RenderのLogs画面に出る）
        print(f"📊 抽出データ: {extracted_data}")

    # LINEに返信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=ai_response)
    )

if __name__ == "__main__":
    app.run(port=5000)