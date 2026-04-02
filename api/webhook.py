import os
import time
import telebot
from flask import Flask, request, jsonify
from utils.supabase_client import insert_message, insert_embedding, get_messages, search_similar_messages
from utils.llm import summarize_messages, QuotaExceededError
from utils.embeddings import get_embedding
from utils.chatbot import chat_with_context

app = Flask(__name__)
# QUAN TRỌNG: threaded=False để handler chạy đồng bộ trên Vercel Serverless
bot = telebot.TeleBot(os.environ.get("TELEGRAM_BOT_TOKEN", ""), threaded=False)

# Bộ nhớ tạm để cache lại kết quả trong 60s
summary_cache = {}

@bot.message_handler(commands=['summary'])
def send_summary(message):
    chat_id = message.chat.id
    thread_id = message.message_thread_id
    
    # Nếu user cấu hình một topic cố định cho kết quả lệnh /summary
    if os.environ.get("SUMMARY_TOPIC_ID"):
        thread_id = int(os.environ.get("SUMMARY_TOPIC_ID"))
    
    # Kiểm tra cache 5 phút
    cache_key = f"{chat_id}_{thread_id}"
    current_time = time.time()
    
    if cache_key in summary_cache:
        last_time, cached_summary = summary_cache[cache_key]
        remaining = int(300 - (current_time - last_time))
        if remaining > 0:
            bot.send_message(chat_id, f"⚡ Kết quả được lưu tạm (còn {remaining}s)\n\n{cached_summary}", message_thread_id=thread_id)
            return
            
    loading_msg = bot.reply_to(message, "⏳ Đang tổng hợp tin nhắn và tạo tóm tắt, vui lòng đợi...")
    
    try:
        # Lấy 500 tin nhắn gần nhất từ Supabase
        data = get_messages(chat_id, 500)
        
        if not data:
            bot.edit_message_text("Không có tin nhắn nào được lưu trữ để tóm tắt.", chat_id=chat_id, message_id=loading_msg.message_id)
            return
            
        # Đảo ngược mảng để tin nhắn hiển thị theo thứ tự thời gian (cũ -> mới)
        data.reverse() 
        
        chat_text = "\n".join([f"{msg['user_name']}: {msg['text']}" for msg in data if msg.get('text')])
        
        if not chat_text:
            bot.edit_message_text("Không có nội dung tin nhắn dạng văn bản để tóm tắt.", chat_id=chat_id, message_id=loading_msg.message_id)
            return
            
        # Gọi Groq để tóm tắt
        summary = summarize_messages(chat_text)
        final_text = f"🌟 *Tóm tắt {len(data)} tin nhắn gần nhất:*\n\n{summary}"
        
        # Lưu kết quả vào biến tạm (cache) để dùng lại nếu có ai bấm gọi /summary liên tục
        summary_cache[cache_key] = (time.time(), final_text)
        
        bot.edit_message_text(final_text, chat_id=chat_id, message_id=loading_msg.message_id)
        
    except QuotaExceededError as qe:
        bot.edit_message_text(str(qe), chat_id=chat_id, message_id=loading_msg.message_id)
    except Exception as e:
        print(f"Lỗi khi tổng hợp: {type(e).__name__}: {e}")
        bot.edit_message_text("❌ Không thể tổng hợp tin nhắn lúc này. Vui lòng thử lại sau!", chat_id=chat_id, message_id=loading_msg.message_id)


