import os
import telebot
from flask import Flask, request, jsonify

app = Flask(__name__)
bot = telebot.TeleBot(os.environ.get("TELEGRAM_BOT_TOKEN", ""), threaded=False)

@app.route('/api/notify-payment', methods=['POST'])
def send_payment_notification():
    data = request.get_json()
    if not data or 'title' not in data or 'body' not in data:
        return jsonify({"error": "Missing 'title' or 'body' in JSON"}), 400
        
    title = data['title']
    body = data['body']
    
    # Lấy Chat ID từ biến môi trường (nhóm sẽ nhận tin)
    chat_id = os.environ.get("NOTI_CHAT_ID")
    if not chat_id:
        return jsonify({"error": "Bị thiếu biến môi trường NOTI_CHAT_ID trên Vercel"}), 500
        
    # Gửi đến Topic cho thanh toán (lấy từ env PAYMENT_TOPIC_ID)
    thread_id = os.environ.get("PAYMENT_TOPIC_ID")
    if not thread_id:
        return jsonify({"error": "Bị thiếu biến môi trường PAYMENT_TOPIC_ID trên Vercel"}), 500
    thread_id = int(thread_id)
    
    message_text = f"📢 *{title}*\n\n{body}"
    
    try:
        kwargs = {"parse_mode": "Markdown", "message_thread_id": thread_id}
        bot.send_message(chat_id, message_text, **kwargs)
            
        return jsonify({"status": "success", "message": "Đã gửi thông báo thanh toán thành công lên Telegram"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
