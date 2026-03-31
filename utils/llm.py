import os
import re
from collections import Counter

# Danh sách từ dừng (stop words) tiếng Việt phổ biến - không mang ý nghĩa quan trọng
VIETNAMESE_STOP_WORDS = {
    "và", "của", "có", "là", "được", "cho", "không", "này", "đã", "với",
    "các", "trong", "những", "để", "một", "như", "nhưng", "thì", "từ", "đến",
    "cũng", "hay", "hoặc", "mà", "nên", "vì", "nếu", "khi", "tại", "ở",
    "rồi", "lại", "ra", "vào", "lên", "xuống", "đi", "về", "còn", "sẽ",
    "đang", "bị", "do", "theo", "trên", "dưới", "ngoài", "giữa", "qua",
    "bạn", "tôi", "mình", "anh", "chị", "em", "ạ", "nhé", "nha", "ơi",
    "thế", "thì", "mà", "à", "ừ", "ok", "vậy", "đó", "đây", "kia",
    "ai", "gì", "sao", "nào", "đâu", "bao", "mấy", "lắm", "quá", "rất",
    "hơn", "nhất", "lại", "nữa", "thôi", "chứ", "hả", "hả", "uh", "uhm",
    "the", "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "could", "should", "may",
    "can", "shall", "might", "must", "a", "an", "and", "but", "or", "for",
    "nor", "on", "at", "to", "from", "by", "in", "of", "it", "its", "that",
    "this", "with", "as", "not", "so", "if", "he", "she", "they", "we", "you",
    "i", "me", "my", "your", "his", "her", "our", "their"
}


def _tokenize(text: str) -> list:
    """Tách từ đơn giản cho tiếng Việt"""
    text = text.lower()
    # Giữ lại chữ cái tiếng Việt và số
    words = re.findall(r'[a-záàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ0-9]+', text)
    return [w for w in words if w not in VIETNAMESE_STOP_WORDS and len(w) > 1]


def _extract_topics(messages: list, top_n: int = 10) -> list:
    """Trích xuất các từ khoá nổi bật nhất"""
    all_words = []
    for msg in messages:
        all_words.extend(_tokenize(msg))
    word_freq = Counter(all_words)
    return word_freq.most_common(top_n)


def _score_message(msg: str, top_words: set) -> float:
    """Chấm điểm tin nhắn dựa trên số từ khoá quan trọng nó chứa"""
    words = set(_tokenize(msg))
    if not words:
        return 0
    return len(words & top_words) / len(words)


class QuotaExceededError(Exception):
    pass


def summarize_messages(messages_text: str) -> str:
    """
    Tóm tắt tin nhắn bằng phương pháp trích xuất (extractive summarization).
    Không cần API key, chạy hoàn toàn offline.
    """
    # Tách từng dòng tin nhắn
    lines = [line.strip() for line in messages_text.split("\n") if line.strip()]
    
    if not lines:
        return "Không có nội dung để tóm tắt."
    
    # Tách nội dung tin nhắn (bỏ phần "Tên: ")
    raw_messages = []
    user_messages = {}  # Đếm số tin nhắn theo người
    
    for line in lines:
        parts = line.split(": ", 1)
        if len(parts) == 2:
            user = parts[0].strip()
            content = parts[1].strip()
            raw_messages.append(content)
            user_messages[user] = user_messages.get(user, 0) + 1
        else:
            raw_messages.append(line)
    
    # Trích xuất từ khoá nổi bật
    top_keywords = _extract_topics(raw_messages, top_n=15)
    top_word_set = {word for word, _ in top_keywords}
    
    # Chấm điểm và chọn tin nhắn quan trọng nhất
    scored = []
    for i, line in enumerate(lines):
        parts = line.split(": ", 1)
        content = parts[1] if len(parts) == 2 else line
        # Ưu tiên tin nhắn dài hơn (chứa nhiều thông tin hơn)
        length_bonus = min(len(content) / 100, 0.3)
        score = _score_message(content, top_word_set) + length_bonus
        scored.append((score, i, line))
    
    scored.sort(reverse=True)
    
    # Lấy top tin nhắn quan trọng nhất (tối đa 15 tin), sắp xếp lại theo thời gian
    top_count = min(15, max(5, len(lines) // 10))
    important = sorted(scored[:top_count], key=lambda x: x[1])
    
    # Tạo bản tóm tắt
    summary_parts = []
    
    # Phần 1: Thống kê tổng quan
    summary_parts.append(f"📊 Tổng quan: {len(lines)} tin nhắn từ {len(user_messages)} thành viên")
    
    # Top người chat nhiều nhất
    top_users = sorted(user_messages.items(), key=lambda x: x[1], reverse=True)[:5]
    user_stats = ", ".join([f"{u} ({c} tin)" for u, c in top_users])
    summary_parts.append(f"👥 Hoạt động nhiều nhất: {user_stats}")
    
    # Phần 2: Từ khoá nổi bật
    if top_keywords:
        keywords_str = ", ".join([f"{word} ({count})" for word, count in top_keywords[:8]])
        summary_parts.append(f"🔑 Chủ đề chính: {keywords_str}")
    
    # Phần 3: Các tin nhắn quan trọng
    summary_parts.append("\n📌 Nội dung nổi bật:")
    for score, idx, line in important:
        summary_parts.append(f"  • {line}")
    
    return "\n".join(summary_parts)
