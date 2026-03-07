import base64
import json
import os
import io
from openai import AsyncOpenAI
from typing import Dict, Any
import fitz # PyMuPDF

# Create the client lazily so the server can boot even if the key is empty initially.
# It will fail at inference time explicitly instead of at boot time.
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", "dummy-key-for-local-boot"))

SYSTEM_PROMPT = """
You are an expert Check OCR and Data Extraction Assistant for 'Quick Track'.
Your single job is to accurately extract fields from the provided check image.

CRITICAL INSTRUCTION FOR MICR LINE (at the bottom of the check):
- IGNORE all MICR transit symbols and boundaries such as ⑆ and ⑈.
- Extract ONLY the exactly 9-digit Routing Number and the exactly 10-digit Account Number.
- Discard any other peripheral numbers in the MICR line (such as the appended check number).

Return the extracted data EXACTLY in this JSON structure (no markdown tags, just the raw JSON object):
{
  "store_name": "string",
  "check_number": "string",
  "check_date": "YYYY-MM-DD",
  "payee_name": "string",
  "amount": float,
  "memo": "string",
  "bank_name": "string",
  "routing_number": "string",
  "account_number": "string",
  "confidence_score": float
}
"""

async def extract_check_data_via_ai(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Handles PDF to JPG conversion if necessary, then passes to GPT-4o-mini API
    Returns dict directly aligned with PRD 3 requirements
    """
    key = os.getenv("OPENAI_API_KEY", "")
    is_placeholder = not key or key in [
        "", "sk-your-key-here", "dummy-key-for-local-boot",
        "sk-placeholder-replace-me", "your-openai-key-here"
    ] or key.startswith("sk-placeholder")
    
    if is_placeholder:
        # MOCK DATA RETURN for testing without credentials
        return {
            "store_name": "Quick Track 119",
            "check_number": "1190005",
            "check_date": "2026-02-16",
            "payee_name": "Aryan Poudel",
            "amount": 10.05,
            "memo": "walmart",
            "bank_name": "Stellar Bank",
            "routing_number": "113025723",
            "account_number": "2017237191",
            "confidence_score": 0.65  # Force a MANUAL_REVIEW for UI testing
        }

    # 1. Provide PDF Support per PRD 3
    if filename.lower().endswith(".pdf"):
        # Convert first page of PDF to image bytes using PyMuPDF (no poppler needed)
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
        if pdf_document.page_count == 0:
            raise ValueError("Empty PDF document")
            
        page = pdf_document[0]
        # Generate pixmap (image) from page
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # 2x zoom for better OCR
        target_bytes = pix.tobytes("jpeg")
        pdf_document.close()
    else:
        # Standard JPG/PNG upload
        target_bytes = file_bytes
        
    base64_image = base64.b64encode(target_bytes).decode('utf-8')
    model_name = "gpt-4o-mini"

    response = await client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract the check details from this image accurately."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        temperature=0.0,
        response_format={ "type": "json_object" }
    )

    try:
        content = response.choices[0].message.content
        data = json.loads(content)
        return data
    except Exception as e:
        raise RuntimeError(f"Failed to parse target AI response: {str(e)}\nRaw: {content}")
