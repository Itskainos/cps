import re
from typing import Dict, Any, Tuple

def is_valid_routing(routing: str) -> bool:
    """Validates US routing numbers using the mathematical checksum."""
    if not routing or len(routing) != 9 or not routing.isdigit():
        return False
    
    # Weights for ABA Routing Number Checksum
    weights = [3, 7, 1, 3, 7, 1, 3, 7, 1]
    total = sum(int(digit) * weight for digit, weight in zip(routing, weights))
    
    return total % 10 == 0

def validate_extracted_check_data(data: Dict[str, Any]) -> Tuple[str, str]:
    """
    Validates check data against business rules.
    Returns: (status_enum_string, comma_separated_notes)
    """
    notes = []
    
    routing = str(data.get("routing_number", "")).strip()
    if not re.fullmatch(r"^\d{9}$", routing):
        notes.append(f"Routing Number issue (Expected 9 digits, got '{routing}')")
    elif not is_valid_routing(routing):
        notes.append(f"Routing Number Checksum Failed (OCR misread likely for '{routing}')")
        
    account = str(data.get("account_number", "")).strip()
    if not re.fullmatch(r"^\d{10}$", account):
        notes.append(f"Account Number issue (Expected 10 digits, got '{account}')")

    # Check for forced MANUAL_REVIEW_REQUIRED from ai_extractor.py
    if data.get("status") == "MANUAL_REVIEW_REQUIRED":
        notes.append("Force Manual Review Required (Checksum or Extraction Failure)")

    confidence = data.get("confidence_score")
    if confidence is None or confidence < 0.80:
        notes.append("Hard Block: Force a human to type the numbers manually.")
    elif 0.80 <= confidence < 0.95:
        notes.append("Warning: The data might be correct, but the image was a bit blurry.")
        
    # Return status depending on presence of validation notes
    if notes:
        return "MANUAL_REVIEW", " | ".join(notes)
    
    return "APPROVED", "AI Extraction Complete - Passed Validation"
