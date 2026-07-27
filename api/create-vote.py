import os
import telebot
from flask import Flask, request, jsonify

from utils.supabase_client import insert_poll

app = Flask(__name__)
bot = telebot.TeleBot(os.environ.get("TELEGRAM_BOT_TOKEN", ""), threaded=False)

@app.route('/api/create-vote', methods=['POST', 'GET'])
@app.route('/create-vote', methods=['POST', 'GET'])
@app.route('/', methods=['POST', 'GET'])
def create_vote(*args, **kwargs):
    # Lấy dữ liệu từ JSON body (POST) hoặc Query params (GET)
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
    else:
        data = request.args.to_dict()
        
    title = data.get('title') or data.get('question')
    if not title:
        return jsonify({"error": "Thiếu tham số 'title' hoặc 'question' (Tiêu đề biểu quyết)"}), 400
        
    # Danh sách lựa chọn mặc định: ["0", "+1", "+2", "+3", "+4"]
    options = data.get('options')
    if not options or not isinstance(options, list):
        options = ["0", "+1", "+2", "+3", "+4"]
        
    # Cho phép ẩn danh hay hiển thị tên người vote (mặc định là False để hiện tên người vote như hình)
    is_anonymous = data.get('is_anonymous', False)
    if isinstance(is_anonymous, str):
        is_anonymous = is_anonymous.lower() in ['true', '1', 'yes']
        
    # Có cho chọn nhiều phương án hay không (mặc định False)
    allows_multiple_answers = data.get('allows_multiple_answers', False)
    if isinstance(allows_multiple_answers, str):
        allows_multiple_answers = allows_multiple_answers.lower() in ['true', '1', 'yes']

    # Chat ID (Lấy từ param hoặc biến môi trường NOTI_CHAT_ID)
    chat_id = data.get('chat_id') or os.environ.get("NOTI_CHAT_ID")
    if not chat_id:
        return jsonify({"error": "Thiếu chat_id và chưa cấu hình biến môi trường NOTI_CHAT_ID"}), 400

    # Thread ID / Topic ID (Lấy từ param hoặc biến môi trường NOTI_TOPIC_ID / SUMMARY_TOPIC_ID)
    thread_id = data.get('thread_id') or data.get('topic_id') or os.environ.get("NOTI_TOPIC_ID") or os.environ.get("SUMMARY_TOPIC_ID")
    
    kwargs = {
        "chat_id": chat_id,
        "question": title,
        "options": options,
        "is_anonymous": bool(is_anonymous),
        "allows_multiple_answers": bool(allows_multiple_answers)
    }
    
    parsed_thread_id = None
    if thread_id:
        try:
            parsed_thread_id = int(thread_id)
            kwargs["message_thread_id"] = parsed_thread_id
        except ValueError:
            pass

    try:
        sent_message = bot.send_poll(**kwargs)
        
        # Lưu cuộc biểu quyết vào Database (Supabase)
        db_saved = False
        try:
            insert_poll(
                poll_id=sent_message.poll.id,
                message_id=sent_message.message_id,
                chat_id=int(chat_id),
                thread_id=parsed_thread_id,
                title=sent_message.poll.question,
                options=[opt.text for opt in sent_message.poll.options],
                is_anonymous=sent_message.poll.is_anonymous
            )
            db_saved = True
        except Exception as db_err:
            print(f"⚠️ Không thể lưu Poll vào DB (kiểm tra lại bảng 'polls'): {db_err}")

        return jsonify({
            "status": "success",
            "message": "Đã tạo vote thành công!",
            "db_saved": db_saved,
            "data": {
                "message_id": sent_message.message_id,
                "poll_id": sent_message.poll.id,
                "title": sent_message.poll.question,
                "options": [opt.text for opt in sent_message.poll.options],
                "is_anonymous": sent_message.poll.is_anonymous,
                "chat_id": chat_id,
                "thread_id": thread_id
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
