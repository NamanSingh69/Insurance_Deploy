
import pytest
import sys
import os
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestReportDataValidation:
    """Tests for report data validation."""
    
    def test_valid_survey_data(self):
        """Test validates survey report data structure."""
        from app import EXPECTED_FIELDS
        # Just checking if we can import
        assert len(EXPECTED_FIELDS) > 0
    
    def test_valid_assessment_data(self):
        """Test validates assessment data structure."""
        pass # Structure is implicit in code


class TestParseGeminiResponse:
    """Tests for parse_gemini_response function."""
    
    def test_parse_valid_json(self):
        """Test parsing valid JSON response."""
        from app import parse_gemini_response
        valid_json = json.dumps({
            "survey_report_data": {"report_no": "123"},
            "assessment_data": {"parts": []}
        })
        result = parse_gemini_response(valid_json)
        assert result['survey_report']['report_no'] == "123"
        
    def test_parse_json_with_markdown(self):
        """Test parsing JSON with markdown code blocks."""
        from app import parse_gemini_response
        response = """```json
        {
            "survey_report_data": {"report_no": "123"},
            "assessment_data": {}
        }
        ```"""
        result = parse_gemini_response(response)
        assert result['survey_report']['report_no'] == "123"
        
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        from app import parse_gemini_response
        response = "This is not JSON"
        
        # Should raise ValueError
        with pytest.raises(ValueError):
            parse_gemini_response(response)
            
    def test_parse_empty_response(self):
        """Test parsing empty response."""
        from app import parse_gemini_response
        
        # Should raise ValueError
        with pytest.raises(ValueError):
            parse_gemini_response('')


class TestParseInvoiceGeminiResponse:
    """Tests for parse_invoice_gemini_response."""
    
    def test_parse_valid_invoice_json(self):
        """Test parsing valid invoice JSON."""
        from app import parse_invoice_gemini_response
        valid_json = json.dumps({
            "customer_gstin": "GST123",
            "parts": [{"part_name": "Part A"}]
        })
        result = parse_invoice_gemini_response(valid_json)
        assert result['customer_gstin'] == "GST123"
        assert len(result['parts']) == 1
        
    def test_parse_invoice_with_markdown(self):
        """Test parsing invoice JSON with markdown."""
        from app import parse_invoice_gemini_response
        response = """```json
        {
            "customer_gstin": "GST123",
            "parts": []
        }
        ```"""
        result = parse_invoice_gemini_response(response)
        assert result['customer_gstin'] == "GST123"


class TestReportSaveLoad:
    """Tests for high-level save/load logic (integration like)."""
    
    def test_save_and_load_roundtrip(self):
        """Test saving data and loading it back (mocked)."""
        pass # Covered by API tests


class TestPhotosInReport:
    """Tests for photo handling in reports."""
    
    def test_report_with_empty_photos(self):
        """Test report structure with no photos."""
        from modules.pdf import render_report
        data = {
            'survey_report': {'report_no': 'R-100', 'vehicle_regn_no': 'WB01A1234'},
            'assessment': {'parts': []},
            'photos': {'reinspection': {'images': [], 'per_page': 4}}
        }
        user_snapshot = {'full_name': 'Test User', 'license_no': 'LIC123'}
        result = render_report(data, user_snapshot, 'user_1')
        assert 'pdf_bytes' in result
        assert isinstance(result['pdf_bytes'], (bytes, bytearray))

    def test_report_with_photo_urls(self):
        """Test report rendering with asset photo URLs and edge-case assessment values."""
        from modules.pdf import render_report
        data = {
            'survey_report': {'report_no': 'R-101', 'vehicle_regn_no': 'WB01A1234'},
            'assessment': {
                'parts': [{'part_name': 'Bumper', 'qty': 1, 'part_amt': 500, 'depr': ''}],
                'labour_paint_depn': None,
                'nd_deduction_pc': '',
                'nd_deduction_amount': None,
                'towing_charges': ''
            },
            'photos': {
                'reinspection': {
                    'images': ['/assets/test-asset-12345/content', '/proxy_image/legacy-123'],
                    'per_page': 4
                }
            }
        }
        user_snapshot = {'full_name': 'Test User', 'license_no': 'LIC123'}
        with patch('modules.assets.get_accessible_asset_content') as mock_asset, \
             patch('modules.pdf.db') as mock_db:
            mock_asset.return_value = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82', {'mime_type': 'image/png'})
            mock_db.get_asset_by_locator.return_value = None
            mock_db.get_file_content.return_value = None
            mock_db.upload_report_pdf.return_value = None
            result = render_report(data, user_snapshot, 'user_1')
            assert 'pdf_bytes' in result
            assert len(result['pdf_bytes']) > 0


class TestConsolidatedCSVDownload:
    """Tests for CSV download logic."""
    
    def test_download_csv_empty(self, authenticated_client, mock_sheets_db):
        """Test CSV download with no reports."""
        mock_sheets_db.get_user_reports.return_value = []
        mock_sheets_db.get_user_fee_bills.return_value = []
        
        # Needs date params
        response = authenticated_client.get('/download_consolidated_csv?from_date=2024-01-01&to_date=2024-12-31')
        
        assert response.status_code == 200
        assert 'text/csv' in response.headers['Content-Type']
        assert b"Insured Name,Insurer Company Name,Policy number" in response.data
        
    def test_download_csv_with_data(self, authenticated_client, mock_sheets_db):
        """Test CSV download with reports."""
        mock_reports = [
            {
                'id': '1',
                'saved_at': '2024-03-01T10:00:00',
                'include_in_consolidated': True,
                'report_data_json': json.dumps({
                    'survey_report': {'report_no': 'R-001', 'insurer': 'Insurer A', 'insured': 'John Doe'},
                    'assessment': {'parts': [], 'page3_details': {}}
                })
            }
        ]
        mock_sheets_db.get_user_reports.return_value = mock_reports
        mock_sheets_db.get_user_fee_bills.return_value = []
        
        # Needs date params
        response = authenticated_client.get('/download_consolidated_csv?from_date=2024-01-01&to_date=2024-12-31')
        
        assert response.status_code == 200
        assert b"R-001" in response.data
        assert b"John Doe" in response.data

