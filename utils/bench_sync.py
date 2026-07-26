import requests
from utils.supabase_client import get_user_poll_answer, get_poll_by_id

BENCH_BULK_API_URL = "https://cham-het-fc-team.vercel.app/api/match/bench/bulk"

def parse_count_from_option_ids(option_ids, options_list):
    """Quy đổi option_ids thành số lượng người (+0, +1, +2, +3, +4...)"""
    if not option_ids:
        return 0
    opt_idx = option_ids[0]
    if options_list and opt_idx < len(options_list):
        text = str(options_list[opt_idx]).strip()
        if text.startswith('+'):
            text = text[1:]
        if text.isdigit():
            return int(text)
    return opt_idx

def sync_vote_to_bench(poll_id: str, user, new_option_ids: list):
    """
    So sánh trạng thái vote cũ và mới, sau đó tự động gọi API https://cham-het-fc-team.vercel.app/api/match/bench/bulk
    để thêm/bớt cầu thủ vào danh sách thi đấu.
    """
    try:
        user_id = user.id
        user_id_str = str(user_id)
        username = getattr(user, 'username', None)
        telegram_handle = f"@{username.lstrip('@')}" if username else None
        
        first_name = getattr(user, 'first_name', None)
        full_name = getattr(user, 'full_name', None)
        base_name = first_name or full_name or username or f"User_{user_id}"
        
        # 1. Lấy vote cũ của user và thông tin Poll từ Supabase
        old_answer = get_user_poll_answer(str(poll_id), user_id)
        poll_info = get_poll_by_id(str(poll_id))
        
        options_list = poll_info.get("options") if poll_info else ["0", "+1", "+2", "+3", "+4"]
        old_option_ids = old_answer.get("option_ids") if old_answer else []
        
        # 2. Quy đổi thành số lượng (old_count vs new_count)
        old_count = parse_count_from_option_ids(old_option_ids, options_list)
        new_count = parse_count_from_option_ids(new_option_ids, options_list)
        
        # Nếu số lượng không đổi thì không cần gọi API
        if old_count == new_count:
            print(f"ℹ️ Lượt vote của {base_name} không thay đổi số lượng ({old_count}). Bỏ qua gọi bench API.")
            return
            
        # Dựng đối tượng main user
        main_user_obj = {
            "name": base_name,
            "telegramId": user_id_str
        }
        if telegram_handle:
            main_user_obj["telegramHandle"] = telegram_handle
            
        def make_guest_obj(index: int):
            return {"name": f"{base_name} {index}"}
            
        players = []
        player_out = []
        
        # 3. Tính danh sách `players` mới (nếu new_count > 0)
        if new_count > 0:
            players.append(main_user_obj)
            for i in range(1, new_count):
                players.append(make_guest_obj(i))
                
        # 4. Tính danh sách `playerOut` bị loại bớt
        if old_count > new_count:
            if new_count == 0:
                # Bỏ chọn hẳn -> main user out và toàn bộ guest cũ out
                player_out.append(main_user_obj)
                for i in range(1, old_count):
                    player_out.append(make_guest_obj(i))
            else:
                # Giảm số lượng (VD +3 -> +1) -> chỉ các guest dư ra bị out
                for i in range(new_count, old_count):
                    player_out.append(make_guest_obj(i))
                    
        payload = {
            "players": players,
            "playerOut": player_out
        }
        
        print(f"🔄 Đồng bộ bench API cho {base_name} (Vote thay đổi {old_count} -> {new_count}): {payload}")
        
        # 5. Gọi API bench bulk
        resp = requests.post(
            BENCH_BULK_API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        print(f"✅ Kết quả bench API: HTTP {resp.status_code} - {resp.text}")
        
    except Exception as e:
        print(f"❌ Lỗi khi đồng bộ vote sang bench API: {e}")
