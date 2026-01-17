#!/usr/bin/env python3
"""
Pattern Library for Invoice Parsing
Centralized repository of all regex patterns and label definitions for English and German invoices.
"""

import re
from typing import List, Dict


class PatternLibrary:
    """Centralized pattern definitions for invoice parsing"""

    # ========== LANGUAGE-SPECIFIC LABEL PATTERNS ==========

    # Sender label patterns (English and German)
    # Note: (.+) can be empty if label is on its own line
    SENDER_LABELS = {
        'en': [
            r'^\s*From:\s*(.*)',
            r'^\s*Invoice\s+from:\s*(.*)',
            r'^\s*Sender:\s*(.*)',
            r'^\s*Bill\s+from:\s*(.*)',
        ],
        'de': [
            r'^\s*Absender:\s*(.*)',
            r'^\s*Von:\s*(.*)',
            r'^\s*Rechnungssteller:\s*(.*)',
        ]
    }

    # Recipient label patterns (English and German)
    # Note: (.*) can be empty if label is on its own line
    RECIPIENT_LABELS = {
        'en': [
            r'^\s*To:\s*(.*)',
            r'^\s*Bill\s+to:\s*(.*)',
            r'^\s*Recipient:\s*(.*)',
            r'^\s*Invoice\s+to:\s*(.*)',
            r'^\s*Customer:\s*(.*)',
        ],
        'de': [
            r'^\s*Rechnungsempfänger:\s*(.*)',
            r'^\s*An:\s*(.*)',
            r'^\s*Empfänger:\s*(.*)',
            r'^\s*Kunde:\s*(.*)',
        ]
    }

    # ========== UNIVERSAL PATTERNS ==========

    # Email pattern
    EMAIL_PATTERN = r'[\w\.-]+@[\w\.-]+\.\w+'

    # IBAN pattern (supports spaces, will be removed during extraction)
    IBAN_PATTERN = r'IBAN[:\s]*([A-Z]{2}\s?\d{2}(?:\s?\d{4}){4}(?:\s?\d{0,2})?)'

    # BIC/SWIFT pattern (must have BIC: label to avoid false positives)
    BIC_PATTERN = r'BIC[:\s]*([A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)'
    SWIFT_PATTERN = r'SWIFT[:\s]*([A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)'

    # Bank name patterns (generic, not bank-specific)
    BANK_NAME_PATTERNS = [
        r'Bank[:\s]+([A-Z][a-zA-Z\s&]+(?:Bank|AG|GmbH|Corp|Inc)[\w\s]*)',
        r'([A-Z][a-zA-Z\s]+(?:Bank|bank)[\w\s]*(?:AG|GmbH)?)',
        r'(Postbank[^:\n]*)',
        r'(Deutsche Bank[^:\n]*)',
        r'([A-Z][a-zA-Z\s]+(?:AG|GmbH)\s*$)',
    ]

    # Payment address section header
    PAYMENT_ADDRESS_PATTERN = r'PAYMENT\s+ADDRESS'

    # ========== AMOUNT PATTERNS ==========

    AMOUNT_PATTERNS = [
        # English patterns (with thousand separators)
        r'Total\s+Amount[:\s]*([€$£]?\s*\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
        r'Amount\s+(?:Due|Invoice|Total)[:\s]+([€$£]?\s*\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
        r'Invoice\s+Amount[:\s]+([€$£]?\s*\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
        r'€\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s+(?:due|total)',
        r'\$\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
        r'£\s*(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',

        # German patterns (with thousand separators)
        r'Gesamtbetrag[:\s]+(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
        r'Rechnungsbetrag[:\s]+(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
        r'Betrag[:\s]+(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
        r'gross\s+amount\s+(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
    ]

    # ========== POSTAL CODE PATTERNS ==========

    POSTAL_CODE_PATTERNS = {
        'de': r'\b\d{5}\b',  # German: 10319, 60327
        'us': r'\b\d{5}(?:-\d{4})?\b',  # US: 94104, 94104-1234
        'uk': r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}\b',  # UK: SW1A 1AA
        'nl': r'\b\d{4}\s*[A-Z]{2}\b',  # Netherlands: 1234 AB
        'fr': r'\b\d{5}\b',  # France: 75001
        'at': r'\b\d{4}\b',  # Austria: 1010
        'ch': r'\b\d{4}\b',  # Switzerland: 8000
    }

    # ========== STREET PATTERNS ==========

    STREET_PATTERNS = [
        # English street patterns
        r'\b\d+[A-Z]?\s+[A-Z][a-z]+\s+(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Drive|Dr\.?|Lane|Ln\.?|Boulevard|Blvd\.?)',
        r'\b\d+\s+[A-Z][a-z]+\s+[A-Z][a-z]+\s+(?:Street|St\.?|Avenue|Ave\.?)',

        # German street patterns
        r'[A-Z][a-zäöüß]+(?:straße|strasse|weg|platz|allee)\s+\d+[A-Z]?',
        r'[A-Z][a-zäöüß]+\s+[A-Z][a-zäöüß]+(?:straße|strasse)\s+\d+',

        # PO Box patterns
        r'\bPMB\s+\d+',
        r'\bP\.?O\.?\s+Box\s+\d+',
        r'\bPostfach\s+\d+',
    ]

    # ========== COUNTRY NAMES ==========

    COUNTRIES = [
        # English names
        'Germany', 'United States', 'USA', 'United Kingdom', 'UK',
        'France', 'Netherlands', 'Belgium', 'Austria', 'Switzerland',
        'Italy', 'Spain', 'Portugal', 'Sweden', 'Denmark', 'Norway',
        'Poland', 'Czech Republic', 'Ireland', 'Canada',

        # German names
        'Deutschland', 'Vereinigte Staaten', 'Großbritannien',
        'Frankreich', 'Niederlande', 'Belgien', 'Österreich',
        'Schweiz', 'Italien', 'Spanien', 'Portugal',
    ]

    # ========== CITY PATTERNS ==========

    # Common city name patterns (capitalized words)
    CITY_PATTERN = r'\b[A-Z][a-zäöüß]+(?:\s+[A-Z][a-zäöüß]+)?\b'

    # ========== LANGUAGE DETECTION ==========

    GERMAN_INDICATORS = [
        'Rechnung', 'Rechnungsnummer', 'Absender', 'Rechnungsempfänger',
        'Gesamtbetrag', 'Rechnungsbetrag', 'MwSt', 'Mehrwertsteuer',
        'Zahlungsbedingungen', 'Fälligkeitsdatum', 'Kundennummer',
        'straße', 'strasse', 'GmbH', 'AG'
    ]

    ENGLISH_INDICATORS = [
        'Invoice', 'Bill to', 'From:', 'To:', 'Amount Due',
        'Total Amount', 'Payment Terms', 'Due Date', 'Customer',
        'Street', 'Avenue', 'Road', 'Inc', 'Corp', 'LLC'
    ]

    # ========== UTILITY METHODS ==========

    @staticmethod
    def detect_language(text: str) -> str:
        """
        Detect if invoice is English or German based on keyword presence.

        Args:
            text: Full text of the invoice

        Returns:
            'de' for German, 'en' for English
        """
        german_count = sum(1 for word in PatternLibrary.GERMAN_INDICATORS if word in text)
        english_count = sum(1 for word in PatternLibrary.ENGLISH_INDICATORS if word in text)

        # If German indicators are stronger, return 'de'
        if german_count > english_count:
            return 'de'
        else:
            return 'en'

    @staticmethod
    def get_all_sender_labels() -> List[str]:
        """Get all sender label patterns (English + German)"""
        return PatternLibrary.SENDER_LABELS['en'] + PatternLibrary.SENDER_LABELS['de']

    @staticmethod
    def get_all_recipient_labels() -> List[str]:
        """Get all recipient label patterns (English + German)"""
        return PatternLibrary.RECIPIENT_LABELS['en'] + PatternLibrary.RECIPIENT_LABELS['de']

    @staticmethod
    def find_label_in_lines(lines: List[str], patterns: List[str]) -> tuple:
        """
        Find the first occurrence of a label pattern in lines.

        Args:
            lines: List of text lines
            patterns: List of regex patterns to search for

        Returns:
            Tuple of (line_index, matched_text, extracted_value) or (-1, None, None)
        """
        for i, line in enumerate(lines):
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    extracted = match.group(1).strip() if match.lastindex >= 1 else None
                    return (i, line, extracted)
        return (-1, None, None)

    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """Extract all email addresses from text"""
        return re.findall(PatternLibrary.EMAIL_PATTERN, text)

    @staticmethod
    def is_sender_email(email: str) -> bool:
        """
        Determine if an email likely belongs to the sender (company) or recipient.

        Args:
            email: Email address to check

        Returns:
            True if likely sender email, False otherwise
        """
        sender_indicators = ['support@', 'billing@', 'info@', 'invoices@',
                            'accounts@', 'sales@', 'contact@', 'hello@']
        return any(indicator in email.lower() for indicator in sender_indicators)

    @staticmethod
    def extract_postal_codes(text: str) -> List[tuple]:
        """
        Extract postal codes from text with their country type.

        Returns:
            List of tuples (postal_code, country_code)
        """
        results = []
        for country_code, pattern in PatternLibrary.POSTAL_CODE_PATTERNS.items():
            matches = re.findall(pattern, text)
            for match in matches:
                results.append((match, country_code))
        return results

    @staticmethod
    def contains_country(line: str) -> bool:
        """Check if line contains a country name"""
        return any(country in line for country in PatternLibrary.COUNTRIES)

    # ========== VALIDATION FUNCTIONS ==========

    @staticmethod
    def validate_iban(iban: str) -> bool:
        """
        Validate IBAN using mod-97 checksum algorithm.

        Args:
            iban: IBAN string (with or without spaces)

        Returns:
            True if IBAN is valid, False otherwise
        """
        if not iban:
            return False

        # Remove spaces and convert to uppercase
        iban = iban.replace(' ', '').replace('-', '').upper()

        # IBAN must be 15-34 characters
        if len(iban) < 15 or len(iban) > 34:
            return False

        # First two characters must be letters (country code)
        if not iban[:2].isalpha():
            return False

        # Next two characters must be digits (check digits)
        if not iban[2:4].isdigit():
            return False

        # Move first 4 characters to end
        rearranged = iban[4:] + iban[:4]

        # Convert letters to numbers (A=10, B=11, ..., Z=35)
        try:
            numeric = ''.join(
                str(int(c, 36)) if c.isalpha() else c
                for c in rearranged
            )
            # Validate checksum: mod 97 must equal 1
            return int(numeric) % 97 == 1
        except (ValueError, OverflowError):
            return False

    @staticmethod
    def validate_bic(bic: str) -> bool:
        """
        Validate BIC/SWIFT code format.

        Args:
            bic: BIC/SWIFT code

        Returns:
            True if BIC format is valid, False otherwise
        """
        if not bic:
            return False

        # Remove spaces
        bic = bic.replace(' ', '').upper()

        # BIC must be 8 or 11 characters
        if len(bic) not in [8, 11]:
            return False

        # Format: AAAA BB CC DDD
        # AAAA (4 chars): Bank code (letters only)
        # BB (2 chars): Country code (letters only)
        # CC (2 chars): Location code (letters or digits)
        # DDD (3 chars, optional): Branch code (letters or digits)

        # Check bank code (first 4 characters - letters only)
        if not bic[:4].isalpha():
            return False

        # Check country code (characters 5-6 - letters only)
        if not bic[4:6].isalpha():
            return False

        # Check location code (characters 7-8 - alphanumeric)
        if not bic[6:8].isalnum():
            return False

        # If 11 characters, check branch code (alphanumeric)
        if len(bic) == 11 and not bic[8:11].isalnum():
            return False

        return True

    @staticmethod
    def normalize_amount(amount_str: str, currency: str = None, language: str = 'en') -> Dict[str, any]:
        """
        Normalize amount string to float with proper locale handling.

        Args:
            amount_str: Raw amount string (e.g., "1.234,56" or "1,234.56")
            currency: Currency code if known (EUR, USD, etc.)
            language: Language hint ('en' or 'de')

        Returns:
            Dict with:
                - amount: float value
                - raw_amount: original string
                - currency: currency code
                - locale: detected locale ('en_US' or 'de_DE')
        """
        if not amount_str or amount_str == "PARSING FAILED":
            return {
                "amount": None,
                "raw_amount": amount_str,
                "currency": currency,
                "locale": None,
                "valid": False
            }

        # Remove currency symbols
        clean_amount = amount_str.replace('€', '').replace('$', '').replace('£', '').replace('CHF', '').strip()

        # Detect format based on multiple indicators
        has_comma_decimal = ',' in clean_amount and clean_amount.rfind(',') > clean_amount.rfind('.')
        has_dot_decimal = '.' in clean_amount and clean_amount.rfind('.') > clean_amount.rfind(',')

        # Use language hint if format is ambiguous
        if currency == "EUR" or language == 'de':
            # German format: 1.234,56
            locale = 'de_DE'
            if has_comma_decimal or (',' in clean_amount and '.' not in clean_amount):
                # Remove thousand separators (.) and replace decimal comma
                normalized = clean_amount.replace('.', '').replace(',', '.')
            else:
                # Might be US format or just decimal
                normalized = clean_amount.replace(',', '')
        else:
            # US format: 1,234.56
            locale = 'en_US'
            if has_dot_decimal or ('.' in clean_amount and ',' not in clean_amount):
                # Remove thousand separators (,)
                normalized = clean_amount.replace(',', '')
            else:
                # Might be German format or just decimal
                normalized = clean_amount.replace(',', '.')

        # Try to convert to float
        try:
            amount_float = float(normalized)

            # Validate amount is reasonable (> 0)
            if amount_float <= 0:
                raise ValueError("Amount must be positive")

            return {
                "amount": amount_float,
                "raw_amount": amount_str,
                "currency": currency,
                "locale": locale,
                "valid": True
            }
        except (ValueError, AttributeError):
            return {
                "amount": None,
                "raw_amount": amount_str,
                "currency": currency,
                "locale": None,
                "valid": False
            }


