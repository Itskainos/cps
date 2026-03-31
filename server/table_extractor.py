import pdfplumber
import re
from typing import Dict, Tuple, List, Optional
import logging
import io

logger = logging.getLogger("quicktrack")

def extract_table_data(pdf_bytes: bytes, page_indices: Optional[List[int]] = None) -> Dict[str, Tuple[str, float]]:
    """
    Extracts the source-of-truth table mapping Check Number -> (Date, Amount).
    
    Args:
        pdf_bytes: Raw bytes of the PDF.
        page_indices: Optional 0-based list of page numbers to scan. 
                     If None, defaults to scanning first 7 pages.
    
    Returns:
        Dict mapping check_number (str) -> (ISO date string, amount float)
    """
    check_data = {}
    
    # Matches dates like 02/15 or 02/15/26 or 02/15/2026
    date_pattern = re.compile(r'^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?$')
    statement_year = "2026" # Fallback based on known dataset
    
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            # 1. Try to dynamically extract statement year from page 1
            if len(pdf.pages) > 0:
                first_page_text = pdf.pages[0].extract_text() or ""
                year_matches = re.findall(r'20\d{2}', first_page_text)
                if year_matches:
                    statement_year = year_matches[0]
            
            # 2. Determine which pages to scan
            if page_indices is not None:
                scan_pages = [p for p in page_indices if p < len(pdf.pages)]
            else:
                # Default: scan first 7 pages (where header tables usually are)
                scan_pages = range(min(7, len(pdf.pages)))
            
            for i in scan_pages:
                page = pdf.pages[i]
                words = page.extract_words()
                
                # Group words into lines based on Y coordinate (vertical). 
                # Tolerance of 3 points is standard for slight PDF misalignments.
                lines = {}
                for w in words:
                    y0 = round(w['top'] / 3) * 3
                    if y0 not in lines:
                        lines[y0] = []
                    lines[y0].append(w)
                
                # Process line by line
                for y0 in sorted(lines.keys()):
                    # Sort left-to-right
                    line_words = sorted(lines[y0], key=lambda w: w['x0'])
                    texts = [w['text'] for w in line_words]
                    
                    # Scan across the words in this line looking for Date -> Number -> Amount triplets
                    for j in range(len(texts) - 2):
                        match = date_pattern.match(texts[j])
                        if match:
                            # Found a date. Next word should be check number or asterisk then number
                            chk_text = texts[j+1].replace('*', '').strip()
                            
                            if chk_text.isdigit() and len(chk_text) >= 3:
                                # Next word should be amount
                                amt_text = texts[j+2].replace('$', '').replace(',', '').strip()
                                
                                # Sometimes amount is negative or has a trailing minus like 150.00-
                                is_negative = False
                                if amt_text.endswith('-'):
                                    is_negative = True
                                    amt_text = amt_text[:-1]
                                elif amt_text.startswith('-'):
                                    is_negative = True
                                    amt_text = amt_text[1:]
                                
                                # Check if it's a valid float
                                if amt_text.replace('.', '', 1).isdigit():
                                    try:
                                        amount = float(amt_text)
                                        if is_negative: amount = -amount
                                        
                                        # Ensure we have absolute value for our use case (checks are debits)
                                        amount = abs(amount)
                                        
                                        # Format Date
                                        m, d, y = match.groups()
                                        if not y:
                                            y = statement_year
                                        elif len(y) == 2:
                                            y = "20" + y
                                            
                                        iso_date = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
                                        
                                        # Register to source of truth!
                                        check_data[chk_text] = (iso_date, amount)
                                    except ValueError:
                                        pass

    except Exception as e:
        logger.error(f"Failed to extract table data: {e}", exc_info=True)
        
    logger.info(f"Table Extractor found {len(check_data)} checks in summary tables.")
    return check_data
