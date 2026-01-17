#!/usr/bin/env python3
"""
Train layout classifier on labeled invoice samples.

This script trains a lightweight sklearn classifier to predict invoice layout types.

Usage:
    1. Create labeled_invoices.csv with columns: pdf_path, layout_type
    2. Run: python3 scripts/train_layout_classifier.py

Layout types:
    - two_column: Two-column layout (Anthropic-style)
    - single_column: Single-column with labels
    - company_specific: Known company format (Deutsche Bahn)
    - unstructured: No clear structure
"""

import sys
import csv
import pickle
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invoice_processor.ml.layout_features import LayoutFeatureExtractor
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
import numpy as np


def load_labeled_data(csv_path: str):
    """
    Load labeled invoice data from CSV.

    CSV format:
        pdf_path,layout_type
        invoices/pending/invoice1.pdf,two_column
        invoices/pending/invoice2.pdf,single_column
        ...

    Args:
        csv_path: Path to CSV file

    Returns:
        List of (pdf_path, layout_type) tuples
    """
    data = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pdf_path = row['pdf_path']
            layout_type = row['layout_type']

            # Validate layout type
            valid_types = ['two_column', 'single_column', 'company_specific', 'unstructured']
            if layout_type not in valid_types:
                print(f"Warning: Invalid layout type '{layout_type}' for {pdf_path}, skipping")
                continue

            # Check file exists
            if not Path(pdf_path).exists():
                print(f"Warning: PDF not found: {pdf_path}, skipping")
                continue

            data.append((pdf_path, layout_type))

    return data


def extract_features_batch(pdf_paths: list):
    """Extract features from multiple PDFs."""
    extractor = LayoutFeatureExtractor()
    feature_names = extractor.get_feature_names()

    X = []
    for pdf_path in pdf_paths:
        print(f"Extracting features from {Path(pdf_path).name}...")
        features = extractor.extract(pdf_path)
        # Convert to array in consistent order
        feature_array = [features[name] for name in feature_names]
        X.append(feature_array)

    return np.array(X), feature_names


def train_classifier(X, y, feature_names):
    """Train Random Forest classifier."""
    print(f"\nTraining classifier on {len(X)} samples...")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Train Random Forest (fast, accurate, interpretable)
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight='balanced'  # Handle imbalanced classes
    )

    clf.fit(X_train, y_train)

    # Evaluate
    print("\n=== Training Set Performance ===")
    train_score = clf.score(X_train, y_train)
    print(f"Accuracy: {train_score:.3f}")

    print("\n=== Test Set Performance ===")
    test_score = clf.score(X_test, y_test)
    print(f"Accuracy: {test_score:.3f}")

    # Cross-validation
    print("\n=== Cross-Validation (5-fold) ===")
    cv_scores = cross_val_score(clf, X, y, cv=5)
    print(f"Scores: {cv_scores}")
    print(f"Mean: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")

    # Detailed classification report
    y_pred = clf.predict(X_test)
    print("\n=== Classification Report ===")
    print(classification_report(y_test, y_pred))

    print("\n=== Confusion Matrix ===")
    print(confusion_matrix(y_test, y_pred))

    # Feature importance
    print("\n=== Top 10 Most Important Features ===")
    importances = clf.feature_importances_
    indices = np.argsort(importances)[::-1][:10]
    for i, idx in enumerate(indices, 1):
        print(f"{i}. {feature_names[idx]}: {importances[idx]:.4f}")

    return clf


def save_model(clf, output_path: str):
    """Save trained model to pickle file."""
    with open(output_path, 'wb') as f:
        pickle.dump(clf, f)
    print(f"\nModel saved to: {output_path}")


def main():
    """Main training script."""
    print("=" * 60)
    print("Layout Classifier Training Script")
    print("=" * 60)

    # Check for labeled data
    csv_path = "labeled_invoices.csv"
    if not Path(csv_path).exists():
        print(f"\nError: {csv_path} not found!")
        print("\nPlease create labeled_invoices.csv with format:")
        print("  pdf_path,layout_type")
        print("  invoices/pending/invoice1.pdf,two_column")
        print("  invoices/pending/invoice2.pdf,single_column")
        print("  ...")
        print("\nLayout types:")
        print("  - two_column: Two-column layout (Anthropic-style)")
        print("  - single_column: Single-column with labels")
        print("  - company_specific: Known company format")
        print("  - unstructured: No clear structure")
        sys.exit(1)

    # Load labeled data
    print(f"\nLoading labeled data from {csv_path}...")
    data = load_labeled_data(csv_path)

    if len(data) < 10:
        print(f"\nWarning: Only {len(data)} samples found. Recommended: 50-100 samples.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)

    print(f"Loaded {len(data)} labeled invoices")

    # Count per class
    from collections import Counter
    class_counts = Counter(layout_type for _, layout_type in data)
    print("\nClass distribution:")
    for layout_type, count in class_counts.items():
        print(f"  {layout_type}: {count}")

    # Extract features
    print("\n" + "=" * 60)
    print("Extracting Features")
    print("=" * 60)

    pdf_paths = [pdf for pdf, _ in data]
    labels = [layout for _, layout in data]

    X, feature_names = extract_features_batch(pdf_paths)
    y = np.array(labels)

    print(f"\nFeature matrix shape: {X.shape}")
    print(f"Number of features: {len(feature_names)}")

    # Train classifier
    print("\n" + "=" * 60)
    print("Training Classifier")
    print("=" * 60)

    clf = train_classifier(X, y, feature_names)

    # Save model
    output_path = "src/invoice_processor/ml/models/layout_classifier.pkl"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    save_model(clf, output_path)

    print("\n" + "=" * 60)
    print("Training Complete!")
    print("=" * 60)
    print(f"\nTo use the trained model, update config.yaml:")
    print(f"  ml:")
    print(f"    layout:")
    print(f"      enabled: true")
    print(f"      model_path: \"{output_path}\"")


if __name__ == "__main__":
    main()
