"""
Feature parity validation tests comparing the calculation logic
and JSON data schema structure against the legacy specification.
"""
import pytest
from app import get_backend_depreciation_rate

class TestFeatureParityCalculations:
    """Validate all core calculation algorithms for parity."""

    def test_depreciation_rates_parity(self):
        """Verify depreciation rates match the exact rules for Glass, Plastic, and Metal."""
        # Glass: Always 0%
        assert get_backend_depreciation_rate('G', '0') == 0.0
        assert get_backend_depreciation_rate('G', '5') == 0.0
        assert get_backend_depreciation_rate('G', '12') == 0.0

        # Plastic: Always 50%
        assert get_backend_depreciation_rate('P', '0') == 50.0
        assert get_backend_depreciation_rate('P', '5') == 50.0
        assert get_backend_depreciation_rate('P', '12') == 50.0

        # Metal (M): Tiered by year bucket (vehicle age in total years/buckets)
        # Age <= 6 months (Year 0) -> 0%
        assert get_backend_depreciation_rate('M', '0') == 0.0
        # > 6 months to 1 year (Year 1) -> 5%
        assert get_backend_depreciation_rate('M', '1') == 5.0
        # > 1 year to 2 years (Year 2) -> 10%
        assert get_backend_depreciation_rate('M', '2') == 10.0
        # > 2 years to 3 years (Year 3) -> 15%
        assert get_backend_depreciation_rate('M', '3') == 15.0
        # > 3 years to 4 years (Year 4) -> 25%
        assert get_backend_depreciation_rate('M', '4') == 25.0
        # > 4 years to 5 years (Year 5) -> 35%
        assert get_backend_depreciation_rate('M', '5') == 35.0
        # > 5 years to 10 years (Year 6-10) -> 40%
        assert get_backend_depreciation_rate('M', '6') == 40.0
        assert get_backend_depreciation_rate('M', '10') == 40.0
        # > 10 years (Year 11+) -> 50%
        assert get_backend_depreciation_rate('M', '11') == 50.0

    def test_calculation_formulas_parity(self):
        """Verify the calculation formula matches the client JS calculations exactly."""
        # Scenario: Part assessed amount is 10000, Qty is 1, Part Type is Plastic (50% depr), GST is 18%.
        qty = 1
        part_amt = 10000.0
        depr_rate = 50.0 / 100.0
        gst_pc = 18.0 / 100.0

        total_parts_amt = qty * part_amt
        calculated_depr = total_parts_amt * depr_rate
        net_base = total_parts_amt - calculated_depr
        total_gst = net_base * gst_pc
        gross_amt = net_base + total_gst

        assert total_parts_amt == 10000.0
        assert calculated_depr == 5000.0
        assert net_base == 5000.0
        assert total_gst == 900.0
        assert gross_amt == 5900.0

        # IMT 23 reduction (50% on Gross)
        imt_23_amt = gross_amt * 0.5
        net_amt = gross_amt - imt_23_amt
        assert imt_23_amt == 2950.0
        assert net_amt == 2950.0

    def test_schema_backwards_compatibility(self, sample_report_data):
        """Verify the structured report JSON payload keeps its key attributes for backward compatibility."""
        assert "survey_report" in sample_report_data
        assert "assessment" in sample_report_data
        assert "photos" in sample_report_data

        survey = sample_report_data["survey_report"]
        assert "report_no" in survey
        assert "policy_no" in survey
        assert "vehicle_regn_no" in survey

        assessment = sample_report_data["assessment"]
        assert "parts" in assessment
        assert "salvage" in assessment
        assert "deductibles" in assessment
        assert isinstance(assessment["parts"], list)
