import os
import requests
import telebot
from flask import Flask, request, jsonify

app = Flask(__name__)
bot = telebot.TeleBot(os.environ.get("TELEGRAM_BOT_TOKEN", ""), threaded=False)

def check_and_send_payment():
    """Kiểm tra và gửi thông báo thanh toán tiền sân"""
    try:
        resp = requests.get("https://cham-het-fc-team.vercel.app/api/payment/check-paid", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            unpaidAmount = data.get('unpaidAmount', 0)
            if unpaidAmount > 0:
                totalCount = data.get('totalCount', 0)
                paidCount = data.get('paidCount', 0)
                unpaidCount = data.get('unpaidCount', 0)
                totalAmount = data.get('totalAmount', 0)
                paidAmount = data.get('paidAmount', 0)
                unpaidPlayers = data.get('unpaidPlayers', [])
                
                msg_text = (
                    f"📊 *THÔNG TIN THANH TOÁN*\n\n"
                    f"👥 Tổng cầu thủ: {totalCount} ({paidCount} đã đóng, {unpaidCount} chưa đóng)\n"
                    f"💰 Tổng tiền: {totalAmount:,.0f}đ\n"
                    f"✅ Đã thu: {paidAmount:,.0f}đ\n"
                    f"⚠️ Chưa thu: {unpaidAmount:,.0f}đ\n"
                    f"🔗 Link thanh toán: https://cham-het-fc-team.vercel.app/payment\n"
                    f"📋 *Danh sách chưa thanh toán ({len(unpaidPlayers)} người):*\n"
                )
                for idx, p in enumerate(unpaidPlayers, 1):
                    name = p.get('playerName', 'Unknown')
                    team = p.get('teamName', 'Unknown')
                    amount = p.get('totalAmount', 0)
                    msg_text += f"{idx}. {name} ({team}): {amount:,.0f}đ\n"
                
                target_chat_id = os.environ.get("NOTI_CHAT_ID")
                if target_chat_id:
                    thread_id = os.environ.get("PAYMENT_TOPIC_ID") or os.environ.get("NOTI_TOPIC_ID")
                    kwargs = {"parse_mode": "Markdown"}
                    if thread_id:
                        try:
                            kwargs["message_thread_id"] = int(thread_id)
                        except ValueError:
                            pass
                    bot.send_message(target_chat_id, msg_text, **kwargs)
                    print("✅ Đã gửi thông báo thanh toán tiền sân")
                    return True
    except Exception as e:
        print(f"Lỗi khi check payment thông tin: {e}")
    return False

@app.route('/api/cron', methods=['GET'])
def cron_job():
    # Xác thực CRON_SECRET từ Vercel để tránh bị trigger lậu
    auth_header = request.headers.get('Authorization')
    if auth_header != f"Bearer {os.environ.get('CRON_SECRET')}":
        return jsonify({"error": "Unauthorized"}), 401

    try:
        # Chỉ kiểm tra và gửi thông báo thanh toán
        payment_sent = check_and_send_payment()

        return jsonify({
            "status": "success",
            "payment_sent": payment_sent,
            "message": "Đã thực hiện gửi thông báo thanh toán thành công"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
