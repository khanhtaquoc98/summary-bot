import os
from flask import Flask, jsonify
from utils.supabase_client import get_messages, get_all_messages
from utils.llm import summarize_messages

app = Flask(__name__)

@app.route('/api/test', methods=['GET'])
def test_summary():
    results = {}
    
    # 1. Lấy tất cả tin nhắn trong DB
    try:
        all_messages = get_all_messages()
        results["total_messages"] = len(all_messages)
        results["latest_5"] = [
            {"user": m["user_name"], "text": m["text"][:50], "time": m["created_at"]}
            for m in sorted(all_messages, key=lambda x: x["created_at"], reverse=True)[:5]
        ]
    except Exception as e:
        results["db_error"] = f"{type(e).__name__}: {e}"
        return jsonify(results), 500

    # 2. Thử tóm tắt nếu có tin nhắn
    if all_messages:
        chat_text = "\n".join([f"{msg['user_name']}: {msg['text']}" for msg in all_messages if msg.get('text')])
        try:
            summary = summarize_messages(chat_text)
            results["summary"] = summary
            results["status"] = "success"
        except Exception as e:
            results["summary_error"] = f"{type(e).__name__}: {e}"
            results["status"] = "failed"
    else:
        results["status"] = "no_messages"

    return jsonify(results), 200
