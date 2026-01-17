#!/usr/bin/env python3
"""
PDF Invoice Parser - Orchestrator
Coordinates multiple parsing strategies to handle various invoice formats.
"""

import pdfplumber
from typing import Dict, Optional
from pathlib import Path

from ..core.logging_config import get_logger
from ..core.config import get_config
from .parser_utils import normalize_text, calculate_confidence, create_default_result
from .parsing_strategies import (
    TwoColumnStrategy,
    SingleColumnLabelStrategy,
    CompanySpecificStrategy,
    PatternFallbackStrategy
)
from ..core.exceptions import PDFParsingError, PDFCorruptedError
from ..core.constants import PARSING_FAILED

logger = get_logger(__name__)

# Global ML components (initialized lazily)
_ml_extractor: Optional['SpacyNERExtractor'] = None
_layout_classifier: Optional['LayoutClassifier'] = None


def get_ml_extractor():
    """Get or initialize the ML extractor."""
    global _ml_extractor
    if _ml_extractor is None:
        try:
            from ..ml import SpacyNERExtractor
            config = get_config()
            _ml_extractor = SpacyNERExtractor(model_name=config.ml.ner.model)
            logger.info("ML extractor initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize ML extractor: {e}")
            _ml_extractor = None
    return _ml_extractor


def get_layout_classifier():
    """Get or initialize the layout classifier."""
    global _layout_classifier
    if _layout_classifier is None:
        try:
            from ..ml import LayoutClassifier
            config = get_config()
            model_path = config.ml.layout.model_path
            _layout_classifier = LayoutClassifier(model_path=model_path)
            logger.info("Layout classifier initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize layout classifier: {e}")
            _layout_classifier = None
    return _layout_classifier


def merge_results(regex_result: Dict[str, str], ml_result: Dict[str, str],
                   regex_confidence: float, ml_confidence: float) -> Dict[str, str]:
    """
    Merge regex and ML results using ensemble strategy.

    Strategy:
    - Prefer regex if field is not PARSING_FAILED (regex is more accurate for known formats)
    - Use ML as fallback when regex fails
    - Only use ML result if ML confidence is above threshold

    Args:
        regex_result: Result from regex strategies
        ml_result: Result from ML extraction
        regex_confidence: Confidence score for regex result
        ml_confidence: Confidence score for ML result

    Returns:
        Merged result dictionary
    """
    config = get_config()
    merged = regex_result.copy()

    # Only consider ML results if confidence is sufficient
    if ml_confidence < config.ml.ensemble.ml_min_confidence:
        logger.debug(f"ML confidence too low ({ml_confidence:.2f}), using regex only")
        return merged

    # For each field, prefer regex but use ML as fallback
    for field in merged.keys():
        regex_value = regex_result.get(field, PARSING_FAILED)
        ml_value = ml_result.get(field, PARSING_FAILED)

        # If regex failed but ML succeeded, use ML value
        if regex_value == PARSING_FAILED and ml_value != PARSING_FAILED:
            merged[field] = ml_value
            logger.debug(f"Using ML value for {field}: {ml_value}")

        # If prefer_regex is False and both have values, compare confidences
        elif (not config.ml.ensemble.prefer_regex and
              regex_value != PARSING_FAILED and
              ml_value != PARSING_FAILED and
              ml_confidence > regex_confidence):
            merged[field] = ml_value
            logger.debug(f"ML confidence higher, using ML value for {field}")

    return merged


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

        # Initialize strategies
        strategy_map = {
            'TwoColumnStrategy': TwoColumnStrategy(),
            'SingleColumnLabelStrategy': SingleColumnLabelStrategy(),
            'CompanySpecificStrategy': CompanySpecificStrategy(),
            'PatternFallbackStrategy': PatternFallbackStrategy()
        }

        # Determine strategy order (either from layout classifier or default)
        config = get_config()
        if config.ml.enabled and config.ml.layout.enabled and config.ml.layout.optimize_strategy_order:
            try:
                layout_classifier = get_layout_classifier()
                if layout_classifier:
                    layout_type = layout_classifier.predict(pdf_path)
                    strategy_names = layout_classifier.get_strategy_order(layout_type)
                    logger.info(f"Layout predicted: {layout_type}, using optimized strategy order")
                else:
                    # Fallback to default order
                    strategy_names = ['TwoColumnStrategy', 'SingleColumnLabelStrategy',
                                     'CompanySpecificStrategy', 'PatternFallbackStrategy']
            except Exception as e:
                logger.warning(f"Layout prediction failed: {e}, using default order")
                strategy_names = ['TwoColumnStrategy', 'SingleColumnLabelStrategy',
                                 'CompanySpecificStrategy', 'PatternFallbackStrategy']
        else:
            # Default priority order
            strategy_names = ['TwoColumnStrategy', 'SingleColumnLabelStrategy',
                             'CompanySpecificStrategy', 'PatternFallbackStrategy']

        # Convert strategy names to instances in order
        strategies = [strategy_map[name] for name in strategy_names]

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

        # Use ML ensemble mode if enabled
        config = get_config()
        if config.ml.enabled and config.ml.ensemble.enabled and best_result:
            try:
                ml_extractor = get_ml_extractor()
                if ml_extractor:
                    logger.debug("Running ML extraction for ensemble mode")
                    ml_result = ml_extractor.extract(text)
                    ml_confidence = ml_extractor.get_confidence(ml_result)

                    logger.debug(f"ML extraction confidence: {ml_confidence:.2f}")

                    # Merge regex and ML results
                    merged_result = merge_results(
                        regex_result=best_result,
                        ml_result=ml_result,
                        regex_confidence=best_confidence,
                        ml_confidence=ml_confidence
                    )

                    # Recalculate confidence for merged result
                    merged_confidence = calculate_confidence(merged_result)
                    logger.info(
                        f"Ensemble mode: regex={best_confidence:.2f}, "
                        f"ml={ml_confidence:.2f}, merged={merged_confidence:.2f}"
                    )

                    result = merged_result
                    logger.info(f"Successfully parsed {pdf_file.name} using ensemble mode (confidence: {merged_confidence:.2f})")
                else:
                    # ML not available, use regex only
                    result = best_result
                    logger.info(f"Successfully parsed {pdf_file.name} using {best_strategy} (confidence: {best_confidence:.2f})")
            except Exception as e:
                # ML failed, fall back to regex
                logger.warning(f"ML extraction failed, using regex only: {e}")
                result = best_result
                logger.info(f"Successfully parsed {pdf_file.name} using {best_strategy} (confidence: {best_confidence:.2f})")
        elif best_result:
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
