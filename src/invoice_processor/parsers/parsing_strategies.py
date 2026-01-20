#!/usr/bin/env python3
"""
Parsing Strategies for Invoice Parser
Implements multiple parsing strategies using the Strategy Pattern.
"""

import re
from abc import ABC, abstractmethod
from typing import Dict, List
from .pattern_library import PatternLibrary
from .email_utils import extract_emails_from_text
from .extraction_utils import (
    create_default_result, extract_section,
    extract_amount, calculate_confidence, extract_banking_info,
    extract_invoice_metadata, extract_tax_info
)


class BaseStrategy(ABC):
    """Abstract base class for parsing strategies"""

    @abstractmethod
    def can_handle(self, text: str, lines: List[str]) -> bool:
        """
        Determine if this strategy can handle the invoice format.

        Args:
            text: Full text of invoice
            lines: Text split into lines

        Returns:
            True if this strategy should be tried
        """
        pass

    @abstractmethod
    def parse(self, text: str, lines: List[str]) -> Dict[str, str]:
        """
        Parse the invoice using this strategy.

        Args:
            text: Full text of invoice
            lines: Text split into lines

        Returns:
            Dictionary with extracted fields
        """
        pass


class TwoColumnStrategy(BaseStrategy):
    """
    Strategy for parsing two-column layout invoices (Anthropic-style).
    Detects "Bill to" anchor and parses side-by-side sender/recipient data.
    """

    def can_handle(self, text: str, lines: List[str]) -> bool:
        """Detect if invoice has two-column layout with 'Bill to' anchor"""
        # Must have "Bill to" marker
        has_bill_to = any(re.search(r'bill\s+to', line, re.IGNORECASE) for line in lines)

        if not has_bill_to:
            return False

        # Additional indicators of two-column layout
        # Check for multiple emails on same line or dual postal codes
        for line in lines:
            emails = re.findall(PatternLibrary.EMAIL_PATTERN, line)
            if len(emails) >= 2:
                return True

            # Check for two 5-digit postal codes on same line (US + German pattern)
            zip_codes = re.findall(r'\b\d{5}\b', line)
            if len(zip_codes) >= 2:
                return True

        # If we have "Bill to", assume it's this format even without other indicators
        return True

    def parse(self, text: str, lines: List[str]) -> Dict[str, str]:
        """Parse two-column layout invoice (extracted from current pdf_parser.py)"""
        result = create_default_result()

        # Find "Bill to" line
        bill_to_line_idx = -1
        for i, line in enumerate(lines):
            if re.search(r'bill\s+to', line, re.IGNORECASE):
                bill_to_line_idx = i
                # Extract sender name from same line (before "Bill to")
                match = re.search(r'(.+?)\s+Bill\s+to', line, re.IGNORECASE)
                if match:
                    result["sender"] = match.group(1).strip()
                break

        # Parse subsequent lines (two-column layout)
        if bill_to_line_idx >= 0:
            sender_addr = []
            recipient_addr = []

            for i in range(bill_to_line_idx + 1, min(bill_to_line_idx + 6, len(lines))):
                line = lines[i].strip()
                if not line or '€' in line or 'due' in line.lower() or 'pay' in line.lower():
                    break

                # PRIORITY 1: Check for pattern "email's Name" to extract recipient
                match = re.search(r"(.*?)([\w\.-]+@[\w\.-]+\.\w+)'s\s+(.+)", line)
                if match:
                    sender_addr.append(match.group(1).strip())
                    email = match.group(2)
                    recip_name = match.group(3).strip()
                    # Determine which email is which
                    if 'support@' in email or 'billing@' in email or 'info@' in email:
                        result["sender_email"] = email
                    else:
                        result["recipient_email"] = email
                        result["recipient"] = recip_name
                    continue

                # PRIORITY 2: Check for two emails on same line
                if '@' in line:
                    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', line)
                    if len(emails) == 2:
                        # Two emails: left=sender, right=recipient
                        result["sender_email"] = emails[0]
                        result["recipient_email"] = emails[1]
                        continue
                    elif len(emails) == 1:
                        # Single email - determine which
                        if 'support@' in emails[0] or 'billing@' in emails[0]:
                            result["sender_email"] = emails[0]
                        else:
                            result["recipient_email"] = emails[0]
                        continue

                # Look for double location pattern
                zip_matches = list(re.finditer(r'\b\d{5}\b', line))
                if len(zip_matches) == 2:
                    # Two zip codes - split between them
                    split_pos = zip_matches[1].start()
                    sender_part = line[:split_pos].strip()
                    recipient_part = line[split_pos:].strip()
                    sender_addr.append(sender_part)
                    recipient_addr.append(recipient_part)
                    continue

                # Look for country pattern
                if "United States" in line and "Germany" in line:
                    parts = line.split("United States")
                    sender_addr.append("United States")
                    if len(parts) > 1:
                        recipient_addr.append(parts[1].strip())
                    continue

                # Default: try to split by common patterns
                if "Balatonstraße" in line or (re.search(r'PMB\s+\d+', line) and re.search(r'\d+[A-Z]', line)):
                    parts = re.split(r'([A-Z][a-zä-ü]+straße\s+\d+[A-Z]?)', line)
                    if len(parts) >= 2:
                        sender_addr.append(parts[0].strip())
                        recipient_addr.append(parts[1].strip())
                    continue

                # Fallback: if we can't split, and we have no sender addr yet, it's sender
                if not sender_addr:
                    sender_addr.append(line)
                else:
                    recipient_addr.append(line)

            if sender_addr:
                result["sender_address"] = ', '.join(sender_addr)
            if recipient_addr:
                result["recipient_address"] = ', '.join(recipient_addr)

        # Extract amount
        amount = extract_amount(text)
        if amount:
            result["amount"] = amount

        # Extract currency
        if '€' in text or 'EUR' in text:
            result["currency"] = "EUR"
        elif '$' in text or 'USD' in text:
            result["currency"] = "USD"

        # Extract banking info using shared function
        banking_info = extract_banking_info(text, lines)
        result.update(banking_info)

        # Extract invoice metadata (invoice number, dates, payment terms) - v2.2.0
        metadata = extract_invoice_metadata(text, result.get('sender'))
        result.update(metadata)

        # Extract tax/VAT information - v2.2.0
        tax_info = extract_tax_info(text)
        result.update(tax_info)

        return result


