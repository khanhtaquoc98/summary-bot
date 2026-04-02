import os
import requests
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/test_embedding', methods=['GET'])
def test_embedding():
    """API test embedding - thử fix multilingual-minilm"""
    hf_token = os.environ.get("HF_API_TOKEN", "")
    test_text = "Hôm nay trời đẹp quá"

    results = {}

    model = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    base_url = f"https://router.huggingface.co/hf-inference/models/{model}"

    test_cases = [
        {
            "name": "task_in_payload",
            "url": base_url,
            "payload": {"inputs": test_text, "parameters": {"task": "feature-extraction"}},
        },
        {
            "name": "x_use_task_header",
            "url": base_url,
            "extra_headers": {"x-use-task": "feature-extraction"},
            "payload": {"inputs": test_text},
        },
        {
            "name": "query_param_task",
            "url": base_url + "?task=feature-extraction",
            "payload": {"inputs": test_text},
        },
        {
            "name": "pipeline_url",
            "url": f"https://router.huggingface.co/hf-inference/pipeline/feature-extraction/{model}",
            "payload": {"inputs": test_text},
        },
        {
            "name": "intfloat_multilingual_e5_small",
            "url": "https://router.huggingface.co/hf-inference/models/intfloat/multilingual-e5-small",
            "payload": {"inputs": test_text},
        },
        {
            "name": "bge_m3_512",
            "url": "https://router.huggingface.co/hf-inference/models/BAAI/bge-m3",
            "payload": {"inputs": test_text},
        },
    ]

    for tc in test_cases:
        try:
            headers = {
                "Authorization": f"Bearer {hf_token}",
                "Content-Type": "application/json"
            }
            if "extra_headers" in tc:
                headers.update(tc["extra_headers"])

            resp = requests.post(
                tc["url"],
                headers=headers,
                json=tc["payload"],
                timeout=30
            )

            dims = None
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    if isinstance(data[0], list):
                        dims = len(data[0])
                    elif isinstance(data[0], float):
                        dims = len(data)

            results[tc["name"]] = {
                "url": tc["url"],
                "status": resp.status_code,
                "dimensions": dims,
                "body_preview": resp.text[:200] if resp.status_code != 200 else f"OK, dims={dims}"
            }
        except Exception as e:
            results[tc["name"]] = {"error": str(e)}

    return jsonify({
        "hf_token_set": bool(hf_token),
        "results": results
    })
