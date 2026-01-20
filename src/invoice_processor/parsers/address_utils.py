#!/usr/bin/env python3
"""
Address Utilities

Address detection and parsing functions for invoice text.
Provides heuristics to identify address blocks and section boundaries.
"""

import re
from typing import List

from .pattern_library import PatternLibrary


def is_address_line(line: str) -> bool:
    """
    Determine if a line contains address information.

    Args:
        line: Text line to check

    Returns:
        True if line appears to be part of an address
    """
    if not line or len(line) < 3:
        return False

    # Check for postal code
    for pattern in PatternLibrary.POSTAL_CODE_PATTERNS.values():
        if re.search(pattern, line):
            return True

    # Check for street patterns
    for pattern in PatternLibrary.STREET_PATTERNS:
        if re.search(pattern, line):
            return True

    # Check for country names
    if PatternLibrary.contains_country(line):
        return True

    # Check for city names (capitalized words with optional state/region)
    # Example: "San Francisco, California"
    if re.search(r'[A-Z][a-z]+(?:,?\s+[A-Z][a-z]+)*', line):
        # Avoid false positives on labels
        if not re.search(r':\s*$', line) and not line.endswith(':'):
            return True

    return False


def is_section_boundary(line: str) -> bool:
    """
    Check if line marks a section boundary (indicates end of address block).

    Args:
        line: Text line to check

    Returns:
        True if line marks a boundary
    """
    # Check for common section headers
    boundary_keywords = [
        'invoice', 'description', 'item', 'quantity', 'price',
        'amount', 'total', 'subtotal', 'tax', 'vat', 'mwst',
        'payment', 'due', 'date', 'number', 'reference'
    ]

    line_lower = line.lower()

    # Check if line is a header (ends with colon or is all caps)
    if line.endswith(':') or (line.isupper() and len(line) > 3):
        return True

    # Check for boundary keywords
    for keyword in boundary_keywords:
        if keyword in line_lower:
            return True

    # Check for horizontal rules
    if re.search(r'^[-=_]{3,}$', line):
        return True

    return False


def find_postal_codes(text: str) -> List[str]:
    """
    Extract all postal codes from text.

    Args:
        text: Text to search

    Returns:
        List of postal codes found
    """
    postal_codes = PatternLibrary.extract_postal_codes(text)
    return [code for code, country in postal_codes]
