import os
import time
import telebot
from flask import Flask, request, jsonify
from utils.supabase_client import get_supabase
from utils.llm import summarize_messages, QuotaExceededError

app = Flask(__name__)
bot = telebot.TeleBot(os.environ.get("TELEGRAM_BOT_TOKEN", ""))

# Bộ nhớ tạm để cache lại kết quả trong 60s
summary_cache = {}

@bot.message_handler(commands=['summary'])
def send_summary(message):
    chat_id = message.chat.id
    thread_id = message.message_thread_id
    
    # Nếu user cấu hình một topic cố định cho kết quả lệnh /summary
    if os.environ.get("SUMMARY_TOPIC_ID"):
        thread_id = int(os.environ.get("SUMMARY_TOPIC_ID"))
    
    # Kiểm tra cache 1 phút
    cache_key = f"{chat_id}_{thread_id}"
    current_time = time.time()
    
    if cache_key in summary_cache:
        last_time, cached_summary = summary_cache[cache_key]
        if current_time - last_time < 60:
            bot.send_message(chat_id, f"⚡ *(Kết quả cũ cách đây vài giây)*\n{cached_summary}", parse_mode="Markdown", message_thread_id=thread_id)
            return
            
    bot.reply_to(message, "Đang tổng hợp tin nhắn và tạo tóm tắt, vui lòng đợi...")
    
    try:
        supabase = get_supabase()
        # Lấy 500 tin nhắn gần nhất từ Supabase
        response = supabase.table("messages").select("*").eq("chat_id", chat_id).order("created_at", desc=True).limit(500).execute()
        data = response.data
        
        if not data:
            bot.send_message(chat_id, "Không có tin nhắn nào được lưu trữ để tóm tắt.", message_thread_id=thread_id)
            return
            
        # Đảo ngược mảng để tin nhắn hiển thị theo thứ tự thời gian (cũ -> mới)
        data.reverse() 
        
        chat_text = "\\n".join([f"{msg['user_name']}: {msg['text']}" for msg in data if msg.get('text')])
        
        if not chat_text:
            bot.send_message(chat_id, "Không có nội dung tin nhắn dạng văn bản để tóm tắt.", message_thread_id=thread_id)
            return
            
        # Gọi Gemini để tóm tắt
        summary = summarize_messages(chat_text)
        final_text = f"🌟 *Tóm tắt {len(data)} tin nhắn gần nhất:*\n\n{summary}"
        
        # Lưu kết quả vào biến tạm (cache) để dùng lại nếu có ai bấm gọi /summary liên tục
        summary_cache[cache_key] = (time.time(), final_text)
        
        bot.send_message(chat_id, final_text, parse_mode="Markdown", message_thread_id=thread_id)
        
    except QuotaExceededError as qe:
        bot.send_message(chat_id, str(qe), message_thread_id=thread_id)
    except Exception as e:
        bot.send_message(chat_id, f"Có lỗi xảy ra: {str(e)}", message_thread_id=thread_id)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def save_message(message):
    # Nếu user cấu hình một topic cố định, chỉ tiếp thu và lưu tin nhắn được gửi từ Topic đó
    env_summary_topic = os.environ.get("SUMMARY_TOPIC_ID")
    if env_summary_topic and str(message.message_thread_id) != env_summary_topic:
        return

    # Cần set privacy của bot là disable ở BotFather để bot đọc được tin nhắn
    if message.text and not message.text.startswith('/'):
        try:
            supabase = get_supabase()
            supabase.table("messages").insert({
                "chat_id": message.chat.id,
                "user_id": message.from_user.id,
                "user_name": message.from_user.full_name or message.from_user.username or "Unknown",
                "text": message.text
            }).execute()
        except Exception as e:
            print(f"Lỗi khi lưu tin nhắn: {e}")

@app.route('/api/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    else:
        return 'Forbidden', 403

# Endpoint để kiểm tra server
@app.route('/api/webhook', methods=['GET'])
def check_status():
    return jsonify({"status": "Bot is running on Vercel"}), 200
