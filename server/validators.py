import re
from typing import Dict, Any, Tuple
from thefuzz import fuzz

OFFICIAL_QUICK_TRACK_STORES = [
    "Quick Track Store 1",
    "Quick Track Express Main",
    "Quick Track Dallas"
]

FUZZY_MATCH_THRESHOLD = 80  

def validate_extracted_check_data(data: Dict[str, Any]) -> Tuple[str, str]:
    """
    Validates check data against business rules.
    Returns: (status_enum_string, comma_separated_notes)
    """
    notes = []
    
    routing = str(data.get("routing_number", "")).strip()
    if not re.fullmatch(r"^\d{9}$", routing):
        notes.append(f"Routing Number issue (Expected 9 digits, got '{routing}')")
        
    account = str(data.get("account_number", "")).strip()
    if not re.fullmatch(r"^\d{10}$", account):
        notes.append(f"Account Number issue (Expected 10 digits, got '{account}')")

    store_name = str(data.get("store_name", "")).strip()
    best_match_score = 0
    if store_name:
        for official_store in OFFICIAL_QUICK_TRACK_STORES:
            score = fuzz.token_sort_ratio(store_name.lower(), official_store.lower())
            if score > best_match_score:
                best_match_score = score
                
    if best_match_score < FUZZY_MATCH_THRESHOLD:
        notes.append(f"Store name '{store_name}' failed fuzzy match (Highest Score: {best_match_score})")
        
    confidence = data.get("confidence_score")
    if confidence is not None and confidence < 0.8:
        notes.append(f"Low AI Confidence Score: {confidence}")

    # PRD 3 requires validation failure logic -> MANUAL_REVIEW
    # We now default to MANUAL_REVIEW for ALL extractions to ensure human-in-the-loop approval.
    return "MANUAL_REVIEW", " | ".join(notes) if notes else "AI Extraction Complete - Awaiting Verification"
