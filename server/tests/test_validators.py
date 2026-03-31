# import pytest
import sys
import os

# Add the server directory to the path so we can import validators
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validators import is_valid_routing, try_repair_routing

def test_is_valid_routing():
    # Real valid routing numbers (using standard ABA checksum)
    assert is_valid_routing("122105155") is True # Prosperity Bank
    assert is_valid_routing("021000021") is True # JPMorgan Chase
    assert is_valid_routing("051000017") is True # Bank of America
    
    # Invalid numbers
    assert is_valid_routing("122105154") is False # Off by 1
    assert is_valid_routing("12210515") is False # 8 digits
    assert is_valid_routing("1221051555") is False # 10 digits
    assert is_valid_routing("ABCDEFGHI") is False # Non-digits
    assert is_valid_routing("") is False

def test_try_repair_routing():
    # Prosperity Bank: 122105155 (Check digit 5)
    assert try_repair_routing("12210515") == "122105155"
    
    # Chase: 021000021 (Check digit 1)
    assert try_repair_routing("02100002") == "021000021"
    
    # BoA: 051000017 (Check digit 7)
    assert try_repair_routing("05100001") == "051000017"
    
    # Already 9 digits (too long)
    assert try_repair_routing("122105155") is None
    
    # Too short
    assert try_repair_routing("122105") is None
    
    # Non-digits
    assert try_repair_routing("ABCDEFGH") is None

if __name__ == "__main__":
    # If run directly instead of via pytest
    test_is_valid_routing()
    test_try_repair_routing()
    print("All validator tests passed!")
