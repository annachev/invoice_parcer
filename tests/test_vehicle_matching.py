#!/usr/bin/env python3
"""
Unit Tests for Vehicle Matching
Tests the VehicleMatcher class with various matching scenarios.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from invoice_processor.utils.vehicle_matcher import VehicleMatcher
from invoice_processor.core.exceptions import ConfigurationError


class TestVehicleMatcher:
    """Test suite for VehicleMatcher class."""

    @pytest.fixture
    def matcher(self):
        """Create a matcher instance with test database."""
        excel_path = "vehicles/vehicles.xlsx"
        return VehicleMatcher(excel_path, threshold=0.9)

    @pytest.fixture
    def low_threshold_matcher(self):
        """Create a matcher with lower threshold for testing edge cases."""
        excel_path = "vehicles/vehicles.xlsx"
        return VehicleMatcher(excel_path, threshold=0.75)

    def test_exact_match(self, matcher):
        """Test exact match returns 100% score."""
        matched_name, vehicle_id, score = matcher.match_recipient("Acme Corporation")

        assert matched_name == "Acme Corporation"
        assert vehicle_id == "V001"
        assert score == 1.0
        print(f"✓ Exact match: '{matched_name}' (ID: {vehicle_id}, score: {score:.2%})")

    def test_fuzzy_match_above_threshold(self, matcher):
        """Test fuzzy match above 90% threshold."""
        # Use a name that will match above 90% - just a typo
        matched_name, vehicle_id, score = matcher.match_recipient("Acme Corporaton")  # Missing 'i'

        # Should match "Acme Corporation" with high score
        assert matched_name == "Acme Corporation"
        assert vehicle_id == "V001"
        assert score >= 0.9
        print(f"✓ Fuzzy match (high): '{matched_name}' (ID: {vehicle_id}, score: {score:.2%})")

    def test_fuzzy_match_below_threshold(self, matcher):
        """Test fuzzy match below 90% threshold returns original."""
        matched_name, vehicle_id, score = matcher.match_recipient("Random Company XYZ")

        # Should keep original and return N/A
        assert matched_name == "Random Company XYZ"
        assert vehicle_id == "N/A"
        assert score < 0.9
        print(f"✓ No match (low score): '{matched_name}' (ID: {vehicle_id}, score: {score:.2%})")

    def test_case_insensitive_matching(self, matcher):
        """Test that matching is case-insensitive."""
        # Test uppercase
        matched_name1, vehicle_id1, score1 = matcher.match_recipient("ACME CORPORATION")
        assert matched_name1 == "Acme Corporation"
        assert vehicle_id1 == "V001"

        # Test lowercase
        matched_name2, vehicle_id2, score2 = matcher.match_recipient("acme corporation")
        assert matched_name2 == "Acme Corporation"
        assert vehicle_id2 == "V001"

        # Test mixed case
        matched_name3, vehicle_id3, score3 = matcher.match_recipient("AcMe CoRpOrAtIoN")
        assert matched_name3 == "Acme Corporation"
        assert vehicle_id3 == "V001"

        print(f"✓ Case insensitive: All variants matched correctly")

    def test_partial_name_matching(self, low_threshold_matcher):
        """Test partial name matching with lower threshold."""
        matched_name, vehicle_id, score = low_threshold_matcher.match_recipient("Global Logistics")

        # Should match "Global Logistics GmbH" with lower threshold
        assert matched_name == "Global Logistics GmbH"
        assert vehicle_id == "V002"
        assert score >= 0.75
        print(f"✓ Partial match: '{matched_name}' (ID: {vehicle_id}, score: {score:.2%})")

    def test_empty_recipient(self, matcher):
        """Test empty recipient name returns N/A."""
        matched_name, vehicle_id, score = matcher.match_recipient("")

        assert matched_name == ""
        assert vehicle_id == "N/A"
        assert score == 0.0
        print(f"✓ Empty recipient: Returns N/A")

    def test_parsing_failed_recipient(self, matcher):
        """Test PARSING FAILED recipient returns N/A."""
        matched_name, vehicle_id, score = matcher.match_recipient("PARSING FAILED")

        assert matched_name == "PARSING FAILED"
        assert vehicle_id == "N/A"
        assert score == 0.0
        print(f"✓ PARSING FAILED: Returns N/A")

    def test_multiple_similar_names(self, matcher):
        """Test that best match is returned when multiple similar names exist."""
        # "Tech Solutions Inc" (without period) should match "Tech Solutions Inc." above 90%
        matched_name, vehicle_id, score = matcher.match_recipient("Tech Solutions Inc")

        assert matched_name == "Tech Solutions Inc."
        assert vehicle_id == "V003"
        assert score >= 0.9
        print(f"✓ Best match selected: '{matched_name}' (ID: {vehicle_id}, score: {score:.2%})")

    def test_missing_excel_file(self):
        """Test graceful handling of missing Excel file."""
        matcher = VehicleMatcher("nonexistent_file.xlsx", threshold=0.9)

        # Should raise ConfigurationError when trying to load
        with pytest.raises(ConfigurationError):
            matcher.load_vehicles()

        # Matching should return N/A after error
        assert matcher.enabled == False
        matched_name, vehicle_id, score = matcher.match_recipient("Any Company")
        assert vehicle_id == "N/A"
        print(f"✓ Missing file: Gracefully returns N/A")

    def test_threshold_boundary(self):
        """Test matching behavior right at threshold boundary."""
        matcher = VehicleMatcher("vehicles/vehicles.xlsx", threshold=0.90)

        # Find a match that's close to 90%
        matched_name, vehicle_id, score = matcher.match_recipient("Tech Solutions")

        if score >= 0.90:
            # Above threshold - should use matched name
            assert vehicle_id != "N/A"
            print(f"✓ At threshold: Match accepted (score: {score:.2%})")
        else:
            # Below threshold - should keep original
            assert vehicle_id == "N/A"
            print(f"✓ At threshold: Match rejected (score: {score:.2%})")

    def test_special_characters_in_name(self, matcher):
        """Test matching with special characters."""
        # Test with company that has special chars
        matched_name, vehicle_id, score = matcher.match_recipient("Deutsche Transportgesellschaft")

        # Should match "Deutsche Transportgesellschaft mbH"
        assert matched_name == "Deutsche Transportgesellschaft mbH"
        assert vehicle_id == "V004"
        print(f"✓ Special chars: '{matched_name}' (ID: {vehicle_id}, score: {score:.2%})")

    def test_lazy_loading(self, matcher):
        """Test that vehicles are loaded lazily on first use."""
        # Vehicles should be None initially
        assert matcher.vehicles is None

        # First match triggers loading
        matcher.match_recipient("Acme Corporation")
        assert matcher.vehicles is not None
        assert len(matcher.vehicles) > 0
        print(f"✓ Lazy loading: Database loaded on first use ({len(matcher.vehicles)} vehicles)")

    def test_reload_functionality(self, matcher):
        """Test reload clears cache and allows fresh load."""
        # Load initially
        matcher.match_recipient("Acme Corporation")
        assert matcher.vehicles is not None

        # Reload
        matcher.reload()
        assert matcher.vehicles is None

        # Should reload on next match
        matcher.match_recipient("Acme Corporation")
        assert matcher.vehicles is not None
        print(f"✓ Reload: Cache cleared and reloaded successfully")


def run_manual_tests():
    """Run manual tests with visual output."""
    print("\n" + "=" * 60)
    print("VEHICLE MATCHING UNIT TESTS")
    print("=" * 60)

    # Check if test database exists
    if not Path("vehicles/vehicles.xlsx").exists():
        print("\n✗ Error: Test database not found at vehicles/vehicles.xlsx")
        print("Run 'python scripts/create_test_vehicles.py' first")
        return False

    try:
        # Create test instance
        print("\nInitializing matcher...")
        matcher = VehicleMatcher("vehicles/vehicles.xlsx", threshold=0.9)

        # Test cases with expected results
        test_cases = [
            ("Acme Corporation", "V001", "exact match"),
            ("Acme Corporaton", "V001", "fuzzy match high (typo)"),
            ("Global Logistics GmbH", "V002", "exact match"),
            ("Tech Solutions Inc", "V003", "fuzzy match (missing period)"),
            ("Acme Corp", "N/A", "below threshold (72%)"),
            ("Random Company", "N/A", "no match"),
            ("", "N/A", "empty string"),
            ("PARSING FAILED", "N/A", "parsing failed"),
        ]

        print(f"\nRunning {len(test_cases)} test cases:")
        print("-" * 60)

        all_passed = True
        for recipient, expected_id, test_type in test_cases:
            matched_name, vehicle_id, score = matcher.match_recipient(recipient)

            passed = vehicle_id == expected_id
            all_passed = all_passed and passed

            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"\n{status} | {test_type}")
            print(f"  Input:    '{recipient}'")
            print(f"  Matched:  '{matched_name}'")
            print(f"  Vehicle:  {vehicle_id} (expected: {expected_id})")
            print(f"  Score:    {score:.2%}")

        print("\n" + "=" * 60)
        if all_passed:
            print("✓ ALL TESTS PASSED")
        else:
            print("✗ SOME TESTS FAILED")
        print("=" * 60 + "\n")

        return all_passed

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run manual tests with visual output
    success = run_manual_tests()

    # Run pytest if available
    try:
        print("\nRunning pytest suite...")
        exit_code = pytest.main([__file__, "-v", "--tb=short"])
        sys.exit(exit_code if exit_code == 0 and success else 1)
    except ImportError:
        print("\npytest not installed - skipping pytest suite")
        print("Install pytest with: pip install pytest")
        sys.exit(0 if success else 1)