if __name__ == "__main__":
    # Test language detection
    german_text = "Rechnung für Deutsche Bahn GmbH. Gesamtbetrag: 100,00 €"
    english_text = "Invoice from Acme Corp. Total Amount: $100.00"

    print(f"German text detected as: {PatternLibrary.detect_language(german_text)}")
    print(f"English text detected as: {PatternLibrary.detect_language(english_text)}")

    # Test email extraction
    text = "Contact: support@company.com or john@example.com"
    emails = PatternLibrary.extract_emails(text)
    print(f"\nEmails found: {emails}")
    for email in emails:
        print(f"  {email} - {'Sender' if PatternLibrary.is_sender_email(email) else 'Recipient'}")

    # Test postal code extraction
    text2 = "Berlin 10319, Frankfurt 60327, New York 10001"
    postal_codes = PatternLibrary.extract_postal_codes(text2)
    print(f"\nPostal codes: {postal_codes}")

    # Test IBAN validation
    print("\n=== IBAN Validation ===")
    valid_iban = "DE89 3704 0044 0532 0130 00"
    invalid_iban = "DE89 3704 0044 0532 0130 99"
    print(f"Valid IBAN '{valid_iban}': {PatternLibrary.validate_iban(valid_iban)}")
    print(f"Invalid IBAN '{invalid_iban}': {PatternLibrary.validate_iban(invalid_iban)}")

    # Test BIC validation
    print("\n=== BIC Validation ===")
    valid_bic = "DEUTDEFF"
    invalid_bic = "DEUT123"
    print(f"Valid BIC '{valid_bic}': {PatternLibrary.validate_bic(valid_bic)}")
    print(f"Invalid BIC '{invalid_bic}': {PatternLibrary.validate_bic(invalid_bic)}")

    # Test amount normalization
    print("\n=== Amount Normalization ===")
    test_amounts = [
        ("1.234,56", "EUR", "de"),  # German format
        ("1,234.56", "USD", "en"),  # US format
        ("21.42", "EUR", "en"),     # Simple decimal
        ("9,00", "EUR", "de"),      # German decimal
    ]
    for amount_str, currency, lang in test_amounts:
        result = PatternLibrary.normalize_amount(amount_str, currency, lang)
        print(f"{amount_str} ({currency}, {lang}): {result['amount']} - valid: {result['valid']}")
