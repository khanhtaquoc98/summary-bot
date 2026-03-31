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
    """Chèn tin nhắn mới vào bảng messages"""
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

def delete_messages_before(max_time: str):
    """Xoá tất cả tin nhắn có created_at <= max_time"""
    url = f"{SUPABASE_URL}/rest/v1/messages"
    params = {"created_at": f"lte.{max_time}"}
    resp = requests.delete(url, params=params, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp
