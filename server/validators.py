import re
from typing import Dict, Any, Tuple, Optional

def is_valid_routing(routing: str) -> bool:
    """
    Validates US routing numbers using the mathematical checksum.
    Also checks for valid US ABA prefixes to reduce hallucinations.
    """
    if not routing or len(routing) != 9 or not routing.isdigit():
        return False
    
    # Prefix check: 00-12, 21-32, 61-72, 80 are the standard US routing prefixes
    prefix = int(routing[:2])
    valid_prefixes = (
        (0 <= prefix <= 12) or 
        (21 <= prefix <= 32) or 
        (61 <= prefix <= 72) or 
        (prefix == 80)
    )
    if not valid_prefixes:
        return False
    
    # Weights for ABA Routing Number Checksum
    weights = [3, 7, 1, 3, 7, 1, 3, 7, 1]
    total = sum(int(digit) * weight for digit, weight in zip(routing, weights))
    
    return total % 10 == 0

def try_repair_routing(partial: str) -> Optional[str]:
    """
    If OCR gives 8 digits, compute the missing ABA check digit mathematically.
    Works because the 9th digit is purely derived from digits 1-8.
    """
    digits = re.sub(r'\D', '', partial)
    if len(digits) == 8:
        weights_8 = [3, 7, 1, 3, 7, 1, 3, 7]
        total = sum(int(d) * w for d, w in zip(digits, weights_8))
        check_digit = (10 - (total % 10)) % 10
        candidate = digits + str(check_digit)
        if is_valid_routing(candidate):
            return candidate
    return None

def validate_extracted_check_data(data: Dict[str, Any]) -> Tuple[str, str]:
    """
    Validates check data against business rules and handles auto-approval/swapping.
    Returns: (status_enum_string, comma_separated_notes)
    """
    critical_notes = []
    info_notes = []
    
    # ── 1. CLEANING & INITIAL PREP ───────────────────────────────────────────
    routing = str(data.get("routing_number", "")).strip()
    routing = re.sub(r"\D", "", routing) 
    
    account = str(data.get("account_number", "")).strip()
    account = re.sub(r"\D", "", account)
    
    # ── 2. SWAPPED FIELDS DETECTION ──────────────────────────────────────────
    # If the routing number is invalid but the account number passes ABA checksum, 
    # it is highly likely they are swapped in the OCR buffer.
    # We strip all non-digits from both before checking to be robust.
    clean_routing = re.sub(r"\D", "", str(data.get("routing_number", "")))
    clean_account = re.sub(r"\D", "", str(data.get("account_number", "")))

    if not is_valid_routing(clean_routing) and is_valid_routing(clean_account):
        # Perform Auto-Swap
        data["routing_number"] = clean_account
        data["account_number"] = clean_routing
        info_notes.append("Routing and Account numbers were swapped (detected via ABA checksum)")
        # Update local variables for remaining validation steps
        routing, account = clean_account, clean_routing
    else:
        routing, account = clean_routing, clean_account

    # ── 3. CRITICAL FIELD VALIDATION ─────────────────────────────────────────
    if not re.fullmatch(r"^\d{9}$", routing):
        critical_notes.append(f"Routing Number issue (Expected 9 digits, got '{routing}')")
    elif not is_valid_routing(routing):
        critical_notes.append(f"Routing Number Checksum Failed (OCR misread likely for '{routing}')")
        
    if not re.fullmatch(r"^\d{1,15}$", account): # Standardize range for accounts
        critical_notes.append(f"Account Number issue (Expected digits, got '{account}')")

    # Check for forced MANUAL_REVIEW_REQUIRED from ai_extractor.py
    # If the routing number is mathematically valid, we can relax this 
    # to allow auto-approval even if Tesseract was unconfirmed.
    if data.get("status") == "MANUAL_REVIEW_REQUIRED":
        if is_valid_routing(routing):
            info_notes.append("Forced Review relaxed: Routing is mathematically valid")
        else:
            critical_notes.append("Force Manual Review Required (Checksum or Extraction Failure)")

    # ── 4. INFORMATIONAL FLAGS & REPAIR LOGGING ──────────────────────────────
    if data.get("routing_repair_method") == "check_digit_math":
        info_notes.append("Routing Number was mathematically repaired")
    elif data.get("routing_repair_method") == "tesseract_primary":
        info_notes.append("Routing Number extracted via Tesseract (AI overridden)")
    elif data.get("routing_repair_method") == "ai_unconfirmed":
        # This is a bit risky, but if it passes checksum, it might be okay. 
        # Keep as informational for now.
        info_notes.append("Routing Number from AI only (Tesseract unconfirmed)")

    if data.get("table_mismatch_note"):
        critical_notes.append(data.get("table_mismatch_note"))

    if data.get("alignment_warning"):
        critical_notes.append(data.get("alignment_warning"))
        
    # ── 5. CONFIDENCE & AUTO-APPROVE LOGIC ────────────────────────────────────
    confidence = float(data.get("confidence_score") or 0.0)
    table_match = data.get("table_match") is True
    
    all_notes_str = " | ".join(critical_notes + info_notes)

    # RULE 1: If there are critical errors (Checksum failure, mismatch with table), ALWAYS MANUAL_REVIEW
    if critical_notes:
        return "MANUAL_REVIEW", all_notes_str
    
    # RULE 2: If it matches the summary table and routing is valid -> AUTO-APPROVE
    # We trust Table Matching (source of truth) even if there are informational flags.
    if table_match:
        return "APPROVED", f"Auto-Approved (Matches Table) | {all_notes_str}" if all_notes_str else "Auto-Approved (Matches Table)"

    # RULE 3: If confidence is very high and no critical errors -> AUTO-APPROVE
    # Threshold check (95% represents high confidence in GPT-4o OCR accuracy)
    if confidence >= 0.95:
        return "APPROVED", f"Auto-Approved (High Confidence: {confidence*100:.0f}%) | {all_notes_str}" if all_notes_str else f"Auto-Approved (High Confidence: {confidence*100:.0f}%)"
        
    # DEFAULT: If no critical errors but not high enough confidence for auto-approve
    return "MANUAL_REVIEW", f"Requires Review (Confidence: {confidence*100:.0f}%) | {all_notes_str}" if all_notes_str else f"Requires Review (Confidence: {confidence*100:.0f}%)"
