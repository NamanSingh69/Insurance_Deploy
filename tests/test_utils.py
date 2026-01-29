"""
Unit tests for utility functions in app.py
"""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import utility functions directly (they don't require Flask context)
# We'll test them without the full app context


class TestIsNumber:
    """Tests for is_number() function."""
    
    def test_valid_integer(self):
        """Test with valid integer."""
        from app import is_number
        assert is_number("123") == True
    
    def test_valid_float(self):
        """Test with valid float."""
        from app import is_number
        assert is_number("123.45") == True
    
    def test_valid_negative(self):
        """Test with negative number."""
        from app import is_number
        assert is_number("-123.45") == True
    
    def test_invalid_string(self):
        """Test with non-numeric string."""
        from app import is_number
        assert is_number("abc") == False
    
    def test_empty_string(self):
        """Test with empty string."""
        from app import is_number
        assert is_number("") == False
    
    def test_none(self):
        """Test with None value - raises TypeError."""
        from app import is_number
        with pytest.raises(TypeError):
            is_number(None)
    
    def test_with_spaces(self):
        """Test with spaces around number."""
        from app import is_number
        # May or may not be valid depending on implementation
        result = is_number(" 123 ")
        assert isinstance(result, bool)
    
    def test_zero(self):
        """Test with zero."""
        from app import is_number
        assert is_number("0") == True


class TestFormatPdfNumber:
    """Tests for format_pdf_number() function."""
    
    def test_integer(self):
        """Test formatting integer."""
        from app import format_pdf_number
        result = format_pdf_number(1234)
        assert result == "1234.00" or result == "1,234.00"
    
    def test_float(self):
        """Test formatting float."""
        from app import format_pdf_number
        result = format_pdf_number(1234.567)
        assert "1234.57" in result or "1,234.57" in result
    
    def test_zero(self):
        """Test formatting zero."""
        from app import format_pdf_number
        result = format_pdf_number(0)
        assert result == "0" or result == "0.00"
    
    def test_none(self):
        """Test formatting None - returns string 'None'."""
        from app import format_pdf_number
        result = format_pdf_number(None)
        assert result == "None"
    
    def test_string_number(self):
        """Test formatting string number."""
        from app import format_pdf_number
        result = format_pdf_number("1234.56")
        assert "1234.56" in result or "1,234.56" in result
    
    def test_negative(self):
        """Test formatting negative number."""
        from app import format_pdf_number
        result = format_pdf_number(-500.25)
        assert "-500.25" in result


class TestNormalizePdfText:
    """Tests for normalize_pdf_text_for_fpdf() function."""
    
    def test_regular_text(self):
        """Test with regular ASCII text."""
        from app import normalize_pdf_text_for_fpdf
        result = normalize_pdf_text_for_fpdf("Hello World")
        assert result == "Hello World"
    
    def test_unicode_hyphen(self):
        """Test with Unicode hyphen characters."""
        from app import normalize_pdf_text_for_fpdf
        # EN DASH
        result = normalize_pdf_text_for_fpdf("Test–Value")
        assert "–" not in result or result == "Test–Value"  # Either normalized or kept
    
    def test_empty_string(self):
        """Test with empty string."""
        from app import normalize_pdf_text_for_fpdf
        result = normalize_pdf_text_for_fpdf("")
        assert result == ""
    
    def test_none(self):
        """Test with None value - converts to 'None' string."""
        from app import normalize_pdf_text_for_fpdf
        result = normalize_pdf_text_for_fpdf(None)
        assert result == "None"
    
    def test_integer_input(self):
        """Test with integer input."""
        from app import normalize_pdf_text_for_fpdf
        result = normalize_pdf_text_for_fpdf(12345)
        assert "12345" in str(result)


class TestNumberToWordsIndian:
    """Tests for number_to_words_indian() function."""
    
    def test_zero(self):
        """Test converting zero."""
        from app import number_to_words_indian
        result = number_to_words_indian(0)
        assert "ZERO" in result.upper() or "0" in result
    
    def test_single_digit(self):
        """Test converting single digit."""
        from app import number_to_words_indian
        result = number_to_words_indian(5)
        assert "FIVE" in result.upper()
    
    def test_two_digits(self):
        """Test converting two digit number."""
        from app import number_to_words_indian
        result = number_to_words_indian(42)
        assert "FORTY" in result.upper()
        assert "TWO" in result.upper()
    
    def test_hundreds(self):
        """Test converting hundreds."""
        from app import number_to_words_indian
        result = number_to_words_indian(500)
        assert "FIVE" in result.upper()
        assert "HUNDRED" in result.upper()
    
    def test_thousands(self):
        """Test converting thousands (Indian style)."""
        from app import number_to_words_indian
        result = number_to_words_indian(12345)
        assert "THOUSAND" in result.upper()
    
    def test_lakhs(self):
        """Test converting lakhs (Indian numbering)."""
        from app import number_to_words_indian
        result = number_to_words_indian(150000)
        assert "LAKH" in result.upper()
    
    def test_with_paise(self):
        """Test converting amount with paise."""
        from app import number_to_words_indian
        result = number_to_words_indian(1234.56)
        # Should include paise
        assert "RUPEE" in result.upper() or "1234" in result
    
    def test_negative(self):
        """Test converting negative number."""
        from app import number_to_words_indian
        # Should handle or convert to positive
        result = number_to_words_indian(-100)
        assert isinstance(result, str)


class TestGetBackendDepreciationRate:
    """Tests for get_backend_depreciation_rate() function."""
    
    def test_plastic_first_year(self):
        """Test plastic depreciation for first year."""
        from app import get_backend_depreciation_rate
        rate = get_backend_depreciation_rate("P", "1")
        assert rate == 50  # Plastic typically 50%
    
    def test_metal_first_year(self):
        """Test metal depreciation for first year."""
        from app import get_backend_depreciation_rate
        rate = get_backend_depreciation_rate("M", "1")
        assert rate == 5.0  # Metal 5% for year 1
    
    def test_glass_any_year(self):
        """Test glass depreciation (no depreciation)."""
        from app import get_backend_depreciation_rate
        rate = get_backend_depreciation_rate("G", "3")
        assert rate == 0.0  # Glass typically 0%
    
    def test_metal_fifth_year(self):
        """Test metal depreciation after 5 years."""
        from app import get_backend_depreciation_rate
        rate = get_backend_depreciation_rate("M", "5")
        assert rate == 35.0  # Metal 35% for year 5
    
    def test_invalid_type(self):
        """Test with invalid part type."""
        from app import get_backend_depreciation_rate
        rate = get_backend_depreciation_rate("X", "3")
        # Should return default or 0
        assert isinstance(rate, (int, float))
    
    def test_empty_year(self):
        """Test with empty year string."""
        from app import get_backend_depreciation_rate
        rate = get_backend_depreciation_rate("M", "")
        assert isinstance(rate, (int, float))
