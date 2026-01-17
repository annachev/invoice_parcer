#!/usr/bin/env python3
"""
PDF Invoice Parser - Orchestrator
Coordinates multiple parsing strategies to handle various invoice formats.
"""

import pdfplumber
from typing import Dict
from pathlib import Path

from ..core.logging_config import get_logger
from .parser_utils import normalize_text, calculate_confidence, create_default_result
from .parsing_strategies import (
    TwoColumnStrategy,
    SingleColumnLabelStrategy,
    CompanySpecificStrategy,
    PatternFallbackStrategy
)
from ..core.exceptions import PDFParsingError, PDFCorruptedError

logger = get_logger(__name__)


def parse_invoice(pdf_path: str) -> Dict[str, str]:
    """
    Parse invoice using multiple strategies with confidence-based selection.

    This orchestrator tries multiple parsing strategies in priority order:
    1. Two-Column Layout (Anthropic-style)
    2. Single-Column Labels (simple invoices)
    3. Company-Specific (Deutsche Bahn-style)
    4. Pattern Fallback (generic extraction)

    Args:
        pdf_path: Path to PDF invoice file

    Returns:
        Dictionary with extracted fields (or "PARSING FAILED" for missing data)
    """
    result = create_default_result()
    pdf_file = Path(pdf_path)

    logger.debug(f"Starting parse for: {pdf_file.name}")

    try:
        # Check file exists
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Extract text from PDF
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) == 0:
                    logger.warning(f"PDF has no pages: {pdf_file.name}")
                    raise PDFParsingError(f"PDF has no pages: {pdf_file.name}")

                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

                if not text.strip():
                    logger.warning(f"No text extracted from PDF: {pdf_file.name}")
                    raise PDFParsingError(f"No text could be extracted: {pdf_file.name}")

        except pdfplumber.pdfminer.pdfparser.PDFSyntaxError as e:
            logger.error(f"Corrupted PDF file: {pdf_file.name} - {e}")
            raise PDFCorruptedError(f"PDF file is corrupted: {pdf_file.name}") from e

        # Normalize text into lines
        lines = normalize_text(text)
        logger.debug(f"Extracted {len(lines)} lines from {pdf_file.name}")

        # Initialize strategies in priority order
        strategies = [
            TwoColumnStrategy(),           # Priority 1: Anthropic-style two-column
            SingleColumnLabelStrategy(),   # Priority 2: Simple label-based
            CompanySpecificStrategy(),     # Priority 3: Deutsche Bahn-style
            PatternFallbackStrategy()      # Priority 4: Generic patterns
        ]

        best_result = None
        best_confidence = 0.0
        best_strategy = None

        # Try each strategy
        for strategy in strategies:
            if strategy.can_handle(text, lines):
                logger.debug(f"Trying strategy: {strategy.__class__.__name__}")

                # Parse using this strategy
                strategy_result = strategy.parse(text, lines)

                # Calculate confidence score
                confidence = calculate_confidence(strategy_result)
                logger.debug(f"Strategy {strategy.__class__.__name__} confidence: {confidence:.2f}")

                # Track best result
                if confidence > best_confidence:
                    best_result = strategy_result
                    best_confidence = confidence
                    best_strategy = strategy.__class__.__name__

                # Early exit on high confidence (>= 0.9)
                if confidence >= 0.9:
                    logger.debug(f"High confidence achieved, using {best_strategy}")
                    break

        # Return best result or default
        if best_result:
            result = best_result
            logger.info(f"Successfully parsed {pdf_file.name} using {best_strategy} (confidence: {best_confidence:.2f})")
        else:
            logger.warning(f"All strategies failed for {pdf_file.name}")

    except (FileNotFoundError, PDFParsingError, PDFCorruptedError) as e:
        # Expected errors - log and return default result
        logger.error(f"Failed to parse {pdf_file.name}: {e}")
    except Exception as e:
        # Unexpected errors - log with full traceback
        logger.exception(f"Unexpected error parsing {pdf_file.name}: {e}")

    return result


if __name__ == "__main__":
    import sys
    from logging_config import setup_logging

    # Enable debug logging for CLI usage
    setup_logging(log_level="DEBUG", log_to_console=True, log_file=None)

    if len(sys.argv) > 1:
        result = parse_invoice(sys.argv[1])
        print("Results:")
        print("\n=== BASIC INFO ===")
        print(f"  Sender: {result['sender']}")
        print(f"  Recipient: {result['recipient']}")
        print(f"  Amount: {result['amount']}")
        print(f"  Currency: {result['currency']}")
        print("\n=== ADDRESSES ===")
        print(f"  Sender Address: {result['sender_address']}")
        print(f"  Recipient Address: {result['recipient_address']}")
        print("\n=== EMAILS ===")
        print(f"  Sender Email: {result['sender_email']}")
        print(f"  Recipient Email: {result['recipient_email']}")
        print("\n=== BANKING ===")
        print(f"  Bank Name: {result['bank_name']}")
        print(f"  IBAN: {result['iban']}")
        print(f"  BIC: {result['bic']}")
        print(f"  Payment Address: {result['payment_address']}")
