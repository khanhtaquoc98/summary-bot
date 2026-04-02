import os
import requests
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/test_embedding', methods=['GET'])
def test_embedding():
    """API test embedding - thử nhiều model và format khác nhau"""
    hf_token = os.environ.get("HF_API_TOKEN", "")
    test_text = "Hôm nay trời đẹp quá"

    results = {}

    # Danh sách model thử nghiệm (384 dimensions)
    test_cases = [
        {
            "name": "multilingual-minilm",
            "model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        },
        {
            "name": "bge-small-en",
            "model": "BAAI/bge-small-en-v1.5",
        },
    ]

    for tc in test_cases:
        try:
            url = f"https://router.huggingface.co/hf-inference/models/{tc['model']}"

            if "payload" in tc:
                payload = tc["payload"]
            else:
                payload = {"inputs": test_text, "options": {"wait_for_model": True}}
                if "extra_params" in tc:
                    payload.update(tc["extra_params"])

            resp = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {hf_token}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=20
            )

            body = resp.text[:500]
            # Kiểm tra embedding dimension nếu thành công
            dims = None
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    if isinstance(data[0], list):
                        dims = len(data[0])
                    elif isinstance(data[0], float):
                        dims = len(data)

            results[tc["name"]] = {
                "url": url,
                "status": resp.status_code,
                "dimensions": dims,
                "body_preview": body[:200] if resp.status_code != 200 else f"OK, dims={dims}"
            }
        except Exception as e:
            results[tc["name"]] = {"error": str(e)}

    return jsonify({
        "hf_token_set": bool(hf_token),
        "results": results
    })
