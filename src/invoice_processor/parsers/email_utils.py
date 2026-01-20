#!/usr/bin/env python3
"""
Email Utilities

Email validation and extraction functions for invoice parsing.
Provides intelligent email detection with sender vs recipient heuristics.
"""

import re
from typing import Optional, Tuple

from .pattern_library import PatternLibrary
from ..core.constants import PARSING_FAILED


def extract_email(line: str) -> Optional[str]:
    """
    Extract email address from a line with validation.

    Args:
        line: Text line potentially containing email

    Returns:
        Email address if found and valid, None otherwise
    """
    match = re.search(PatternLibrary.EMAIL_PATTERN, line)
    if match:
        email = match.group(0)
        # Basic validation: has @ and domain
        if '@' in email and '.' in email.split('@')[1]:
            return email
    return None


def is_valid_email(email: str) -> bool:
    """
    Validate email format.

    Args:
        email: Email string to validate

    Returns:
        True if email has valid format, False otherwise
    """
    if not email or email == PARSING_FAILED:
        return False

    # Basic validation: has @ and domain with dot
    if '@' not in email:
        return False

    parts = email.split('@')
    if len(parts) != 2:
        return False

    local, domain = parts
    # Local part should be non-empty
    if not local or len(local) < 1:
        return False

    # Domain should have at least one dot
    if '.' not in domain:
        return False

    # Domain should have non-empty parts
    domain_parts = domain.split('.')
    if any(len(part) == 0 for part in domain_parts):
        return False

    return True


def extract_emails_from_text(text: str) -> tuple:
    """
    Extract sender and recipient emails from text using heuristics.

    Args:
        text: Full invoice text

    Returns:
        Tuple of (sender_email, recipient_email)
    """
    emails = PatternLibrary.extract_emails(text)

    sender_email = None
    recipient_email = None

    for email in emails:
        if PatternLibrary.is_sender_email(email):
            if not sender_email:  # Take first sender email
                sender_email = email
        else:
            if not recipient_email:  # Take first recipient email
                recipient_email = email

    return (sender_email, recipient_email)
