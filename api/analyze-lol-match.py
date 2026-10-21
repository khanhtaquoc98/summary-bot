import os
import json
import urllib.request
import urllib.error

try:
    from flask import Flask, request, jsonify, make_response
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

ROLES_ORDER = ["TOP", "JG", "MID", "AD", "SP"]


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
            f"Tổng vàng: {team.get('totalGold', 0):,} | "
            f"Baron: {objs.get('baron', 0)}, Rồng: {objs.get('dragon', 0)}, "
            f"Sâu Hư Không: {objs.get('horde', 0)}, Trụ: {objs.get('tower', 0)})"
        )
        rows = []
        for p in team.get("participants", []):
            rows.append(
                f"  - [{p.get('role')}] {p.get('riotIdGameName')}#{p.get('riotIdTagline')} "
                f"({p.get('championName')}): KDA {p.get('kills')}/{p.get('deaths')}/{p.get('assists')} "
                f"(KDA Ratio: {p.get('kda')}), Sát thương: {p.get('totalDamageDealtToChampions', 0):,} "
                f"({p.get('damageShare', 0)}% đội), Vàng: {p.get('goldEarned', 0):,}, "
                f"CS: {p.get('cs', 0)} ({p.get('csPerMin', 0)}/p), "
                f"Tầm nhìn: {p.get('visionScore', 0)}, Tham gia hạ gục (KP): {p.get('killParticipation', 0)}%, "
                f"Điểm OP: {p.get('mvpScore', 0)}"
            )
        return header + "\n" + "\n".join(rows)

    focused_name = f"{focused_player.get('riotIdGameName', 'Player')}#{focused_player.get('riotIdTagline', 'VN2')}"
    focused_champ = focused_player.get("championName", "Unknown")
    focused_role = focused_player.get("role", "TOP")

    return f"""# ROLE
Bạn là Huấn luyện viên trưởng (Head Coach) & Chuyên gia phân tích dữ liệu Liên Minh Huyền Thoại cấp độ Thách Đấu.
Nhiệm vụ của bạn là phân tích sâu trận đấu dưới đây bằng tiếng Việt chuẩn thuật ngữ LMHT (snowball, kiểm soát mục tiêu, prio đường, nhịp độ, tầm nhìn, giao tranh tổng) và trả về DUY NHẤT một chuỗi JSON hợp lệ.

# DỮ LIỆU TRẬN ĐẤU
- Mã trận: {match.get('matchId', 'UNKNOWN')} ({match.get('queueName', 'Ranked')})
- Thời lượng: {duration_min} phút | Phiên bản: {match.get('gameVersion', '14.24')}
- Người chơi trọng tâm cần mổ xẻ chi tiết: {focused_name} (Tướng: {focused_champ} - Đường: {focused_role})

{format_team(blue_team, "ĐỘI XANH (BLUE TEAM - teamId 100)")}

{format_team(red_team, "ĐỘI ĐỎ (RED TEAM - teamId 200)")}

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
    "strengths": [
      "Điểm mạnh cụ thể 1 trong trận kèm dẫn chứng số liệu",
      "Điểm mạnh cụ thể 2 trong trận kèm dẫn chứng số liệu",
      "Điểm mạnh cụ thể 3"
    ],
    "weaknesses": [
      "Điểm hạn chế / sai lầm 1 cần khắc phục",
      "Điểm hạn chế / sai lầm 2 cần khắc phục"
    ],
    "actionableAdvice": [
      "Lời khuyên chiến thuật thực tế 1 cho trận tiếp theo",
      "Lời khuyên chiến thuật thực tế 2 cho trận tiếp theo",
      "Lời khuyên chiến thuật thực tế 3 cho trận tiếp theo"
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

    mvp_score = focused.get("mvpScore", 75)
    grade = "S+" if mvp_score >= 92 else "S" if mvp_score >= 84 else "A" if mvp_score >= 74 else "B" if mvp_score >= 62 else "C"

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
            "playerName": f"{focused.get('riotIdGameName')}#{focused.get('riotIdTagline')}",
            "champion": focused.get("championName", ""),
            "role": focused.get("role", "TOP"),
            "grade": grade,
            "strengths": [
                f"Đóng góp {focused.get('totalDamageDealtToChampions', 0):,} sát thương ({focused.get('damageShare', 0)}% toàn đội) và tham gia {focused.get('killParticipation', 0)}% hạ gục.",
                f"Thu thập {focused.get('goldEarned', 0):,} vàng với chỉ số lính {focused.get('cs', 0)} CS ({focused.get('csPerMin', 0)} CS/phút).",
                f"Đạt {focused.get('visionScore', 0)} điểm tầm nhìn ({focused.get('wardsPlaced', 0)} mắt cắm, {focused.get('wardsKilled', 0)} mắt phá).",
            ],
            "weaknesses": [
                f"Nằm xuống {focused.get('deaths', 0)} lần trong trận — cần hạn chế các pha di chuyển lẻ khi không có tầm nhìn.",
                "Cần tối ưu hóa việc chuyển hóa lợi thế đi đường thành kiểm soát Sâu Hư Không / Rồng sớm hơn.",
            ],
            "actionableAdvice": [
                f"Khi cầm {focused.get('championName')} ở đường {focused.get('role')}, hãy kiểm soát thế lính trước các mốc mục tiêu lớn 45 giây.",
                "Chú ý cắm mắt kiểm soát ở các bụi cỏ sông và phối hợp cùng Rừng/Hỗ Trợ khi xâm lăng.",
                "Trong giao tranh tổng, giữ kỹ năng quan trọng để khóa chủ lực đối phương hoặc bảo kê tuyến sau.",
            ],
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

    model = data.get("model") or "llama-3.3-70b-versatile"
    if model in ["gpt-4o-mini", "default", ""]:
        model = "llama-3.3-70b-versatile"

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
                        "Bạn là Chuyên gia phân tích trận đấu Liên Minh Huyền Thoại (LoL AI Coach). "
                        "Luôn trả về kết quả định dạng JSON hợp lệ bằng tiếng Việt theo đúng schema được yêu cầu."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.35,
            "max_tokens": 2500,
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
        merged = {
            **fallback_result,
            **ai_json,
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


if HAS_FLASK:
    app = Flask(__name__)

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