class CompanySpecificStrategy(BaseStrategy):
    """
    Strategy for parsing company-specific invoice formats (Deutsche Bahn-style).
    Uses company-specific patterns and German formatting.
    """

    def can_handle(self, text: str, lines: List[str]) -> bool:
        """Detect if invoice is from Deutsche Bahn or similar German company"""
        # Check for Deutsche Bahn specifically
        if 'Deutsche Bahn' in text:
            return True

        # Check for other indicators of German corporate invoice
        german_indicators = ['GmbH', 'AG', 'straße', '·']
        indicator_count = sum(1 for ind in german_indicators if ind in text)

        return indicator_count >= 2

    def parse(self, text: str, lines: List[str]) -> Dict[str, str]:
        """Parse Deutsche Bahn style invoice (extracted from current pdf_parser.py)"""
        result = create_default_result()

        # Find sender (Deutsche Bahn or GmbH company)
        for i, line in enumerate(lines):
            if 'Deutsche Bahn' in line or 'GmbH' in line:
                result["sender"] = line.strip()
                # Get address from next line
                if i+1 < len(lines) and ('straße' in lines[i+1] or '·' in lines[i+1]):
                    result["sender_address"] = lines[i+1].strip().replace(' · ', ', ')
                break

        # Find recipient (person name) - look after sender address
        for i, line in enumerate(lines[3:20], start=3):
            line_clean = line.strip()
            # Skip header/metadata lines
            if any(x in line_clean for x in ['Invoice', 'GmbH', 'Customer', 'Page', 'Frankfurt', 'Mainzer']):
                continue
            # Look for capitalized name pattern
            words = line_clean.split()
            if 2 <= len(words) <= 3 and all(w[0].isupper() for w in words if w and len(w) > 1):
                result["recipient"] = line_clean
                break

        # Extract amount
        amount = extract_amount(text)
        if amount:
            result["amount"] = amount

        # Extract currency
        if '€' in text or 'EUR' in text:
            result["currency"] = "EUR"
        elif '$' in text or 'USD' in text:
            result["currency"] = "USD"

        # Extract banking info using shared function
        banking_info = extract_banking_info(text, lines)
        result.update(banking_info)

        # Extract invoice metadata (invoice number, dates, payment terms) - v2.2.0
        metadata = extract_invoice_metadata(text, result.get('sender'))
        result.update(metadata)

        # Extract tax/VAT information - v2.2.0
        tax_info = extract_tax_info(text)
        result.update(tax_info)

        return result


