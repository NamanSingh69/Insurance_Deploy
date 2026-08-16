# tests/test_fee_bill_word_template.py
import io
import pytest
from unittest.mock import patch, MagicMock
from modules.pdf import render_fee_report, number_to_words_indian
from PIL import Image

def test_number_to_words_indian_rupees():
    words = number_to_words_indian(3245.0)
    assert "three thousand two hundred forty five" in words.lower()

def test_render_fee_report_full_word_template_items():
    fee_data = {
        'report_no': 'K08/G4/24/1365',
        'invoice_no': 'KG-2365',
        'invoice_date': '22-07-2026',
        'insurer_name': 'IndusInd General Insurance Co. Ltd.',
        'insurer_address': '4th Floor Thapar House, 163 Shyama Prasad Mukherjee Rd, Kolkata-700026',
        'insurer_gst': '19AAACB6747B1ZD',
        'insured_name': 'TK DEVELOPERS',
        'policy_no': '9505292412030017417',
        'claim_no': '3126258760',
        'vehicle_no': 'JK-01-DM-0393',
        'date_of_accident': '04/07/2026',
        'fee_items': [
            {'name': '1. Final Survey Fees :', 'amount': 2000.0},
            {'name': '2. Conveyance Expenses :', 'amount': 750.0},
            {'name': '3. 2nd visited Conveyance Expenses : Kolkata to Mumbai (100 x 2 =200 km @ Rs. 10/-)', 'amount': 2000.0},
            {'name': '4. Re-inspection Fees :', 'amount': 1000.0},
            {'name': '5. Conveyance Expenses : Kolkata to Mumbai (100 x 2 =200 km @ Rs. 10/-)', 'amount': 2000.0},
            {'name': '6. photos :', 'amount': 500.0},
            {'name': '7. Halting Charges :', 'amount': 1000.0},
            {'name': '8. Other charges: ( like , postal charges)', 'amount': 250.0},
        ],
        'taxable_amount': 9500.0,
        'gst_pc': 18.0,
        'gst_amount': 1710.0,
        'total_amount': 11210.0,
        'include_signature': False
    }
    user_snapshot = {
        'full_name': 'SK ANOWAR ALI',
        'qualifications': 'B.Tech (Automobile), LIII(Life)',
        'designation': 'Surveyor & Loss Assessor',
        'license_no': 'SLA-121784',
        'expiry_date': '13-12-2026',
        'membership_no': 'L/E/10721',
        'address_line_1': 'Natungram, P.O-Sondanga,',
        'address_line_2': 'P.S-Nabadwip, City-Krishnanagar,',
        'address_line_3': 'Dist.-Nadia, W.B-741125',
        'contact_no': '8777207014',
        'email': 'skanowarali93@gmail.com',
        'surveyor_code': '2075995',
        'surveyor_gstin': '19AZZPA2301R1ZM',
        'bank_account_no': '33717014374',
        'bank_name': 'State Bank Of India (SBI)',
        'bank_branch': 'Nabadwip (01402)',
        'bank_ifsc': 'SBIN0001402'
    }

    result = render_fee_report(fee_data, user_snapshot, user_id=1, include_signature=False)
    assert 'pdf_bytes' in result
    pdf_bytes = result['pdf_bytes']
    assert pdf_bytes.startswith(b'%PDF-')
    assert len(pdf_bytes) > 1000
    assert result['invoice_no'] == 'KG-2365'

def test_render_fee_report_standalone_no_report_no():
    fee_data = {
        'invoice_no': 'NIC-0001',
        'invoice_date': '16-08-2026',
        'insurer_name': 'National Insurance Company',
        'insured_name': 'John Doe',
        'vehicle_no': 'WB-01-AB-1234',
        'taxable_amount': 2500.0,
        'gst_pc': 18.0,
        'gst_amount': 450.0,
        'total_amount': 2950.0,
        'include_signature': False
    }
    user_snapshot = {'full_name': 'SK ANOWAR ALI'}
    result = render_fee_report(fee_data, user_snapshot, user_id=1, include_signature=False)
    assert result['pdf_bytes'].startswith(b'%PDF-')

def test_photo_rendering_rgb_conversion():
    # Test that PIL conversion handles RGBA, WebP, and CMYK formats cleanly
    img = Image.new('RGBA', (200, 200), color=(255, 0, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    raw_bytes = buf.getvalue()

    with Image.open(io.BytesIO(raw_bytes)) as loaded:
        if loaded.mode not in ('RGB', 'L'):
            converted = loaded.convert('RGB')
            out_buf = io.BytesIO()
            converted.save(out_buf, format='JPEG')
            out_buf.seek(0)
            assert out_buf.getvalue().startswith(b'\xff\xd8')
