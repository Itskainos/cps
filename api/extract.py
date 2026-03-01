import os
import io
import re
import sys
import json
import pdfplumber
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

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

    # Cleaning logic
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

@app.route('/api/extract', methods=['POST'])
def extract():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
        
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

# Standalone CLI mode (Called by Node.js bridge locally)
def cli_mode(file_path):
    results = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                data = extract_zonal_data(page)
                if any(data.values()):
                    results.append(data)
        print(json.dumps(results))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    # If a filename is passed as argument, use CLI mode
    if len(sys.argv) > 1:
        cli_mode(sys.argv[1])
    else:
        # Otherwise start the Flask server
        app.run(port=5000)
