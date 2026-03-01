from http.server import BaseHTTPRequestHandler
import json
import cgi
import io
import re
import pdfplumber

# Defined Coordinates (Zonal OCR) based on Stellar Bank Template
ZONES = {
    "Cheque_No": (480, 5, 570, 30),
    "Date": (480, 30, 580, 50),
    "Payee": (18, 80, 500, 100),
    "Amount": (530, 75, 605, 95),
    "Memo": (50, 135, 300, 160),
    "Bank": (200, 15, 412, 40),
    "Routing_No": (250, 250, 345, 275),
    "Account_No": (345, 250, 450, 275),
}

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST'}
            )
            
            if 'file' not in form:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'No file uploaded')
                return

            file_item = form['file']
            file_data = file_item.file.read()
            
            results = []
            with pdfplumber.open(io.BytesIO(file_data)) as pdf:
                for page in pdf.pages:
                    data = self.extract_zonal_data(page)
                    if any(data.values()):
                        results.append(data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(results).encode())
            
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def extract_zonal_data(self, page) -> dict:
        headers = ["Date", "Cheque_No", "Payee", "Amount", "Memo", "Bank", "Routing_No", "Account_No"]
        res = {h: "" for h in headers}
        
        raw = {}
        for field, bbox in ZONES.items():
            cropped = page.crop(bbox)
            raw[field] = cropped.extract_text() or ""

        # Cleaning
        res["Date"] = raw.get("Date", "").strip()
        res["Cheque_No"] = re.sub(r"[^0-9]", "", raw.get("Cheque_No", ""))
        
        p = raw.get("Payee", "").split('$')[0].split('\n')[0].strip()
        res["Payee"] = p
        
        amt = raw.get("Amount", "").replace('$', '').replace('*', '').strip()
        res["Amount"] = amt
        
        res["Memo"] = raw.get("Memo", "").strip()
        res["Bank"] = raw.get("Bank", "").strip()
        
        res["Routing_No"] = re.sub(r'[^0-9]', '', raw.get("Routing_No", ""))
        res["Account_No"] = re.sub(r'[^0-9]', '', raw.get("Account_No", ""))
        
        return res
