from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler

from linebot.exceptions import InvalidSignatureError

from linebot.models import MessageEvent, TextMessage, TextSendMessage

from openai import OpenAI

import os



app = Flask(__name__)



# ==========================================

# 設定エリア（環境変数から読み込むように変更）

# ==========================================

# GitHubに公開しても安全なように、キーを直接書かないようにしました

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN")

LINE_CHANNEL_SECRET = os.environ.get("CHANNEL_SECRET")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")



line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

handler = WebhookHandler(LINE_CHANNEL_SECRET)

client = OpenAI(api_key=OPENAI_API_KEY)



# 【重要】ユーザーごとの会話履歴を保存する「メモリ」

user_memories = {}



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



    # 1. 履歴がなければ初期化

    if user_id not in user_memories:

        user_memories[user_id] = [

            {"role": "system", "content": "あなたは親身な心理カウンセラーです。ユーザーの悩みを傾聴し、解決策を急がず、優しく共感してください。返信は短めに、友人のような距離感で。"}

        ]



    # 2. ユーザーのメッセージを追加

    user_memories[user_id].append({"role": "user", "content": user_message})



    # メモリ節約（最大10ターン）

    if len(user_memories[user_id]) > 11:

        del user_memories[user_id][1:3]



    try:

        # 3. AIに履歴を渡す

        completion = client.chat.completions.create(

            model="gpt-4o-mini",

            messages=user_memories[user_id]

        )

        

        ai_response = completion.choices[0].message.content


        print(f"📩 受信: {user_message}")
        print(f"🤖 返信: {ai_response}")

        # 4. AIの返事も履歴に追加

        user_memories[user_id].append({"role": "assistant", "content": ai_response})



        # ログ出力

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