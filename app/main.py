from flask import Flask, jsonify, request
import os

from app.services.llm_service import get_llm_response

app = Flask(__name__)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/ping")
def ping():
    return jsonify({"message": "pong"})


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    prompt = data.get("message", "")

    response = get_llm_response(prompt)

    return jsonify({
        "input": prompt,
        "response": response
    })


port = int(os.environ.get("PORT", 5000))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)