class SingleColumnLabelStrategy(BaseStrategy):
    """
    Strategy for parsing single-column invoices with clear labels (From:, To:, etc.).
    Handles simple structured invoices with sequential label-based sections.
    """

    def can_handle(self, text: str, lines: List[str]) -> bool:
        """Detect if invoice has single-column format with labels"""
        # Check for sender labels
        sender_idx, _, _ = PatternLibrary.find_label_in_lines(
            lines, PatternLibrary.get_all_sender_labels()
        )

        # Check for recipient labels
        recipient_idx, _, _ = PatternLibrary.find_label_in_lines(
            lines, PatternLibrary.get_all_recipient_labels()
        )

        # Must have at least one label (sender or recipient)
        return sender_idx >= 0 or recipient_idx >= 0

    def parse(self, text: str, lines: List[str]) -> Dict[str, str]:
        """Parse single-column label-based invoice"""
        result = create_default_result()

        # Find sender section
        sender_idx, _, sender_name = PatternLibrary.find_label_in_lines(
            lines, PatternLibrary.get_all_sender_labels()
        )

        # Find recipient section
        recipient_idx, _, recipient_name = PatternLibrary.find_label_in_lines(
            lines, PatternLibrary.get_all_recipient_labels()
        )

        # Determine section boundaries
        # Sender section: from sender_idx to recipient_idx (or line 15)
        # Recipient section: from recipient_idx to end of header (or line 25)

        if sender_idx >= 0:
            end_idx = recipient_idx if recipient_idx > sender_idx else min(sender_idx + 10, len(lines))
            sender_data = extract_section(lines, sender_idx, end_idx)

            if sender_data['name']:
                result["sender"] = sender_data['name']
            elif sender_name:  # Use name from label line
                result["sender"] = sender_name

            if sender_data['address']:
                result["sender_address"] = sender_data['address']
            if sender_data['email']:
                result["sender_email"] = sender_data['email']

        if recipient_idx >= 0:
            end_idx = min(recipient_idx + 10, len(lines))
            recipient_data = extract_section(lines, recipient_idx, end_idx)

            if recipient_data['name']:
                result["recipient"] = recipient_data['name']
            elif recipient_name:  # Use name from label line
                result["recipient"] = recipient_name

            if recipient_data['address']:
                result["recipient_address"] = recipient_data['address']
            if recipient_data['email']:
                result["recipient_email"] = recipient_data['email']

        # If emails not found in sections, try extracting from full text
        if result["sender_email"] == "PARSING FAILED" or result["recipient_email"] == "PARSING FAILED":
            sender_email, recipient_email = extract_emails_from_text(text)
            if sender_email and result["sender_email"] == "PARSING FAILED":
                result["sender_email"] = sender_email
            if recipient_email and result["recipient_email"] == "PARSING FAILED":
                result["recipient_email"] = recipient_email

        # Extract amount
        amount = extract_amount(text)
        if amount:
            result["amount"] = amount

        # Extract currency
        if '€' in text or 'EUR' in text:
            result["currency"] = "EUR"
        elif '$' in text or 'USD' in text:
            result["currency"] = "USD"
        elif '£' in text or 'GBP' in text:
            result["currency"] = "GBP"

        # Extract banking info using shared function
        banking_info = extract_banking_info(text, lines)
        result.update(banking_info)

        # Extract invoice metadata (invoice number, dates, payment terms) - v2.2.0
        metadata = extract_invoice_metadata(text, result.get('sender'))
        result.update(metadata)

        # Extract tax/VAT information - v2.2.0
        tax_info = extract_tax_info(text)
        result.update(tax_info)

        return result


