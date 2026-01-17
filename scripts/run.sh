#!/bin/bash
# Quick-start script for Invoice Processor

echo "=========================================="
echo "  Invoice Processor"
echo "=========================================="
echo ""

# Navigate to project root
cd "$(dirname "$0")/.."

# Check if we're in the right directory
if [ ! -f "setup.py" ]; then
    echo "Error: setup.py not found. Please run this script from the project directory."
    exit 1
fi

# Check for dependencies
echo "Checking dependencies..."
if ! python3 -c "import pdfplumber; import reportlab; import tkinter; import yaml" 2>/dev/null; then
    echo "Missing dependencies. Installing..."
    pip3 install -e .
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies"
        exit 1
    fi
fi

echo "✓ Dependencies installed"
echo ""

# Check for test invoices
if [ ! -d "invoices/pending" ]; then
    echo "Creating folder structure..."
    mkdir -p invoices/pending invoices/processed
fi

# Check if there are any PDFs
pdf_count=$(find invoices/pending -name "*.pdf" 2>/dev/null | wc -l | tr -d ' ')
if [ "$pdf_count" -eq 0 ]; then
    echo "No invoices found in invoices/pending/"
    echo "Copying test invoices..."
    if [ -d "test_invoices" ]; then
        cp test_invoices/*.pdf invoices/pending/
        echo "✓ Test invoices copied"
    else
        echo "Generating test invoices..."
        python3 scripts/generate_test_invoices.py
        cp test_invoices/*.pdf invoices/pending/
    fi
fi

echo ""
echo "✓ Ready to launch!"
echo "=========================================="
echo ""

# Launch the application
PYTHONPATH=src python3 -m invoice_processor.gui.main
