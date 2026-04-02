import os
import requests
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/test_embedding', methods=['GET'])
def test_embedding():
    """API test embedding để debug lỗi 400"""
    hf_token = os.environ.get("HF_API_TOKEN", "")
    model = "sentence-transformers/all-MiniLM-L6-v2"
    test_text = "Hôm nay trời đẹp quá"

    results = {}

    # Test 1: Endpoint mới (router) với format json
    try:
        url1 = f"https://router.huggingface.co/hf-inference/models/{model}"
        resp1 = requests.post(
            url1,
            headers={
                "Authorization": f"Bearer {hf_token}",
                "Content-Type": "application/json"
            },
            json={"inputs": test_text, "options": {"wait_for_model": True}},
            timeout=15
        )
        results["router_json"] = {
            "url": url1,
            "status": resp1.status_code,
            "body": resp1.text[:500]
        }
    except Exception as e:
        results["router_json"] = {"error": str(e)}

    # Test 2: Endpoint mới với format text thuần
    try:
        url2 = f"https://router.huggingface.co/hf-inference/models/{model}"
        resp2 = requests.post(
            url2,
            headers={
                "Authorization": f"Bearer {hf_token}",
            },
            json=test_text,
            timeout=15
        )
        results["router_text"] = {
            "url": url2,
            "status": resp2.status_code,
            "body": resp2.text[:500]
        }
    except Exception as e:
        results["router_text"] = {"error": str(e)}

    # Test 3: Endpoint pipeline cũ qua router
    try:
        url3 = f"https://router.huggingface.co/hf-inference/pipeline/feature-extraction/{model}"
        resp3 = requests.post(
            url3,
            headers={
                "Authorization": f"Bearer {hf_token}",
                "Content-Type": "application/json"
            },
            json={"inputs": test_text, "options": {"wait_for_model": True}},
            timeout=15
        )
        results["router_pipeline"] = {
            "url": url3,
            "status": resp3.status_code,
            "body": resp3.text[:500]
        }
    except Exception as e:
        results["router_pipeline"] = {"error": str(e)}

    return jsonify({
        "hf_token_set": bool(hf_token),
        "hf_token_prefix": hf_token[:10] + "..." if hf_token else "EMPTY",
        "results": results
    })
