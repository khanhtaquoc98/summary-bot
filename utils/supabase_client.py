import os
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

def _headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

def insert_message(chat_id: int, user_id: int, user_name: str, text: str):
    """Chèn tin nhắn mới vào bảng messages (chỉ phục vụ summary)"""
    url = f"{SUPABASE_URL}/rest/v1/messages"
    payload = {
        "chat_id": chat_id,
        "user_id": user_id,
        "user_name": user_name,
        "text": text
    }
    resp = requests.post(url, json=payload, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()

def insert_embedding(chat_id: int, user_id: int, user_name: str, text: str, embedding: list):
    """Chèn embedding vào bảng message_embeddings (phục vụ vector search /ai)"""
    url = f"{SUPABASE_URL}/rest/v1/message_embeddings"
    payload = {
        "chat_id": chat_id,
        "user_id": user_id,
        "user_name": user_name,
        "text": text,
        "embedding": embedding
    }
    resp = requests.post(url, json=payload, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()

def get_messages(chat_id: int, limit: int = 500):
    """Lấy tin nhắn gần nhất theo chat_id, sắp xếp mới nhất trước"""
    url = f"{SUPABASE_URL}/rest/v1/messages"
    params = {
        "chat_id": f"eq.{chat_id}",
        "order": "created_at.desc",
        "limit": limit,
        "select": "*"
    }
    resp = requests.get(url, params=params, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()

def get_all_messages():
    """Lấy tất cả tin nhắn"""
    url = f"{SUPABASE_URL}/rest/v1/messages"
    params = {"select": "*"}
    resp = requests.get(url, params=params, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()

def search_similar_messages(query_embedding: list, chat_id: int, match_count: int = 10):
    """Tìm kiếm tin nhắn liên quan nhất bằng vector similarity search (pgvector)
    Sử dụng bảng message_embeddings riêng biệt
    """
    url = f"{SUPABASE_URL}/rest/v1/rpc/match_messages"
    payload = {
        "query_embedding": query_embedding,
        "target_chat_id": chat_id,
        "match_count": match_count
    }
    resp = requests.post(url, json=payload, headers=_headers(), timeout=15)
    resp.raise_for_status()
    return resp.json()

def delete_messages_before(max_time: str):
    """Xoá tất cả tin nhắn có created_at <= max_time"""
    url = f"{SUPABASE_URL}/rest/v1/messages"
    params = {"created_at": f"lte.{max_time}"}
    resp = requests.delete(url, params=params, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp

def insert_poll(poll_id: str, message_id: int, chat_id: int, thread_id: int, title: str, options: list, is_anonymous: bool):
    """Lưu/cập nhật thông tin cuộc biểu quyết (Poll) vào bảng polls (upsert)"""
    url = f"{SUPABASE_URL}/rest/v1/polls?on_conflict=poll_id"
    headers = _headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=representation"
    payload = {
        "poll_id": str(poll_id),
        "message_id": int(message_id) if message_id is not None else None,
        "chat_id": int(chat_id) if chat_id is not None else None,
        "thread_id": int(thread_id) if thread_id is not None else None,
        "title": title,
        "options": options,
        "is_anonymous": is_anonymous
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()

def save_poll_answer(poll_id: str, user_id: int, user_name: str, option_ids: list):
    """Lưu/cập nhật kết quả vote của người dùng vào bảng poll_answers (upsert)"""
    url = f"{SUPABASE_URL}/rest/v1/poll_answers?on_conflict=poll_id,user_id"
    headers = _headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=representation"
    payload = {
        "poll_id": str(poll_id),
        "user_id": user_id,
        "user_name": user_name,
        "option_ids": option_ids
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()

def get_poll_voters(poll_id: str):
    """Lấy danh sách người đã vote theo poll_id"""
    url = f"{SUPABASE_URL}/rest/v1/poll_answers"
    params = {
        "poll_id": f"eq.{poll_id}",
        "select": "*"
    }
    resp = requests.get(url, params=params, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()

def get_poll_by_id(poll_id: str):
    """Lấy thông tin cuộc biểu quyết theo poll_id"""
    url = f"{SUPABASE_URL}/rest/v1/polls"
    params = {
        "poll_id": f"eq.{poll_id}",
        "select": "*"
    }
    resp = requests.get(url, params=params, headers=_headers(), timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data[0] if data else None

def get_user_poll_answer(poll_id: str, user_id: int):
    """Lấy kết quả vote cũ của người dùng trong poll_answers"""
    url = f"{SUPABASE_URL}/rest/v1/poll_answers"
    params = {
        "poll_id": f"eq.{poll_id}",
        "user_id": f"eq.{user_id}",
        "select": "*"
    }
    resp = requests.get(url, params=params, headers=_headers(), timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data[0] if data else None

def clear_all_poll_answers(poll_id: str = None):
    """Xoá tất cả lượt vote cũ trong poll_answers (hoặc xoá theo poll_id nếu có)"""
    url = f"{SUPABASE_URL}/rest/v1/poll_answers"
    if poll_id:
        params = {"poll_id": f"eq.{poll_id}"}
    else:
        params = {"id": "gte.0"}
    resp = requests.delete(url, params=params, headers=_headers(), timeout=10)
    return resp



