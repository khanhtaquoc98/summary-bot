import os
import telebot
from flask import Flask, request, jsonify

app = Flask(__name__)
bot = telebot.TeleBot(os.environ.get("TELEGRAM_BOT_TOKEN", ""), threaded=False)

@app.route('/api/notify-user', methods=['POST'])
def send_user_notification():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON payload"}), 400
        
    title = data.get('title', '⚽ Chấm Hết FC')
    body = data.get('body') or data.get('message') or ''
    
    if not body:
        return jsonify({"error": "Missing 'body' or 'message' in JSON"}), 400
        
    # Lấy danh sách ID người nhận (chấp nhận telegram_ids, chat_ids, chat_id hoặc telegram_id)
    chat_ids = data.get('telegram_ids') or data.get('chat_ids') or data.get('chat_id') or data.get('telegram_id')
    
    if not chat_ids:
        return jsonify({"error": "Missing 'telegram_ids' or 'chat_ids' in JSON"}), 400
        
    if isinstance(chat_ids, (str, int)):
        chat_ids = [chat_ids]
        
    message_text = f"📢 *{title}*\n\n{body}"
    
    sent = 0
    failed = 0
    errors = []
    
    for cid in chat_ids:
        try:
            bot.send_message(cid, message_text, parse_mode="Markdown")
            sent += 1
        except Exception as e:
            failed += 1
            errors.append(f"Chat {cid}: {str(e)}")
            
    return jsonify({
        "ok": True if sent > 0 else False,
        "status": "success" if sent > 0 else "error",
        "sent": sent,
        "failed": failed,
        "errors": errors
    }), 200
