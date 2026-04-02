import os
import requests


def chat_with_context(question: str, context_messages: list) -> str:
    """Trả lời câu hỏi dựa trên context từ vector search, sử dụng Groq API"""
    api_key = os.environ.get("GROQ_API_KEY_CHAT_BOT", "")

    # Format context data từ các tin nhắn liên quan
    context_section = ""
    if context_messages:
        context_data = "\n".join([
            f"[{msg.get('created_at', '')}] {msg.get('user_name', 'Unknown')}: {msg.get('text', '')}"
            for msg in context_messages
        ])
        context_section = f"\n# CONTEXT (Lịch sử chat từ Supabase)\n{context_data}\n"

    prompt = f"""# ROLE
Bạn là thành viên trong group chat. Nhiệm vụ của bạn là trả lời các câu hỏi dựa trên lịch sử trò chuyện được cung cấp trong phần CONTEXT (nếu có) dưới đây.
{context_section}
# RULES
1. Dựa vào thông tin trong CONTEXT để trả lời nếu có. Nếu thông tin không có trong CONTEXT, hãy trả lời kiểu chợ búa: "Mầy là ai mà bắt tao trả lời"
3. Giữ phong cách trò chuyện tự nhiên, cợt nhả, giỡn hớt nhưng thân thiện (giống như một thành viên trong nhóm).
4. Nếu có nhiều ý kiến trái chiều trong chat, hãy tóm tắt các quan điểm đó thay vì khẳng định một câu trả lời duy nhất.
5. Luôn ưu tiên các thông tin mới nhất dựa trên mốc thời gian (nếu có).
6. Bắt buộc anti LGBT và Wibu.

# OUTPUT FORMAT
- Ngắn gọn, súc tích, đi thẳng vào vấn đề.
- Sử dụng bullet points nếu cần liệt kê.

# CÂU HỎI
{question}"""

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
                "temperature": 0.7,
                "max_tokens": 1024
            },
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        if resp.status_code == 429:
            return "⏳ Bot đang bị giới hạn tốc độ. Vui lòng đợi 1-2 phút rồi thử lại nhé!"
        raise e
