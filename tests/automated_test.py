#!/usr/bin/env python3
"""Automated test to verify all success criteria without manual interaction."""

import os
import sys
import time
from pathlib import Path

# Add src to path to import invoice_processor package
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from invoice_processor.parsers.pdf_parser import parse_invoice
from invoice_processor.utils.file_manager import FileManager
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


def print_header(text):
    """Print a test section header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def test_1_folder_structure():
    """Test 1: Verify folder structure exists."""
    print_header("TEST 1: Folder Structure")

    pending = Path("invoices/pending")
    processed = Path("invoices/processed")

    assert pending.exists(), "Pending folder missing"
    assert pending.is_dir(), "Pending is not a directory"
    print("✓ Pending folder exists")

    assert processed.exists(), "Processed folder missing"
    assert processed.is_dir(), "Processed is not a directory"
    print("✓ Processed folder exists")

    print("✓✓✓ TEST 1 PASSED")


def test_2_pdf_parser():
    """Test 2: PDF parser handles all test cases."""
    print_header("TEST 2: PDF Parser")

    test_cases = [
        ("test_invoices/simple_eur.pdf", "Should parse EUR invoice"),
        ("test_invoices/simple_usd.pdf", "Should parse USD invoice"),
        ("test_invoices/messy_german.pdf", "Should parse German invoice"),
        ("test_invoices/missing_data.pdf", "Should mark missing data as PARSING FAILED"),
        ("test_invoices/corrupted.pdf", "Should handle corrupted PDF gracefully"),
    ]

    for pdf_path, description in test_cases:
        if not Path(pdf_path).exists():
            print(f"⚠ Skipping {pdf_path} - file not found")
            continue

        print(f"\n  Testing: {pdf_path}")
        result = parse_invoice(pdf_path)

        assert isinstance(result, dict), f"Parser should return dict for {pdf_path}"
        assert 'sender' in result, "Missing 'sender' key"
        assert 'recipient' in result, "Missing 'recipient' key"
        assert 'amount' in result, "Missing 'amount' key"
        assert 'currency' in result, "Missing 'currency' key"

        print(f"    From: {result['sender']}")
        print(f"    To: {result['recipient']}")
        print(f"    Amount: {result['amount']}")
        print(f"    Currency: {result['currency']}")
        print(f"    ✓ {description}")

    print("\n✓✓✓ TEST 2 PASSED")


def test_3_file_manager():
    """Test 3: File manager operations."""
    print_header("TEST 3: File Manager")

    fm = FileManager()
    print("✓ FileManager initialized")

    # Scan for initial files
    files = fm.scan_folder(initial_scan=True)
    print(f"✓ Initial scan found {len(files)} files: {files}")

    # Create a test file
    test_file = Path("invoices/pending/test_fm.pdf")
    with open(test_file, 'w') as f:
        f.write("%PDF-1.4\ntest")
    print("✓ Created test file")

    # Scan for new files
    new_files = fm.scan_folder(initial_scan=False)
    assert "test_fm.pdf" in new_files, "New file not detected"
    print("✓ New file detected in scan")

    # Move file
    success = fm.move_invoice("test_fm.pdf")
    assert success, "File move failed"
    assert not (Path("invoices/pending") / "test_fm.pdf").exists(), "File still in pending"
    assert (Path("invoices/processed") / "test_fm.pdf").exists(), "File not in processed"
    print("✓ File moved successfully")

    # Cleanup
    (Path("invoices/processed") / "test_fm.pdf").unlink()

    print("✓✓✓ TEST 3 PASSED")


def test_4_currency_detection():
    """Test 4: Currency detection determines Local vs International."""
    print_header("TEST 4: Currency-based Transfer Type")

    eur_result = parse_invoice("test_invoices/simple_eur.pdf")
    usd_result = parse_invoice("test_invoices/simple_usd.pdf")

    assert eur_result['currency'] == 'EUR', "EUR invoice should detect EUR"
    print("✓ EUR invoice detected as EUR (Local)")

    assert usd_result['currency'] == 'USD', "USD invoice should detect USD"
    print("✓ USD invoice detected as USD (International)")

    print("✓✓✓ TEST 4 PASSED")


def test_5_edge_cases():
    """Test 5: Edge cases and error handling."""
    print_header("TEST 5: Edge Cases")

    # Test non-existent file
    result = parse_invoice("nonexistent.pdf")
    assert all(v == "PARSING FAILED" for v in result.values()), \
        "Non-existent file should return all PARSING FAILED"
    print("✓ Non-existent file handled gracefully")

    # Test corrupted PDF
    result = parse_invoice("test_invoices/corrupted.pdf")
    assert all(v == "PARSING FAILED" for v in result.values()), \
        "Corrupted PDF should return all PARSING FAILED"
    print("✓ Corrupted PDF handled gracefully")

    # Test file with missing data
    result = parse_invoice("test_invoices/missing_data.pdf")
    assert result['sender'] == "PARSING FAILED", "Should fail to find sender"
    print("✓ Missing sender detected correctly")

    # Test FileManager with non-existent file
    fm = FileManager()
    success = fm.move_invoice("nonexistent_file.pdf")
    assert not success, "Moving non-existent file should fail gracefully"
    print("✓ FileManager handles non-existent file")

    print("✓✓✓ TEST 5 PASSED")


def test_6_number_formats():
    """Test 6: Different number formats (US vs European)."""
    print_header("TEST 6: Number Format Parsing")

    # US format: 1,234.56
    eur_result = parse_invoice("test_invoices/simple_eur.pdf")
    assert eur_result['amount'] in ['1,250.00', '1250.00'], \
        f"Expected 1,250.00 or 1250.00, got {eur_result['amount']}"
    print(f"✓ US format parsed: {eur_result['amount']}")

    # European format: 1.234,56
    german_result = parse_invoice("test_invoices/messy_german.pdf")
    assert german_result['amount'] in ['8.750,50', '8750.50', '8750,50'], \
        f"Expected European format, got {german_result['amount']}"
    print(f"✓ European format parsed: {german_result['amount']}")

    print("✓✓✓ TEST 6 PASSED")


def test_7_background_scanning_simulation():
    """Test 7: Simulate background scanning behavior."""
    print_header("TEST 7: Background Scanning (Simulated)")

    fm = FileManager()

    # Initial scan
    initial_files = fm.scan_folder(initial_scan=True)
    print(f"✓ Initial scan: {len(initial_files)} files")

    # Create new file
    new_invoice = Path("invoices/pending/background_test.pdf")
    c = canvas.Canvas(str(new_invoice), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, 10*inch, "TEST INVOICE")
    c.setFont("Helvetica", 11)
    c.drawString(1*inch, 9.5*inch, "From: Background Test Inc")
    c.drawString(1*inch, 9*inch, "To: Test Client")
    c.drawString(1*inch, 8.5*inch, "Amount: 100.00 EUR")
    c.save()
    print("✓ Created new invoice during 'runtime'")

    # Scan again (simulating background scan)
    new_files = fm.scan_folder(initial_scan=False)
    assert "background_test.pdf" in new_files, "New file not detected in background scan"
    print("✓ Background scan detected new file")

    # Cleanup
    new_invoice.unlink()

    print("✓✓✓ TEST 7 PASSED")


def test_8_app_launch():
    """Test 8: Verify app can launch without errors."""
    print_header("TEST 8: Application Launch")

    print("Testing imports...")
    try:
        import tkinter as tk
        from tkinter import ttk
        print("✓ Tkinter available")

        import pdfplumber
        print("✓ pdfplumber available")

        from invoice_processor.parsers.pdf_parser import parse_invoice
        print("✓ pdf_parser module loads")

        from invoice_processor.utils.file_manager import FileManager
        print("✓ file_manager module loads")

        # Try to import main (but don't run it)
        from invoice_processor.gui import main
        print("✓ main module loads without errors")

    except Exception as e:
        print(f"✗ Import error: {e}")
        raise

    print("✓✓✓ TEST 8 PASSED")


def run_all_tests():
    """Run all automated tests."""
    print("\n" + "="*60)
    print("  INVOICE PROCESSOR - AUTOMATED TEST SUITE")
    print("="*60)

    tests = [
        test_1_folder_structure,
        test_2_pdf_parser,
        test_3_file_manager,
        test_4_currency_detection,
        test_5_edge_cases,
        test_6_number_formats,
        test_7_background_scanning_simulation,
        test_8_app_launch,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n✗✗✗ TEST FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n✗✗✗ TEST ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*60)
    print(f"  TEST SUMMARY")
    print("="*60)
    print(f"  Passed: {passed}/{len(tests)}")
    print(f"  Failed: {failed}/{len(tests)}")

    if failed == 0:
        print("\n  🎉 ALL TESTS PASSED! 🎉")
        print("="*60)
        return 0
    else:
        print("\n  ❌ SOME TESTS FAILED")
        print("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
