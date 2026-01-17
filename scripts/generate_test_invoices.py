#!/usr/bin/env python3
"""Generate test invoice PDFs for testing the invoice processor."""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import os


def create_simple_eur_invoice():
    """Clean EUR invoice with clear structure."""
    filename = "test_invoices/simple_eur.pdf"
    c = canvas.Canvas(filename, pagesize=letter)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, 10*inch, "INVOICE #001")

    c.setFont("Helvetica", 11)
    c.drawString(1*inch, 9.5*inch, "From: Acme Consulting GmbH")
    c.drawString(1*inch, 9.3*inch, "Email: billing@acme-consulting.de")
    c.drawString(1*inch, 9.1*inch, "Berlin, Germany")

    c.drawString(1*inch, 8.5*inch, "To: Tech Solutions Ltd")
    c.drawString(1*inch, 8.3*inch, "Email: accounts@techsolutions.com")
    c.drawString(1*inch, 8.1*inch, "London, UK")

    c.drawString(1*inch, 7.5*inch, "Services Rendered")
    c.drawString(1*inch, 7.2*inch, "Consulting services - January 2025")

    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, 6.5*inch, "Total Amount: 1,250.00 EUR")

    c.save()
    print(f"✓ Created {filename}")


def create_simple_usd_invoice():
    """Clean USD invoice."""
    filename = "test_invoices/simple_usd.pdf"
    c = canvas.Canvas(filename, pagesize=letter)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, 10*inch, "INVOICE #002")

    c.setFont("Helvetica", 11)
    c.drawString(1*inch, 9.5*inch, "Invoice from: Global Services Inc")
    c.drawString(1*inch, 9.3*inch, "Contact: info@globalservices.com")
    c.drawString(1*inch, 9.1*inch, "New York, USA")

    c.drawString(1*inch, 8.5*inch, "Bill to: European Imports Co")
    c.drawString(1*inch, 8.3*inch, "Email: payments@euimports.fr")
    c.drawString(1*inch, 8.1*inch, "Paris, France")

    c.drawString(1*inch, 7.5*inch, "Product delivery and handling")

    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, 6.5*inch, "Amount Due: $3,456.78 USD")

    c.save()
    print(f"✓ Created {filename}")


def create_messy_german_invoice():
    """German invoice with different formatting."""
    filename = "test_invoices/messy_german.pdf"
    c = canvas.Canvas(filename, pagesize=letter)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, 10*inch, "Rechnung Nr. 2025-003")

    c.setFont("Helvetica", 10)
    c.drawString(1*inch, 9.5*inch, "Absender:")
    c.drawString(1.5*inch, 9.3*inch, "Deutsche Dienstleistungen AG")
    c.drawString(1.5*inch, 9.1*inch, "Hauptstraße 42, München")
    c.drawString(1.5*inch, 8.9*inch, "kontakt@deutsche-dienst.de")

    c.drawString(1*inch, 8.3*inch, "Rechnungsempfänger:")
    c.drawString(1.5*inch, 8.1*inch, "International Trading BV")
    c.drawString(1.5*inch, 7.9*inch, "Amsterdam, Netherlands")
    c.drawString(1.5*inch, 7.7*inch, "finance@inttrading.nl")

    c.drawString(1*inch, 7.0*inch, "Leistungsbeschreibung:")
    c.drawString(1.5*inch, 6.8*inch, "Beratungsleistungen Q4 2024")
    c.drawString(1.5*inch, 6.6*inch, "Projektmanagement und Koordination")

    c.setFont("Helvetica-Bold", 13)
    c.drawString(1*inch, 6.0*inch, "Gesamtbetrag: 8.750,50 EUR")
    c.setFont("Helvetica", 9)
    c.drawString(1*inch, 5.8*inch, "Inklusive 19% MwSt.")

    c.save()
    print(f"✓ Created {filename}")


def create_missing_data_invoice():
    """Invoice with missing sender information."""
    filename = "test_invoices/missing_data.pdf"
    c = canvas.Canvas(filename, pagesize=letter)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, 10*inch, "INVOICE")

    c.setFont("Helvetica", 11)
    # Missing sender - only has recipient
    c.drawString(1*inch, 9.5*inch, "To: Mystery Client Ltd")
    c.drawString(1*inch, 9.3*inch, "London, UK")

    c.drawString(1*inch, 8.5*inch, "Services provided as discussed")

    # Amount without clear currency
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, 7.5*inch, "Total: 500.00")

    c.save()
    print(f"✓ Created {filename}")


def create_corrupted_pdf():
    """Create an empty/corrupted PDF file."""
    filename = "test_invoices/corrupted.pdf"
    # Write invalid PDF content
    with open(filename, 'w') as f:
        f.write("This is not a valid PDF file")
    print(f"✓ Created {filename} (intentionally corrupted)")


if __name__ == "__main__":
    os.makedirs("test_invoices", exist_ok=True)

    print("Generating test invoice PDFs...")
    create_simple_eur_invoice()
    create_simple_usd_invoice()
    create_messy_german_invoice()
    create_missing_data_invoice()
    create_corrupted_pdf()

    print("\n✓ All test invoices created successfully!")
    print("Files are in: test_invoices/")
