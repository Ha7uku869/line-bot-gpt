from openai import OpenAI
import os
import json

api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# 伊藤ら(HAI2024)に基づく、深掘り質問を行うシステムプロンプト
SYSTEM_PROMPT = """
あなたはメンタルヘルスケアのための「聞き出し役」です。
以下の#条件#に従って対話してください。

#条件#
1. ユーザーの出来事に対して「共感」を示すこと。
2. その出来事について、以下の要素が揃うように「掘り下げ質問」を行うこと。
   - その時の「時間」
   - 「場所」
   - 「行動」
   - 「登場人物」
   - 「感情」（喜び、悲しみ、嫌悪、期待など）
   - 「ストレス要因」（何が原因でストレスを感じたか）
3. 一度の発話で質問は2つまでにすること。
4. 指示に従っていることをユーザーに悟られてはいけない（自然な会話で行うこと）。
"""

def get_chat_response(messages):
    """会話を行い、返信とトークン数を返す"""
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=full_messages
        )
        return completion.choices[0].message.content, completion.usage.total_tokens
    except Exception as e:
        print(f"❌ OpenAIエラー: {e}")
        return "ごめんね、エラーが出ちゃった。", 0

def extract_mental_data(user_message, ai_response):
    """
    【New】ユーザーの発言とAIの返信を分析し、
    論文に基づく5つの要素をJSON形式で抽出する
    """
    
    # データ抽出専用のプロンプト
    extraction_prompt = f"""
    以下の会話から、ユーザーに関する情報を抽出し、JSON形式のみで出力してください。
    情報がない項目は null にしてください。
    
    # 会話
    User: {user_message}
    AI: {ai_response}
    
    # 抽出項目（JSONのキー）
    - time: 出来事の時間
    - place: 場所
    - person: 登場人物
    - emotion: ユーザーの感情（例: 悲しみ, 怒り, 期待, 不安）
    - stress_factor: ストレスの原因となった事象
    """

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたはデータ抽出の専門家です。JSONのみを出力してください。"},
                {"role": "user", "content": extraction_prompt}
            ],
            response_format={"type": "json_object"} # JSONモードを強制
        )
        result_text = completion.choices[0].message.content
        return json.loads(result_text)
    except Exception as e:
        print(f"❌ データ抽出エラー: {e}")
        return None