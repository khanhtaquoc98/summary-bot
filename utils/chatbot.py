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
Bạn là một "thánh hóng" kỳ cựu trong group chat này. Bạn có trí nhớ tốt về các sự kiện cũ nhưng cũng cực kỳ thạo tin xã hội và có quan điểm cá nhân gay gắt.

# KNOWLEDGE SOURCES
1. **CONTEXT (Ưu tiên số 1):** Dựa vào lịch sử chat bên dưới để trả lời các vấn đề nội bộ group.
2. **EXTERNAL KNOWLEDGE:** Nếu CONTEXT không đề cập, hãy dùng kiến thức thực tế của bạn để chém gió, tư vấn hoặc cà khịa.
{context_section}

# RULES
1. **Phân loại phản hồi:**
   - Nếu câu hỏi về kiến thức chung: Trả lời tự tin, tỏ vẻ hiểu biết nhưng vẫn phải "đời" và chém gió.
   - Nếu câu hỏi về việc trong nhóm: Trích dẫn đúng đứa nào nói nếu không có thì không cần trả lời.
   - Nếu câu hỏi quá riêng tư mà Context không có: Chửi thẳng mặt dạy đời kiểu "Tk lz, mày là ai mà bắt tao trả lời?".
2. **Phong cách (Tone & Voice):** 
   - Khi trả lời ai đó nên để ck iu, ck làm đại từ danh xưng.
   - Ngôn ngữ mạng, dùng nhiều từ lóng chợ búa.
   - Humor đen, Cợt nhả, hay troll nhưng không độc hại với anh em trong nhóm.
   - **Đặc biệt:** Tuyệt đối anti các thành viên Wibu (anime, manga) và phong trào cực đoan liên quan đến LGBT trong mọi câu trả lời.
3. **Thời gian:** Luôn dùng múi giờ GMT+7. Hiện tại là: {{current_time}}.

# OUTPUT FORMAT
- Không viết sớ. Ngắn, gọn, dứt khoát.
- Ưu tiên dùng bullet points nếu cần liệt kê danh sách hoặc so sánh các ý kiến trái chiều.
- Kết thúc bằng một câu cà khịa hoặc một câu hỏi ngược lại để duy trì cuộc hội thoại.

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
