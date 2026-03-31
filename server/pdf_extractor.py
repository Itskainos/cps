"""
PDF Check Extractor Module
Extracts signed check images from bank statement PDFs.
"""
import io
import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageFilter, ImageOps
from typing import List, Tuple, Optional
import re
import logging

logger = logging.getLogger("quicktrack")
def _normalize_image(img: Image.Image) -> Image.Image:
    """Convert any image mode to grayscale with white background."""
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        alpha = img.convert('RGBA').split()[-1]
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.paste(img, mask=alpha)
        return bg.convert('L')
    return img.convert('L')


def _is_signed_check(pixels: np.ndarray, W: int, H: int) -> Tuple[bool, str]:
    """
    Determine if an image is a signed check with MICR values.
    Returns (True, "found") or (False, "reason for skip").
    """
    aspect_ratio = W / H
    
    # Check dimensions (stricter width/height for standard checks)
    if W < 700: # Lowered from 950 to capture more varieties
        return False, f"too small (W={W})"
    if H < 180: # Lowered from 250
        return False, f"too short (H={H})"
    if aspect_ratio < 1.7:
        return False, f"too square (AR={aspect_ratio:.2f})"
    if aspect_ratio > 3.8:
        return False, f"too wide (AR={aspect_ratio:.2f}) - likely logo banner"

    # Binary mask: text/ink pixels = 255, background = 0
    ink_mask = (pixels < 185).astype(np.uint8) * 255
    
    # Global ink density - Checks are mostly white space (ink < 30%)
    total_ink_ratio = np.sum(ink_mask > 0) / float(ink_mask.size)
    if total_ink_ratio > 0.35:
        # Logos are very dense and high-contrast
        return False, f"too dense ({total_ink_ratio:.1%}) - likely logo"
    if total_ink_ratio < 0.001:
        return False, f"too sparse ({total_ink_ratio:.1%}) - likely empty"

    # --- Vertical Distribution Check (3-Band DNA) ---
    # Divide into top, mid, bottom
    top = ink_mask[:int(0.33 * H), :]
    mid = ink_mask[int(0.33 * H):int(0.66 * H), :]
    bot = ink_mask[int(0.66 * H):, :]
    
    top_density = np.sum(top > 0) / float(top.size)
    mid_density = np.sum(mid > 0) / float(mid.size)
    bot_density = np.sum(bot > 0) / float(bot.size)
    
    # Checks have a sparse mid-section (payee line) compared to top/bottom
    # Deposit slips and logos are usually more uniformly dense vertically.
    if mid_density > 0.15:
        return False, f"middle too dense ({mid_density:.3f}) - likely deposit slip"
    
    # Real checks have dozens of letters and signature strokes.
    # We measure horizontal transitions (black to white) to approximate complexity.
    transitions = np.sum(np.diff(ink_mask.astype(np.int16), axis=1) != 0)
    if transitions < 80: # Very lenient for clean digital PDFs
        return False, f"too simple (transitions={transitions}) - likely logo"

    # --- Specific ROI checks ---
    # Signature region: bottom-right quadrant
    sig_roi = ink_mask[int(0.65 * H):int(0.95 * H), int(0.65 * W):int(0.98 * W)]
    sig_ratio = np.sum(sig_roi > 0) / float(sig_roi.size)

    # Bottom strip: where MICR routing/account numbers are printed
    bottom_strip = ink_mask[int(0.85 * H):int(0.99 * H), int(0.10 * W):int(0.90 * W)]
    bottom_strip_density = np.sum(bottom_strip > 0) / float(bottom_strip.size)

    if sig_ratio < 0.008: # Natural grays might have very light ink
        return False, f"signature check failed ({sig_ratio:.3f})"
    if bottom_strip_density < 0.003: # High-res digital PDFs have very thin MICR
        return False, f"MICR strip check failed ({bottom_strip_density:.3f})"

    # --- Step 3: Gradient Variance (Edginess) ---
    # A valid check must have high variance in the bottom 15% and bottom-right quadrant.
    def calculate_variance(region):
        # Approximate Laplacian variance using numpy gradients
        # dy, dx = np.gradient(region.astype(float))
        # This measures the "sharpness" of edges
        grad_x = np.diff(region.astype(float), axis=1)
        grad_y = np.diff(region.astype(float), axis=0)
        return np.var(grad_x) + np.var(grad_y)
    
    bot_15 = pixels[int(0.85 * H):, :]
    sig_quad = pixels[int(0.50 * H):, int(0.50 * W):]
    
    bot_variance = calculate_variance(bot_15)
    sig_variance = calculate_variance(sig_quad)
    
    # Very lenient thresholds for initial non-opencv version
    if bot_variance < 5:
        return False, f"Edge variance too low in MICR strip ({bot_variance:.1f})"
    if sig_variance < 3:
        return False, f"Edge variance too low in signature quad ({sig_variance:.1f})"

    return True, "valid check"