@bot.message_handler(commands=['kutien'])
def handle_ai_command(message):
    """Xử lý lệnh /kutien <câu hỏi> - tìm tin nhắn liên quan bằng vector search rồi trả lời"""
    chat_id = message.chat.id
    thread_id = getattr(message, 'message_thread_id', None)

    # Lấy câu hỏi từ sau lệnh /kutien
    question = message.text.replace('/kutien', '', 1).strip()
    if not question:
        bot.reply_to(message, "💡 Cách dùng: /kutien <câu hỏi>")
        return

    loading_msg = bot.reply_to(message, "🤖 Đang tìm kiếm thông tin và suy nghĩ...")
    start_time = time.time()

    try:
        # Bước 1: Sinh embedding vector cho câu hỏi
        question_embedding = get_embedding(question)
        
        # Bước 2: Tìm tin nhắn liên quan bằng vector search (nếu có embedding)
        similar_messages = []
        if question_embedding:
            try:
                similar_messages = search_similar_messages(question_embedding, chat_id, match_count=10)
            except Exception:
                pass  # Không tìm được thì vẫn trả lời không cần context

        # Bước 3: Gửi context + câu hỏi vào Groq để trả lời (context có thể rỗng)
        answer = chat_with_context(question, similar_messages)

        # Đảm bảo thời gian phản hồi >= 2s để tạo cảm giác bot đang suy nghĩ
        elapsed = time.time() - start_time
        if elapsed < 2:
            time.sleep(2 - elapsed)

        bot.edit_message_text(
            f"🤖 {answer}",
            chat_id=chat_id, message_id=loading_msg.message_id
        )

    except Exception as e:
        print(f"Lỗi khi xử lý /kutien: {type(e).__name__}: {e}")
        bot.edit_message_text(
            "❌ Mày hỏi đểu hả, biết rồi hỏi clz!",
            chat_id=chat_id, message_id=loading_msg.message_id
        )


@bot.message_handler(func=lambda message: True, content_types=['text'])
def save_message(message):
    print(f"=> Bắt được tin nhắn từ Chat ID: {message.chat.id} | Topic Thread ID: {getattr(message, 'message_thread_id', 'None')}")

    # Nếu user cấu hình một topic cố định, chỉ tiếp thu và lưu tin nhắn được gửi từ Topic đó
    env_summary_topic = os.environ.get("SUMMARY_TOPIC_ID")
    if env_summary_topic:
        print(f"=> Đang kiểm tra điều kiện lọc: Topic cấu hình là {env_summary_topic}")
        if str(getattr(message, 'message_thread_id', None)) != str(env_summary_topic):
            print(f"=> ⛔ Đã huỷ lưu vì khác Topic ID yêu cầu.")
            return

    print("=> 🟢 Topic hợp lệ, chuẩn bị đẩy vào Supabase...")
    import sys
    sys.stdout.flush()
    
    # Cần set privacy của bot là disable ở BotFather để bot đọc được tin nhắn
    if message.text and not message.text.startswith('/'):
        print(f"=> Nội dung tin nhắn: '{message.text[:50]}'")
        sys.stdout.flush()
        try:
            print("=> Đang gọi insert_message...")
            sys.stdout.flush()
            
            # Luôn lưu vào bảng messages (phục vụ /summary)
            insert_message(
                chat_id=message.chat.id,
                user_id=message.from_user.id,
                user_name=message.from_user.full_name or message.from_user.username or "Unknown",
                text=message.text
            )
            
            # Sinh embedding và lưu vào bảng message_embeddings riêng (phục vụ /ai)
            if len(message.text.split()) >= 2:
                embedding = get_embedding(message.text)
                if embedding:
                    try:
                        insert_embedding(
                            chat_id=message.chat.id,
                            user_id=message.from_user.id,
                            user_name=message.from_user.full_name or message.from_user.username or "Unknown",
                            text=message.text,
                            embedding=embedding
                        )
                    except Exception as emb_err:
                        # Embedding lỗi thì bỏ qua, không ảnh hưởng đến việc lưu message
                        print(f"⚠️ Lỗi lưu embedding (bỏ qua): {type(emb_err).__name__}: {emb_err}")
            
            print("=> ✅ Lưu thành công vào Supabase!")
            sys.stdout.flush()
        except Exception as e:
            print(f"Lỗi khi lưu tin nhắn: {type(e).__name__}: {e}")
            sys.stdout.flush()
    else:
        print(f"=> ⚠️ Bỏ qua: text is None or starts with '/' | text={message.text}")
        sys.stdout.flush()

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
