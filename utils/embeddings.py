import os
import requests


# Dùng HuggingFace Inference API (free) với model bge-small-en-v1.5 (384 dimensions)
HF_API_TOKEN = os.environ.get("HF_API_TOKEN", "")
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
API_URL = f"https://router.huggingface.co/hf-inference/models/{EMBEDDING_MODEL}"


def get_embedding(text: str) -> list:
    """Sinh embedding vector 384 chiều cho đoạn text bằng HuggingFace Inference API (miễn phí)"""
    if not HF_API_TOKEN:
        return None

    # Cắt text quá dài (model chỉ hỗ trợ ~512 tokens)
    truncated = text[:500] if len(text) > 500 else text

    try:
        resp = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {HF_API_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "inputs": truncated,
                "options": {"wait_for_model": True}
            },
            timeout=15
        )
        resp.raise_for_status()
        embedding = resp.json()

        # API trả về list of floats cho single input
        if isinstance(embedding, list) and len(embedding) > 0:
            # Nếu trả về nested list [[...]], lấy phần tử đầu
            if isinstance(embedding[0], list):
                return embedding[0]
            return embedding

        return None
    except Exception as e:
        print(f"Lỗi khi sinh embedding: {type(e).__name__}: {e}")
        # In thêm response body để debug
        try:
            print(f"Response body: {resp.text}")
        except Exception:
            pass
        return None
