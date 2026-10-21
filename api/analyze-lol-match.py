import os
import json
import urllib.request
import urllib.error
from flask import Flask, request, jsonify, make_response

app = Flask(__name__)

ROLES_ORDER = ["TOP", "JG", "MID", "AD", "SP"]

ROLE_VI_NAME = {
    "TOP": "đường trên",
    "JG": "đi rừng",
    "MID": "đường giữa",
    "AD": "xạ thủ đường dưới",
    "SP": "hỗ trợ",
}

ROLE_ARCHETYPE_VI = {
    "TOP": "đấu sĩ / tiên phong đường trên",
    "JG": "người đi rừng kiểm soát nhịp độ",
    "MID": "chủ lực đường giữa",
    "AD": "xạ thủ chủ lực",
    "SP": "hỗ trợ kiểm soát tầm nhìn & mở giao tranh",
}


def build_lol_analysis_prompt(match: dict, focused_player: dict) -> str:
    duration_sec = match.get("gameDurationSeconds", 1800)
    duration_min = round(duration_sec / 60, 1)
    blue_team = match.get("blueTeam", {})
    red_team = match.get("redTeam", {})

    def format_team(team: dict, label: str) -> str:
        win_str = "THẮNG" if team.get("win") else "THUA"
        objs = team.get("objectives", {})
        header = (
            f"{label} ({win_str} | Tổng mạng: {team.get('totalKills', 0)} | "
            f"Tổng vàng: {team.get('totalGold', 0)} | "
            f"Baron: {objs.get('baron', 0)}, Rồng: {objs.get('dragon', 0)}, "
            f"Sâu Hư Không: {objs.get('horde', 0)}, Trụ: {objs.get('tower', 0)})"
        )
        rows = []
        for p in team.get("participants", []):
            kills = p.get("kills", 0)
            deaths = p.get("deaths", 0)
            assists = p.get("assists", 0)
            kda_val = float(p.get("kda", 0))
            spree = p.get("largestKillingSpree", max(0, kills - 1))
            pink_wards = p.get("visionWardsBoughtInGame", 0)
            rows.append(
                f"  - [{p.get('role')}] {p.get('riotIdGameName')}#{p.get('riotIdTagline')} "
                f"({p.get('championName')}): KDA {kda_val:.2f} ({kills}/{deaths}/{assists}), "
                f"Chuỗi hạ gục lớn nhất: {spree}, "
                f"Sát thương lên tướng: {p.get('totalDamageDealtToChampions', 0)} "
                f"({p.get('damageShare', 0)}% đội), Vàng: {p.get('goldEarned', 0)}, "
                f"Lính (CS): {p.get('cs', 0)} ({p.get('csPerMin', 0)}/p), "
                f"Mắt kiểm soát đã mua: {pink_wards}, "
                f"Điểm tầm nhìn: {p.get('visionScore', 0)} (Cắm {p.get('wardsPlaced', 0)}/Phá {p.get('wardsKilled', 0)}), "
                f"Tham gia hạ gục (KP): {p.get('killParticipation', 0)}%, "
                f"Điểm OP: {p.get('mvpScore', 0)}"
            )
        return header + "\n" + "\n".join(rows)

    focused_name = f"{focused_player.get('riotIdGameName', 'Player')}#{focused_player.get('riotIdTagline', 'VN2')}"
    focused_champ = focused_player.get("championName", "Unknown")
    focused_role = focused_player.get("role", "TOP")
    role_vi = ROLE_VI_NAME.get(focused_role, focused_role)
    archetype_vi = ROLE_ARCHETYPE_VI.get(focused_role, "người chơi chủ chốt")
    f_kills = focused_player.get("kills", 0)
    f_deaths = focused_player.get("deaths", 0)
    f_assists = focused_player.get("assists", 0)
    f_kda = float(focused_player.get("kda", 0))
    f_spree = focused_player.get("largestKillingSpree", max(0, f_kills - 1))
    f_dmg = focused_player.get("totalDamageDealtToChampions", 0)
    f_cs = focused_player.get("cs", 0)
    f_gold = focused_player.get("goldEarned", 0)
    f_pink = focused_player.get("visionWardsBoughtInGame", 0)

    return f"""# ROLE
Bạn là Huấn luyện viên trưởng (Head Coach) & Chuyên gia phân tích dữ liệu Liên Minh Huyền Thoại cấp độ Thách Đấu.
Nhiệm vụ của bạn là phân tích sâu trận đấu dưới đây bằng tiếng Việt chuẩn thuật ngữ LMHT và trả về DUY NHẤT một chuỗi JSON hợp lệ.

# DỮ LIỆU TRẬN ĐẤU
- Mã trận: {match.get('matchId', 'UNKNOWN')} ({match.get('queueName', 'Ranked')})
- Thời lượng: {duration_min} phút | Phiên bản: {match.get('gameVersion', '14.24')}
- Thành viên trọng tâm cần đánh giá chi tiết: {focused_name} (Tướng: {focused_champ} - Vị trí: {role_vi})

{format_team(blue_team, "ĐỘI XANH (BLUE TEAM - teamId 100)")}

{format_team(red_team, "ĐỘI ĐỎ (RED TEAM - teamId 200)")}

# HƯỚNG DẪN ĐẶC BIỆT CHO PHẦN "focusedPlayerReview" (Đánh giá thành viên {focused_name})
Hãy viết lời nhận xét xưng "Bạn", trích dẫn số liệu chính xác từ trận đấu theo đúng phong cách mẫu sau:
- "summary": "Trong trận đấu này, {focused_name} đã có một màn trình diễn [rất ấn tượng / đầy nỗ lực / ...] với vị tướng {focused_champ} ở {role_vi}, [góp công lớn vào chiến thắng của đội / nỗ lực giữ thế trận cho đội / ...]."
- "strengths" (✨ Điểm mạnh - 2 đến 3 gạch đầu dòng):
  + So sánh tổng sát thương lên tướng địch ({f_dmg}) với các thành viên trong đội và cả trận (ví dụ: "Bạn là nguồn sát thương chủ lực của đội với tổng sát thương lên tướng địch cao nhất ({f_dmg}), vượt xa các thành viên khác.").
  + Nêu bật chỉ số KDA {f_kda:.2f} ({f_kills}/{f_deaths}/{f_assists}) và chuỗi hạ gục lớn nhất ({f_spree}) hoặc tỷ lệ tham gia hạ gục ({focused_player.get('killParticipation', 0)}%).
  + Nêu khả năng kiểm soát tài nguyên với {f_cs} lính và lượng vàng ({f_gold}) so với toàn đội/cả trận để sớm hoàn thành các trang bị quan trọng.
- "weaknesses" (💡 Điểm cần cải thiện - 1 đến 2 gạch đầu dòng):
  + Kiểm tra số Mắt kiểm soát đã mua ({f_pink}). Nếu bằng 0, BẮT BUỘC nhận xét: "Mặc dù là người chơi xuất sắc, nhưng bạn không mua bất kỳ Mắt kiểm soát nào trong suốt trận đấu. Việc thiếu tầm nhìn kiểm soát có thể khiến bạn gặp nguy hiểm khi đẩy cao hoặc bỏ lỡ cơ hội bắt lẻ đối phương."
  + Nêu thêm điểm cần cải thiện về số lần nằm xuống ({f_deaths}), CS/phút hoặc chênh lệch với đối thủ cùng đường nếu có.
- "actionableAdvice" (🎮 Lời khuyên cải thiện - 1 đến 2 lời khuyên thực tế):
  + Gắn trực tiếp với vai trò {archetype_vi} như {focused_champ} (ví dụ: "Với vai trò là một {archetype_vi} như {focused_champ}, việc đầu tư vào Mắt kiểm soát là cực kỳ cần thiết để kiểm soát các mục tiêu lớn và đảm bảo an toàn cho bản thân khi đi lẻ. Hãy tập thói quen mua ít nhất một hoặc hai mắt mỗi khi về nhà.").

# YÊU CẦU ĐẦU RA (JSON SCHEMA BẮT BUỘC)
Trả về JSON đúng cấu trúc sau (không bọc markdown, không giải thích ngoài JSON):
{{
  "overview": "Đoạn văn 2-3 câu tóm tắt cục diện, nhịp độ trận đấu và chênh lệch giữa 2 đội",
  "winConditionSummary": "Phân tích rõ điều kiện thắng và bước ngoặt giúp đội thắng giành chiến thắng",
  "mvpPlayer": {{
    "name": "Tên#Tag của MVP đội thắng",
    "champion": "Tên tướng MVP",
    "role": "TOP|JG|MID|AD|SP",
    "reason": "Lý do cụ thể kèm số liệu (KDA, sát thương, KP, mục tiêu)"
  }},
  "svpPlayer": {{
    "name": "Tên#Tag của SVP đội thua",
    "champion": "Tên tướng SVP",
    "role": "TOP|JG|MID|AD|SP",
    "reason": "Lý do cụ thể kèm số liệu nổi bật nhất bên đội thua"
  }},
  "focusedPlayerReview": {{
    "playerName": "{focused_name}",
    "champion": "{focused_champ}",
    "role": "{focused_role}",
    "grade": "S+|S|A|B|C",
    "summary": "Trong trận đấu này, {focused_name} đã có một màn trình diễn ... với vị tướng {focused_champ} ở {role_vi}, ...",
    "strengths": [
      "Điểm mạnh cụ thể 1 kèm số liệu so sánh",
      "Điểm mạnh cụ thể 2 kèm KDA và chuỗi hạ gục",
      "Điểm mạnh cụ thể 3 kèm số lính và lượng vàng"
    ],
    "weaknesses": [
      "Điểm cần cải thiện cụ thể 1 (kiểm tra Mắt kiểm soát đã mua, số mạng nằm xuống...)"
    ],
    "actionableAdvice": [
      "Lời khuyên cải thiện gắn với vai trò và chất tướng {focused_champ}"
    ]
  }},
  "laneComparisons": [
    {{
      "role": "TOP",
      "blueChampion": "Tướng Top đội xanh",
      "redChampion": "Tướng Top đội đỏ",
      "winnerTeam": 100,
      "verdict": "Nhận xét kèo đấu Top giữa 2 người chơi kèm chênh lệch vàng/sát thương/KDA"
    }},
    {{
      "role": "JG",
      "blueChampion": "Tướng Rừng đội xanh",
      "redChampion": "Tướng Rừng đội đỏ",
      "winnerTeam": 100,
      "verdict": "Nhận xét kèo đấu Rừng"
    }},
    {{
      "role": "MID",
      "blueChampion": "Tướng Mid đội xanh",
      "redChampion": "Tướng Mid đội đỏ",
      "winnerTeam": 100,
      "verdict": "Nhận xét kèo đấu Mid"
    }},
    {{
      "role": "AD",
      "blueChampion": "Tướng AD đội xanh",
      "redChampion": "Tướng AD đội đỏ",
      "winnerTeam": 100,
      "verdict": "Nhận xét kèo đấu Xạ Thủ"
    }},
    {{
      "role": "SP",
      "blueChampion": "Tướng SP đội xanh",
      "redChampion": "Tướng SP đội đỏ",
      "winnerTeam": 100,
      "verdict": "Nhận xét kèo đấu Hỗ Trợ & kiểm soát tầm nhìn"
    }}
  ],
  "macroInsights": [
    "Nhận xét Macro toàn đội 1 (Kiểm soát Rồng/Baron/Sâu Hư Không)",
    "Nhận xét Macro toàn đội 2 (Chuyển hóa vàng & phá trụ)",
    "Nhận xét Macro toàn đội 3 (Kiểm soát tầm nhìn & giao tranh tổng)"
  ],
  "allPlayerReviews": [
    {{
      "puuid": "puuid người chơi",
      "playerName": "Tên#Tag",
      "champion": "Tên tướng",
      "role": "TOP|JG|MID|AD|SP",
      "grade": "S+|S|A|B|C",
      "summary": "Nhận xét thực tế màn trình diễn gắn với chất tướng và kèo đối đầu cùng đường",
      "strengths": ["Điểm làm tốt 1", "Điểm làm tốt 2"],
      "weaknesses": ["Điểm cần cải thiện 1", "Điểm cần cải thiện 2"],
      "actionableAdvice": ["Lời khuyên thực chiến 1", "Lời khuyên thực chiến 2"]
    }}
  ]
}}"""


