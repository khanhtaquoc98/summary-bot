import os
import requests
from flask import Flask, request, jsonify
from utils.supabase_client import get_poll_voters, get_poll_by_id, SUPABASE_URL, _headers
from utils.bench_sync import parse_count_from_option_ids, BENCH_BULK_API_URL

app = Flask(__name__)

def get_latest_poll():
    """Lấy cuộc biểu quyết mới nhất từ Supabase"""
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

@app.route('/api/sync-vote', methods=['POST', 'GET'])
def sync_vote():
    """
    API đồng bộ lại toàn bộ dữ liệu vote từ Supabase sang Bench Bulk API.
    Cho phép truyền poll_id (nếu không truyền sẽ tự lấy Poll mới nhất).
    """
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
    else:
        data = request.args.to_dict()
        
    poll_id = data.get('poll_id')
    
    try:
        # 1. Lấy thông tin Poll
        if poll_id:
            poll_info = get_poll_by_id(str(poll_id))
        else:
            poll_info = get_latest_poll()
            
        if not poll_info:
            return jsonify({"error": "Không tìm thấy dữ liệu Poll nào trong database"}), 444 if poll_id else 404
            
        target_poll_id = str(poll_info['poll_id'])
        options_list = poll_info.get('options', ["0", "+1", "+2", "+3", "+4"])
        
        # 2. Lấy tất cả lượt vote của Poll này
        answers = get_poll_voters(target_poll_id)
        
        players = []
        player_out = []
        
        for ans in answers:
            user_id_str = str(ans.get('user_id', ''))
            user_name = ans.get('user_name', 'Unknown')
            option_ids = ans.get('option_ids', [])
            
            count = parse_count_from_option_ids(option_ids, options_list)
            
            main_user_obj = {
                "name": user_name,
                "telegramId": user_id_str
            }
            
            if count > 0:
                players.append(main_user_obj)
                for i in range(1, count):
                    players.append({"name": f"{user_name} {i}"})
            else:
                player_out.append(main_user_obj)
                
        payload = {
            "players": players,
            "playerOut": player_out
        }
        
        # 3. Gọi API Bench Bulk
        resp = requests.post(
            BENCH_BULK_API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        return jsonify({
            "status": "success",
            "message": "Đã đồng bộ thành công dữ liệu vote sang bench API",
            "poll_id": target_poll_id,
            "poll_title": poll_info.get('title'),
            "total_voters": len(answers),
            "players_count": len(players),
            "player_out_count": len(player_out),
            "bench_api_response": {
                "http_code": resp.status_code,
                "body": resp.text
            },
            "synced_payload": payload
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