def parse_range_string(range_str: str, max_pages: int) -> List[int]:
    """
    Parses a string like "1, 3, 5-10" into a list of 0-based page indices.
    """
    if not range_str or not range_str.strip():
        return []

    indices = set()
    parts = range_str.split(',')
    
    for part in parts:
        part = part.strip()
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                # User enters 1-based, we convert to 0-based
                for p in range(start, end + 1):
                    if 1 <= p <= max_pages:
                        indices.add(p - 1)
            except ValueError:
                continue
        elif part.isdigit():
            p = int(part)
            if 1 <= p <= max_pages:
                indices.add(p - 1)
                
    return sorted(list(indices))


def extract_checks_from_pdf(pdf_bytes: bytes, page_indices: Optional[List[int]] = None, force_scan: bool = False) -> List[Tuple[bytes, str]]:
    """
    Extract all signed check images from a bank statement PDF.
    
    Args:
        pdf_bytes: Raw bytes of the PDF file.
        page_indices: Optional list of 0-based page indices to process.
        
    Returns:
        List of (image_bytes_png, filename) tuples for each detected check.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    checks: List[Tuple[bytes, str]] = []
    img_counter = 0

    # Determine which pages to scan
    pages_to_scan = page_indices if page_indices is not None else range(doc.page_count)
    msg = f"[EXTRACTOR] Starting scan on {len(pages_to_scan)} pages (Force={force_scan}): {[p+1 for p in pages_to_scan]}"
    print(msg) # Ensure visibility in terminal
    logger.info(msg)

    for page_num in pages_to_scan:
        if page_num >= doc.page_count:
            continue
            
        page = doc[page_num]
        
        # --- Structural Anchoring ---
        # Find the header "Checks and Other Debits" to avoid capturing logos above it
        search_zone_y_min = 0
        text_instances = page.search_for("Checks and Other Debits")
        if text_instances:
            search_zone_y_min = text_instances[0].y0 - 20
        
        images = page.get_images(full=True)

        for img_info in images:
            xref = img_info[0]
            width = img_info[2]
            height = img_info[3]

            # Skip tiny images (logos, icons, or narrow fragments)
            if width < 400 or height < 200:
                continue

            # --- Explicit Range & Page Logging ---
            # CONFIRM: Are we on a page we are supposed to be scanning?
            if page_num not in pages_to_scan: # Should never happen due to for-loop but good to be certain
                logger.warning(f"CRITICAL: Scanning page {page_num+1} which is NOT in range {pages_to_scan}")
                continue

            try:
                # --- Image Extraction & DNA Validation ---
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                img = Image.open(io.BytesIO(image_bytes))
                img_gray = _normalize_image(img)
                W, H = img_gray.size

                pixels = np.array(img_gray)
                mean_val = np.mean(pixels)

                # Handle inverted (black background) images
                if mean_val < 127:
                    pixels = 255 - pixels

                # --- SCAN LOGIC ---
                if force_scan:
                    # When force_scan is true (manual selection), we skip all DNA/Dimension filters
                    # We only check for absolute tiny images (logos)
                    if W < 300 or H < 100:
                        logger.info(f"Page {page_num+1} img {xref}: Skipped even in Force mode (too tiny W={W}, H={H})")
                        continue
                    is_check, reason = True, "forced"
                else:
                    is_check, reason = _is_signed_check(pixels, W, H)

                if is_check:
                    # Convert the original image to JPEG for storage
                    # (re-open from original bytes to preserve quality)
                    original_img = Image.open(io.BytesIO(image_bytes))
                    
                    # If inverted, invert back for display
                    if mean_val < 127:
                        if original_img.mode == 'L':
                            inv_arr = 255 - np.array(original_img)
                            original_img = Image.fromarray(inv_arr)
                        elif original_img.mode in ('RGB', 'RGBA'):
                            arr = np.array(original_img.convert('RGB'))
                            inv_arr = 255 - arr
                            original_img = Image.fromarray(inv_arr)
                    
                    # --- Natural Grayscale Processing for AI OCR ---
                    # 1. Grayscale & Contrast
                    proc_img = original_img.convert('L')
                    proc_img = ImageOps.autocontrast(proc_img, cutoff=1)
                    
                    # 2. Subtle Sharpening (better for GPT-4o-mini than binary conversion)
                    proc_img = proc_img.filter(ImageFilter.SHARPEN)
                    
                    # We no longer binarize or dilate, as it distorts characters for modern AI.
                    original_img = proc_img
                    
                    buf = io.BytesIO()
                    original_img.convert('RGB').save(buf, format='JPEG', quality=95) # Higher quality for OCR
                    jpeg_bytes = buf.getvalue()

                    filename = f"check_p{page_num + 1}_{img_counter}.jpg"
                    checks.append((jpeg_bytes, filename))
                    img_counter += 1
                else:
                    if W > 500: # Only log reasoning for larger images to avoid spam
                        logger.info(f"Page {page_num+1} img {xref}: Skipped ({reason})")

            except Exception:
                continue

    doc.close()
    return checks