def build_fallback_analysis(match: dict, focused: dict) -> dict:
    """Fallback phân tích chiến thuật chi tiết nếu chưa có GROQ_API_KEY hoặc hết quota"""
    blue_team = match.get("blueTeam", {})
    red_team = match.get("redTeam", {})
    winning_team = blue_team if blue_team.get("win") else red_team
    losing_team = red_team if blue_team.get("win") else blue_team

    win_parts = winning_team.get("participants", [])
    lose_parts = losing_team.get("participants", [])
    all_parts = blue_team.get("participants", []) + red_team.get("participants", [])

    mvp = sorted(win_parts, key=lambda x: x.get("mvpScore", 0), reverse=True)[0] if win_parts else focused
    svp = sorted(lose_parts, key=lambda x: x.get("mvpScore", 0), reverse=True)[0] if lose_parts else focused

    gold_diff = abs(blue_team.get("totalGold", 0) - red_team.get("totalGold", 0))
    duration_min = round(match.get("gameDurationSeconds", 1800) / 60)

    lane_comparisons = []
    for role in ROLES_ORDER:
        bp = next((p for p in blue_team.get("participants", []) if p.get("role") == role), None)
        rp = next((p for p in red_team.get("participants", []) if p.get("role") == role), None)
        if not bp or not rp:
            continue
        score_diff = bp.get("mvpScore", 0) - rp.get("mvpScore", 0)
        gold_gap = abs(bp.get("goldEarned", 0) - rp.get("goldEarned", 0))
        winner_team = "EVEN" if abs(score_diff) < 4 else (100 if score_diff > 0 else 200)
        wp = bp if winner_team == 100 else rp
        lp = rp if winner_team == 100 else bp

        verdict = (
            f"Kèo đấu cân bằng giữa {bp.get('championName')} và {rp.get('championName')} (chênh lệch {gold_gap:,} vàng)."
            if winner_team == "EVEN"
            else f"{wp.get('championName')} ({wp.get('riotIdGameName')}) thắng thế trước {lp.get('championName')} với KDA {wp.get('kills')}/{wp.get('deaths')}/{wp.get('assists')}, gác +{gold_gap:,} vàng."
        )
        lane_comparisons.append({
            "role": role,
            "blueChampion": bp.get("championName", ""),
            "redChampion": rp.get("championName", ""),
            "winnerTeam": winner_team,
            "verdict": verdict,
        })

    mvp_score = float(focused.get("mvpScore", 75))
    grade = "S+" if mvp_score >= 92 else "S" if mvp_score >= 84 else "A" if mvp_score >= 74 else "B" if mvp_score >= 62 else "C"

    player_team = blue_team if focused.get("teamId") == 100 else red_team
    enemy_team = red_team if focused.get("teamId") == 100 else blue_team
    team_parts = player_team.get("participants", [])
    opponent = next((p for p in enemy_team.get("participants", []) if p.get("role") == focused.get("role")), None)

    team_by_dmg = sorted(team_parts, key=lambda x: x.get("totalDamageDealtToChampions", 0), reverse=True)
    match_by_dmg = sorted(all_parts, key=lambda x: x.get("totalDamageDealtToChampions", 0), reverse=True)
    match_by_cs = sorted(all_parts, key=lambda x: x.get("cs", 0), reverse=True)
    team_by_cs = sorted(team_parts, key=lambda x: x.get("cs", 0), reverse=True)
    match_by_gold = sorted(all_parts, key=lambda x: x.get("goldEarned", 0), reverse=True)
    team_by_gold = sorted(team_parts, key=lambda x: x.get("goldEarned", 0), reverse=True)

    f_puuid = focused.get("puuid")
    dmg_rank_team = next((i + 1 for i, p in enumerate(team_by_dmg) if p.get("puuid") == f_puuid), 1)
    dmg_rank_match = next((i + 1 for i, p in enumerate(match_by_dmg) if p.get("puuid") == f_puuid), 1)
    cs_rank_match = next((i + 1 for i, p in enumerate(match_by_cs) if p.get("puuid") == f_puuid), 1)
    cs_rank_team = next((i + 1 for i, p in enumerate(team_by_cs) if p.get("puuid") == f_puuid), 1)
    gold_rank_match = next((i + 1 for i, p in enumerate(match_by_gold) if p.get("puuid") == f_puuid), 1)
    gold_rank_team = next((i + 1 for i, p in enumerate(team_by_gold) if p.get("puuid") == f_puuid), 1)

    full_tag = f"{focused.get('riotIdGameName')}#{focused.get('riotIdTagline')}"
    role_code = focused.get("role", "TOP")
    role_vi = ROLE_VI_NAME.get(role_code, role_code)
    archetype_vi = ROLE_ARCHETYPE_VI.get(role_code, "người chơi chủ chốt")
    champ_name = focused.get("championName", "")
    kills = int(focused.get("kills", 0))
    deaths = int(focused.get("deaths", 0))
    assists = int(focused.get("assists", 0))
    kda_val = float(focused.get("kda", 0))
    dmg_val = int(focused.get("totalDamageDealtToChampions", 0))
    dmg_share = focused.get("damageShare", 0)
    cs_val = int(focused.get("cs", 0))
    cs_per_min = focused.get("csPerMin", 0)
    gold_val = int(focused.get("goldEarned", 0))
    kp_val = focused.get("killParticipation", 0)
    spree = int(focused.get("largestKillingSpree", max(3, kills - 2) if kills >= 3 else kills))
    items_list = focused.get("items", [])
    control_wards = focused.get(
        "visionWardsBoughtInGame",
        2 if 2055 in items_list else (3 if role_code in ["SP", "JG"] else 0),
    )

    if focused.get("win"):
        if mvp_score >= 82 or dmg_rank_team <= 2 or kda_val >= 3.0:
            summary = f"Trong trận đấu này, {full_tag} đã có một màn trình diễn rất ấn tượng với vị tướng {champ_name} ở {role_vi}, góp công lớn vào chiến thắng của đội."
        else:
            summary = f"Trong trận đấu này, {full_tag} đã có một màn trình diễn tròn vai và gắn kết với vị tướng {champ_name} ở {role_vi}, đóng góp tích cực vào chiến thắng chung của toàn đội."
    else:
        if mvp_score >= 75 or dmg_rank_team == 1 or kda_val >= 3.0:
            summary = f"Trong trận đấu này, dù đội nhà chưa thể giành chiến thắng nhưng {full_tag} vẫn có một màn trình diễn đầy nỗ lực và nổi bật với vị tướng {champ_name} ở {role_vi}."
        else:
            summary = f"Trong trận đấu này, {full_tag} với vị tướng {champ_name} ở {role_vi} đã trải qua một ván đấu nhiều thử thách trước áp lực lớn từ đội hình đối phương."

    strengths = []
    weaknesses = []
    actionable_advice = []

    if dmg_rank_match == 1:
        strengths.append(
            f"Bạn là nguồn sát thương chủ lực của đội với tổng sát thương lên tướng địch cao nhất ({dmg_val}), vượt xa các thành viên khác."
        )
    elif dmg_rank_team == 1:
        strengths.append(
            f"Bạn là nguồn sát thương chủ lực của đội với tổng sát thương lên tướng địch cao nhất đội ({dmg_val}, chiếm {dmg_share}% tổng sát thương)."
        )
    elif dmg_rank_team == 2 and role_code != "SP":
        strengths.append(
            f"Bạn đóng góp lượng sát thương đầu ra rất lớn cho đội hình với tổng sát thương lên tướng địch đạt {dmg_val} (cao thứ 2 toàn đội, chiếm {dmg_share}%)."
        )
    elif role_code == "SP":
        strengths.append(
            f"Bạn làm rất tốt nhiệm vụ kiến tạo và bảo kê với {assists} điểm hỗ trợ (tham gia {kp_val}% tổng mạng hạ gục của đội) cùng {focused.get('visionScore', 0)} điểm tầm nhìn."
        )

    if kda_val >= 3.0 or kills >= 6:
        spree_clause = (
            f" và việc đạt được chuỗi hạ gục lớn nhất là {spree}"
            if spree >= 3
            else f" cùng tỷ lệ tham gia hạ gục đạt {kp_val}%"
        )
        strengths.append(
            f"Khả năng gánh đội của bạn thể hiện rõ qua chỉ số KDA {kda_val:.2f} ({kills}/{deaths}/{assists}){spree_clause}."
        )
    else:
        strengths.append(
            f"Khả năng phối hợp giao tranh của bạn thể hiện qua chỉ số KDA {kda_val:.2f} ({kills}/{deaths}/{assists}) và tỷ lệ tham gia hạ gục đạt {kp_val}%."
        )

    if role_code != "SP":
        cs_rank_str = (
            "dẫn đầu cả trận đấu"
            if cs_rank_match == 1
            else ("dẫn đầu toàn đội" if cs_rank_team == 1 else f"đạt hiệu suất {cs_per_min} lính/phút")
        )
        gold_rank_str = (
            f"giúp bạn có lượng vàng cao nhất ({gold_val})"
            if gold_rank_match == 1
            else (
                f"giúp bạn có lượng vàng cao nhất đội ({gold_val})"
                if gold_rank_team == 1
                else f"giúp bạn tích lũy được lượng vàng ổn định ({gold_val})"
            )
        )
        strengths.append(
            f"Bạn kiểm soát tài nguyên rất tốt với {cs_val} lính, {cs_rank_str}, {gold_rank_str} để sớm hoàn thành các trang bị quan trọng."
        )
    else:
        strengths.append(
            f"Bạn kiểm soát tầm nhìn bản đồ hiệu quả với {focused.get('wardsPlaced', 0)} mắt cắm ra và {focused.get('wardsKilled', 0)} mắt địch bị phá hủy, tích lũy {gold_val} vàng."
        )

    if control_wards == 0:
        prefix = "Mặc dù là người chơi xuất sắc, nhưng bạn" if (mvp_score >= 78 or kda_val >= 3.0) else "Trong suốt ván đấu, bạn"
        weaknesses.append(
            f"{prefix} không mua bất kỳ Mắt kiểm soát nào trong suốt trận đấu. Việc thiếu tầm nhìn kiểm soát có thể khiến bạn gặp nguy hiểm khi đẩy cao hoặc bỏ lỡ cơ hội bắt lẻ đối phương."
        )
    elif control_wards == 1 and role_code in ["JG", "SP", "MID"]:
        weaknesses.append(
            f"Bạn chỉ mua duy nhất 1 Mắt kiểm soát trong suốt {duration_min} phút thi đấu. Việc đầu tư ít mắt kiểm soát làm giảm khả năng chiếm bụi cỏ chiến thuật quanh khu vực mục tiêu lớn."
        )

    if deaths >= 6:
        weaknesses.append(
            f"Số lần nằm xuống của bạn còn khá cao ({deaths} lần bị hạ gục), khiến nhịp độ đẩy đường và kiểm soát tài nguyên đôi lúc bị gián đoạn."
        )
    elif opponent and opponent.get("goldEarned", 0) > gold_val + 800:
        gap = opponent.get("goldEarned", 0) - gold_val
        weaknesses.append(
            f"Bạn để đối thủ cùng đường là {opponent.get('championName')} tạo khoảng cách {gap} vàng ({gold_val} so với {opponent.get('goldEarned', 0)}), gây bất lợi trong các pha đối đầu."
        )

    if not weaknesses:
        weaknesses.append(
            f"Mặc dù giữ chỉ số cá nhân rất tốt ({kills}/{deaths}/{assists}), bạn vẫn có thể gia tăng thêm điểm tầm nhìn ({focused.get('visionScore', 0)}) và chủ động kêu gọi đồng đội ép sớm các mục tiêu lớn."
        )

    if control_wards == 0:
        actionable_advice.append(
            f"Với vai trò là một {archetype_vi} như {champ_name}, việc đầu tư vào Mắt kiểm soát là cực kỳ cần thiết để kiểm soát các mục tiêu lớn và đảm bảo an toàn cho bản thân khi đi lẻ. Hãy tập thói quen mua ít nhất một hoặc hai mắt mỗi khi về nhà."
        )
    else:
        actionable_advice.append(
            f"Với vai trò là một {archetype_vi} như {champ_name}, hãy duy trì việc cắm Mắt kiểm soát ở các bụi cỏ trọng yếu trước khi Rồng hoặc Baron ra mắt 45 giây để tạo thế chủ động bắt lẻ và ép giao tranh cho toàn đội."
        )

    return {
        "overview": (
            f"Trận đấu kéo dài {duration_min} phút với chiến thắng dành cho "
            f"{'Đội Xanh' if blue_team.get('win') else 'Đội Đỏ'} "
            f"(Tỷ số {winning_team.get('totalKills', 0)} - {losing_team.get('totalKills', 0)}, "
            f"chênh lệch {gold_diff:,} vàng)."
        ),
        "winConditionSummary": (
            f"Đội thắng kiểm soát vượt trội mục tiêu lớn với {winning_team.get('objectives', {}).get('dragon', 0)} Rồng "
            f"và {winning_team.get('objectives', {}).get('baron', 0)} Baron dưới sự dẫn dắt của {mvp.get('championName')} ({mvp.get('riotIdGameName')})."
        ),
        "mvpPlayer": {
            "name": f"{mvp.get('riotIdGameName')}#{mvp.get('riotIdTagline')}",
            "champion": mvp.get("championName", ""),
            "role": mvp.get("role", "JG"),
            "reason": f"Điểm OP {mvp.get('mvpScore')} với KDA {mvp.get('kills')}/{mvp.get('deaths')}/{mvp.get('assists')} và KP {mvp.get('killParticipation')}%.",
        },
        "svpPlayer": {
            "name": f"{svp.get('riotIdGameName')}#{svp.get('riotIdTagline')}",
            "champion": svp.get("championName", ""),
            "role": svp.get("role", "MID"),
            "reason": f"Gánh đội tốt nhất bên đội thua (Điểm OP {svp.get('mvpScore')}, chiếm {svp.get('damageShare')}% sát thương).",
        },
        "focusedPlayerReview": {
            "playerName": full_tag,
            "champion": champ_name,
            "role": role_code,
            "grade": grade,
            "summary": summary,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "actionableAdvice": actionable_advice,
        },
        "laneComparisons": lane_comparisons,
        "macroInsights": [
            f"Kiểm soát mục tiêu: Đội thắng ăn {winning_team.get('objectives', {}).get('dragon', 0)} Rồng và {winning_team.get('objectives', {}).get('baron', 0)} Baron.",
            f"Chênh lệch kinh tế: Khoảng cách {gold_diff:,} vàng tạo ưu thế lớn về trang bị trong giao tranh tổng.",
            f"Phá hủy công trình: Đội thắng lấy được {winning_team.get('objectives', {}).get('tower', 0)} trụ bảo vệ của đối phương.",
        ],
    }


