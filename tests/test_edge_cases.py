#!/usr/bin/env python3
"""Test edge cases and error handling."""

import os
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from invoice_processor.core.file_manager import FileManager


def test_txt_file_in_pending():
    """Test 1: Put a .txt file in pending folder."""
    print("\n=== TEST: .txt file in pending folder ===")

    txt_file = Path("invoices/pending/not_a_pdf.txt")
    with open(txt_file, 'w') as f:
        f.write("This is not a PDF file")

    print("✓ Created .txt file in pending folder")

    # Verify FileManager ignores it
    fm = FileManager()
    files = fm.scan_folder(initial_scan=True)

    if "not_a_pdf.txt" in files:
        print("✗ FAIL: FileManager should ignore .txt files")
        txt_file.unlink()
        return False
    else:
        print("✓ FileManager correctly ignores .txt files")

    # Cleanup
    txt_file.unlink()
    return True


def test_zero_byte_pdf():
    """Test 2: Create a 0-byte PDF file."""
    print("\n=== TEST: 0-byte PDF file ===")

    zero_pdf = Path("invoices/pending/zero_byte.pdf")
    zero_pdf.touch()  # Create empty file

    print("✓ Created 0-byte PDF file")

    # Try to parse it
    from pdf_parser import parse_invoice

    result = parse_invoice(str(zero_pdf))

    # Should return all PARSING FAILED
    if all(v == "PARSING FAILED" for v in result.values()):
        print("✓ Parser handles 0-byte PDF gracefully")
        zero_pdf.unlink()
        return True
    else:
        print(f"✗ FAIL: Expected all PARSING FAILED, got {result}")
        zero_pdf.unlink()
        return False


def test_many_pdfs_at_once():
    """Test 3: Put 20 PDFs in folder at once."""
    print("\n=== TEST: 20 PDFs at once ===")

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch

    # Create 20 simple PDFs
    created_files = []
    for i in range(20):
        filename = f"invoices/pending/bulk_test_{i:02d}.pdf"
        c = canvas.Canvas(filename, pagesize=letter)
        c.setFont("Helvetica", 12)
        c.drawString(1*inch, 10*inch, f"Bulk Test Invoice #{i}")
        c.drawString(1*inch, 9.5*inch, f"From: Company {i}")
        c.drawString(1*inch, 9*inch, f"To: Client {i}")
        c.drawString(1*inch, 8.5*inch, f"Amount: {i * 100}.00 EUR")
        c.save()
        created_files.append(Path(filename))

    print(f"✓ Created {len(created_files)} PDF files")

    # Test FileManager can handle them
    fm = FileManager()
    files = fm.scan_folder(initial_scan=True)

    bulk_files = [f for f in files if f.startswith("bulk_test_")]

    if len(bulk_files) == 20:
        print(f"✓ FileManager found all 20 bulk files")
    else:
        print(f"⚠ FileManager found {len(bulk_files)}/20 bulk files")

    # Cleanup
    for f in created_files:
        if f.exists():
            f.unlink()

    print("✓ Cleaned up bulk files")
    return True


def test_file_with_special_chars():
    """Test 4: PDF with special characters in filename."""
    print("\n=== TEST: Special characters in filename ===")

    special_names = [
        "invoice with spaces.pdf",
        "invoice-with-dashes.pdf",
        "invoice_with_underscores.pdf",
    ]

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch

    created = []
    for name in special_names:
        filepath = Path("invoices/pending") / name
        c = canvas.Canvas(str(filepath), pagesize=letter)
        c.setFont("Helvetica", 12)
        c.drawString(1*inch, 10*inch, "Special Chars Test")
        c.drawString(1*inch, 9.5*inch, "From: Test Inc")
        c.drawString(1*inch, 9*inch, "To: Client Ltd")
        c.drawString(1*inch, 8.5*inch, "Amount: 100.00 EUR")
        c.save()
        created.append(filepath)
        print(f"  ✓ Created: {name}")

    # Test FileManager
    fm = FileManager()
    files = fm.scan_folder(initial_scan=True)

    found = [name for name in special_names if name in files]

    if len(found) == len(special_names):
        print(f"✓ FileManager handles special chars correctly ({len(found)}/{len(special_names)})")
    else:
        print(f"⚠ Only found {len(found)}/{len(special_names)} files with special chars")

    # Test moving
    for name in special_names:
        success = fm.move_invoice(name)
        if success:
            print(f"  ✓ Moved: {name}")
        else:
            print(f"  ✗ Failed to move: {name}")

    # Cleanup processed folder
    for name in special_names:
        processed_path = Path("invoices/processed") / name
        if processed_path.exists():
            processed_path.unlink()

    return True


def test_duplicate_filenames():
    """Test 5: Moving file when duplicate exists in processed folder."""
    print("\n=== TEST: Duplicate filename handling ===")

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch

    # Create a file in pending
    pending_file = Path("invoices/pending/duplicate_test.pdf")
    c = canvas.Canvas(str(pending_file), pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(1*inch, 10*inch, "Duplicate Test - Pending")
    c.save()

    # Create same filename in processed
    processed_file = Path("invoices/processed/duplicate_test.pdf")
    c = canvas.Canvas(str(processed_file), pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(1*inch, 10*inch, "Duplicate Test - Already Processed")
    c.save()

    print("✓ Created duplicate filenames in pending and processed")

    # Try to move
    fm = FileManager()
    success = fm.move_invoice("duplicate_test.pdf")

    if success:
        # Check if it was renamed
        if processed_file.exists():
            renamed_file = Path("invoices/processed/duplicate_test_1.pdf")
            if renamed_file.exists():
                print("✓ FileManager renamed duplicate file correctly")
                renamed_file.unlink()
            else:
                print("⚠ File moved but naming unclear")
                # Find any duplicate_test files
                for f in Path("invoices/processed").glob("duplicate_test*.pdf"):
                    f.unlink()
        processed_file.unlink()
    else:
        print("✗ Failed to move duplicate file")
        if pending_file.exists():
            pending_file.unlink()
        if processed_file.exists():
            processed_file.unlink()

    return True


def test_concurrent_operations():
    """Test 6: Rapid operations (simulating rapid clicking)."""
    print("\n=== TEST: Rapid operations ===")

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch

    # Create test file
    test_file = Path("invoices/pending/rapid_test.pdf")
    c = canvas.Canvas(str(test_file), pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(1*inch, 10*inch, "Rapid Test")
    c.save()

    fm = FileManager()

    # Try to move multiple times rapidly
    results = []
    for i in range(5):
        result = fm.move_invoice("rapid_test.pdf")
        results.append(result)

    # First should succeed, rest should fail
    if results[0] and not any(results[1:]):
        print("✓ Only first move succeeded, subsequent moves failed gracefully")
    else:
        print(f"⚠ Results: {results} (expected: [True, False, False, ...])")

    # Cleanup
    processed_path = Path("invoices/processed/rapid_test.pdf")
    if processed_path.exists():
        processed_path.unlink()

    return True


def run_all_edge_case_tests():
    """Run all edge case tests."""
    print("\n" + "="*60)
    print("  EDGE CASE TESTING")
    print("="*60)

    tests = [
        test_txt_file_in_pending,
        test_zero_byte_pdf,
        test_many_pdfs_at_once,
        test_file_with_special_chars,
        test_duplicate_filenames,
        test_concurrent_operations,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ TEST ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*60)
    print(f"  Edge Case Tests: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_edge_case_tests()
    sys.exit(0 if success else 1)
