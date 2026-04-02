import os
import requests
from flask import Flask, jsonify
from huggingface_hub import InferenceClient

app = Flask(__name__)

@app.route('/api/test_embedding', methods=['GET'])
def test_embedding():
    """API test embedding - dùng thư viện chính thức huggingface_hub"""
    hf_token = os.environ.get("HF_API_TOKEN", "")
    test_text = "Hôm nay trời đẹp quá"

    results = {}
    
    models_to_test = [
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "intfloat/multilingual-e5-small",
        "BAAI/bge-small-en-v1.5"
    ]

    client = InferenceClient(api_key=hf_token)

    for model in models_to_test:
        try:
            # Dùng thư viện chính thức, gọi thẳng hàm feature_extraction
            embedding = client.feature_extraction(
                text=test_text,
                model=model
            )
            
            # Kiểm tra số chiều
            dims = None
            if isinstance(embedding, list) and len(embedding) > 0:
                dims = len(embedding)
            elif hasattr(embedding, "shape"): # numpy array
                dims = embedding.shape[-1]
                
            results[model] = {
                "status": "success",
                "dimensions": dims,
                "type": str(type(embedding))
            }
        except Exception as e:
            results[model] = {
                "status": "error",
                "error_message": str(e)
            }

    return jsonify({
        "hf_token_set": bool(hf_token),
        "results": results
    })
