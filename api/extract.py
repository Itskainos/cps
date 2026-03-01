import os
import sys
import json
import re
import pdfplumber

# --- ZONAL OCR LOGIC ---
ZONES = {
    "Cheque_No": (480, 5, 570, 30),
    "Date": (480, 30, 580, 50),
    "Payee": (18, 80, 500, 110),
    "Amount": (530, 75, 605, 100),
    "Memo": (50, 135, 300, 160),
    "Bank": (200, 15, 412, 45),
    "Routing_No": (250, 250, 345, 275),
    "Account_No": (345, 250, 450, 275),
}

def extract_zonal_data(page):
    headers = ["Date", "Cheque_No", "Payee", "Amount", "Memo", "Bank", "Routing_No", "Account_No"]
    res = {h: "" for h in headers}
    raw = {}
    for field, bbox in ZONES.items():
        try:
            cropped = page.crop(bbox)
            raw[field] = cropped.extract_text() or ""
        except:
            raw[field] = ""
    res["Date"] = raw.get("Date", "").strip()
    res["Cheque_No"] = re.sub(r"[^0-9]", "", raw.get("Cheque_No", ""))
    p = raw.get("Payee", "").split('$')[0].split('\n')[0].strip()
    res["Payee"] = p
    amt_raw = raw.get("Amount", "")
    amt = re.sub(r'[^0-9.]', '', amt_raw)
    res["Amount"] = amt
    res["Memo"] = raw.get("Memo", "").strip()
    res["Bank"] = raw.get("Bank", "").strip()
    res["Routing_No"] = re.sub(r'[^0-9]', '', raw.get("Routing_No", ""))
    res["Account_No"] = re.sub(r'[^0-9]', '', raw.get("Account_No", ""))
    return res

# --- CLI MODE (For Local Dev via Node Bridge) ---
def run_cli(pdf_path):
    try:
        results = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                data = extract_zonal_data(page)
                if any(data.values()):
                    results.append(data)
        print(json.dumps(results))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

# --- VERCEL SERVERLESS HANDLER ---
# We define a function that Vercel's Python runtime can use
try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    
    app = Flask(__name__)
    CORS(app)

    @app.route('/', methods=['POST'])
    @app.route('/api/extract', methods=['POST'])
    def vercel_handler():
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        file = request.files['file']
        results = []
        try:
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    data = extract_zonal_data(page)
                    if any(data.values()):
                        results.append(data)
            return jsonify(results)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
except ImportError:
    # Flask not available locally, which is fine for CLI mode
    app = None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # If we have an argument, it's the file path from the Node bridge
        run_cli(sys.argv[1])
    elif app:
        # If no arguments and Flask is available, start the server (Vercel/Manual)
        app.run(port=5000)
    else:
        print("Missing argument or Flask not installed.")
        sys.exit(1)
