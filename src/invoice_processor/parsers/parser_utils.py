#!/usr/bin/env python3
"""
Parser Utility Functions
Shared helper functions used across parsing strategies.
"""

import re
from typing import List, Dict, Optional
from .pattern_library import PatternLibrary
from ..core.constants import PARSING_FAILED


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


def extract_amount(text: str, patterns: List[str] = None) -> Optional[str]:
    """
    Extract monetary amount from text using multiple patterns.

    Args:
        text: Text to search
        patterns: Optional list of custom patterns (uses default if None)

    Returns:
        Amount string if found, None otherwise
    """
    if patterns is None:
        patterns = PatternLibrary.AMOUNT_PATTERNS

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = match.group(1)
            # Clean currency symbols and extra spaces
            amount = amount.replace('€', '').replace('$', '').replace('£', '').strip()
            return amount

    return None


def calculate_confidence(result: Dict[str, str]) -> float:
    """
    Calculate confidence score for parsing result based on fields extracted.

    Scoring:
    - Core fields (sender, recipient, amount, currency): 2.0 points each
    - Address fields (sender_address, recipient_address): 1.0 point each
    - Email fields (sender_email, recipient_email): 1.0 point each
    - Banking fields (iban/bic, bank_name, payment_address): 0.5 points each

    Args:
        result: Parsing result dictionary

    Returns:
        Confidence score from 0.0 to 1.0
    """
    score = 0.0
    max_score = 12.0

    # Core fields (highest weight)
    if result.get('sender') != PARSING_FAILED and result.get('sender'):
        score += 2.0
    if result.get('recipient') != PARSING_FAILED and result.get('recipient'):
        score += 2.0
    if result.get('amount') != PARSING_FAILED and result.get('amount'):
        score += 2.0
    if result.get('currency') != PARSING_FAILED and result.get('currency'):
        score += 1.0

    # Address fields (medium weight)
    if result.get('sender_address') != PARSING_FAILED and result.get('sender_address'):
        score += 1.0
    if result.get('recipient_address') != PARSING_FAILED and result.get('recipient_address'):
        score += 1.0

    # Email fields (medium weight)
    if result.get('sender_email') != PARSING_FAILED and result.get('sender_email'):
        score += 1.0
    if result.get('recipient_email') != PARSING_FAILED and result.get('recipient_email'):
        score += 1.0

    # Banking fields (lower weight - not all invoices have banking info)
    banking_fields = ['iban', 'bic', 'bank_name', 'payment_address']
    banking_found = sum(1 for field in banking_fields
                       if result.get(field) != PARSING_FAILED and result.get(field))
    if banking_found > 0:
        score += 0.5  # 0.5 points if any banking info found

    return min(score / max_score, 1.0)


def create_default_result() -> Dict[str, str]:
    """
    Create a default result dictionary with all fields set to PARSING FAILED.

    Returns:
        Dictionary with all invoice fields initialized
    """
    return {
        "sender": PARSING_FAILED,
        "recipient": PARSING_FAILED,
        "amount": PARSING_FAILED,
        "currency": PARSING_FAILED,
        "sender_address": PARSING_FAILED,
        "recipient_address": PARSING_FAILED,
        "sender_email": PARSING_FAILED,
        "recipient_email": PARSING_FAILED,
        "bank_name": PARSING_FAILED,
        "iban": PARSING_FAILED,
        "bic": PARSING_FAILED,
        "payment_address": PARSING_FAILED,
    }


def extract_name_from_line(line: str) -> Optional[str]:
    """
    Extract name/company name from a line (first non-label part).

    Args:
        line: Text line potentially containing a name

    Returns:
        Extracted name or None
    """
    # Remove common label prefixes
    line = re.sub(r'^(From|To|Bill to|Invoice from|Sender|Recipient|Absender|Rechnungsempfänger):\s*',
                  '', line, flags=re.IGNORECASE)

    line = line.strip()

    # Skip if empty or too short
    if not line or len(line) < 2:
        return None

    # Skip if it's just an email
    if '@' in line and extract_email(line) == line:
        return None

    return line


