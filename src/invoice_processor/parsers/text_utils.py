#!/usr/bin/env python3
"""
Text Processing Utilities

Basic text normalization and pattern extraction functions.
These utilities provide foundational text processing capabilities
used throughout the invoice parsing pipeline.
"""

import re
from typing import List, Optional


def normalize_text(text: str) -> List[str]:
    """
    Normalize text by cleaning whitespace and splitting into lines.

    Args:
        text: Raw text from PDF

    Returns:
        List of normalized text lines
    """
    # Remove null characters that sometimes appear in PDFs
    text = text.replace('\x00', ' ')

    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)

    # Split into lines
    lines = text.split('\n')

    # Strip whitespace from each line
    lines = [line.strip() for line in lines]

    return lines


def extract_pattern(text: str, pattern: str) -> Optional[str]:
    """
    Extract first match of pattern from text.

    Args:
        text: Text to search
        pattern: Regex pattern (should have one capture group)

    Returns:
        Captured string or None if not found
    """
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None
