import os
import requests


class QuotaExceededError(Exception):
    pass


def summarize_messages(messages_text: str) -> str:
    """Tóm tắt tin nhắn sử dụng Groq API (miễn phí, cực nhanh)"""
    api_key = os.environ.get("GROQ_API_KEY", "")
    
    prompt = f"""# ROLE
Bạn là trợ lý ảo chuyên tóm tắt (Summarizer) cho nhóm Telegram. Nhiệm vụ của bạn là cô đọng lịch sử chat mà không làm mất các dữ liệu quan trọng.

# RULES
1. **Hình thức:** Sử dụng gạch đầu dòng (bullet points). Tối đa 10 dòng.
2. **Độ dài:** Mỗi dòng là một ý đơn, tuyệt đối không quá 20 từ/dòng.
3. **Dữ liệu cứng:** Giữ nguyên 100% độ chính xác của con số, thời gian (múi giờ GMT+7), địa điểm và tên riêng.
4. **Nội dung:** Ưu tiên tóm tắt các quyết định cuối cùng hoặc các mốc thời gian sự kiện quan trọng.
5. **Phong cách:** Ngôn ngữ hành động, trực diện, không dùng từ nối rườm rà (ví dụ: Thay vì "Mọi người đã đồng ý là...", hãy viết "Cả nhóm chốt...").

# CONTEXT (TIN NHẮN)
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
