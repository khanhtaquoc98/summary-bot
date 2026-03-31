import os
import requests


class QuotaExceededError(Exception):
    pass


def summarize_messages(messages_text: str) -> str:
    """Tóm tắt tin nhắn sử dụng Groq API (miễn phí, cực nhanh)"""
    api_key = os.environ.get("GROQ_API_KEY", "")
    
    prompt = f"""Bạn là một trợ lý ảo quản lý nhóm Telegram. Hãy tóm tắt lại nội dung cuộc trò chuyện sau đây trong nhóm một cách ngắn gọn, súc tích và dễ hiểu bằng tiếng Việt.
Tập trung vào các ý chính, các quyết định được đưa ra hoặc các chủ đề được thảo luận nhiều nhất.

Nội dung tin nhắn:
{messages_text}"""

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 2048
            },
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        error_msg = str(e).lower()
        if "429" in error_msg or resp.status_code == 429:
            raise QuotaExceededError("⏳ Bot đang bị giới hạn tốc độ tạm thời. Vui lòng đợi 1-2 phút rồi thử lại nhé!")
        raise e
