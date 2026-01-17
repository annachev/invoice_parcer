"""
NER-based field extraction using pre-trained spaCy models.

This module uses spaCy's pre-trained NER models to extract invoice fields
as a fallback when regex patterns fail.
"""

import logging
from typing import Dict, Optional, List
from ..core.constants import PARSING_FAILED

logger = logging.getLogger(__name__)


class SpacyNERExtractor:
    """
    Extract invoice fields using spaCy's pre-trained NER models.

    Uses entity types:
    - ORG: Organizations (sender/recipient companies)
    - MONEY: Monetary amounts
    - GPE: Geo-political entities (cities, countries for addresses)
    - PERSON: Person names (recipient names)
    """

    def __init__(self, model_name: str = "en_core_web_sm"):
        """
        Initialize the spaCy NER extractor.

        Args:
            model_name: spaCy model to use (default: en_core_web_sm for speed)
                       Options: en_core_web_sm (small, fast)
                               en_core_web_md (medium, balanced)
                               en_core_web_lg (large, accurate)
        """
        self.model_name = model_name
        self.nlp = None
        self._load_model()

    def _load_model(self):
        """Load spaCy model lazily."""
        try:
            import spacy
            self.nlp = spacy.load(self.model_name)
            logger.info(f"Loaded spaCy model: {self.model_name}")
        except OSError as e:
            logger.warning(
                f"spaCy model '{self.model_name}' not found. "
                f"Please install it with: python -m spacy download {self.model_name}"
            )
            raise
        except ImportError as e:
            logger.error("spaCy not installed. Install with: pip install spacy")
            raise

    def extract(self, text: str) -> Dict[str, str]:
        """
        Extract invoice fields using NER.

        Args:
            text: Invoice text content

        Returns:
            Dictionary with extracted fields (sender, recipient, amount, etc.)
        """
        if not self.nlp:
            logger.warning("spaCy model not loaded, returning empty results")
            return self._empty_result()

        try:
            doc = self.nlp(text)

            # Extract entities by type
            organizations = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
            money_amounts = [ent.text for ent in doc.ents if ent.label_ == "MONEY"]
            locations = [ent.text for ent in doc.ents if ent.label_ == "GPE"]
            persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]

            # Map entities to invoice fields
            result = {
                "sender": organizations[0] if len(organizations) > 0 else PARSING_FAILED,
                "recipient": organizations[1] if len(organizations) > 1 else (
                    persons[0] if persons else PARSING_FAILED
                ),
                "amount": money_amounts[0] if money_amounts else PARSING_FAILED,
                "currency": self._extract_currency(money_amounts[0]) if money_amounts else PARSING_FAILED,
                "sender_address": self._build_address(locations, 0) if locations else PARSING_FAILED,
                "recipient_address": self._build_address(locations, 1) if len(locations) > 1 else PARSING_FAILED,
                "sender_email": PARSING_FAILED,  # NER doesn't extract emails well
                "recipient_email": PARSING_FAILED,
                "iban": PARSING_FAILED,  # NER doesn't recognize IBAN patterns
                "bic": PARSING_FAILED,
                "bank_name": PARSING_FAILED,
                "payment_address": PARSING_FAILED,
            }

            logger.debug(f"NER extracted: {len(organizations)} orgs, {len(money_amounts)} amounts")
            return result

        except Exception as e:
            logger.error(f"NER extraction failed: {e}", exc_info=True)
            return self._empty_result()

    def _extract_currency(self, money_str: str) -> str:
        """Extract currency code from money string."""
        if not money_str:
            return PARSING_FAILED

        # Common currency symbols/codes
        if '$' in money_str or 'USD' in money_str:
            return 'USD'
        elif '€' in money_str or 'EUR' in money_str:
            return 'EUR'
        elif '£' in money_str or 'GBP' in money_str:
            return 'GBP'
        elif 'CHF' in money_str:
            return 'CHF'

        return PARSING_FAILED

    def _build_address(self, locations: List[str], index: int) -> str:
        """Build address string from location entities."""
        if index >= len(locations):
            return PARSING_FAILED

        # Simple heuristic: take the location at the given index
        # In future, could combine multiple locations for full address
        return locations[index]

    def _empty_result(self) -> Dict[str, str]:
        """Return empty result with all fields set to PARSING_FAILED."""
        return {
            "sender": PARSING_FAILED,
            "recipient": PARSING_FAILED,
            "amount": PARSING_FAILED,
            "currency": PARSING_FAILED,
            "sender_address": PARSING_FAILED,
            "recipient_address": PARSING_FAILED,
            "sender_email": PARSING_FAILED,
            "recipient_email": PARSING_FAILED,
            "iban": PARSING_FAILED,
            "bic": PARSING_FAILED,
            "bank_name": PARSING_FAILED,
            "payment_address": PARSING_FAILED,
        }

    def get_confidence(self, result: Dict[str, str]) -> float:
        """
        Calculate confidence score for NER extraction.

        Args:
            result: Extraction result dictionary

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Count successfully extracted fields
        extracted = sum(1 for v in result.values() if v != PARSING_FAILED)
        total_fields = len(result)

        # NER typically extracts fewer fields than regex, so lower threshold
        # Weight based on critical fields
        critical_extracted = sum(
            1 for field in ['sender', 'recipient', 'amount']
            if result.get(field) != PARSING_FAILED
        )

        # Confidence is weighted: 70% critical fields, 30% all fields
        critical_score = critical_extracted / 3.0 * 0.7
        total_score = extracted / total_fields * 0.3

        return min(critical_score + total_score, 1.0)
