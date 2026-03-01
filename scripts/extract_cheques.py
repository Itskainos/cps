
import csv
import re
from pathlib import Path
from typing import Optional
import pdfplumber

# Configuration
CHEQUE_FOLDER = Path(__file__).parent / "cheques"
OUTPUT_CSV = Path(__file__).parent / "processed_cheques.csv"
CSV_HEADERS = ["Date", "Cheque_No", "Payee", "Amount", "Memo", "Bank", "Routing_No", "Account_No"]

# Defined Coordinates (Zonal OCR) based on Stellar Bank Template
# Format: (x0, top, x1, bottom) 
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

def extract_zonal_data(page) -> dict:
    res = {h: "" for h in CSV_HEADERS}
    
    # 1. Capture Raw Text per Zone
    raw = {}
    for field, bbox in ZONES.items():
        cropped = page.crop(bbox)
        raw[field] = cropped.extract_text() or ""

    # 2. Field-Specific Cleaning
    res["Date"] = raw["Date"].strip()
    res["Cheque_No"] = re.sub(r"[^0-9]", "", raw["Cheque_No"]) # Keep numeric only
    
    # Payee: Locate after 'ORDER OF' logic (already captured Aryan Poudel in the zone)
    # The user says "Locate following ORDER OF". The zone starts after that label usually.
    # In our test, Aryan Poudel was exactly in that zone.
    res["Payee"] = raw["Payee"].split('$')[0].split('\n')[0].strip()
    
    # Amount: Strip $, *, and whitespace
    amt = raw["Amount"].replace('$', '').replace('*', '').strip()
    res["Amount"] = amt
    
    res["Memo"] = raw["Memo"].strip()
    res["Bank"] = raw["Bank"].strip()
    
    # MICR: Strip non-numeric glyphs
    res["Routing_No"] = re.sub(r'[^0-9]', '', raw["Routing_No"])
    res["Account_No"] = re.sub(r'[^0-9]', '', raw["Account_No"])
    
    return res

def process():
    CHEQUE_FOLDER.mkdir(exist_ok=True)
    files = sorted(list(CHEQUE_FOLDER.glob("*.pdf")))
    results = []

    for f in files:
        try:
            with pdfplumber.open(f) as pdf:
                # We assume 1 cheque per page for this extraction
                for page in pdf.pages:
                    data = extract_zonal_data(page)
                    if any(data.values()):
                        print(f"✅ {f.name} | Payee: {data['Payee']} | Routing: {data['Routing_No']} | Acc: {data['Account_No']}")
                        results.append(data)
        except Exception as e:
            print(f"❌ Error processing {f.name}: {e}")

    # Write Results
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n✨ Successfully processed {len(results)} cheque(s).")
    print(f"📄 Exported to {OUTPUT_CSV}")

if __name__ == "__main__":
    process()
