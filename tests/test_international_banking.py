#!/usr/bin/env python3
"""
Unit tests for international banking pattern matching and validation.

Tests US (ABA routing), UK (sort code), and unlabeled IBAN extraction.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from invoice_processor.parsers.pattern_library import PatternLibrary
from invoice_processor.parsers.extraction_utils import (
    extract_banking_info,
    detect_payment_method,
    extract_account_number_smart
)
from invoice_processor.core.constants import PARSING_FAILED


def test_aba_routing_validation():
    """Test ABA routing number checksum validation."""
    print("\n=== Testing ABA Routing Number Validation ===")

    # Valid routing numbers
    valid_routing_numbers = [
        "121000248",  # Wells Fargo
        "026009593",  # Bank of America
        "011000015",  # Federal Reserve
        "121000358",  # Bank of the West
    ]

    for routing in valid_routing_numbers:
        result = PatternLibrary.validate_aba_routing(routing)
        assert result, f"Valid routing number {routing} should pass validation"
        print(f"✓ {routing} validated successfully")

    # Invalid checksums
    invalid_routing_numbers = [
        "121000247",  # Off by one
        "000000000",  # All zeros
        "123456789",  # Random invalid
    ]

    for routing in invalid_routing_numbers:
        result = PatternLibrary.validate_aba_routing(routing)
        assert not result, f"Invalid routing number {routing} should fail validation"
        print(f"✓ {routing} correctly rejected")

    # Invalid formats
    assert not PatternLibrary.validate_aba_routing("12100024")  # Too short
    assert not PatternLibrary.validate_aba_routing("1210002481")  # Too long
    assert not PatternLibrary.validate_aba_routing("12100024A")  # Contains letter
    print("✓ Invalid formats correctly rejected")

    print("✓✓✓ ABA Routing Validation Tests PASSED")


def test_sort_code_validation():
    """Test UK sort code format validation."""
    print("\n=== Testing Sort Code Validation ===")

    # Valid sort codes
    valid_sort_codes = [
        "20-00-00",  # Barclays (with hyphens)
        "200000",    # Barclays (no hyphens)
        "60-16-13",  # NatWest (with hyphens)
        "601613",    # NatWest (no hyphens)
    ]

    for sort_code in valid_sort_codes:
        result = PatternLibrary.validate_sort_code(sort_code)
        assert result, f"Valid sort code {sort_code} should pass validation"
        print(f"✓ {sort_code} validated successfully")

    # Invalid sort codes
    invalid_sort_codes = [
        "2000",      # Too short
        "20000",     # 5 digits
        "2000000",   # Too long
        "20-00-0A",  # Contains letter
        "AB-CD-EF",  # All letters
    ]

    for sort_code in invalid_sort_codes:
        result = PatternLibrary.validate_sort_code(sort_code)
        assert not result, f"Invalid sort code {sort_code} should fail validation"
        print(f"✓ {sort_code} correctly rejected")

    print("✓✓✓ Sort Code Validation Tests PASSED")


def test_sort_code_normalization():
    """Test UK sort code normalization to XX-XX-XX format."""
    print("\n=== Testing Sort Code Normalization ===")

    test_cases = [
        ("200000", "20-00-00"),
        ("601613", "60-16-13"),
        ("20-00-00", "20-00-00"),  # Already normalized
        ("60 16 13", "60-16-13"),  # Spaces
    ]

    for input_code, expected in test_cases:
        result = PatternLibrary.normalize_sort_code(input_code)
        assert result == expected, f"Expected {expected}, got {result}"
        print(f"✓ {input_code} → {result}")

    print("✓✓✓ Sort Code Normalization Tests PASSED")


def test_unlabeled_iban_extraction():
    """Test IBAN extraction without 'IBAN:' label."""
    print("\n=== Testing Unlabeled IBAN Extraction ===")

    # Valid IBAN without label
    text = "Please pay to DE89370400440532013000 within 30 days."
    banking = extract_banking_info(text, text.split('\n'))

    assert banking['iban'] == "DE89370400440532013000", "Should extract unlabeled IBAN"
    assert banking['payment_method'] == "SEPA", "Should detect SEPA payment method"
    print(f"✓ Extracted unlabeled IBAN: {banking['iban']}")
    print(f"✓ Payment method: {banking['payment_method']}")

    # Invalid IBAN should not be extracted
    text_invalid = "Invoice number AB12345678901234567890 due soon."
    banking_invalid = extract_banking_info(text_invalid, text_invalid.split('\n'))

    assert banking_invalid['iban'] == PARSING_FAILED, "Should reject invalid IBAN"
    print("✓ Invalid IBAN correctly rejected")

    print("✓✓✓ Unlabeled IBAN Extraction Tests PASSED")


def test_us_banking_extraction():
    """Test US routing number + account number extraction."""
    print("\n=== Testing US Banking Extraction ===")

    # Test with explicit labels
    text = """
    Please pay via ACH:
    Routing Number: 121000248
    Account Number: 1234567890
    """
    banking = extract_banking_info(text, text.split('\n'))

    assert banking['routing_number'] == "121000248", f"Expected routing 121000248, got {banking['routing_number']}"
    assert banking['account_number'] == "1234567890", f"Expected account 1234567890, got {banking['account_number']}"
    assert banking['payment_method'] == "ACH", f"Expected ACH, got {banking['payment_method']}"
    print(f"✓ Routing Number: {banking['routing_number']}")
    print(f"✓ Account Number: {banking['account_number']}")
    print(f"✓ Payment Method: {banking['payment_method']}")

    # Test with alternative labels
    text2 = "ABA Number: 026009593, Acct #: 9876543210"
    banking2 = extract_banking_info(text2, text2.split('\n'))

    assert banking2['routing_number'] == "026009593", "Should extract ABA routing number"
    assert banking2['account_number'] == "9876543210", "Should extract account with 'Acct #' label"
    print("✓ Alternative labels work correctly")

    # Test invalid routing (bad checksum)
    text3 = "Routing Number: 121000247"  # Invalid checksum
    banking3 = extract_banking_info(text3, text3.split('\n'))

    assert banking3['routing_number'] == PARSING_FAILED, "Should reject invalid routing checksum"
    print("✓ Invalid routing checksum correctly rejected")

    print("✓✓✓ US Banking Extraction Tests PASSED")


def test_uk_banking_extraction():
    """Test UK sort code + account number extraction."""
    print("\n=== Testing UK Banking Extraction ===")

    # Test with explicit labels
    text = """
    Payment details:
    Sort Code: 20-00-00
    Account Number: 12345678
    """
    banking = extract_banking_info(text, text.split('\n'))

    assert banking['sort_code'] == "20-00-00", f"Expected sort code 20-00-00, got {banking['sort_code']}"
    assert banking['account_number'] == "12345678", f"Expected account 12345678, got {banking['account_number']}"
    assert banking['payment_method'] == "BACS", f"Expected BACS, got {banking['payment_method']}"
    print(f"✓ Sort Code: {banking['sort_code']}")
    print(f"✓ Account Number: {banking['account_number']}")
    print(f"✓ Payment Method: {banking['payment_method']}")

    # Test with no hyphens in sort code
    text2 = "SC: 601613, A/C: 87654321"
    banking2 = extract_banking_info(text2, text2.split('\n'))

    assert banking2['sort_code'] == "60-16-13", "Should normalize sort code to XX-XX-XX format"
    assert banking2['account_number'] == "87654321", "Should extract account with 'A/C' label"
    print("✓ Sort code normalization works")
    print("✓ Alternative labels work correctly")

    print("✓✓✓ UK Banking Extraction Tests PASSED")


def test_payment_method_detection():
    """Test automatic payment method detection."""
    print("\n=== Testing Payment Method Detection ===")

    # SEPA (German IBAN)
    result1 = detect_payment_method({'iban': 'DE89370400440532013000'})
    assert result1 == "SEPA", f"Expected SEPA, got {result1}"
    print(f"✓ German IBAN → {result1}")

    # SEPA_INTERNATIONAL (US IBAN, hypothetical)
    result2 = detect_payment_method({'iban': 'US64SVBKUS6S3300958879'})
    assert result2 == "SEPA_INTERNATIONAL", f"Expected SEPA_INTERNATIONAL, got {result2}"
    print(f"✓ Non-SEPA IBAN → {result2}")

    # ACH (US routing number)
    result3 = detect_payment_method({'routing_number': '121000248'})
    assert result3 == "ACH", f"Expected ACH, got {result3}"
    print(f"✓ US routing → {result3}")

    # BACS (UK sort code)
    result4 = detect_payment_method({'sort_code': '20-00-00'})
    assert result4 == "BACS", f"Expected BACS, got {result4}"
    print(f"✓ UK sort code → {result4}")

    # No banking info
    result5 = detect_payment_method({})
    assert result5 == PARSING_FAILED, f"Expected PARSING_FAILED, got {result5}"
    print(f"✓ No banking info → {result5}")

    print("✓✓✓ Payment Method Detection Tests PASSED")


def test_account_number_variations():
    """Test recognition of various account number terminology."""
    print("\n=== Testing Account Number Variations ===")

    variations = [
        ("Account Number: 12345678", "12345678"),
        ("Account No: 87654321", "87654321"),
        ("Acct #: 11223344", "11223344"),
        ("Banking Account: 99887766", "99887766"),
        ("Bank Account: 55667788", "55667788"),
        ("A/C: 44556677", "44556677"),
    ]

    for text, expected_account in variations:
        banking = extract_banking_info(text, [text])
        assert banking['account_number'] == expected_account, f"Failed to extract from '{text}'"
        print(f"✓ '{text}' → {banking['account_number']}")

    print("✓✓✓ Account Number Variations Tests PASSED")


def test_mixed_banking_systems():
    """Test invoice with multiple banking systems."""
    print("\n=== Testing Mixed Banking Systems ===")

    # Invoice with both IBAN and US routing (edge case)
    text = """
    European Payment:
    IBAN: DE89370400440532013000
    BIC: DEUTDEFF

    US Payment:
    Routing Number: 121000248
    Account Number: 1234567890
    """
    banking = extract_banking_info(text, text.split('\n'))

    # Should extract both
    assert banking['iban'] == "DE89370400440532013000", "Should extract IBAN"
    assert banking['bic'] == "DEUTDEFF", "Should extract BIC"
    assert banking['routing_number'] == "121000248", "Should extract routing number"
    assert banking['account_number'] == "1234567890", "Should extract account number"

    # Payment method should prefer IBAN (first in priority)
    assert banking['payment_method'] == "SEPA", "Should prefer SEPA when both present"

    print(f"✓ IBAN: {banking['iban']}")
    print(f"✓ BIC: {banking['bic']}")
    print(f"✓ Routing: {banking['routing_number']}")
    print(f"✓ Account: {banking['account_number']}")
    print(f"✓ Payment Method (IBAN priority): {banking['payment_method']}")

    print("✓✓✓ Mixed Banking Systems Tests PASSED")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  INTERNATIONAL BANKING UNIT TESTS")
    print("="*60)

    try:
        test_aba_routing_validation()
        test_sort_code_validation()
        test_sort_code_normalization()
        test_unlabeled_iban_extraction()
        test_us_banking_extraction()
        test_uk_banking_extraction()
        test_payment_method_detection()
        test_account_number_variations()
        test_mixed_banking_systems()

        print("\n" + "="*60)
        print("  🎉 ALL INTERNATIONAL BANKING TESTS PASSED! 🎉")
        print("="*60 + "\n")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