def extract_banking_info(text: str, lines: List[str]) -> Dict[str, str]:
    """
    Extract banking information from invoice text.

    This function is shared across all parsing strategies to avoid code duplication.

    Args:
        text: Full invoice text
        lines: Text split into lines

    Returns:
        Dictionary with banking fields: iban, bic, bank_name, payment_address
    """
    banking = {
        "iban": PARSING_FAILED,
        "bic": PARSING_FAILED,
        "bank_name": PARSING_FAILED,
        "payment_address": PARSING_FAILED
    }

    # IBAN
    iban_match = re.search(PatternLibrary.IBAN_PATTERN, text, re.IGNORECASE)
    if iban_match:
        banking["iban"] = iban_match.group(1).replace(' ', '')

    # BIC
    bic_match = re.search(PatternLibrary.BIC_PATTERN, text, re.IGNORECASE)
    if bic_match:
        banking["bic"] = bic_match.group(1)

    # Bank name
    for pattern in PatternLibrary.BANK_NAME_PATTERNS:
        bank_match = re.search(pattern, text)
        if bank_match:
            banking["bank_name"] = bank_match.group(1).strip()
            break

    # Payment address
    payment_idx = -1
    for i, line in enumerate(lines):
        if re.search(PatternLibrary.PAYMENT_ADDRESS_PATTERN, line, re.IGNORECASE):
            payment_idx = i
            break

    if payment_idx >= 0:
        payment_lines = []
        for i in range(payment_idx + 1, min(payment_idx + 5, len(lines))):
            line = lines[i].strip()
            if not line or line.startswith('---') or 'Description' in line:
                break
            payment_lines.append(line)
        if payment_lines:
            banking["payment_address"] = ', '.join(payment_lines)

    return banking


def extract_section(lines: List[str], start_idx: int, end_idx: int = None) -> Dict[str, Optional[str]]:
    """
    Extract name, address, and email from a labeled section.

    Args:
        lines: All text lines
        start_idx: Starting line index (label line)
        end_idx: Optional ending line index (next label or end)

    Returns:
        Dictionary with 'name', 'address', 'email'
    """
    if end_idx is None:
        end_idx = len(lines)

    section_lines = lines[start_idx:end_idx]

    if not section_lines:
        return {'name': None, 'address': None, 'email': None}

    # First line contains the label and possibly the name
    first_line = section_lines[0]
    name = extract_name_from_line(first_line)

    # Collect address lines and email from subsequent lines
    address_parts = []
    email = None

    for line in section_lines[1:]:
        line = line.strip()

        if not line:
            continue

        # Check if it's a section boundary
        if is_section_boundary(line):
            break

        # Extract email if present
        line_email = extract_email(line)
        if line_email and not email:
            email = line_email
            # Don't continue - the line might have address info too
            # Remove email from line to process remaining text
            line = line.replace(line_email, '').strip()
            if not line:
                continue

        # If we don't have a name yet and this line isn't obviously an address, it's probably the name
        if not name:
            # First non-empty line after label should be the name
            if not is_address_line(line) and len(line) > 2:
                name = line
                continue

        # Check if it's an address line
        if is_address_line(line):
            address_parts.append(line)

    address = ', '.join(address_parts) if address_parts else None

    return {
        'name': name,
        'address': address,
        'email': email
    }


if __name__ == "__main__":
    # Test text normalization
    text = "Line 1\n  Line 2   with    spaces\nLine 3"
    lines = normalize_text(text)
    print("Normalized lines:", lines)

    # Test email extraction
    test_line = "Contact: support@company.com for help"
    email = extract_email(test_line)
    print(f"\nEmail from line: {email}")

    # Test address detection
    addr_lines = [
        "123 Main Street",
        "San Francisco, California 94104",
        "Invoice Date:",
        "Product Description"
    ]
    for line in addr_lines:
        print(f"{line}: {'Address' if is_address_line(line) else 'Not Address'}")

    # Test confidence scoring
    result1 = {
        "sender": "Acme Corp",
        "recipient": "John Doe",
        "amount": "100.00",
        "currency": "USD",
        "sender_address": "123 Main St",
        "recipient_address": "456 Oak Ave",
        "sender_email": "billing@acme.com",
        "recipient_email": "john@example.com",
        "iban": "PARSING FAILED",
        "bic": "PARSING FAILED",
        "bank_name": "PARSING FAILED",
        "payment_address": "PARSING FAILED",
    }
    print(f"\nConfidence score (complete): {calculate_confidence(result1):.2f}")

    result2 = {
        "sender": "Acme Corp",
        "recipient": "PARSING FAILED",
        "amount": "100.00",
        "currency": "USD",
        "sender_address": "PARSING FAILED",
        "recipient_address": "PARSING FAILED",
        "sender_email": "PARSING FAILED",
        "recipient_email": "PARSING FAILED",
        "iban": "PARSING FAILED",
        "bic": "PARSING FAILED",
        "bank_name": "PARSING FAILED",
        "payment_address": "PARSING FAILED",
    }
    print(f"Confidence score (partial): {calculate_confidence(result2):.2f}")
