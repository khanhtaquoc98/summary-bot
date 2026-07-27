import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/test_embedding', methods=['GET'])
def test_embedding():
    return jsonify({
        "message": "Please read agent response. Hugging Face free API strictly enforces model tags. Cannot use sentence-similarity models for feature-extraction anymore."
    })