def process_analysis_request(data: dict, headers: dict) -> tuple[dict, int]:
    match = data.get("match")
    if not match or not isinstance(match, dict):
        return {"error": "Thiếu dữ liệu 'match' trong JSON payload"}, 400

    all_participants = (
        match.get("blueTeam", {}).get("participants", [])
        + match.get("redTeam", {}).get("participants", [])
    )
    if not all_participants:
        return {"error": "Không tìm thấy danh sách người chơi (participants) trong match"}, 400

    focused_player = data.get("focusedPlayer")
    focus_puuid = data.get("focusPuuid")
    if not focused_player or not isinstance(focused_player, dict):
        focused_player = next(
            (p for p in all_participants if p.get("puuid") == focus_puuid),
            all_participants[0],
        )

    auth_header = headers.get("Authorization") or headers.get("authorization") or ""
    header_key = (
        auth_header.replace("Bearer ", "").strip()
        if auth_header.startswith("Bearer ")
        else (headers.get("x-api-key") or "").strip()
    )
    api_key = (
        header_key
        or str(data.get("apiKey") or "").strip()
        or os.environ.get("GROQ_API_KEY", "").strip()
        or os.environ.get("GROQ_API_KEY_CHAT_BOT", "").strip()
    )

    model = data.get("model") or "openai/gpt-oss-120b"
    if model in ["gpt-4o-mini", "llama-3.3-70b-versatile", "default", ""]:
        model = "openai/gpt-oss-120b"

    prompt = build_lol_analysis_prompt(match, focused_player)
    fallback_result = build_fallback_analysis(match, focused_player)

    if not api_key:
        fallback_result["usedEndpoint"] = "bot-summary (/api/analyze-lol-match - Fallback Mode)"
        return {
            "status": "success",
            "provider": "bot-summary-fallback",
            "analysis": fallback_result,
        }, 200

    try:
        payload_bytes = json.dumps({
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Bạn là Huấn luyện viên trưởng (Head Coach - HLV) chuyên nghiệp cấp độ LCK / Thách Đấu Liên Minh Huyền Thoại. "
                        "Luôn trả về kết quả định dạng JSON hợp lệ bằng tiếng Việt theo đúng schema được yêu cầu."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.45,
            "max_tokens": 6000,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload_bytes,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "bot-summary-lol-analyzer/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            groq_data = json.loads(resp.read().decode("utf-8"))

        content_str = groq_data["choices"][0]["message"]["content"]
        cleaned = content_str.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        ai_json = json.loads(cleaned)
        ai_focused = ai_json.get("focusedPlayerReview") or {}
        fb_focused = fallback_result.get("focusedPlayerReview", {})
        merged_focused = {
            **fb_focused,
            **ai_focused,
            "summary": ai_focused.get("summary") or fb_focused.get("summary"),
        }
        merged = {
            **fallback_result,
            **ai_json,
            "focusedPlayerReview": merged_focused,
            "usedEndpoint": f"bot-summary Groq AI ({model})",
        }
        return {
            "status": "success",
            "provider": "bot-summary-groq",
            "model": model,
            "analysis": merged,
        }, 200

    except Exception as e:
        fallback_result["usedEndpoint"] = f"bot-summary (Fallback: {str(e)[:80]})"
        return {
            "status": "success",
            "provider": "bot-summary-fallback",
            "warning": str(e),
            "analysis": fallback_result,
        }, 200


def _add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization, x-api-key"
    )
    return response


@app.after_request
def after_request(response):
    return _add_cors_headers(response)


@app.route("/api/analyze-lol-match", methods=["POST", "OPTIONS", "GET"])
@app.route("/analyze-lol-match", methods=["POST", "OPTIONS", "GET"])
@app.route("/", methods=["POST", "OPTIONS", "GET"])
def analyze_lol_match(*args, **kwargs):
    if request.method == "OPTIONS":
        return _add_cors_headers(make_response("", 204))
    if request.method == "GET":
        return jsonify({
            "status": "ok",
            "service": "bot-summary LoL Match AI Analyzer",
            "endpoint": "/api/analyze-lol-match",
            "method": "POST",
        }), 200

    data = request.get_json(silent=True) or {}
    res_body, status_code = process_analysis_request(data, dict(request.headers))
    return jsonify(res_body), status_code


if __name__ == "__main__":
    from http.server import HTTPServer, BaseHTTPRequestHandler

    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                if s.startswith("#"):
                    uncommented = s.lstrip("#").strip()
                    if uncommented.startswith("GROQ_API_KEY") and "=" in uncommented:
                        k, v = uncommented.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
                elif "=" in s:
                    k, v = s.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    class LocalHandler(BaseHTTPRequestHandler):
        def _send_json(self, body: dict, status: int = 200):
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, x-api-key")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_OPTIONS(self):
            self._send_json({}, 204)

        def do_GET(self):
            self._send_json({
                "status": "ok",
                "service": "bot-summary LoL Match AI Analyzer",
                "endpoint": "/api/analyze-lol-match",
                "method": "POST",
            }, 200)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            try:
                data = json.loads(raw)
            except Exception:
                data = {}
            res_body, status_code = process_analysis_request(data, dict(self.headers))
            self._send_json(res_body, status_code)

    port = int(os.environ.get("PORT", 5555))
    print(f"🚀 bot-summary LoL Analyzer API running on http://localhost:{port}/api/analyze-lol-match", flush=True)
    server = HTTPServer(("0.0.0.0", port), LocalHandler)
    server.serve_forever()
