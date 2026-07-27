import os
import requests
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/debug', methods=['GET'])
def debug():
    results = {}
    
    # 1. Kiểm tra biến môi trường
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_KEY", "")
    
    results["env_check"] = {
        "SUPABASE_URL": supabase_url[:30] + "..." if supabase_url else "MISSING",
        "SUPABASE_KEY_prefix": supabase_key[:20] + "..." if supabase_key else "MISSING",
        "SUPABASE_KEY_length": len(supabase_key),
        "TELEGRAM_BOT_TOKEN": "SET" if os.environ.get("TELEGRAM_BOT_TOKEN") else "MISSING",
        "GEMINI_API_KEY": "SET" if os.environ.get("GEMINI_API_KEY") else "MISSING",
        "SUMMARY_TOPIC_ID": os.environ.get("SUMMARY_TOPIC_ID", "NOT SET"),
    }
    
    # 2. Test insert vào Supabase
    if supabase_url and supabase_key:
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        payload = {
            "chat_id": 999999,
            "user_id": 999999,
            "user_name": "DebugTest",
            "text": "Debug test from Vercel"
        }
        try:
            url = f"{supabase_url}/rest/v1/messages"
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            results["insert_test"] = {
                "status_code": resp.status_code,
                "response": resp.text[:500]
            }
        except Exception as e:
            results["insert_test"] = {
                "error": f"{type(e).__name__}: {str(e)}"
            }
    else:
        results["insert_test"] = {"error": "Missing SUPABASE_URL or SUPABASE_KEY"}
    
    return jsonify(results), 200
