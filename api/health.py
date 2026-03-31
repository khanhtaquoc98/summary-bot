import time
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "telegram-summary-bot",
        "timestamp": time.time(),
        "version": "1.0.0"
    }), 200
