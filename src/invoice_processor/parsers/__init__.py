#!/usr/bin/env python3
"""
Invoice Parsing Module

Multi-strategy PDF invoice parser with confidence-based selection.

Submodules:
- text_utils: Text processing utilities
- email_utils: Email validation and extraction
- address_utils: Address detection and parsing
- extraction_utils: Complex data extraction (banking, metadata, scoring)
- pattern_library: Pattern definitions for parsing
- parsing_strategies: Main parsing strategies
- pdf_parser: PDF parsing entry point
"""

from .pdf_parser import parse_invoice
from .parsing_strategies import (
    TwoColumnStrategy,
    SingleColumnLabelStrategy,
    CompanySpecificStrategy,
    PatternFallbackStrategy
)

# Re-export commonly used functions for convenience
from .text_utils import normalize_text, extract_pattern
from .email_utils import is_valid_email, extract_email
from .extraction_utils import create_default_result, calculate_confidence

__all__ = [
    # Main parsing interface
    'parse_invoice',
    # Parsing strategies
    'TwoColumnStrategy',
    'SingleColumnLabelStrategy',
    'CompanySpecificStrategy',
    'PatternFallbackStrategy',
    # Utility functions
    'normalize_text',
    'extract_pattern',
    'is_valid_email',
    'extract_email',
    'create_default_result',
    'calculate_confidence',
]
