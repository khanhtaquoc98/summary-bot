import os
import telebot
from flask import Flask, request, jsonify

app = Flask(__name__)
bot = telebot.TeleBot(os.environ.get("TELEGRAM_BOT_TOKEN", ""), threaded=False)

@app.route('/api/notify', methods=['POST'])
def send_notification():
    # Bảo mật: Cần truyền Authorization: Bearer <CRON_SECRET> để chống spam
    # auth_header = request.headers.get('Authorization')
    # if auth_header != f"Bearer {os.environ.get('CRON_SECRET')}":
    #     return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    if not data or 'title' not in data or 'body' not in data:
        return jsonify({"error": "Missing 'title' or 'body' in JSON"}), 400
        
    title = data['title']
    body = data['body']
    
    # Lấy Chat ID từ biến môi trường (nhóm sẽ nhận tin)
    chat_id = os.environ.get("NOTI_CHAT_ID")
    if not chat_id:
        return jsonify({"error": "Bị thiếu biến môi trường NOTI_CHAT_ID trên Vercel"}), 500
        
    # Gửi đến SUMMARY_TOPIC_ID theo yêu cầu
    thread_id = os.environ.get("SUMMARY_TOPIC_ID")
    
    message_text = f"📢 *{title}*\n\n{body}"
    
    try:
        kwargs = {"parse_mode": "MarkdownV2"}
        if thread_id:
            kwargs["message_thread_id"] = int(thread_id)
            
        bot.send_message(chat_id, message_text, **kwargs)
            
        return jsonify({"status": "success", "message": "Đã gửi tin nhắn thành công lên Telegram"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
