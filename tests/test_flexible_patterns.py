#!/usr/bin/env python3
"""
Unit tests for flexible pattern matching across ALL invoice fields.

Tests v2.2.0 features:
- Flexible sender/recipient patterns
- Flexible amount patterns
- Invoice metadata extraction (number, dates, terms)
- Tax/VAT extraction
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from invoice_processor.parsers.parser_utils import (
    extract_invoice_metadata,
    extract_tax_info,
    PARSING_FAILED
)


def test_flexible_sender_patterns():
    """Test flexible sender label recognition."""
    print("\n=== Testing Flexible Sender Patterns ===")

    test_cases = [
        "Billed by: Acme Corp",
        "Issued by: Tech Services Inc",
        "Provider: Consulting Solutions",
        "Vendor: Office Supplies Ltd",
        "Supplier: Manufacturing Co",
        "Contractor: Build Services",
    ]

    # Note: Sender extraction happens in strategies, not in metadata
    # This test documents the patterns exist
    from invoice_processor.parsers.pattern_library import PatternLibrary

    patterns = PatternLibrary.SENDER_LABELS['en']
    assert len(patterns) >= 12, f"Should have at least 12 sender patterns, got {len(patterns)}"
    print(f"✓ {len(patterns)} sender patterns defined")
    print("✓✓✓ Flexible Sender Patterns Tests PASSED")


def test_flexible_recipient_patterns():
    """Test flexible recipient label recognition."""
    print("\n=== Testing Flexible Recipient Patterns ===")

    from invoice_processor.parsers.pattern_library import PatternLibrary

    patterns = PatternLibrary.RECIPIENT_LABELS['en']
    assert len(patterns) >= 12, f"Should have at least 12 recipient patterns, got {len(patterns)}"
    print(f"✓ {len(patterns)} recipient patterns defined")
    print("✓✓✓ Flexible Recipient Patterns Tests PASSED")


def test_flexible_amount_patterns():
    """Test flexible amount label recognition."""
    print("\n=== Testing Flexible Amount Patterns ===")

    from invoice_processor.parsers.pattern_library import PatternLibrary

    patterns = PatternLibrary.AMOUNT_PATTERNS
    assert len(patterns) >= 20, f"Should have at least 20 amount patterns, got {len(patterns)}"
    print(f"✓ {len(patterns)} amount patterns defined")
    print("✓✓✓ Flexible Amount Patterns Tests PASSED")


def test_invoice_number_extraction():
    """Test invoice number extraction with various labels."""
    print("\n=== Testing Invoice Number Extraction ===")

    test_cases = [
        ("Invoice Number: INV-2024-001", "INV-2024-001"),
        ("Invoice No: 12345", "12345"),
        ("Invoice #: ABC-123", "ABC-123"),
        ("Reference: REF-999", "REF-999"),
        ("Ref: X123456", "X123456"),
        ("Document Number: DOC-2024-01", "DOC-2024-01"),
        ("Bill #: B-001", "B-001"),
        ("Rechnungsnummer: RN-2024-001", "RN-2024-001"),  # German
    ]

    for text, expected in test_cases:
        metadata = extract_invoice_metadata(text)
        assert metadata['invoice_number'] == expected, \
            f"Expected '{expected}', got '{metadata['invoice_number']}' for text: {text}"
        print(f"✓ '{text}' → {metadata['invoice_number']}")

    print("✓✓✓ Invoice Number Extraction Tests PASSED")


def test_invoice_date_extraction():
    """Test invoice date extraction with various formats."""
    print("\n=== Testing Invoice Date Extraction ===")

    test_cases = [
        ("Invoice Date: 2024-01-15", "2024-01-15"),
        ("Date: 01/15/2024", "01/15/2024"),
        ("Issued: 15.01.2024", "15.01.2024"),
        ("Issued on: 2024-01-15", "2024-01-15"),
        ("Date of Issue: 15/01/2024", "15/01/2024"),
        ("Rechnungsdatum: 15.01.2024", "15.01.2024"),  # German
    ]

    for text, expected in test_cases:
        metadata = extract_invoice_metadata(text)
        assert metadata['invoice_date'] == expected, \
            f"Expected '{expected}', got '{metadata['invoice_date']}' for text: {text}"
        print(f"✓ '{text}' → {metadata['invoice_date']}")

    print("✓✓✓ Invoice Date Extraction Tests PASSED")


def test_due_date_extraction():
    """Test due date extraction with various labels."""
    print("\n=== Testing Due Date Extraction ===")

    test_cases = [
        ("Due Date: 2024-02-15", "2024-02-15"),
        ("Payment Due: 02/15/2024", "02/15/2024"),
        ("Pay by: 15.02.2024", "15.02.2024"),
        ("Payable by: 2024-02-15", "2024-02-15"),
        ("Due on: 15/02/2024", "15/02/2024"),
        ("Fälligkeitsdatum: 15.02.2024", "15.02.2024"),  # German
    ]

    for text, expected in test_cases:
        metadata = extract_invoice_metadata(text)
        assert metadata['due_date'] == expected, \
            f"Expected '{expected}', got '{metadata['due_date']}' for text: {text}"
        print(f"✓ '{text}' → {metadata['due_date']}")

    print("✓✓✓ Due Date Extraction Tests PASSED")


def test_payment_terms_extraction():
    """Test payment terms extraction."""
    print("\n=== Testing Payment Terms Extraction ===")

    test_cases = [
        ("Payment Terms: Net 30", "Net 30"),
        ("Terms: Net 30 days", "Net 30 days"),
        ("Payment Terms: Due on receipt", "Due on receipt"),
        ("Zahlungsbedingungen: Zahlbar innerhalb 30 Tagen", "Zahlbar innerhalb 30 Tagen"),  # German
    ]

    for text, expected in test_cases:
        metadata = extract_invoice_metadata(text)
        # Payment terms might include more context, so check if expected is in result
        assert expected in metadata['payment_terms'], \
            f"Expected '{expected}' in result, got '{metadata['payment_terms']}' for text: {text}"
        print(f"✓ '{text}' → {metadata['payment_terms']}")

    print("✓✓✓ Payment Terms Extraction Tests PASSED")


def test_tax_amount_extraction():
    """Test tax/VAT amount extraction."""
    print("\n=== Testing Tax Amount Extraction ===")

    test_cases = [
        ("VAT: €250.00", "€250.00"),
        ("Tax: $50.00", "$50.00"),
        ("Sales Tax: £100.00", "£100.00"),
        ("GST: $75.50", "$75.50"),
        ("MwSt: 50,00", "50,00"),  # German
    ]

    for text, expected in test_cases:
        tax_info = extract_tax_info(text)
        assert expected in tax_info['tax_amount'], \
            f"Expected '{expected}' in result, got '{tax_info['tax_amount']}' for text: {text}"
        print(f"✓ '{text}' → {tax_info['tax_amount']}")

    print("✓✓✓ Tax Amount Extraction Tests PASSED")


def test_tax_rate_extraction():
    """Test tax/VAT rate extraction."""
    print("\n=== Testing Tax Rate Extraction ===")

    test_cases = [
        ("VAT: 19%", "19%"),
        ("Tax Rate: 7.5%", "7.5%"),
        ("Sales Tax Rate: 10%", "10%"),
        ("MwSt: 19%", "19%"),  # German
    ]

    for text, expected in test_cases:
        tax_info = extract_tax_info(text)
        assert tax_info['tax_rate'] == expected, \
            f"Expected '{expected}', got '{tax_info['tax_rate']}' for text: {text}"
        print(f"✓ '{text}' → {tax_info['tax_rate']}")

    print("✓✓✓ Tax Rate Extraction Tests PASSED")


def test_tax_id_extraction():
    """Test tax/VAT ID extraction."""
    print("\n=== Testing Tax ID Extraction ===")

    test_cases = [
        ("VAT Number: DE123456789", "DE123456789"),
        ("Tax ID: GB987654321", "GB987654321"),
        ("TIN: 12-3456789", "12-3456789"),
        ("EIN: 12-3456789", "12-3456789"),  # US
        ("USt-IdNr: DE123456789", "DE123456789"),  # German
    ]

    for text, expected in test_cases:
        tax_info = extract_tax_info(text)
        assert tax_info['tax_id'] == expected, \
            f"Expected '{expected}', got '{tax_info['tax_id']}' for text: {text}"
        print(f"✓ '{text}' → {tax_info['tax_id']}")

    print("✓✓✓ Tax ID Extraction Tests PASSED")


def test_missing_fields():
    """Test that missing fields return PARSING_FAILED."""
    print("\n=== Testing Missing Fields Handling ===")

    text = "This is an invoice with no metadata or tax info."

    metadata = extract_invoice_metadata(text)
    assert metadata['invoice_number'] == PARSING_FAILED
    assert metadata['invoice_date'] == PARSING_FAILED
    assert metadata['due_date'] == PARSING_FAILED
    assert metadata['payment_terms'] == PARSING_FAILED
    print("✓ Missing metadata fields correctly marked as PARSING_FAILED")

    tax_info = extract_tax_info(text)
    assert tax_info['tax_amount'] == PARSING_FAILED
    assert tax_info['tax_rate'] == PARSING_FAILED
    assert tax_info['tax_id'] == PARSING_FAILED
    print("✓ Missing tax fields correctly marked as PARSING_FAILED")

    print("✓✓✓ Missing Fields Handling Tests PASSED")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  FLEXIBLE PATTERN MATCHING TESTS (v2.2.0)")
    print("="*60)

    try:
        test_flexible_sender_patterns()
        test_flexible_recipient_patterns()
        test_flexible_amount_patterns()
        test_invoice_number_extraction()
        test_invoice_date_extraction()
        test_due_date_extraction()
        test_payment_terms_extraction()
        test_tax_amount_extraction()
        test_tax_rate_extraction()
        test_tax_id_extraction()
        test_missing_fields()

        print("\n" + "="*60)
        print("  🎉 ALL FLEXIBLE PATTERN TESTS PASSED! 🎉")
        print("="*60 + "\n")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
