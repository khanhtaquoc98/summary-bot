import os
from flask import Flask, request, jsonify
from utils.supabase_client import get_all_messages, delete_messages_before
from utils.llm import summarize_messages, QuotaExceededError
import telebot

app = Flask(__name__)
bot = telebot.TeleBot(os.environ.get("TELEGRAM_BOT_TOKEN", ""), threaded=False)

@app.route('/api/cron', methods=['GET'])
def cron_job():
    # Xác thực CRON_SECRET từ Vercel để tránh bị trigger lậu
    auth_header = request.headers.get('Authorization')
    if auth_header != f"Bearer {os.environ.get('CRON_SECRET')}":
        return jsonify({"error": "Unauthorized"}), 401

    try:
        # Lấy tất cả tin nhắn hiện có
        messages = get_all_messages()
        
        if not messages:
            return jsonify({"status": "Không có tin nhắn nào để tóm tắt trong hôm qua"}), 200
            
        # Gom nhóm tin nhắn theo chat_id
        chat_groups = {}
        for msg in messages:
            chat_id = msg['chat_id']
            if chat_id not in chat_groups:
                chat_groups[chat_id] = []
            chat_groups[chat_id].append(msg)
            
        # Xử lý tóm tắt cho từng group chat
        for chat_id, msgs in chat_groups.items():
            msgs.sort(key=lambda x: x['created_at'])
            chat_text = "\n".join([f"{msg['user_name']}: {msg['text']}" for msg in msgs if msg.get('text') and len(msg['text'].split()) >= 2])
            
            # Giới hạn độ dài để tránh 413 Payload Too Large
            MAX_CHARS = 4000
            if len(chat_text) > MAX_CHARS:
                chat_text = chat_text[:MAX_CHARS] + "\n... (đã cắt bớt)"
            
            if chat_text:
                try:
                    summary = summarize_messages(chat_text)
                    
                    # Cho phép khai báo biến môi trường NOTI_CHAT_ID và NOTI_TOPIC_ID để gửi vào chính xác 1 Topic mong muốn
                    noti_chat_id = os.environ.get("NOTI_CHAT_ID")
                    noti_topic_id = os.environ.get("NOTI_TOPIC_ID")
                    
                    target_thread = None
                    if noti_chat_id and str(chat_id) == noti_chat_id and noti_topic_id:
                        target_thread = int(noti_topic_id)
                    
                    bot.send_message(
                        chat_id, 
                        f"🌅 *Tóm tắt tin nhắn ngày hôm qua:*\n\n{summary}", 
                        message_thread_id=target_thread
                    )
                except QuotaExceededError as qe:
                    bot.send_message(chat_id, str(qe), message_thread_id=target_thread)
                except Exception as e:
                    print(f"Lỗi khi gửi tóm tắt cho chat_id {chat_id}: {e}")
                    
        # Lấy thời gian muộn nhất để xóa (chỉ xóa những tin nhắn vừa được đọc)
        max_time = max([m['created_at'] for m in messages])
        delete_messages_before(max_time)

        return jsonify({"status": "success", "groups_summarized": len(chat_groups), "messages_deleted": len(messages)}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

