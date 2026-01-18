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
    Calculate confidence score for parsing result with validation-based scoring.

    Scoring (weighted by importance and validation):
    - Critical fields (50%): sender, recipient, amount (with validation)
    - Banking fields (30%): IBAN, BIC, routing numbers (with checksum validation)
    - Supporting fields (20%): currency, emails, addresses, invoice metadata, tax info

    Args:
        result: Parsing result dictionary

    Returns:
        Confidence score from 0.0 to 1.0
    """
    score = 0.0

    # Critical fields (50% = 0.5)
    # Sender (20% if valid email or non-empty)
    sender = result.get('sender', PARSING_FAILED)
    if sender != PARSING_FAILED and sender:
        if '@' in sender and is_valid_email(sender):
            score += 0.20  # Valid email
        elif len(sender) > 3:
            score += 0.15  # Non-empty company name

    # Recipient (20% if valid email or non-empty)
    recipient = result.get('recipient', PARSING_FAILED)
    if recipient != PARSING_FAILED and recipient:
        if '@' in recipient and is_valid_email(recipient):
            score += 0.20  # Valid email
        elif len(recipient) > 3:
            score += 0.15  # Non-empty company name

    # Amount (10% if parseable as number)
    amount = result.get('amount', PARSING_FAILED)
    if amount != PARSING_FAILED and amount:
        try:
            # Try to parse as float (handles both "1.234,56" and "1,234.56")
            cleaned = amount.replace('.', '').replace(',', '.')
            if float(cleaned) > 0:
                score += 0.10
        except (ValueError, AttributeError):
            pass  # Invalid amount, no points

    # Banking fields (30% = 0.3 total)
    # Distributed across European (IBAN/BIC), US (Routing/Account), and UK (Sort Code/Account) systems
    banking_score = 0.0

    # Option 1: IBAN (European/International)
    iban = result.get('iban', PARSING_FAILED)
    if iban != PARSING_FAILED and iban:
        # IBAN alone is strong (validated checksum)
        banking_score += 0.15
        # Bonus for BIC/SWIFT
        bic = result.get('bic', PARSING_FAILED)
        if bic != PARSING_FAILED and bic:
            banking_score += 0.10
        # Bonus for payment method detection
        if result.get('payment_method') in ['SEPA', 'SEPA_INTERNATIONAL']:
            banking_score += 0.05

    # Option 2: US Banking (ABA Routing + Account)
    elif result.get('routing_number') != PARSING_FAILED and result['routing_number']:
        # Validated ABA routing number (checksum passed)
        banking_score += 0.15
        # Account number present
        if result.get('account_number') != PARSING_FAILED and result['account_number']:
            banking_score += 0.10
        # Payment method detection
        if result.get('payment_method') == 'ACH':
            banking_score += 0.05

    # Option 3: UK Banking (Sort Code + Account)
    elif result.get('sort_code') != PARSING_FAILED and result['sort_code']:
        # Validated sort code (format check)
        banking_score += 0.15
        # Account number present (8 digits)
        if result.get('account_number') != PARSING_FAILED and result['account_number']:
            banking_score += 0.10
        # Payment method detection
        if result.get('payment_method') == 'BACS':
            banking_score += 0.05

    # Fallback: Generic account number only (lower confidence)
    elif result.get('account_number') != PARSING_FAILED and result['account_number']:
        banking_score += 0.10

    # Bank name adds small bonus (5%) regardless of banking system
    if result.get('bank_name') != PARSING_FAILED and result['bank_name']:
        banking_score += 0.05

    # Cap banking score at 0.30 (30% max)
    banking_score = min(banking_score, 0.30)
    score += banking_score

    # Supporting fields (20% = 0.2)
    supporting_score = 0.0

    # Currency (3%)
    if result.get('currency') != PARSING_FAILED and result.get('currency'):
        supporting_score += 0.03

    # Emails (3% each, max 6%)
    if result.get('sender_email') != PARSING_FAILED and result.get('sender_email'):
        if is_valid_email(result.get('sender_email')):
            supporting_score += 0.03
    if result.get('recipient_email') != PARSING_FAILED and result.get('recipient_email'):
        if is_valid_email(result.get('recipient_email')):
            supporting_score += 0.03

    # Addresses (3% total if at least one exists)
    has_address = (
        (result.get('sender_address') != PARSING_FAILED and result.get('sender_address')) or
        (result.get('recipient_address') != PARSING_FAILED and result.get('recipient_address'))
    )
    if has_address:
        supporting_score += 0.03

    # NEW v2.2.0: Invoice metadata fields (5% total)
    # Invoice number (2%)
    if result.get('invoice_number') != PARSING_FAILED and result.get('invoice_number'):
        supporting_score += 0.02
    # Invoice date (1.5%)
    if result.get('invoice_date') != PARSING_FAILED and result.get('invoice_date'):
        supporting_score += 0.015
    # Due date (1%)
    if result.get('due_date') != PARSING_FAILED and result.get('due_date'):
        supporting_score += 0.01
    # Payment terms (0.5%)
    if result.get('payment_terms') != PARSING_FAILED and result.get('payment_terms'):
        supporting_score += 0.005

    # NEW v2.2.0: Tax/VAT fields (3% total)
    # Tax amount (1.5%)
    if result.get('tax_amount') != PARSING_FAILED and result.get('tax_amount'):
        supporting_score += 0.015
    # Tax rate (0.5%)
    if result.get('tax_rate') != PARSING_FAILED and result.get('tax_rate'):
        supporting_score += 0.005
    # Tax ID (1%)
    if result.get('tax_id') != PARSING_FAILED and result.get('tax_id'):
        supporting_score += 0.01

    # Cap supporting score at 0.20 (20% max)
    supporting_score = min(supporting_score, 0.20)
    score += supporting_score

    return min(score, 1.0)


def create_default_result() -> Dict[str, str]:
    """
    Create a default result dictionary with all fields set to PARSING FAILED.

    Returns:
        Dictionary with all invoice fields initialized
    """
    return {
        # Core invoice fields
        "sender": PARSING_FAILED,
        "recipient": PARSING_FAILED,
        "amount": PARSING_FAILED,
        "currency": PARSING_FAILED,
        "sender_address": PARSING_FAILED,
        "recipient_address": PARSING_FAILED,
        "sender_email": PARSING_FAILED,
        "recipient_email": PARSING_FAILED,

        # NEW: Invoice metadata fields (v2.2.0)
        "invoice_number": PARSING_FAILED,
        "invoice_date": PARSING_FAILED,
        "due_date": PARSING_FAILED,

        # NEW: Tax/VAT fields (v2.2.0)
        "tax_amount": PARSING_FAILED,
        "tax_rate": PARSING_FAILED,
        "tax_id": PARSING_FAILED,

        # NEW: Payment terms (v2.2.0)
        "payment_terms": PARSING_FAILED,

        # NEW: Vehicle matching fields (v2.3.0)
        "vehicle_id": "N/A",
        "original_recipient": PARSING_FAILED,
        "vehicle_match_score": "0.0",

        # European banking fields
        "bank_name": PARSING_FAILED,
        "iban": PARSING_FAILED,
        "bic": PARSING_FAILED,
        "payment_address": PARSING_FAILED,
        # US banking fields
        "routing_number": PARSING_FAILED,
        "account_number": PARSING_FAILED,
        # UK banking fields
        "sort_code": PARSING_FAILED,
        # Payment method detection
        "payment_method": PARSING_FAILED,
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


def detect_payment_method(banking_info: dict) -> str:
    """
    Automatically detect payment method from banking fields.

    Args:
        banking_info: Dictionary with banking fields

    Returns:
        Payment method string: SEPA, SEPA_INTERNATIONAL, ACH, BACS, or PARSING_FAILED
    """
    # SEPA detection
    if banking_info.get('iban') and banking_info['iban'] != PARSING_FAILED:
        country_code = banking_info['iban'][:2]
        if country_code in PatternLibrary.SEPA_COUNTRIES:
            return "SEPA"
        else:
            return "SEPA_INTERNATIONAL"

    # US payment detection
    if banking_info.get('routing_number') and banking_info['routing_number'] != PARSING_FAILED:
        # Default to ACH (most common for invoices)
        return "ACH"

    # UK payment detection
    if banking_info.get('sort_code') and banking_info['sort_code'] != PARSING_FAILED:
        # Default to BACS (most common for invoices)
        return "BACS"

    return PARSING_FAILED


def extract_account_number_smart(text: str, banking_context: dict) -> Optional[str]:
    """
    Extract account number with smart context awareness.

    Strategy:
    1. If US routing number present → use US account patterns (6-17 digits)
    2. If UK sort code present → use UK account patterns (8 digits)
    3. Otherwise → use generic account number patterns

    Args:
        text: Full invoice text
        banking_context: Already extracted banking info (routing, sort_code, etc.)

    Returns:
        Account number string or None
    """
    # US context: Look for US-specific account patterns
    if banking_context.get('routing_number'):
        for pattern in PatternLibrary.US_ACCOUNT_PATTERNS:
            account = extract_pattern(text, pattern)
            if account and account.isdigit() and 6 <= len(account) <= 17:
                return account

    # UK context: Look for UK-specific account patterns (8 digits)
    if banking_context.get('sort_code'):
        for pattern in PatternLibrary.UK_ACCOUNT_PATTERNS:
            account = extract_pattern(text, pattern)
            if account and account.isdigit() and len(account) == 8:
                return account

    # Generic: Try generic account number patterns
    for pattern in PatternLibrary.ACCOUNT_NUMBER_PATTERNS:
        account = extract_pattern(text, pattern)
        if account:
            # Clean up account number (remove spaces/hyphens)
            account = account.replace(' ', '').replace('-', '')
            if len(account) >= 6:  # Minimum reasonable account length
                return account

    return None


def extract_banking_info(text: str, lines: List[str]) -> Dict[str, str]:
    """
    Extract banking information with European, US, and UK support.

    Extraction priority:
    1. European: IBAN (labeled or unlabeled) + BIC validation
    2. US: ABA routing number + account number with checksum validation
    3. UK: Sort code + account number with format validation
    4. Generic: Account numbers with context proximity validation

    Args:
        text: Full invoice text
        lines: Text split into lines

    Returns:
        Dictionary with banking fields including payment_method auto-detection
    """
    banking = {
        "iban": PARSING_FAILED,
        "bic": PARSING_FAILED,
        "bank_name": PARSING_FAILED,
        "payment_address": PARSING_FAILED,
        "routing_number": PARSING_FAILED,
        "account_number": PARSING_FAILED,
        "sort_code": PARSING_FAILED,
        "payment_method": PARSING_FAILED,
    }

    # --- European Banking (IBAN/BIC) ---
    # Try labeled IBAN first (higher confidence)
    iban = extract_pattern(text, PatternLibrary.IBAN_PATTERN_LABELED)
    if not iban:
        # Fallback to unlabeled IBAN (user requested this feature)
        iban = extract_pattern(text, PatternLibrary.IBAN_PATTERN_UNLABELED)

    # CRITICAL: Always validate IBAN checksum (strict per user requirement)
    if iban:
        iban_clean = iban.replace(' ', '')
        if PatternLibrary.validate_iban(iban_clean):
            banking["iban"] = iban_clean

    # Extract BIC/SWIFT
    bic = extract_pattern(text, PatternLibrary.BIC_PATTERN)
    if not bic:
        bic = extract_pattern(text, PatternLibrary.SWIFT_PATTERN)
    if bic and PatternLibrary.validate_bic(bic):
        banking["bic"] = bic

    # --- US Banking (ABA Routing) ---
    # Try all ABA routing number patterns
    routing = None
    for pattern in PatternLibrary.ABA_ROUTING_PATTERNS:
        routing = extract_pattern(text, pattern)
        if routing:
            break

    # CRITICAL: Validate ABA checksum (strict per user requirement)
    if routing and PatternLibrary.validate_aba_routing(routing):
        banking["routing_number"] = routing

    # --- UK Banking (Sort Code) ---
    # Try all sort code patterns
    sort_code = None
    for pattern in PatternLibrary.SORT_CODE_PATTERNS:
        sort_code = extract_pattern(text, pattern)
        if sort_code:
            break

    # Validate and normalize sort code
    if sort_code and PatternLibrary.validate_sort_code(sort_code):
        banking["sort_code"] = PatternLibrary.normalize_sort_code(sort_code)

    # --- Generic Account Number ---
    # Extract account number (works for US, UK, and other countries)
    account = extract_account_number_smart(text, banking)
    if account:
        banking["account_number"] = account

    # --- Bank Name (existing logic) ---
    for pattern in PatternLibrary.BANK_NAME_PATTERNS:
        bank_match = re.search(pattern, text)
        if bank_match:
            banking["bank_name"] = bank_match.group(1).strip()
            break

    # --- Payment Address (existing logic) ---
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

    # --- Auto-detect Payment Method ---
    payment_method = detect_payment_method(banking)
    if payment_method != PARSING_FAILED:
        banking["payment_method"] = payment_method

    return banking


def extract_invoice_metadata(text: str) -> Dict[str, str]:
    """
    Extract invoice metadata fields (invoice number, dates, payment terms).

    Args:
        text: Full invoice text

    Returns:
        Dictionary with invoice_number, invoice_date, due_date, payment_terms
    """
    metadata = {
        "invoice_number": PARSING_FAILED,
        "invoice_date": PARSING_FAILED,
        "due_date": PARSING_FAILED,
        "payment_terms": PARSING_FAILED,
    }

    # --- Invoice Number ---
    for pattern in PatternLibrary.INVOICE_NUMBER_PATTERNS:
        invoice_num = extract_pattern(text, pattern)
        if invoice_num:
            # Basic validation: should be alphanumeric with possible separators
            if re.match(r'^[A-Z0-9\-/]+$', invoice_num, re.IGNORECASE):
                metadata["invoice_number"] = invoice_num
                break

    # --- Invoice Date ---
    for pattern in PatternLibrary.INVOICE_DATE_PATTERNS:
        invoice_date = extract_pattern(text, pattern)
        if invoice_date:
            # Basic validation: should match date format
            if re.match(r'\d{2,4}[-/.]\d{2}[-/.]\d{2,4}', invoice_date):
                metadata["invoice_date"] = invoice_date
                break

    # --- Due Date ---
    for pattern in PatternLibrary.DUE_DATE_PATTERNS:
        due_date = extract_pattern(text, pattern)
        if due_date:
            # Basic validation: should match date format
            if re.match(r'\d{2,4}[-/.]\d{2}[-/.]\d{2,4}', due_date):
                metadata["due_date"] = due_date
                break

    # --- Payment Terms ---
    for pattern in PatternLibrary.PAYMENT_TERMS_PATTERNS:
        terms = extract_pattern(text, pattern)
        if terms:
            # Clean up extracted terms (remove extra whitespace)
            terms = ' '.join(terms.split())
            if len(terms) > 3:  # Minimum reasonable length
                metadata["payment_terms"] = terms
                break

    return metadata


def extract_tax_info(text: str) -> Dict[str, str]:
    """
    Extract tax/VAT information (amount, rate, ID).

    Args:
        text: Full invoice text

    Returns:
        Dictionary with tax_amount, tax_rate, tax_id
    """
    tax_info = {
        "tax_amount": PARSING_FAILED,
        "tax_rate": PARSING_FAILED,
        "tax_id": PARSING_FAILED,
    }

    # --- Tax/VAT Rate (check first - more specific with %) ---
    for pattern in PatternLibrary.TAX_RATE_PATTERNS:
        tax_rate = extract_pattern(text, pattern)
        if tax_rate:
            # Validate rate format (should be numeric)
            if re.match(r'\d{1,2}(?:[.,]\d{1,2})?', tax_rate):
                tax_info["tax_rate"] = tax_rate.strip() + "%"
                break

    # --- Tax/VAT Amount ---
    for pattern in PatternLibrary.TAX_AMOUNT_PATTERNS:
        tax_amount = extract_pattern(text, pattern)
        if tax_amount:
            # Validate amount format
            if re.match(r'[€$£]?\s*\d{1,3}(?:[.,]\d{3})*[.,]\d{2}', tax_amount):
                tax_info["tax_amount"] = tax_amount.strip()
                break

    # --- Tax/VAT ID ---
    for pattern in PatternLibrary.TAX_ID_PATTERNS:
        tax_id = extract_pattern(text, pattern)
        if tax_id:
            # Basic validation: should be alphanumeric
            if len(tax_id) >= 8:  # Minimum reasonable length for tax IDs
                tax_info["tax_id"] = tax_id.strip()
                break

    return tax_info


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
