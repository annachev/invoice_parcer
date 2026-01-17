"""
Layout feature extraction for invoice classification.

Extracts structural features from PDF invoices to predict layout type
and optimize parsing strategy selection.
"""

import pdfplumber
import logging
from typing import Dict, List, Optional
from pathlib import Path
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class LayoutFeatureExtractor:
    """
    Extract layout features from PDF invoices.

    Features include:
    - Text density and distribution
    - Column detection
    - Table presence
    - Label patterns
    - Structural characteristics
    """

    def __init__(self):
        """Initialize the layout feature extractor."""
        pass

    def extract(self, pdf_path: str) -> Dict[str, float]:
        """
        Extract layout features from a PDF invoice.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary of feature names to values
        """
        features = {}

        try:
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) == 0:
                    logger.warning(f"PDF has no pages: {pdf_path}")
                    return self._empty_features()

                # Analyze first page (most invoices are single page)
                page = pdf.pages[0]

                # Extract text and chars
                text = page.extract_text() or ""
                chars = page.chars if hasattr(page, 'chars') else []

                # Text-based features
                features.update(self._extract_text_features(text, page))

                # Spatial features
                features.update(self._extract_spatial_features(chars, page))

                # Pattern-based features
                features.update(self._extract_pattern_features(text))

                # Table features
                features.update(self._extract_table_features(page))

                logger.debug(f"Extracted {len(features)} features from {Path(pdf_path).name}")

        except Exception as e:
            logger.error(f"Failed to extract layout features: {e}", exc_info=True)
            features = self._empty_features()

        return features

    def _extract_text_features(self, text: str, page) -> Dict[str, float]:
        """Extract text-based features."""
        features = {}

        lines = text.split('\n')
        non_empty_lines = [l for l in lines if l.strip()]

        # Basic text statistics
        features['line_count'] = len(lines)
        features['non_empty_line_count'] = len(non_empty_lines)
        features['char_count'] = len(text)
        features['word_count'] = len(text.split())

        # Text density (chars per square inch)
        page_area = page.width * page.height
        features['text_density'] = len(text) / page_area if page_area > 0 else 0

        # Average line length
        if non_empty_lines:
            features['avg_line_length'] = sum(len(l) for l in non_empty_lines) / len(non_empty_lines)
            features['max_line_length'] = max(len(l) for l in non_empty_lines)
            features['min_line_length'] = min(len(l) for l in non_empty_lines)
        else:
            features['avg_line_length'] = 0
            features['max_line_length'] = 0
            features['min_line_length'] = 0

        # Line length variance (indicates structured vs unstructured)
        if len(non_empty_lines) > 1:
            avg_len = features['avg_line_length']
            variance = sum((len(l) - avg_len) ** 2 for l in non_empty_lines) / len(non_empty_lines)
            features['line_length_variance'] = variance
        else:
            features['line_length_variance'] = 0

        return features

    def _extract_spatial_features(self, chars: List, page) -> Dict[str, float]:
        """Extract spatial/layout features from character positions."""
        features = {}

        if not chars:
            features['has_two_columns'] = 0
            features['x_position_variance'] = 0
            features['y_position_variance'] = 0
            return features

        # Extract x and y positions
        x_positions = [c['x0'] for c in chars]
        y_positions = [c['y0'] for c in chars]

        # Column detection (simplified: check x-position clustering)
        # If chars are clustered in two distinct x-ranges, likely two-column
        page_center = page.width / 2
        left_chars = sum(1 for x in x_positions if x < page_center)
        right_chars = sum(1 for x in x_positions if x >= page_center)

        # Two-column heuristic: both sides have significant text
        total_chars = len(chars)
        if total_chars > 0:
            left_ratio = left_chars / total_chars
            right_ratio = right_chars / total_chars
            # Two columns if both sides have 20-80% of chars
            features['has_two_columns'] = 1 if (0.2 <= left_ratio <= 0.8 and 0.2 <= right_ratio <= 0.8) else 0
        else:
            features['has_two_columns'] = 0

        # Position variance (high variance = scattered text)
        if x_positions:
            x_mean = sum(x_positions) / len(x_positions)
            x_variance = sum((x - x_mean) ** 2 for x in x_positions) / len(x_positions)
            features['x_position_variance'] = x_variance
        else:
            features['x_position_variance'] = 0

        if y_positions:
            y_mean = sum(y_positions) / len(y_positions)
            y_variance = sum((y - y_mean) ** 2 for y in y_positions) / len(y_positions)
            features['y_position_variance'] = y_variance
        else:
            features['y_position_variance'] = 0

        return features

    def _extract_pattern_features(self, text: str) -> Dict[str, float]:
        """Extract pattern-based features (label presence, structure)."""
        features = {}

        # Two-column strategy patterns
        features['has_from_to'] = 1 if ('From:' in text and 'To:' in text) else 0
        features['has_bill_from_to'] = 1 if ('Bill from:' in text or 'Bill to:' in text) else 0

        # Single-column strategy patterns
        features['has_sender_recipient'] = 1 if ('Sender:' in text or 'Recipient:' in text) else 0
        features['has_german_labels'] = 1 if ('Absender:' in text or 'Empfänger:' in text) else 0

        # Company-specific patterns
        features['has_deutsche_bahn'] = 1 if ('Deutsche Bahn' in text or 'DB Vertrieb' in text) else 0

        # General patterns
        features['has_invoice_keyword'] = 1 if ('invoice' in text.lower() or 'rechnung' in text.lower()) else 0
        features['has_date_pattern'] = 1 if any(c.isdigit() for c in text) and '/' in text or '-' in text else 0

        # Punctuation density (structured documents have more colons, commas)
        if text:
            features['colon_density'] = text.count(':') / len(text)
            features['comma_density'] = text.count(',') / len(text)
            features['period_density'] = text.count('.') / len(text)
        else:
            features['colon_density'] = 0
            features['comma_density'] = 0
            features['period_density'] = 0

        return features

    def _extract_table_features(self, page) -> Dict[str, float]:
        """Extract table-related features."""
        features = {}

        try:
            tables = page.find_tables()
            features['has_tables'] = 1 if tables else 0
            features['table_count'] = len(tables)

            if tables:
                # Table size (cells)
                total_cells = sum(len(table.rows) * len(table.rows[0]) if table.rows else 0 for table in tables)
                features['total_table_cells'] = total_cells
            else:
                features['total_table_cells'] = 0
        except:
            features['has_tables'] = 0
            features['table_count'] = 0
            features['total_table_cells'] = 0

        return features

    def _empty_features(self) -> Dict[str, float]:
        """Return empty feature dict with zero values."""
        return {
            'line_count': 0,
            'non_empty_line_count': 0,
            'char_count': 0,
            'word_count': 0,
            'text_density': 0,
            'avg_line_length': 0,
            'max_line_length': 0,
            'min_line_length': 0,
            'line_length_variance': 0,
            'has_two_columns': 0,
            'x_position_variance': 0,
            'y_position_variance': 0,
            'has_from_to': 0,
            'has_bill_from_to': 0,
            'has_sender_recipient': 0,
            'has_german_labels': 0,
            'has_deutsche_bahn': 0,
            'has_invoice_keyword': 0,
            'has_date_pattern': 0,
            'colon_density': 0,
            'comma_density': 0,
            'period_density': 0,
            'has_tables': 0,
            'table_count': 0,
            'total_table_cells': 0,
        }

    def get_feature_names(self) -> List[str]:
        """Get list of all feature names in order."""
        return list(self._empty_features().keys())
