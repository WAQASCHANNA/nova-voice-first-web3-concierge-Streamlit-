import os, requests, json
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()
CROSSMINT_SERVER_KEY = os.getenv("CROSSMINT_SERVER_KEY")
CROSSMINT_API_BASE = os.getenv("CROSSMINT_API_BASE", "https://staging.crossmint.com/api/2022-06-09")

if not CROSSMINT_SERVER_KEY:
    raise RuntimeError("CROSSMINT_SERVER_KEY required in env")

app = Flask(__name__)

@app.route("/api/mint", methods=["POST"])
def mint():
    """
    Accepts JSON:
    {
      collection_id: "...",
      token_id: "...", (optional)
      buyer_email: "...",
      metadata: {...},
      qty: 1
    }
    Forwards to Crossmint server-side mint endpoint (example). Adjust to Crossmint API shape.
    """
    body = request.get_json(force=True)
    collection_id = body.get("collection_id")
    if not collection_id:
        return jsonify({"error":"collection_id required"}), 400
    # construct Crossmint request - adapt fields to Crossmint's API
    target_url = f"{CROSSMINT_API_BASE}/collections/{collection_id}/nfts"
    payload = {
        "quantity": body.get("qty", 1),
        "metadata": body.get("metadata") or {},
        "buyer_email": body.get("buyer_email"),
        "token_id": body.get("token_id")
    }
    headers = {"Authorization": f"Bearer {CROSSMINT_SERVER_KEY}", "Content-Type":"application/json"}
    r = requests.post(target_url, headers=headers, json=payload, timeout=30)
    try:
        r.raise_for_status()
    except Exception as e:
        return jsonify({"error":"Crossmint error","status_code":r.status_code,"text":r.text}), 502
    return jsonify(r.json())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",9000)))
