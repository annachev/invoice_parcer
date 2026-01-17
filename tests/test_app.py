#!/usr/bin/env python3
"""Test script to verify the application functionality."""

import os
import time
import shutil
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


def create_new_test_invoice():
    """Create a new test invoice to test auto-scanning."""
    filename = "invoices/pending/new_test.pdf"
    c = canvas.Canvas(filename, pagesize=letter)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, 10*inch, "NEW INVOICE #999")

    c.setFont("Helvetica", 11)
    c.drawString(1*inch, 9.5*inch, "From: New Test Company Inc")
    c.drawString(1*inch, 9.3*inch, "Email: test@newcompany.com")

    c.drawString(1*inch, 8.5*inch, "To: Test Client GmbH")
    c.drawString(1*inch, 8.3*inch, "Email: client@test.de")

    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, 7.5*inch, "Total: 999.99 GBP")

    c.save()
    print(f"✓ Created {filename}")


def check_folders():
    """Check the state of pending and processed folders."""
    pending = Path("invoices/pending")
    processed = Path("invoices/processed")

    print("\n=== FOLDER STATUS ===")
    print(f"\nPending folder ({pending}):")
    if pending.exists():
        files = list(pending.glob("*.pdf"))
        if files:
            for f in sorted(files):
                print(f"  - {f.name}")
        else:
            print("  (empty)")
    else:
        print("  (does not exist)")

    print(f"\nProcessed folder ({processed}):")
    if processed.exists():
        files = list(processed.glob("*.pdf"))
        if files:
            for f in sorted(files):
                print(f"  - {f.name}")
        else:
            print("  (empty)")
    else:
        print("  (does not exist)")


def reset_test_environment():
    """Reset the test environment by moving all files back to pending."""
    pending = Path("invoices/pending")
    processed = Path("invoices/processed")

    if processed.exists():
        for pdf in processed.glob("*.pdf"):
            dest = pending / pdf.name
            # Handle duplicates
            if dest.exists():
                base = dest.stem
                ext = dest.suffix
                counter = 1
                while dest.exists():
                    dest = pending / f"{base}_{counter}{ext}"
                    counter += 1
            shutil.move(str(pdf), str(dest))
            print(f"Moved {pdf.name} back to pending")

    # Copy original test files if they're missing
    test_dir = Path("test_invoices")
    if test_dir.exists():
        for pdf in test_dir.glob("*.pdf"):
            dest = pending / pdf.name
            if not dest.exists():
                shutil.copy(str(pdf), str(dest))
                print(f"Restored {pdf.name} to pending")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "check":
            check_folders()

        elif command == "reset":
            print("Resetting test environment...")
            reset_test_environment()
            print("✓ Reset complete")
            check_folders()

        elif command == "new":
            print("Creating new test invoice...")
            create_new_test_invoice()
            print("✓ New invoice created - should appear in app within 30s or after Refresh")

        else:
            print("Unknown command")
            print("Usage: python3 test_app.py [check|reset|new]")
            print("  check - Show current state of folders")
            print("  reset - Move all processed files back to pending")
            print("  new   - Create a new test invoice in pending folder")
    else:
        print("Usage: python3 test_app.py [check|reset|new]")
        print("  check - Show current state of folders")
        print("  reset - Move all processed files back to pending")
        print("  new   - Create a new test invoice in pending folder")
