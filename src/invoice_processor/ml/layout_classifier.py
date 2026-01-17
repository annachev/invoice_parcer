"""
Layout classification for invoice parsing strategy selection.

Uses lightweight sklearn classifier to predict invoice layout type
and optimize parsing strategy selection.
"""

import pickle
import logging
from typing import Optional, Dict
from pathlib import Path
import numpy as np

from ..core.logging_config import get_logger
from .layout_features import LayoutFeatureExtractor

logger = get_logger(__name__)


class LayoutClassifier:
    """
    Classify invoice layout to optimize strategy selection.

    Layout types:
    - 'two_column': Two-column layout (e.g., Anthropic invoices)
    - 'single_column': Single-column with labels (e.g., simple invoices)
    - 'company_specific': Known company format (e.g., Deutsche Bahn)
    - 'unstructured': No clear structure (use fallback patterns)
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the layout classifier.

        Args:
            model_path: Path to trained sklearn model (pickle file)
                       If None, uses rule-based classification
        """
        self.model_path = model_path
        self.model = None
        self.feature_extractor = LayoutFeatureExtractor()
        self.feature_names = self.feature_extractor.get_feature_names()

        if model_path and Path(model_path).exists():
            self._load_model(model_path)
        else:
            logger.info("No trained model found, using rule-based classification")

    def _load_model(self, model_path: str):
        """Load trained sklearn model from pickle file."""
        try:
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            logger.info(f"Loaded layout classifier from {model_path}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.model = None

    def predict(self, pdf_path: str) -> str:
        """
        Predict layout type for an invoice.

        Args:
            pdf_path: Path to PDF invoice

        Returns:
            Layout type: 'two_column', 'single_column', 'company_specific', or 'unstructured'
        """
        # Extract features
        features = self.feature_extractor.extract(pdf_path)

        # Use ML model if available
        if self.model is not None:
            try:
                # Convert features to array in correct order
                feature_array = np.array([features[name] for name in self.feature_names]).reshape(1, -1)
                prediction = self.model.predict(feature_array)[0]
                logger.debug(f"ML predicted layout: {prediction}")
                return prediction
            except Exception as e:
                logger.warning(f"ML prediction failed, using rule-based: {e}")

        # Fallback to rule-based classification
        return self._rule_based_classify(features)

    def predict_with_confidence(self, pdf_path: str) -> tuple:
        """
        Predict layout type with confidence score.

        Args:
            pdf_path: Path to PDF invoice

        Returns:
            Tuple of (layout_type, confidence)
        """
        features = self.feature_extractor.extract(pdf_path)

        if self.model is not None and hasattr(self.model, 'predict_proba'):
            try:
                feature_array = np.array([features[name] for name in self.feature_names]).reshape(1, -1)
                prediction = self.model.predict(feature_array)[0]
                probabilities = self.model.predict_proba(feature_array)[0]
                confidence = max(probabilities)
                logger.debug(f"ML predicted: {prediction} (confidence: {confidence:.2f})")
                return prediction, confidence
            except Exception as e:
                logger.warning(f"ML prediction failed: {e}")

        # Rule-based fallback
        layout = self._rule_based_classify(features)
        return layout, 0.8  # Rule-based has moderate confidence

    def _rule_based_classify(self, features: Dict[str, float]) -> str:
        """
        Rule-based layout classification using feature patterns.

        Args:
            features: Extracted feature dictionary

        Returns:
            Layout type
        """
        # Company-specific (highest priority)
        if features.get('has_deutsche_bahn', 0) > 0:
            logger.debug("Rule-based: company_specific (Deutsche Bahn)")
            return 'company_specific'

        # Two-column layout
        if (features.get('has_from_to', 0) > 0 or
            features.get('has_bill_from_to', 0) > 0 or
            features.get('has_two_columns', 0) > 0):
            logger.debug("Rule-based: two_column")
            return 'two_column'

        # Single-column with labels
        if (features.get('has_sender_recipient', 0) > 0 or
            features.get('has_german_labels', 0) > 0):
            logger.debug("Rule-based: single_column")
            return 'single_column'

        # Structured documents (tables, high colon density)
        if (features.get('has_tables', 0) > 0 or
            features.get('colon_density', 0) > 0.01):
            # Likely has some structure
            if features.get('line_length_variance', 0) < 1000:
                logger.debug("Rule-based: single_column (structured)")
                return 'single_column'

        # Default: unstructured
        logger.debug("Rule-based: unstructured")
        return 'unstructured'

    def get_strategy_order(self, layout_type: str) -> list:
        """
        Get recommended parsing strategy order for a layout type.

        Args:
            layout_type: Layout type from predict()

        Returns:
            List of strategy names in recommended order
        """
        strategy_map = {
            'two_column': ['TwoColumnStrategy', 'SingleColumnLabelStrategy', 'CompanySpecificStrategy', 'PatternFallbackStrategy'],
            'single_column': ['SingleColumnLabelStrategy', 'TwoColumnStrategy', 'CompanySpecificStrategy', 'PatternFallbackStrategy'],
            'company_specific': ['CompanySpecificStrategy', 'SingleColumnLabelStrategy', 'TwoColumnStrategy', 'PatternFallbackStrategy'],
            'unstructured': ['PatternFallbackStrategy', 'SingleColumnLabelStrategy', 'TwoColumnStrategy', 'CompanySpecificStrategy'],
        }

        return strategy_map.get(layout_type, strategy_map['unstructured'])
