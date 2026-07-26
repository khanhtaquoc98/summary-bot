import os
import requests
from flask import Flask, request, jsonify
from utils.supabase_client import get_poll_voters, SUPABASE_URL, _headers
from utils.bench_sync import parse_count_from_option_ids

app = Flask(__name__)

def get_latest_poll():
    """Lấy Poll mới nhất từ database Supabase"""
    url = f"{SUPABASE_URL}/rest/v1/polls"
    params = {
        "order": "created_at.desc",
        "limit": 1,
        "select": "*"
    }
    resp = requests.get(url, params=params, headers=_headers(), timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data[0] if data else None

def build_demnguoi_report(poll_info, answers):
    """Xây dựng dữ liệu đếm người và chuỗi Markdown thống kê"""
    poll_id = poll_info.get('poll_id')
    title = poll_info.get('title', 'Biểu quyết đá bóng')
    options_list = poll_info.get('options', ["0", "+1", "+2", "+3", "+4"])
    
    attending_players = []  # Danh sách tất cả các suất đá (cầu thủ + người thân)
    absent_users = []       # Danh sách người chọn 0 (bận)
    
    by_option = {}
    
    for ans in answers:
        user_name = ans.get('user_name', 'Unknown')
        option_ids = ans.get('option_ids', [])
        count = parse_count_from_option_ids(option_ids, options_list)
        
        opt_text = options_list[option_ids[0]] if (option_ids and option_ids[0] < len(options_list)) else f"+{count}"
        
        if opt_text not in by_option:
            by_option[opt_text] = []
        by_option[opt_text].append(user_name)
        
        if count > 0:
            attending_players.append(user_name)
            for i in range(1, count):
                attending_players.append(f"{user_name} {i}")
        else:
            absent_users.append(user_name)
            
    # Tạo văn bản Markdown hiển thị trên Telegram
    msg = f"⚽ *THỐNG KÊ ĐỂM NGƯỜI ĐÁ BÓNG*\n"
    msg += f"📌 *Tiêu đề:* {title}\n\n"
    msg += f"🔥 *Tổng số suất đá:* *{len(attending_players)} suất* ({len(answers) - len(absent_users)} người đi, {len(absent_users)} người bận)\n\n"
    
    if attending_players:
        msg += "-----------------------------------\n"
        msg += "✅ *DANH SÁCH CẦU THỦ THAM GIA:*\n"
        for idx, p in enumerate(attending_players, 1):
            msg += f"{idx}. {p}\n"
            
    if absent_users:
        msg += "\n-----------------------------------\n"
        msg += f"❌ *BẬN / KHÔNG ĐI ({len(absent_users)} người):*\n"
        for p in absent_users:
            msg += f"• {p}\n"
            
    return {
        "poll_id": poll_id,
        "title": title,
        "total_slots": len(attending_players),
        "total_voters": len(answers),
        "attending_count": len(answers) - len(absent_users),
        "absent_count": len(absent_users),
        "attending_players": attending_players,
        "absent_users": absent_users,
        "by_option": by_option,
        "markdown_text": msg
    }

@app.route('/api/demnguoi', methods=['GET', 'POST'])
def demnguoi_api():
    """API lấy kết quả đếm người đá bóng"""
    try:
        poll_info = get_latest_poll()
        if not poll_info:
            return jsonify({"error": "Chưa có thông tin biểu quyết nào trong database"}), 404
            
        answers = get_poll_voters(str(poll_info['poll_id']))
        report = build_demnguoi_report(poll_info, answers)
        
        return jsonify({
            "status": "success",
            "data": report
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
