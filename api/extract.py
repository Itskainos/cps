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
    return res, raw

# --- AI ENHANCEMENT LAYER ---
def ai_enhance(full_page_text, ocr_result):
    """
    Uses GPT-4o mini to validate and correct OCR output.
    Returns the enhanced result with a confidence score per field.
    Gracefully skipped if OPENAI_API_KEY is not set.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-your"):
        return None  # AI not configured — skip silently

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        prompt = f"""You are a financial document parser specializing in bank cheques.

Given the full raw text of a cheque page and a preliminary OCR extraction, your job is to:
1. Correct any OCR errors in the extracted fields
2. Assign a confidence score (0.0 to 1.0) per field based on how sure you are

Raw cheque text:
\"\"\"
{full_page_text}
\"\"\"

Preliminary OCR extraction:
{json.dumps(ocr_result, indent=2)}

Return ONLY a valid JSON object with this exact structure. No explanation:
{{
  "Date": "...",
  "Cheque_No": "...",
  "Payee": "...",
  "Amount": "...",
  "Memo": "...",
  "Bank": "...",
  "Routing_No": "...",
  "Account_No": "...",
  "confidence": {{
    "Date": 0.95,
    "Cheque_No": 0.99,
    "Payee": 0.92,
    "Amount": 0.97,
    "Memo": 0.85,
    "Bank": 0.98,
    "Routing_No": 0.99,
    "Account_No": 0.99
  }}
}}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        ai_json = json.loads(response.choices[0].message.content)
        return ai_json

    except Exception as e:
        # AI failed — fall back to OCR-only result silently
        sys.stderr.write(f"AI enhancement skipped: {e}\n")
        return None


def process_page(page):
    """
    Runs Zonal OCR then optionally enhances with AI.
    """
    ocr_result, _ = extract_zonal_data(page)

    # Get the full page text for AI context
    full_text = page.extract_text() or ""

    # Try AI enhancement
    ai_result = ai_enhance(full_text, ocr_result)

    if ai_result:
        # Merge AI corrections over OCR base
        fields = ["Date", "Cheque_No", "Payee", "Amount", "Memo", "Bank", "Routing_No", "Account_No"]
        for field in fields:
            if field in ai_result and ai_result[field]:
                ocr_result[field] = ai_result[field]
        ocr_result["confidence"] = ai_result.get("confidence", {})
        ocr_result["ai_enhanced"] = True
    else:
        ocr_result["ai_enhanced"] = False
        ocr_result["confidence"] = {}

    return ocr_result


# --- CLI MODE (For Local Dev via Node Bridge) ---
def run_cli(pdf_path):
    try:
        results = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                data = process_page(page)
                if any(v for k, v in data.items() if k not in ("ai_enhanced", "confidence")):
                    results.append(data)
        print(json.dumps(results))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


# --- VERCEL SERVERLESS HANDLER ---
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
                    data = process_page(page)
                    if any(v for k, v in data.items() if k not in ("ai_enhanced", "confidence")):
                        results.append(data)
            return jsonify(results)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
except ImportError:
    app = None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_cli(sys.argv[1])
    elif app:
        app.run(port=5000)
    else:
        print("Missing argument or Flask not installed.")
        sys.exit(1)