class PatternFallbackStrategy(BaseStrategy):
    """
    Fallback strategy that extracts data using generic patterns only.
    No assumptions about invoice structure - just pattern matching.
    """

    def can_handle(self, text: str, lines: List[str]) -> bool:
        """
        Only use fallback if no other strategy patterns detected.

        Returns False if text contains patterns that other strategies can handle better.
        This prevents fallback from running unnecessarily.
        """
        # Check for TwoColumnStrategy patterns
        has_column_structure = (
            'From:' in text or 'To:' in text or
            'Bill from:' in text or 'Bill to:' in text
        )

        # Check for SingleColumnLabelStrategy patterns
        has_label_structure = (
            'Sender:' in text or 'Recipient:' in text or
            'Absender:' in text or 'Empfänger:' in text
        )

        # Check for CompanySpecificStrategy patterns
        has_company_specific = (
            'Deutsche Bahn' in text or
            'DB Vertrieb' in text
        )

        # Only use fallback if no other strategy can handle it
        return not (has_column_structure or has_label_structure or has_company_specific)

    def parse(self, text: str, lines: List[str]) -> Dict[str, str]:
        """Parse using generic patterns only"""
        result = create_default_result()

        # Extract emails using heuristics
        sender_email, recipient_email = extract_emails_from_text(text)
        if sender_email:
            result["sender_email"] = sender_email
        if recipient_email:
            result["recipient_email"] = recipient_email

        # Try to find names near emails
        all_emails = PatternLibrary.extract_emails(text)
        for email in all_emails:
            # Find line containing this email
            for i, line in enumerate(lines):
                if email in line:
                    # Try to extract name from same line (before or after email)
                    parts = line.split(email)
                    if parts[0].strip() and not re.search(r':', parts[0]):
                        # Text before email might be name
                        potential_name = parts[0].strip().rstrip(':,')
                        if len(potential_name) > 3 and not result.get("sender"):
                            result["sender"] = potential_name
                    break

        # Extract amount
        amount = extract_amount(text)
        if amount:
            result["amount"] = amount

        # Extract currency
        if '€' in text or 'EUR' in text:
            result["currency"] = "EUR"
        elif '$' in text or 'USD' in text:
            result["currency"] = "USD"
        elif '£' in text or 'GBP' in text:
            result["currency"] = "GBP"

        # Extract banking info using shared function (includes US/UK support)
        banking_info = extract_banking_info(text, lines)
        result.update(banking_info)

        # Extract invoice metadata (invoice number, dates, payment terms) - v2.2.0
        metadata = extract_invoice_metadata(text, result.get('sender'))
        result.update(metadata)

        # Extract tax/VAT information - v2.2.0
        tax_info = extract_tax_info(text)
        result.update(tax_info)

        return result


if __name__ == "__main__":
    # Test strategy detection
    print("Testing strategy detection:\n")

    # Test Two-Column detection
    two_col_text = "Anthropic, PBC Bill to\nsupport@anthropic.com john@example.com"
    two_col_lines = two_col_text.split('\n')
    strategy = TwoColumnStrategy()
    print(f"Two-Column: {strategy.can_handle(two_col_text, two_col_lines)}")

    # Test Single-Column detection
    single_col_text = "From: Acme Corp\nTo: John Doe"
    single_col_lines = single_col_text.split('\n')
    strategy2 = SingleColumnLabelStrategy()
    print(f"Single-Column: {strategy2.can_handle(single_col_text, single_col_lines)}")

    # Test Company-Specific detection
    company_text = "Deutsche Bahn Connect GmbH\nMainzer Landstraße 169"
    company_lines = company_text.split('\n')
    strategy3 = CompanySpecificStrategy()
    print(f"Company-Specific: {strategy3.can_handle(company_text, company_lines)}")
