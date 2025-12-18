from openai import OpenAI
import os

# APIキーの読み込み
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def get_chat_response(messages):
    """
    会話履歴(messages)を受け取り、AIの返信と消費トークン数を返す
    """
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