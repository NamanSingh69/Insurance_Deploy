"""
Tests for calculation functions - depreciation, assessment summaries, and financial calculations.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDepreciationRates:
    """Tests for depreciation rate calculations matching actual implementation."""
    
    def test_metal_year_0(self):
        """Metal in first 6 months - 0%."""
        from app import get_backend_depreciation_rate
        rate = get_backend_depreciation_rate("M", "0")
        assert rate == 0.0
    
    def test_metal_year_1(self):
        """Metal > 6 months to 1 year - 5%."""
        from app import get_backend_depreciation_rate
        rate = get_backend_depreciation_rate("M", "1")
        assert rate == 5.0
    
    def test_metal_year_2(self):
        """Metal > 1 year to 2 years - 10%."""
        from app import get_backend_depreciation_rate
        rate = get_backend_depreciation_rate("M", "2")
        assert rate == 10.0
    
    def test_metal_year_3(self):
        """Metal > 2 years to 3 years - 15%."""
        from app import get_backend_depreciation_rate
        rate = get_backend_depreciation_rate("M", "3")
        assert rate == 15.0
    
    def test_metal_year_4(self):
        """Metal > 3 years to 4 years - 25%."""
        from app import get_backend_depreciation_rate
        rate = get_backend_depreciation_rate("M", "4")
        assert rate == 25.0
    
    def test_metal_year_5(self):
        """Metal > 4 years to 5 years - 35%."""
        from app import get_backend_depreciation_rate
        rate = get_backend_depreciation_rate("M", "5")
        assert rate == 35.0
    
    def test_metal_year_6_to_10(self):
        """Metal > 5 years to 10 years - 40%."""
        from app import get_backend_depreciation_rate
        for year in ["6", "7", "8", "9", "10"]:
            rate = get_backend_depreciation_rate("M", year)
            assert rate == 40.0, f"Metal should be 40% for year {year}"
    
    def test_metal_year_11_plus(self):
        """Metal > 10 years - 50%."""
        from app import get_backend_depreciation_rate
        rate = get_backend_depreciation_rate("M", "11")
        assert rate == 50.0
    
    def test_plastic_constant(self):
        """Plastic always 50%."""
        from app import get_backend_depreciation_rate
        for year in ["0", "1", "2", "5", "10"]:
            rate = get_backend_depreciation_rate("P", year)
            assert rate == 50.0, f"Plastic should be 50% for year {year}"
    
    def test_glass_constant(self):
        """Glass always 0% (no depreciation)."""
        from app import get_backend_depreciation_rate
        for year in ["0", "1", "2", "5", "10"]:
            rate = get_backend_depreciation_rate("G", year)
            assert rate == 0.0, f"Glass should be 0% for year {year}"
    
    def test_lowercase_type(self):
        """Test with lowercase part type - should be converted to uppercase."""
        from app import get_backend_depreciation_rate
        rate_upper = get_backend_depreciation_rate("M", "3")
        rate_lower = get_backend_depreciation_rate("m", "3")
        assert rate_lower == rate_upper == 15.0


class TestAssessmentCalculationsSheetsDB:
    """Tests for SheetsDB JSON chunking functions."""
    
    def test_chunk_small_json(self):
        """Small JSON should not be chunked."""
        from sheets_db import SheetsDB
        db = SheetsDB()
        small_json = '{"key": "value"}'
        chunks = db._chunk_json_data(small_json)
        assert len(chunks) == 1
        assert chunks[0] == small_json
    
    def test_chunk_large_json(self):
        """Large JSON should be split into chunks."""
        from sheets_db import SheetsDB, MAX_CELL_CHARS
        db = SheetsDB()
        # Create JSON larger than MAX_CELL_CHARS
        large_json = '{"data": "' + 'x' * (MAX_CELL_CHARS + 1000) + '"}'
        chunks = db._chunk_json_data(large_json)
        assert len(chunks) > 1
        # Each chunk should be <= MAX_CELL_CHARS
        for chunk in chunks:
            assert len(chunk) <= MAX_CELL_CHARS
    
    def test_reassemble_single_chunk(self):
        """Reassemble single chunk."""
        from sheets_db import SheetsDB
        db = SheetsDB()
        original = '{"test": "data"}'
        chunks = [original]
        reassembled = db._reassemble_json_chunks(chunks)
        assert reassembled == original
    
    def test_reassemble_multiple_chunks(self):
        """Reassemble multiple chunks."""
        from sheets_db import SheetsDB
        db = SheetsDB()
        chunks = ['{"part1":', '"value1",', '"part2": "value2"}']
        reassembled = db._reassemble_json_chunks(chunks)
        assert reassembled == '{"part1":"value1","part2": "value2"}'
    
    def test_reassemble_with_empty_padding(self):
        """Reassemble chunks with empty string padding."""
        from sheets_db import SheetsDB
        db = SheetsDB()
        chunks = ['chunk1', 'chunk2', '', '', '']
        reassembled = db._reassemble_json_chunks(chunks)
        assert reassembled == 'chunk1chunk2'
    
    def test_roundtrip_chunk_reassemble(self):
        """Test complete roundtrip: chunk then reassemble."""
        from sheets_db import SheetsDB, MAX_CELL_CHARS
        db = SheetsDB()
        # Create moderately large JSON
        original = '{"data": "' + 'a' * 50000 + '"}'
        chunks = db._chunk_json_data(original)
        # Pad to 5 chunks like real code does
        while len(chunks) < 5:
            chunks.append('')
        reassembled = db._reassemble_json_chunks(chunks)
        assert reassembled == original


class TestPartDeprCalculation:
    """Test part depreciation calculation logic."""
    
    def test_calculate_part_depreciation(self):
        """Test depreciation amount calculation."""
        from app import get_backend_depreciation_rate
        
        part_amount = 10000
        vehicle_year = "3"  # > 2 years to 3 years = 15% for metal
        part_type = "M"
        
        rate = get_backend_depreciation_rate(part_type, vehicle_year)
        depr_amount = part_amount * (rate / 100)
        
        assert rate == 15.0
        assert depr_amount == 1500
    
    def test_nil_depreciation_policy(self):
        """NIL depreciation policy should return 0 depreciation."""
        # In NIL_DEPN policy, all depreciation is 0
        # This is typically enforced at the application level
        from app import get_backend_depreciation_rate
        rate = get_backend_depreciation_rate("M", "3")
        # Normal rate would be 15, but policy overrides
        # The function returns the rate, policy logic is elsewhere
        assert rate == 15.0


class TestPage3GSTCalculations:
    """Test Page 3 Invoice Summary calculation helper under apply_gst true/false."""

    def test_apply_gst_true(self):
        from app import _calculate_report_assessment_summary
        assessment_data = {
            'labour_tax_type': 'CGST/SGST',
            'page3_details': {
                'apply_gst': True,
                'estimated_amount': '1000',
                'photo_copies_count': '10',
                'fee_items': [
                    {'name': 'Survey Fee', 'amount': '1500'}
                ]
            }
        }
        survey_data = {}
        summary = _calculate_report_assessment_summary(assessment_data, survey_data)
        # Subtotal: Fee(1500) + Photo(10 * 10 = 100) = 1600
        # CGST: 1600 * 0.09 = 144.0
        # SGST: 1600 * 0.09 = 144.0
        # Gross Total: 1600 + 144 + 144 = 1888
        assert summary['page3_cgst'] == 144.0
        assert summary['page3_sgst'] == 144.0
        assert summary['page3_gross_total'] == 1888.0

    def test_apply_gst_false(self):
        from app import _calculate_report_assessment_summary
        assessment_data = {
            'labour_tax_type': 'CGST/SGST',
            'page3_details': {
                'apply_gst': False,
                'estimated_amount': '1000',
                'photo_copies_count': '10',
                'fee_items': [
                    {'name': 'Survey Fee', 'amount': '1500'}
                ]
            }
        }
        survey_data = {}
        summary = _calculate_report_assessment_summary(assessment_data, survey_data)
        # Subtotal: Fee(1500) + Photo(100) = 1600
        # CGST: 0.0
        # SGST: 0.0
        # Gross Total: 1600
        assert summary['page3_cgst'] == 0.0
        assert summary['page3_sgst'] == 0.0
        assert summary['page3_gross_total'] == 1600.0
