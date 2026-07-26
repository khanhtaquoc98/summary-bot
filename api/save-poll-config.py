import os
from flask import Flask, request, jsonify
from utils.supabase_client import insert_poll, clear_all_poll_answers

app = Flask(__name__)

@app.route('/api/save-poll-config', methods=['POST', 'GET'])
def save_poll_config():
    """
    API tiếp nhận thông tin cấu hình vote từ bên ngoài, lưu/append vào Database (Supabase polls table)
    và xoá toàn bộ dữ liệu lượt vote cũ trong poll_answers.
    """
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
    else:
        data = request.args.to_dict()
        
    poll_id = data.get('poll_id')
    title = data.get('title')
    
    if not poll_id or not title:
        return jsonify({"error": "Thiếu các thông tin bắt buộc: 'poll_id' và 'title'"}), 400
        
    message_id = data.get('message_id')
    chat_id = data.get('chat_id')
    thread_id = data.get('thread_id')
    options = data.get('options') or ["0", "+1", "+2", "+3", "+4"]
    is_anonymous = data.get('is_anonymous', False)
    clear_old = data.get('clear_old', True)
    
    if isinstance(is_anonymous, str):
        is_anonymous = is_anonymous.lower() in ['true', '1', 'yes']

    try:
        # 1. Lưu cấu hình Poll mới/cập nhật vào bảng polls
        insert_poll(
            poll_id=str(poll_id),
            message_id=int(message_id) if message_id is not None else None,
            chat_id=int(chat_id) if chat_id is not None else None,
            thread_id=int(thread_id) if thread_id is not None else None,
            title=str(title),
            options=options if isinstance(options, list) else ["0", "+1", "+2", "+3", "+4"],
            is_anonymous=bool(is_anonymous)
        )
        
        # 2. Xoá tất cả lượt vote cũ trong bảng poll_answers
        answers_cleared = False
        if clear_old:
            try:
                clear_all_poll_answers()
                answers_cleared = True
            except Exception as clear_err:
                print(f"⚠️ Không thể xoá dữ liệu vote cũ: {clear_err}")

        return jsonify({
            "status": "success",
            "message": "Đã lưu cấu hình Vote và xoá dữ liệu vote cũ thành công!",
            "answers_cleared": answers_cleared,
            "data": {
                "poll_id": str(poll_id),
                "message_id": message_id,
                "chat_id": chat_id,
                "thread_id": thread_id,
                "title": title,
                "options": options,
                "is_anonymous": is_anonymous
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

