import os
from google import genai

# Khởi tạo Client theo chuẩn SDK mới của Google
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))

class QuotaExceededError(Exception):
    pass

def summarize_messages(messages_text: str) -> str:
    prompt = f"""Bạn là một trợ lý ảo quản lý nhóm Telegram. Hãy tóm tắt lại nội dung cuộc trò chuyện sau đây trong nhóm một cách ngắn gọn, súc tích và dễ hiểu bằng tiếng Việt.
Tập trung vào các ý chính, các quyết định được đưa ra hoặc các chủ đề được thảo luận nhiều nhất.

Nội dung tin nhắn:
{messages_text}"""
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        error_msg = str(e).lower()
        if "429" in error_msg or "quota" in error_msg or "exhausted" in error_msg or "rate" in error_msg:
            raise QuotaExceededError("⏳ Bot đang bị giới hạn tốc độ tạm thời (quá nhiều yêu cầu trong thời gian ngắn). Vui lòng đợi 1-2 phút rồi thử lại nhé!")
        raise e
