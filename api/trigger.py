import os
import telebot
from flask import Flask, jsonify
from api.cron import check_and_send_payment

app = Flask(__name__)
bot = telebot.TeleBot(os.environ.get("TELEGRAM_BOT_TOKEN", ""), threaded=False)

@app.route('/api/trigger', methods=['GET'])
def trigger_cron_job():
    try:
        # Chỉ thực hiện kiểm tra và gửi thông báo thanh toán
        payment_sent = check_and_send_payment()

        return jsonify({
            "status": "success",
            "payment_sent": payment_sent,
            "message": "Đã thực hiện gửi thông báo thanh toán thành công"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
