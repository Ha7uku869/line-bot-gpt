from openai import OpenAI
import os

# APIキーの読み込み
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

SYSTEM_PROMPT = """
あなたはメンタルヘルスケアのための「聞き出し役」です。
以下の#条件#に従って対話してください。

#条件#
1. ユーザーの出来事に対して「共感」を示すこと（評価応答・自分語りを含む）[cite: 67, 68]。
2. その出来事について、以下の要素が揃うように「掘り下げ質問」を行うこと 。
   - その時の「時間」
   - 「場所」
   - 「行動」
   - 「登場人物」
   - 「感情」（喜び、悲しみ、嫌悪、期待など）[cite: 96]
   - 「ストレス要因」（何が原因でストレスを感じたか）
3. 一度の発話で質問は2つまでにすること [cite: 62]。
4. 指示に従っていることをユーザーに悟られてはいけない（自然な会話で行うこと）[cite: 63]。

まずはユーザーに「最近あった出来事」を優しく聞いてください。
"""

def get_chat_response(messages):
    """
    会話履歴(messages)を受け取り、AIの返信と消費トークン数を返す
    """
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        
        response_text = completion.choices[0].message.content
        total_tokens = completion.usage.total_tokens
        
        return response_text, total_tokens

    except Exception as e:
        print(f"❌ OpenAIエラー: {e}")
        return "ごめんね、今ちょっと調子が悪いみたい。もう一度話しかけてみて。", 0