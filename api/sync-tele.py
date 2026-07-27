import os
import telebot
from flask import Flask, request, jsonify

app = Flask(__name__)
bot = telebot.TeleBot(os.environ.get("TELEGRAM_BOT_TOKEN", ""), threaded=False)

@app.route('/api/sync-tele', methods=['POST', 'GET'])
@app.route('/', methods=['POST', 'GET'])
def sync_tele_config():
    """
    API đồng bộ cấu hình Telegram Bot:
    1. Đăng ký Webhook URL của dự án với Telegram API (nhận poll_answer, message, callback_query).
    2. Cài đặt danh sách lệnh hiển thị trong ứng dụng Telegram (setMyCommands).
    """
    try:
        # Tự động lấy domain từ request hoặc VERCEL_URL
        host = request.headers.get("X-Forwarded-Host") or request.host
        scheme = request.headers.get("X-Forwarded-Proto", "https")
        webhook_url = f"{scheme}://{host}/api/webhook"

        # 1. Đặt Webhook với các loại update cần lắng nghe
        allowed_updates = ["message", "edited_message", "callback_query", "poll_answer", "poll"]
        webhook_res = bot.set_webhook(url=webhook_url, allowed_updates=allowed_updates)

        # 2. Cấu hình menu lệnh trên Telegram
        commands = [
            telebot.types.BotCommand("demnguoi", "Thống kê danh sách & tổng số suất đá bóng"),
            telebot.types.BotCommand("thanhtoan", "Xem danh sách thanh toán tiền sân"),
            telebot.types.BotCommand("open_ban", "Cấm/Mở chat thành viên"),
            telebot.types.BotCommand("create_vote", "Tạo biểu quyết đá bóng mới")
        ]
        bot.set_my_commands(commands)

        # 3. Lấy thông tin Bot và Webhook hiện tại
        bot_info = bot.get_me()
        webhook_info = bot.get_webhook_info()

        return jsonify({
            "status": "success",
            "message": "Đã đồng bộ cấu hình Telegram Bot thành công!",
            "bot": {
                "id": bot_info.id,
                "username": bot_info.username,
                "first_name": bot_info.first_name
            },
            "webhook": {
                "url": webhook_info.url,
                "pending_update_count": webhook_info.pending_update_count,
                "has_custom_certificate": webhook_info.has_custom_certificate,
                "allowed_updates": webhook_info.allowed_updates
            },
            "env_config": {
                "NOTI_CHAT_ID": os.environ.get("NOTI_CHAT_ID"),
                "NOTI_TOPIC_ID": os.environ.get("NOTI_TOPIC_ID"),
                "SUMMARY_TOPIC_ID": os.environ.get("SUMMARY_TOPIC_ID")
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
