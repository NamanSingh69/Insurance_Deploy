# modules/pdf.py
import os
import io
import base64
import uuid
import requests
import tempfile
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from fpdf.errors import FPDFException
from db import db
from modules.assets import get_owned_asset_content, get_accessible_asset_content

EXPECTED_FIELDS = [
    "report_no", "report_date", "policy_no", "claim_no", "policy_validity",
    "insurer", "insured", "insured_contact_name", "insured_contact_no", "hypothecation", "idv", "policy_type_label",
    "vehicle_regn_no", "vehicle_regn_date", "vehicle_chassis_no", "vehicle_engine_no",
    "vehicle_make_model", "vehicle_type_body", "vehicle_cf_validity", "vehicle_seating",
    "vehicle_bhp_cc", "vehicle_pre_accident_condition", "vehicle_ulw", "vehicle_rlw",
    "vehicle_permit_no", "vehicle_permit_type", "vehicle_permit_validity",
    "vehicle_route_area", "vehicle_tax_token", "vehicle_tax_validity",
    "vehicle_odometer", "vehicle_colour", "class_of_vehicle", "regn_cert_no", "vehicle_cc",
    "dl_name", "dl_no", "dl_issue_date", "dl_validity", "dl_issuing_authority",
    "dl_endorsement", "dl_type", "dl_dob",
    "doc_regn_cert", "doc_dl", "doc_tax_token", "doc_permit_compared",
    "doc_fitness_certificate", "doc_load_challan",
    "load_nature_packing", "load_weight_goods", "load_origin_destination",
    "load_lr_invoice_no", "load_transport_name", "load_date",
    "accident_datetime", "accident_assign_received", "accident_survey_date",
    "accident_place", "accident_survey_place",
    "police_reported_to", "police_diary_case_no", "police_date_reported",
    "tp_details", "accident_cause", "damages_extent", "remark",
    "tp_injury_loss", "injury_driver_occupant", "damages_consistent"
]

class UserSnapshot:
    def __init__(self, data):
        self.full_name = data.get('full_name', '')
        self.qualifications = data.get('qualifications', '')
        self.designation = data.get('designation', '')
        self.license_no = data.get('license_no', '')
        self.expiry_date = data.get('expiry_date', '')
        self.membership_no = data.get('membership_no', '')
        self.address_line_1 = data.get('address_line_1', '')
        self.address_line_2 = data.get('address_line_2', '')
        self.address_line_3 = data.get('address_line_3', '')
        self.contact_no = data.get('contact_no', '')
        self.email = data.get('email', '')


def _private_signature_path(user_id):
    """Materialize an owned signature briefly for FPDF without public static files."""
    if not user_id:
        return None
    try:
        user_data = db.get_user_by_id(user_id)
        asset_id = user_data.get('signature_asset_id') if user_data else None
        if not asset_id:
            return None
        content, asset = get_owned_asset_content(asset_id, user_id)
        if not content or not asset or asset.get('mime_type') not in {'image/jpeg', 'image/png', 'image/webp'}:
            return None
        suffix = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp'}[asset['mime_type']]
        handle = tempfile.NamedTemporaryFile(prefix='insurance-signature-', suffix=suffix, delete=False)
        try:
            handle.write(content)
            return handle.name
        finally:
            handle.close()
    except Exception:
        return None


def _remove_temporary_signature(path):
    if not path:
        return
    try:
        os.unlink(path)
    except OSError:
        pass

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        s = str(val).replace(',', '').strip()
        if not s or s == '-':
            return default
        return float(s)
    except (ValueError, TypeError):
        return default

def normalize_pdf_text_for_fpdf(text_val):
    if not isinstance(text_val, str):
        text_val = str(text_val)
    text_val = text_val.replace('\u2013', '-')
    text_val = text_val.replace('\u2014', '-')
    text_val = text_val.replace('\u2212', '-')
    text_val = text_val.encode('latin-1', 'replace').decode('latin-1')
    return text_val

def format_pdf_number(value):
    try:
        num = float(value)
        if abs(num) < 0.001:
            return '0'
        return f"{num:.2f}"
    except (ValueError, TypeError):
        val_str = str(value)
        return '0' if val_str.strip() == '0' else val_str

def number_to_words_indian(number_val):
    num = round(float(number_val), 2)
    if num == 0:
        return "RUPEES ZERO ONLY"
    if num > 999999999.99:
        return "RUPEES [Amount too large for words]"

    words = []
    units = ["", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN",
             "ELEVEN", "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN", "SEVENTEEN", "EIGHTEEN", "NINETEEN"]
    tens = ["", "", "TWENTY", "THIRTY", "FORTY", "FIFTY", "SIXTY", "SEVENTY", "EIGHTY", "NINETY"]

    def convert_less_than_thousand(n_int):
        s = []
        if n_int >= 100:
            s.append(units[n_int // 100] + " HUNDRED")
            n_int %= 100
        if n_int >= 20:
            s.append(tens[n_int // 10])
            n_int %= 10
        if n_int > 0:
            s.append(units[n_int])
        return " ".join(filter(None, s))

    integer_part = int(num)
    decimal_part = int(round((num - integer_part) * 100))

    if integer_part == 0:
        words.append("ZERO")
    else:
        crores = integer_part // 10000000
        lakhs = (integer_part % 10000000) // 100000
        thousands = (integer_part % 100000) // 1000
        remainder = integer_part % 1000

        if crores > 0:
            words.append(convert_less_than_thousand(crores) + " CRORE")
        if lakhs > 0:
            words.append(convert_less_than_thousand(lakhs) + " LAKH")
        if thousands > 0:
            words.append(convert_less_than_thousand(thousands) + " THOUSAND")
        if remainder > 0:
            words.append(convert_less_than_thousand(remainder))

    rupees_words = " ".join(filter(None, words)).strip()
    result = f"RUPEES {rupees_words}"

    if decimal_part > 0:
        paise_words = convert_less_than_thousand(decimal_part)
        result += f" AND PAISE {paise_words}"

    result += " ONLY"
    return result.upper()

class PDFWithPageNumbers(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')

def render_report(data, user_data_snapshot, user_id):
    """
    Expose a single render_report interface.
    Generates PDF report and uploads it privately to the Service Account Google Drive.
    """
    u = UserSnapshot(user_data_snapshot)

    survey_data = data.get('survey_report', {})
    assessment_data = data.get('assessment', {})
    photos_data = data.get('photos', {})

    page3_details_raw = assessment_data.get('page3_details', {})
    p3_customer_gstin_raw = page3_details_raw.get('customer_gstin', '')
    p3_company_gstin_raw = page3_details_raw.get('company_gstin', '') 
    p3_fee_items_raw = page3_details_raw.get('fee_items', [])
    p3_estimated_amount_str = str(page3_details_raw.get('estimated_amount', '0')).strip()
    
    surveyor_details = page3_details_raw.get('surveyor_details', {})
    p3_apply_gst = page3_details_raw.get('apply_gst', True)

    p3_photo_copies_str = str(page3_details_raw.get('photo_copies_count', '0')).strip()
    p3_photo_copies_count = 0 
    if p3_photo_copies_str: 
        try:
            float_val = float(p3_photo_copies_str)
            if float_val.is_integer(): 
                count_val = int(float_val)
                if count_val >= 0: 
                    p3_photo_copies_count = count_val
        except ValueError:
            pass

    user_labour_rows = assessment_data.get('user_labour_rows', [])
    updated_parts = assessment_data.get('parts', [])
    header_gst_raw = assessment_data.get('header_gst', '') 
    header_vehicle_year_raw = assessment_data.get('header_vehicle_year', '')
    policy_type = assessment_data.get('policy_type', 'NORMAL') 
    report_type_raw = assessment_data.get('report_type', 'Final Survey Report')
    claim_type_raw = assessment_data.get('claim_type', 'Cashless')
    labour_tax_type_main = assessment_data.get('labour_tax_type', 'CGST/SGST')
    labour_imt_applied = assessment_data.get('labour_imt_applied', False) 
    
    reinspection_note_raw = assessment_data.get('reinspection_note', "As per instruction received from your office I had visited the insured repairer garage. I had taken some photographs of the insured's repaired vehicle and checked. The undersigned have been satisfied with the repairing job of insured vehicle.")
    enclosures_text_raw = assessment_data.get('enclosures_text', '')
    parts_table_note_raw = assessment_data.get('parts_table_note', '')
    spot_report_text_raw = assessment_data.get('spot_report_text', '') 
    spot_report_enclosures_raw = assessment_data.get('spot_report_enclosures', '') 

    labour_paint_depn_input = safe_float(assessment_data.get('labour_paint_depn', 0.0))
    salvage_raw_data = assessment_data.get('salvage', '0') 

    est_labour_override = assessment_data.get('est_labour_override', '')
    nd_deduction_pc = safe_float(assessment_data.get('nd_deduction_pc', 5), 5.0)
    nd_deduction_amount = safe_float(assessment_data.get('nd_deduction_amount', 0.0))
    towing_charges = safe_float(assessment_data.get('towing_charges', 0.0))
    est_paint_override = assessment_data.get('est_paint_override', '')
    est_parts_override = assessment_data.get('est_parts_override', '')

    final_survey_data = {key: survey_data.get(key, '') for key in EXPECTED_FIELDS}
    
    def get_survey_val(key):
        raw_value = final_survey_data.get(key, '')
        return normalize_pdf_text_for_fpdf(raw_value)

    header_vehicle_year = normalize_pdf_text_for_fpdf(header_vehicle_year_raw)
    reinspection_note = normalize_pdf_text_for_fpdf(reinspection_note_raw)
    p3_customer_gstin = normalize_pdf_text_for_fpdf(p3_customer_gstin_raw)
    p3_company_gstin = normalize_pdf_text_for_fpdf(p3_company_gstin_raw)
    salvage_raw = normalize_pdf_text_for_fpdf(salvage_raw_data)
    report_type = normalize_pdf_text_for_fpdf(report_type_raw)
    claim_type = normalize_pdf_text_for_fpdf(claim_type_raw)
    enclosures_text = normalize_pdf_text_for_fpdf(enclosures_text_raw)
    parts_table_note = normalize_pdf_text_for_fpdf(parts_table_note_raw)
    spot_report_text = normalize_pdf_text_for_fpdf(spot_report_text_raw)
    spot_report_enclosures = normalize_pdf_text_for_fpdf(spot_report_enclosures_raw)

    try:
        gst_num_raw = str(header_gst_raw).replace('%','').strip()
        gst_num = float(gst_num_raw)
        header_gst_display = normalize_pdf_text_for_fpdf(f"{gst_num:.2f}%")
    except (ValueError, TypeError):
        header_gst_display = normalize_pdf_text_for_fpdf(header_gst_raw)

    # --- Labour Recalculation ---
    labour_sum_removing = 0.0
    labour_sum_denting = 0.0
    labour_sum_painting = 0.0 
    processed_user_labour_rows_for_pdf = []
    
    for row_data in user_labour_rows:
        def safe_float_from_string(val_str, default=0.0):
            try: return float(str(val_str).replace(',', ''))
            except (ValueError, TypeError): return default
        
        removing = safe_float_from_string(row_data.get('removing_refitting', 0))
        denting = safe_float_from_string(row_data.get('denting_repairing', 0))
        painting = safe_float_from_string(row_data.get('painting', 0))
        
        labour_sum_removing += removing
        labour_sum_denting += denting
        labour_sum_painting += painting 
        
        processed_user_labour_rows_for_pdf.append({
            'part_name': normalize_pdf_text_for_fpdf(row_data.get('part_name', '')),
            'removing_refitting': removing,
            'denting_repairing': denting,
            'painting': painting
        })
    
    labour_paint_depn_final = 0.0 if policy_type in ('NIL_DEPN', 'NIL_DEPN_PLUS') else labour_paint_depn_input
    net_paint_after_dep = labour_sum_painting - labour_paint_depn_final
    
    labour_imt_deduction = net_paint_after_dep * 0.5 if (labour_imt_applied and net_paint_after_dep > 0) else 0.0
    net_paint_liability = net_paint_after_dep - labour_imt_deduction
    
    labour_rr_dent_sum = labour_sum_removing + labour_sum_denting
    taxable_labour = labour_rr_dent_sum + net_paint_liability
    
    labour_gst_amount = taxable_labour * 0.18 if labour_tax_type_main != 'Zero' else 0.0
    labour_grand_total_final = taxable_labour + labour_gst_amount
    
    # --- Parts Recalculation ---
    parts_total_base_final = 0.0; parts_total_gst_final = 0.0; parts_grand_total_final = 0.0; parts_net_amt_final = 0.0; parts_depr_sum_final = 0.0
    parts_total_estimate = 0.0; parts_total_bill = 0.0; parts_total_assessed = 0.0; parts_total_imt23 = 0.0
    liability_metal = 0.0; liability_glass = 0.0; liability_plastic = 0.0

    from modules.report_assessment import get_backend_depreciation_rate

    final_parts_calculated = []
    for part in updated_parts:
        try:
            qty = float(part.get('qty', 1.0)); part_amt = float(part.get('part_amt', 0.0)); part_type = str(part.get('type_part', '')).strip().upper()
            gst_applicable = part.get('gst_applicable', False); original_gst_pc = float(part.get('original_gst_pc', 0.0))
            imt_applied = part.get('imt_applied', False) 
            
            estimate_amt = float(part.get('estimate_amt', 0.0))
            bill_amt = float(part.get('bill_amt', 0.0))
            
            depr_amount_from_frontend = safe_float(part.get('depr', -1.0), -1.0)
            
            total_parts_amt = qty * part_amt 
            
            if policy_type in ('NIL_DEPN', 'NIL_DEPN_PLUS'):
                final_depr_amount_to_use = 0.0
            elif depr_amount_from_frontend >= 0:
                final_depr_amount_to_use = depr_amount_from_frontend
            else: 
                calculated_depr_rate = get_backend_depreciation_rate(part_type, header_vehicle_year)
                final_depr_amount_to_use = total_parts_amt * (calculated_depr_rate / 100.0) if total_parts_amt > 0 else 0.0
            
            net_base = total_parts_amt - final_depr_amount_to_use
            total_gst = net_base * (original_gst_pc / 100.0) if gst_applicable else 0.0
            gross_post_dep = net_base + total_gst

            imt_23_amt = gross_post_dep * 0.5 if imt_applied else 0.0
            net_amt = gross_post_dep - imt_23_amt

            if part_type == 'M': liability_metal += net_amt
            elif part_type == 'G': liability_glass += net_amt
            elif part_type == 'P': liability_plastic += net_amt

            part_name_display = normalize_pdf_text_for_fpdf(part.get('part_name', ''))
            
            output_part = part.copy() 
            output_part['total_parts_amt'] = total_parts_amt; output_part['total_gst'] = total_gst; output_part['gross_amt'] = gross_post_dep
            output_part['depr'] = final_depr_amount_to_use; output_part['net_amt'] = net_amt; output_part['part_name_display'] = part_name_display
            output_part['estimate_amt'] = estimate_amt; output_part['bill_amt'] = bill_amt; output_part['imt_23_amt'] = imt_23_amt
            output_part['net_base'] = net_base
            output_part['salvage_produce'] = normalize_pdf_text_for_fpdf(part.get('salvage_produce', 'YES'))
            output_part['remarks'] = normalize_pdf_text_for_fpdf(part.get('remarks', 'REPLACED BY NEW'))

            final_parts_calculated.append(output_part)
            
            parts_total_base_final += total_parts_amt; parts_total_gst_final += total_gst; parts_grand_total_final += gross_post_dep; parts_net_amt_final += net_amt
            parts_depr_sum_final += final_depr_amount_to_use
            parts_total_estimate += estimate_amt; parts_total_bill += bill_amt; parts_total_assessed += total_parts_amt; parts_total_imt23 += imt_23_amt
        except Exception as e:
            print(f"Error processing part: {e}")

    excess_final = safe_float(assessment_data.get('deductibles', 1000.0), 1000.0)
    impose_excess_final = safe_float(assessment_data.get('impose_excess', 0.0), 0.0)
    try: salvage_val_numeric = float(str(salvage_raw).replace(',', ''))
    except (ValueError, TypeError): salvage_val_numeric = 0.0
    
    net_liability_final = (labour_grand_total_final + parts_net_amt_final) - excess_final - impose_excess_final - salvage_val_numeric
    if policy_type == 'NIL_DEPN' and nd_deduction_amount > 0:
        net_liability_final -= nd_deduction_amount
    if towing_charges > 0:
        net_liability_final += towing_charges
    
    p3_photo_total_charge = p3_photo_copies_count * 10.0
    p3_fees_subtotal = 0.0
    p3_valid_fee_items = []
    for item_raw in p3_fee_items_raw:
        name = normalize_pdf_text_for_fpdf(str(item_raw.get('name', '')).strip())
        amount_str = str(item_raw.get('amount', '0')).replace(',', '')
        try:
            amount = float(amount_str)
            if amount != 0.0:
                p3_valid_fee_items.append({'name': name, 'amount': amount})
                p3_fees_subtotal += amount
        except (ValueError, TypeError): pass
        
    p3_total_before_gst = p3_fees_subtotal + p3_photo_total_charge
    p3_cgst = 0.0; p3_sgst = 0.0; p3_igst = 0.0
    
    if p3_apply_gst:
        if labour_tax_type_main == 'IGST': 
            p3_igst = p3_total_before_gst * 0.18
        else:
            p3_cgst = p3_total_before_gst * 0.09; p3_sgst = p3_total_before_gst * 0.09
        
    p3_grand_total = p3_total_before_gst + p3_cgst + p3_sgst + p3_igst
    p3_grand_total_in_words = normalize_pdf_text_for_fpdf(number_to_words_indian(p3_grand_total))
    try: p3_estimated_amount = float(p3_estimated_amount_str.replace(',', ''))
    except ValueError: p3_estimated_amount = 0.0

    # --- PDF Generation Setup ---
    pdf = PDFWithPageNumbers(orientation='P', unit='mm', format='A4')
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    base_font_size_page1 = 10; base_font_size_page2 = 10; base_font_size_page3 = 9 
    line_h_page1 = 5.5; line_h_page2 = 5.5; line_h_page3 = 5    
    table_cell_padding_y = 0.8

    def add_pdf_header(pdf_obj):
        if pdf_obj.page_no() == 1:
            pdf_obj.set_y(10)
            pdf_obj.set_x(10)
            
            pdf_obj.set_text_color(239, 68, 68)
            pdf_obj.set_font('Helvetica', 'B', 16)
            pdf_obj.cell(0, 8, normalize_pdf_text_for_fpdf(u.full_name), border=0, new_x="LMARGIN", new_y="NEXT", align='L')
            
            pdf_obj.set_text_color(0, 0, 0)
            pdf_obj.set_font('Helvetica', '', 9)
            pdf_obj.cell(0, 5, normalize_pdf_text_for_fpdf(u.qualifications), border=0, new_x="LMARGIN", new_y="NEXT", align='L')
            
            pdf_obj.set_text_color(239, 68, 68)
            pdf_obj.set_font('Helvetica', 'B', 10)
            pdf_obj.cell(0, 5, normalize_pdf_text_for_fpdf(u.designation), border=0, new_x="LMARGIN", new_y="NEXT", align='L')
            
            pdf_obj.set_text_color(0, 0, 0)
            pdf_obj.set_font('Helvetica', '', 9)
            pdf_obj.cell(0, 5, normalize_pdf_text_for_fpdf(f"Licence No: {u.license_no}"), border=0, new_x="LMARGIN", new_y="NEXT", align='L')
            pdf_obj.cell(0, 5, normalize_pdf_text_for_fpdf(f"Expiry on: {u.expiry_date}"), border=0, new_x="LMARGIN", new_y="NEXT", align='L')
            pdf_obj.cell(0, 5, normalize_pdf_text_for_fpdf(f"IIISLA Membership No-{u.membership_no}"), border=0, new_x="LMARGIN", new_y="NEXT", align='L')

            def right_text(txt, y_offset=0, color=(0,0,0), bold=False):
                pdf_obj.set_y(10 + y_offset)
                pdf_obj.set_x(120)
                pdf_obj.set_font('Helvetica', 'B' if bold else '', 9)
                pdf_obj.set_text_color(*color)
                pdf_obj.cell(80, 5, normalize_pdf_text_for_fpdf(txt), border=0, new_x="RIGHT", new_y="TOP", align='R')

            right_text(u.address_line_1, 0)
            right_text(u.address_line_2, 5)
            right_text(u.address_line_3, 10)

            cell_val = normalize_pdf_text_for_fpdf(u.contact_no)
            cell_lbl = "Cell: "
            pdf_obj.set_font('Helvetica', 'B', 9); val_w = pdf_obj.get_string_width(cell_val)
            pdf_obj.set_font('Helvetica', '', 9); lbl_w = pdf_obj.get_string_width(cell_lbl)
            start_x = 200 - (lbl_w + val_w)
            
            pdf_obj.set_y(25)
            pdf_obj.set_x(start_x)
            pdf_obj.set_text_color(0,0,0); pdf_obj.cell(lbl_w, 5, cell_lbl, border=0, new_x="RIGHT", new_y="TOP", align='L')
            pdf_obj.set_text_color(239, 68, 68); pdf_obj.set_font('Helvetica', 'B', 9); pdf_obj.cell(val_w, 5, cell_val, border=0, new_x="LMARGIN", new_y="NEXT", align='L')

            email_val = normalize_pdf_text_for_fpdf(u.email)
            email_lbl = "Email: "
            pdf_obj.set_font('Helvetica', 'B', 9); val_w = pdf_obj.get_string_width(email_val)
            pdf_obj.set_font('Helvetica', '', 9); lbl_w = pdf_obj.get_string_width(email_lbl)
            start_x = 200 - (lbl_w + val_w)
            
            pdf_obj.set_y(30)
            pdf_obj.set_x(start_x)
            pdf_obj.set_text_color(0,0,0); pdf_obj.cell(lbl_w, 5, email_lbl, border=0, new_x="RIGHT", new_y="TOP", align='L')
            pdf_obj.set_text_color(239, 68, 68); pdf_obj.set_font('Helvetica', 'B', 9); pdf_obj.cell(val_w, 5, email_val, border=0, new_x="LMARGIN", new_y="NEXT", align='L')

            pdf_obj.set_draw_color(59, 130, 246)
            pdf_obj.set_line_width(0.5)
            pdf_obj.line(10, 42, 200, 42)
            
            pdf_obj.set_y(45)
            pdf_obj.set_text_color(0, 0, 0)
            pdf_obj.set_draw_color(0, 0, 0)
            pdf_obj.set_line_width(0.2)
        else:
            pdf_obj.set_y(10)

        if pdf_obj.page_no() > 1:
            current_y = pdf_obj.get_y()
            pdf_obj.set_font("Helvetica", 'B', 9)
            report_text = f"Report No: {get_survey_val('report_no')}"
            vehicle_text = f"Vehicle No: {get_survey_val('vehicle_regn_no')}"
            pdf_obj.set_xy(pdf_obj.l_margin, current_y)
            pdf_obj.cell(80, 5, normalize_pdf_text_for_fpdf(report_text), border=0, new_x="RIGHT", new_y="TOP", align='L')
            right_margin_x = pdf_obj.w - pdf_obj.r_margin
            pdf_obj.set_xy(right_margin_x - 80, current_y)
            pdf_obj.cell(80, 5, normalize_pdf_text_for_fpdf(vehicle_text), border=0, new_x="LMARGIN", new_y="NEXT", align='R')
            pdf_obj.ln(10)

    def draw_table_row(pdf_inst, data_row, widths, height_per_line, border='TBLR', align='C', fill=False, text_color=(0,0,0), fill_color=(255,255,255), alignments=None, font_style='', is_header=False, current_font_size=9):
        pdf_inst.set_fill_color(*fill_color); pdf_inst.set_text_color(*text_color)
        max_lines = 1
        for idx, item in enumerate(data_row):
            w = widths[idx]
            temp_item_str = format_pdf_number(item) if isinstance(item, (int, float)) else str(item)
            temp_item = normalize_pdf_text_for_fpdf(temp_item_str)
            pdf_inst.set_font("Helvetica", 'B' if is_header else (font_style if font_style else ''), current_font_size)
            lines = pdf_inst.multi_cell(w, height_per_line, temp_item, border=0, align=alignments[idx] if alignments else align, dry_run=True, output="LINES", max_line_height=height_per_line)
            max_lines = max(max_lines, len(lines))
        total_row_height = max_lines * height_per_line + table_cell_padding_y 
        if pdf_inst.get_y() + total_row_height > pdf_inst.h - pdf_inst.b_margin:
            pdf_inst.add_page(orientation=pdf_inst.def_orientation); add_pdf_header(pdf_inst); pdf_inst.set_fill_color(*fill_color); pdf_inst.set_text_color(*text_color)
        x_start = pdf_inst.get_x(); y_start = pdf_inst.get_y()
        if fill: pdf_inst.rect(x_start, y_start, sum(widths), total_row_height, 'F')
        current_x = x_start
        for idx, item in enumerate(data_row):
            w = widths[idx]; cell_align = alignments[idx] if alignments else align
            item_str = format_pdf_number(item) if isinstance(item, (int, float)) else normalize_pdf_text_for_fpdf(str(item))
            pdf_inst.set_font("Helvetica", font_style if font_style else ('B' if is_header else ''), current_font_size)
            pdf_inst.set_xy(current_x, y_start + table_cell_padding_y / 2) 
            pdf_inst.multi_cell(w, height_per_line, item_str, border=0, align=cell_align, padding=(0, 1), max_line_height=height_per_line) 
            current_x += w
        line_x = x_start; line_y = y_start; row_width = sum(widths); row_height = total_row_height
        is_full_border = (isinstance(border, int) and border == 1) or (isinstance(border, str) and border.upper() == 'TBLR')
        draw_top = is_full_border or (isinstance(border, str) and 'T' in border.upper()); draw_bottom = is_full_border or (isinstance(border, str) and 'B' in border.upper())
        draw_left = is_full_border or (isinstance(border, str) and 'L' in border.upper()); draw_right = is_full_border or (isinstance(border, str) and 'R' in border.upper())
        pdf_inst.set_draw_color(0,0,0) 
        if draw_top: pdf_inst.line(line_x, line_y, line_x + row_width, line_y)
        if draw_bottom: pdf_inst.line(line_x, line_y + row_height, line_x + row_width, line_y + row_height)
        if draw_left: pdf_inst.line(line_x, line_y, line_x, line_y + row_height)
        if draw_right: pdf_inst.line(line_x + row_width, line_y, line_x + row_width, line_y + row_height)
        if is_full_border: 
            temp_x = x_start
            for idx in range(len(widths) - 1): temp_x += widths[idx]; pdf_inst.line(temp_x, line_y, temp_x, line_y + row_height)
        pdf_inst.set_y(y_start + total_row_height); pdf_inst.set_x(x_start) 
        return total_row_height

    def calculate_height(texts, widths, font_size, line_height, padding, font_style=None):
        max_lines = 1; temp_pdf = FPDF(); temp_pdf.add_page()
        for idx, text in enumerate(texts):
            current_style = font_style[idx] if isinstance(font_style, list) and idx < len(font_style) else (font_style if font_style else '')
            temp_pdf.set_font("Helvetica", current_style, font_size)
            normalized_text_for_calc = normalize_pdf_text_for_fpdf(str(text) if text is not None else '')
            lines = temp_pdf.multi_cell(widths[idx], line_height, normalized_text_for_calc, dry_run=True, output="LINES", max_line_height=line_height)
            max_lines = max(max_lines, len(lines))
        return max_lines * line_height + padding

    def add_plain_pair(label1, val1, label2, val2, label_width, val_width, font_size=10, line_h=5.5):
        start_y = pdf.get_y()
        norm_label1 = normalize_pdf_text_for_fpdf(label1)
        norm_val1 = normalize_pdf_text_for_fpdf(str(val1))
        norm_label2 = normalize_pdf_text_for_fpdf(label2) if label2 else ""
        norm_val2 = normalize_pdf_text_for_fpdf(str(val2)) if val2 else ""
        
        text1 = f"**{norm_label1}** {norm_val1}"
        text2 = f"**{norm_label2}** {norm_val2}" if label2 else ""
        col_total_width = label_width + val_width
        
        pdf.set_font("Helvetica", '', font_size)
        lines1 = pdf.multi_cell(col_total_width, line_h, text1, markdown=True, dry_run=True, output="LINES", max_line_height=line_h)
        h1 = len(lines1) * line_h
        
        h2 = 0
        if label2:
             lines2 = pdf.multi_cell(col_total_width, line_h, text2, markdown=True, dry_run=True, output="LINES", max_line_height=line_h)
             h2 = len(lines2) * line_h
        
        max_h = max(h1, h2) + table_cell_padding_y
        
        if pdf.get_y() + max_h > pdf.page_break_trigger: 
            pdf.add_page(); add_pdf_header(pdf); start_y = pdf.get_y()
        
        pdf.set_xy(pdf.l_margin, start_y)
        pdf.set_font("Helvetica", '', font_size)
        pdf.multi_cell(col_total_width, line_h, text1, markdown=True, border=0, align='L', max_line_height=line_h)
        
        if label2:
            pdf.set_xy(pdf.l_margin + col_total_width, start_y)
            pdf.set_font("Helvetica", '', font_size)
            pdf.multi_cell(col_total_width, line_h, text2, markdown=True, border=0, align='L', max_line_height=line_h)
        
        pdf.set_y(start_y + max_h)
        return pdf.get_y()

    def add_section_header(text):
        if pdf.get_y() > pdf.h - pdf.b_margin - 30:
            pdf.add_page(orientation=pdf.def_orientation)
            add_pdf_header(pdf)
        pdf.ln(2); pdf.set_font("Helvetica", 'B', base_font_size_page1)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.cell(0, line_h_page1 * 1.5, normalize_pdf_text_for_fpdf(text), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y()); pdf.ln(1); pdf.set_font("Helvetica", '', base_font_size_page1)

    def add_photo_section(pdf_obj, title, vehicle_no, photos_list, photos_per_page):
        if not photos_list or not isinstance(photos_list, list):
            return
        margin = 10
        page_width = 210 - (2 * margin)
        page_height = 297 - (2 * margin) - 35 
        
        cols = 2
        try: photos_per_page = int(photos_per_page)
        except: photos_per_page = 4
        if photos_per_page <= 0: photos_per_page = 4
        if photos_per_page == 4: rows = 2
        elif photos_per_page == 6: rows = 3
        elif photos_per_page == 8: rows = 4
        else: rows = 2 
        
        img_width = (page_width - 5) / cols
        img_height = (page_height - 5) / rows 
        
        start_y = 0
        for idx, raw_photo in enumerate(photos_list):
            if not raw_photo:
                continue
            if isinstance(raw_photo, dict):
                photo_b64 = str(raw_photo.get('url') or raw_photo.get('src') or raw_photo.get('path') or '').strip()
            else:
                photo_b64 = str(raw_photo or '').strip()
            if not photo_b64 or photo_b64 == '[object Object]':
                continue

            if idx % photos_per_page == 0:
                pdf_obj.add_page(orientation='P'); add_pdf_header(pdf_obj)
                pdf_obj.set_font("Helvetica", 'B', 12)
                pdf_obj.cell(0, 10, normalize_pdf_text_for_fpdf(f"{title} ({vehicle_no})"), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
                pdf_obj.ln(1) 
                start_y = pdf_obj.get_y()
            
            pos_in_page = idx % photos_per_page; row = pos_in_page // cols; col = pos_in_page % cols
            x = pdf_obj.l_margin + (col * (img_width + 5)); y = start_y + (row * (img_height + 5))
            try:
                img_stream = None
                if '/assets/' in photo_b64:
                    parts = photo_b64.split('/assets/')
                    asset_id = parts[1].split('/')[0] if len(parts) > 1 else ''
                    ws_admin_id = user_data_snapshot.get('workspace_admin_id') if isinstance(user_data_snapshot, dict) else None
                    img_data, _asset = get_accessible_asset_content(asset_id, user_id, ws_admin_id)
                    if not img_data:
                        img_data, _asset = get_owned_asset_content(asset_id, user_id)
                    if img_data:
                        img_stream = io.BytesIO(img_data)
                    else:
                        pdf_obj.set_xy(x, y); pdf_obj.set_font("Helvetica", '', 8); pdf_obj.cell(img_width, img_height, "Error loading image", border=1, new_x="RIGHT", new_y="TOP", align='C')
                        continue
                elif '/proxy_image/' in photo_b64 or '/local_image/' in photo_b64:
                    if '/proxy_image/' in photo_b64:
                        locator = photo_b64.split('/proxy_image/')[-1].split('?')[0].split('/')[0]
                    else:
                        locator = photo_b64.split('/local_image/')[-1].split('?')[0].split('/')[0]
                    ws_admin_id = user_data_snapshot.get('workspace_admin_id') if isinstance(user_data_snapshot, dict) else None
                    asset = db.get_asset_by_locator(locator, user_id)
                    if asset:
                        img_data, _ = get_accessible_asset_content(asset['id'], user_id, ws_admin_id)
                        if img_data:
                            img_stream = io.BytesIO(img_data)
                    if not img_stream and '/proxy_image/' in photo_b64:
                        img_data = db.get_file_content(locator)
                        if img_data:
                            img_stream = io.BytesIO(img_data)
                    if not img_stream and '/local_image/' in photo_b64:
                        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        local_path = os.path.join(project_root, 'uploads', locator)
                        if os.path.exists(local_path):
                            with open(local_path, 'rb') as f:
                                img_stream = io.BytesIO(f.read())
                    if not img_stream:
                        pdf_obj.set_xy(x, y); pdf_obj.set_font("Helvetica", '', 8); pdf_obj.cell(img_width, img_height, "Legacy image unavailable", border=1, new_x="RIGHT", new_y="TOP", align='C')
                        continue
                elif photo_b64.startswith('http'):
                    try:
                        resp = requests.get(photo_b64, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
                        content_type = str(resp.headers.get('content-type', '')).lower()
                        if resp.ok and resp.content and (content_type.startswith('image/') or not content_type.startswith('text/html')):
                            img_stream = io.BytesIO(resp.content)
                    except Exception:
                        pass
                    if not img_stream:
                        pdf_obj.set_xy(x, y); pdf_obj.set_font("Helvetica", '', 8); pdf_obj.cell(img_width, img_height, "Error DL Image", border=1, new_x="RIGHT", new_y="TOP", align='C')
                        continue
                elif ',' in photo_b64:
                    try:
                        photo_b64_data = photo_b64.split(',')[1]
                        img_data = base64.b64decode(photo_b64_data); img_stream = io.BytesIO(img_data)
                    except Exception:
                        pdf_obj.set_xy(x, y); pdf_obj.set_font("Helvetica", '', 8); pdf_obj.cell(img_width, img_height, "Error loading image", border=1, new_x="RIGHT", new_y="TOP", align='C')
                        continue
                else:
                    try:
                        img_data = base64.b64decode(photo_b64); img_stream = io.BytesIO(img_data)
                    except Exception:
                        pdf_obj.set_xy(x, y); pdf_obj.set_font("Helvetica", '', 8); pdf_obj.cell(img_width, img_height, "Error loading image", border=1, new_x="RIGHT", new_y="TOP", align='C')
                        continue
                
                if img_stream:
                    try:
                        pdf_obj.image(img_stream, x=x, y=y, w=img_width, h=img_height)
                    except Exception:
                        pdf_obj.set_xy(x, y); pdf_obj.set_font("Helvetica", '', 8); pdf_obj.cell(img_width, img_height, "Error loading image", border=1, new_x="RIGHT", new_y="TOP", align='C')
            except Exception:
                pdf_obj.set_xy(x, y); pdf_obj.set_font("Helvetica", '', 8); pdf_obj.cell(img_width, img_height, "Error loading image", border=1, new_x="RIGHT", new_y="TOP", align='C')

    # --- Page 1: Survey Report ---
    pdf.add_page(); pdf.set_margins(10, 10, 10); add_pdf_header(pdf)
    is_spot_report = (report_type_raw == 'Spot Report')
    if is_spot_report:
        combined_heading = normalize_pdf_text_for_fpdf("Spot/Preliminary Survey Report")
    elif report_type_raw == 'Re-inspection Report':
        combined_heading = normalize_pdf_text_for_fpdf(f"Final Survey Report ({claim_type})")
    else:
        combined_heading = normalize_pdf_text_for_fpdf(f"{report_type} ({claim_type})")
        
    pdf.set_font("Helvetica", 'B', 12); pdf.cell(0, 8, combined_heading, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C'); pdf.ln(6)
    pdf.set_font("Helvetica", size=base_font_size_page1)
    usable_width = pdf.w - 2 * pdf.l_margin; col_width = usable_width / 2; label_w = 30; val_w = col_width - label_w
    add_plain_pair("Report No.:", get_survey_val('report_no'), "Date:", get_survey_val('report_date'), label_w, val_w)
    pdf.ln(1); pdf.set_font("Helvetica", size=base_font_size_page1 - 0.5)
    disclaimer = normalize_pdf_text_for_fpdf("This Motor Survey Report is issued without prejudice in respect of cause, nature & extent of Loss/damage & subject to to the terms and conditions of the insurance policy")
    pdf.multi_cell(0, line_h_page1, disclaimer, border=0, align='L'); pdf.ln(2)
    add_plain_pair("Policy No.:", get_survey_val('policy_no'), "Insurer's Claim No.:", get_survey_val('claim_no'), label_w, val_w)
    add_plain_pair("Policy Type:", get_survey_val('policy_type_label'), "Validity:", get_survey_val('policy_validity'), label_w, val_w)
    idv_value = get_survey_val('idv')
    idv_display = f"Rs. {idv_value}" if idv_value else ""
    add_plain_pair("IDV:", idv_display, "Hypothecation:", get_survey_val('hypothecation'), label_w, val_w)
    add_section_header("1) Insurer & Insured Details")
    add_plain_pair("Insurer:", get_survey_val('insurer'), "", "", 30, usable_width - 30)
    add_plain_pair("Insured:", get_survey_val('insured'), "", "", 30, usable_width - 30)
    add_plain_pair("Insured Contact Name:", get_survey_val('insured_contact_name'), "Insured Contact No.:", get_survey_val('insured_contact_no'), 35, col_width - 35)
    add_section_header("2) Reported particulars of vehicle")
    label_w_veh = 35; val_w_veh = col_width - label_w_veh
    add_plain_pair("a. Regn. No.:", get_survey_val('vehicle_regn_no'), "b. Date of Regn.:", get_survey_val('vehicle_regn_date'), label_w_veh, val_w_veh)
    add_plain_pair("c. Chassis No.:", get_survey_val('vehicle_chassis_no'), "d. Engine No.:", get_survey_val('vehicle_engine_no'), label_w_veh, val_w_veh)
    add_plain_pair("e. Make & Model:", get_survey_val('vehicle_make_model'), "f. Type of body:", get_survey_val('vehicle_type_body'), label_w_veh, val_w_veh)
    add_plain_pair("g. C.F. Valid up to:", get_survey_val('vehicle_cf_validity'), "h. Seating capacity:", get_survey_val('vehicle_seating'), label_w_veh, val_w_veh)
    add_plain_pair("i. B.H.P./C.C.:", get_survey_val('vehicle_bhp_cc'), "j. Pre accident condition:", get_survey_val('vehicle_pre_accident_condition'), label_w_veh, val_w_veh)
    add_plain_pair("k. U.L.W.:", get_survey_val('vehicle_ulw'), "l. R.L.W.:", get_survey_val('vehicle_rlw'), label_w_veh, val_w_veh)
    add_plain_pair("m. Class of Vehicle:", get_survey_val('class_of_vehicle'), "n. Regn. Cert. No.:", get_survey_val('regn_cert_no'), label_w_veh, val_w_veh)
    add_plain_pair("o. Vehicle Colour:", get_survey_val('vehicle_colour'), "p. Odometer Reading:", get_survey_val('vehicle_odometer'), label_w_veh, val_w_veh)
    add_plain_pair("q. Tax Token No.:", get_survey_val('vehicle_tax_token'), "r. Tax Validity:", get_survey_val('vehicle_tax_validity'), label_w_veh, val_w_veh)
    add_plain_pair("s. Permit No:", get_survey_val('vehicle_permit_no'), "t. Permit Type:", get_survey_val('vehicle_permit_type'), label_w_veh, val_w_veh)
    add_plain_pair("u. Permit Validity:", get_survey_val('vehicle_permit_validity'), "v. Route area:", get_survey_val('vehicle_route_area'), label_w_veh, val_w_veh)
    add_section_header("3) Reported particulars of Driving Licence:")
    label_w_dl = 35; val_w_dl = col_width - label_w_dl
    add_plain_pair("a. Name:", get_survey_val('dl_name'), "b. Licence No.:", get_survey_val('dl_no'), label_w_dl, val_w_dl)
    add_plain_pair("c. Date of issue:", get_survey_val('dl_issue_date'), "d. Valid up to:", get_survey_val('dl_validity'), label_w_dl, val_w_dl)
    add_plain_pair("e. Issuing Authority:", get_survey_val('dl_issuing_authority'), "f. Endorsement:", get_survey_val('dl_endorsement'), label_w_dl, val_w_dl)
    add_plain_pair("g. Type of Licence:", get_survey_val('dl_type'), "h. DOB of Driver:", get_survey_val('dl_dob'), label_w_dl, val_w_dl)
    add_section_header("4) Documents Compared:")
    doc_items = [("a. Regn. Cert.:", get_survey_val('doc_regn_cert')), ("b. Driving Licence:", get_survey_val('doc_dl')), ("c. Tax Token:", get_survey_val('doc_tax_token')), ("d. Fitness Cert:", get_survey_val('doc_fitness_certificate')), ("e. Permit:", get_survey_val('doc_permit_compared')), ("f. Load Challan:", get_survey_val('doc_load_challan'))]
    doc_label_w = 35; doc_val_w = col_width - doc_label_w
    for idx in range(0, len(doc_items), 2):
        item1 = doc_items[idx]; item2 = doc_items[idx+1] if idx+1 < len(doc_items) else (None, None)
        add_plain_pair(item1[0], item1[1], item2[0] if item2[0] else "", item2[1] if item2[1] else "", doc_label_w, doc_val_w)
    add_section_header("5) Load & Goods Details:")
    load_label_w = 45; load_val_w = col_width - load_label_w
    add_plain_pair("a. Nature of Goods & Packing:", get_survey_val('load_nature_packing'), "b. Weight of Goods:", get_survey_val('load_weight_goods'), load_label_w, load_val_w)
    add_plain_pair("c. Origin & Destination:", get_survey_val('load_origin_destination'), "d. L.R./Invoice No.:", get_survey_val('load_lr_invoice_no'), load_label_w, load_val_w)
    add_plain_pair("e. Name of Transport:", get_survey_val('load_transport_name'), "f. Date:", get_survey_val('load_date'), load_label_w, load_val_w)
    add_section_header("6) Reported date & time of accident")
    label_w_acc = 45; val_w_acc = col_width - label_w_acc
    add_plain_pair("a. Date & time of accident:", get_survey_val('accident_datetime'), "b. Assign. Received:", get_survey_val('accident_assign_received'), label_w_acc, val_w_acc)
    add_plain_pair("c. Date of survey:", get_survey_val('accident_survey_date'), "d. Place of accident:", get_survey_val('accident_place'), label_w_acc, val_w_acc)
    add_plain_pair("e. Place of Survey:", get_survey_val('accident_survey_place'), "", "", label_w_acc, usable_width - label_w_acc)
    add_section_header("7) Reported Police particulars:")
    label_w_pol = 45; val_w_pol = col_width - label_w_pol
    add_plain_pair("a. Accident reported to:", get_survey_val('police_reported_to'), "b. Diary / Case No.:", get_survey_val('police_diary_case_no'), label_w_pol, val_w_pol)
    add_plain_pair("c. Date Reported:", get_survey_val('police_date_reported'), "", "", label_w_pol, usable_width - label_w_pol)
    add_section_header("8) Other Details:")
    label_w_other = 45; val_w_other = col_width - label_w_other
    add_plain_pair("Details of T. P:", get_survey_val('tp_details'), "T.P. Injury/Loss:", get_survey_val('tp_injury_loss'), label_w_other, val_w_other)
    add_plain_pair("Injury to Driver/Occupant:", get_survey_val('injury_driver_occupant'), "Are damages consistent?:", get_survey_val('damages_consistent'), label_w_other, val_w_other)
    add_plain_pair("Cause and nature of accident:", get_survey_val('accident_cause'), "", "", label_w_other, usable_width - label_w_other)
    pdf.ln(5)
    add_plain_pair("Extent of consistent damages:", get_survey_val('damages_extent'), "", "", label_w_other, usable_width - label_w_other)
    pdf.ln(2); pdf.set_font("Helvetica", 'B', base_font_size_page1); pdf.cell(15, line_h_page1, "Remark:", border=0, new_x="RIGHT", new_y="TOP")
    pdf.set_font("Helvetica", '', base_font_size_page1); pdf.multi_cell(0, line_h_page1, get_survey_val('remark'), border=0, align='L')
    
    pdf.ln(1); 
    if not is_spot_report:
        pdf.set_x(pdf.w - pdf.r_margin - 20); pdf.cell(20, line_h_page1, normalize_pdf_text_for_fpdf("contd..."), align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    if is_spot_report:
        pdf.ln(5)
        pdf.set_font("Helvetica", '', base_font_size_page1)
        if spot_report_text:
            pdf.multi_cell(0, 5, spot_report_text, border=0, align='L')
        else:
            default_spot_text = "Since it is Spot/ Preliminary survey the above damages were observed without dismantling the vehicle. More damages may be unearthing after dismantling the vehicle & its parts.\n\nTotal N Nos. photographs of the insured accidentally damaged vehicle were snapped by the undersigned during the course of Spot/ Preliminary survey which are attached with my report."
            pdf.multi_cell(0, 5, normalize_pdf_text_for_fpdf(default_spot_text), border=0, align='L')
        
        pdf.ln(10)
        y_footer_start = pdf.get_y()
        if y_footer_start > 250: 
            pdf.add_page(orientation='P'); add_pdf_header(pdf)
            y_footer_start = pdf.get_y()

        pdf.set_xy(pdf.l_margin, y_footer_start)
        pdf.set_font("Helvetica", 'B', base_font_size_page1)
        pdf.cell(0, 5, "Enclosures:", border=0, new_x="LMARGIN", new_y="NEXT", align='L')
        
        pdf.set_font("Helvetica", '', base_font_size_page1)
        final_spot_enclosures = spot_report_enclosures if spot_report_enclosures else "1. Digital Photos\n2. Professional Bill"
        pdf.multi_cell(80, 5, final_spot_enclosures, border=0, align='L')

        pdf.set_xy(pdf.w - pdf.r_margin - 60, y_footer_start + 5) 
        pdf.ln(10) 
        pdf.set_x(pdf.w - pdf.r_margin - 60)
        pdf.set_font("Helvetica", 'B', 10)
        pdf.cell(60, 5, normalize_pdf_text_for_fpdf(u.full_name), border=0, new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.set_x(pdf.w - pdf.r_margin - 60)
        pdf.set_font("Helvetica", '', 9)
        pdf.cell(60, 5, "( Surveyor and Loss Assessor )", border=0, new_x="LMARGIN", new_y="NEXT", align='C')
        
    else:
        # --- Page 2: Labour Charges ---
        pdf.add_page(); pdf.set_margins(10, 10, 10); add_pdf_header(pdf); pdf.set_font("Helvetica", size=base_font_size_page2); usable_width_page2 = pdf.w - pdf.l_margin - pdf.r_margin
        top_info_y = pdf.get_y() 
        pdf.set_font("Helvetica", 'B', base_font_size_page2)
        gst_text = normalize_pdf_text_for_fpdf(f"GST: {header_gst_display}"); year_text_val = normalize_pdf_text_for_fpdf(f"Vehicle Year: {header_vehicle_year}")
        pdf.set_xy(pdf.l_margin, top_info_y); pdf.cell(60, line_h_page2, gst_text, border=0, new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(pdf.l_margin); pdf.cell(60, line_h_page2, year_text_val, border=0, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(line_h_page2 * 1.5)
        pdf.set_font("Helvetica", 'B', base_font_size_page1); pdf.cell(0, line_h_page2, normalize_pdf_text_for_fpdf("12) Allocation of Labour charges:"), border=0, new_x="LMARGIN", new_y="NEXT"); pdf.ln(line_h_page2 * 0.5)
        
        labour_widths = [80, 35, 35, 35]
        labour_headers_raw = ['Name of the parts', 'Removing/Refitting', 'Denting/Repairing', 'Painting']
        labour_headers = [normalize_pdf_text_for_fpdf(h) for h in labour_headers_raw]
        alignments_labour_headers = ['C', 'C', 'C', 'C']
        alignments_labour_rows = ['L', 'R', 'R', 'R']
        
        draw_table_row(pdf, labour_headers, labour_widths, line_h_page2, border=1, align='C', fill=True, text_color=(0,0,0), fill_color=(220,220,220), alignments=alignments_labour_headers, font_style='B', is_header=True, current_font_size=base_font_size_page2 -1)
        
        def safe_format_pdf_labour(val_str):
            try: num = float(str(val_str).replace(',', '')); return format_pdf_number(num)
            except (ValueError, TypeError): return normalize_pdf_text_for_fpdf(str(val_str))

        for row in processed_user_labour_rows_for_pdf:
            row_data = [
                row.get('part_name', ''),
                safe_format_pdf_labour(row.get('removing_refitting', '0')),
                safe_format_pdf_labour(row.get('denting_repairing', '0')),
                safe_format_pdf_labour(row.get('painting', '0'))
            ]
            estimated_row_height = calculate_height(row_data, labour_widths, base_font_size_page2 - 1, line_h_page2, table_cell_padding_y)
            if pdf.get_y() + estimated_row_height > pdf.page_break_trigger: pdf.add_page(); add_pdf_header(pdf); draw_table_row(pdf, labour_headers, labour_widths, line_h_page2, border=1, align='C', fill=True, text_color=(0,0,0), fill_color=(220,220,220), alignments=alignments_labour_headers, font_style='B', is_header=True, current_font_size=base_font_size_page2 -1)
            draw_table_row(pdf, row_data, labour_widths, line_h_page2, border=1, alignments=alignments_labour_rows, current_font_size=base_font_size_page2 -1)
        
        total_row_data_base_labour = [
            normalize_pdf_text_for_fpdf('TOTAL, Rs'),
            format_pdf_number(labour_sum_removing),
            format_pdf_number(labour_sum_denting),
            format_pdf_number(labour_sum_painting)
        ]
        draw_table_row(pdf, total_row_data_base_labour, labour_widths, line_h_page2, border='T', alignments=alignments_labour_rows, font_style='B', current_font_size=base_font_size_page2 -1)
        
        calc_widths = [150, 35]
        calc_alignments = ['L', 'R']
        
        def draw_calc_row(label, value, bold=False):
            row_data = [normalize_pdf_text_for_fpdf(label), format_pdf_number(value)]
            font_style = 'B' if bold else ''
            draw_table_row(pdf, row_data, calc_widths, line_h_page2, border=1, alignments=calc_alignments, font_style=font_style, current_font_size=base_font_size_page2 -1)

        draw_calc_row("Less: 12.5% (on paint material)", labour_paint_depn_final)
        if labour_imt_deduction > 0:
            draw_calc_row("Less: 50% Liability (As per IMT 23 Norms)", labour_imt_deduction)
        draw_calc_row("Total Painting Charges", net_paint_liability, bold=True)
        draw_calc_row("Add: Labour (R&R + Dent)", labour_rr_dent_sum)
        draw_calc_row("Total Taxable Labour", taxable_labour, bold=True)
        if labour_tax_type_main != 'Zero':
            draw_calc_row("Add: 18% GST", labour_gst_amount)
        draw_calc_row("Final Labour Liability", labour_grand_total_final, bold=True)
        pdf.ln(line_h_page2 * 1.5)
        
        # --- Page 3: Landscape Spare Parts Table ---
        pdf.add_page(orientation='L'); pdf.set_margins(10, 10, 10); add_pdf_header(pdf)
        pdf.set_auto_page_break(auto=False, margin=10) 
        pdf.set_font("Helvetica", size=base_font_size_page2)
        pdf.set_font("Helvetica", 'B', base_font_size_page1); pdf.cell(0, line_h_page2, normalize_pdf_text_for_fpdf("14. Cost of Spare Parts at MRP. :"), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT); pdf.ln(line_h_page2 * 0.5)
        parts_widths = [8, 8, 8, 55, 15, 19, 19, 19, 11, 8, 15, 23, 10, 15, 8, 15, 25]
        parts_headers_raw = ['Sl', 'E\nNo', 'Bill\nSL', 'Parts Descriptions', 'HNS\nCODE', 'Estimate\nAmount', 'Bill\nAmount', 'Assessed\nAmount', 'Parts\nType', 'Dep\n%', 'Dep.\nAMT', 'Net.\nAmount', 'GST\n%', 'GST\nAmount', 'IMT\n23', 'IMT-23\nAMT', 'Net AMT\nIncl. GST']
        parts_headers = [normalize_pdf_text_for_fpdf(h) for h in parts_headers_raw]
        alignments_parts_headers = ['C'] * 17
        alignments_parts_rows = ['C', 'C', 'C', 'L', 'C', 'R', 'R', 'R', 'C', 'C', 'R', 'R', 'C', 'R', 'C', 'R', 'R']
        
        draw_table_row(pdf, parts_headers, parts_widths, line_h_page2, border=1, align='C', fill=True, text_color=(0,0,0), fill_color=(200,200,200), alignments=alignments_parts_headers, font_style='B', is_header=True, current_font_size=base_font_size_page2 -1)
        pdf.set_text_color(0,0,0) 

        for idx, part in enumerate(final_parts_calculated):
            sl_no_str = normalize_pdf_text_for_fpdf(str(int(part.get('sl_no', 0))))
            est_sl_no_str = normalize_pdf_text_for_fpdf(part.get('est_sl_no', sl_no_str))
            bill_sl_no_str = normalize_pdf_text_for_fpdf(part.get('bill_sl_no', sl_no_str))
            dep_pc_display = "0%"
            if part.get('total_parts_amt', 0) > 0 and part.get('depr', 0) > 0:
                rate = (part.get('depr', 0) / part.get('total_parts_amt', 0)) * 100
                dep_pc_display = f"{rate:.0f}%"
            elif policy_type in ('NIL_DEPN', 'NIL_DEPN_PLUS'): dep_pc_display = "NIL"
            imt_23_display = "NIL"
            if part.get('imt_23_amt', 0) > 0: imt_23_display = "YES"

            part_data = [
                sl_no_str, est_sl_no_str, bill_sl_no_str, part.get('part_name_display', ''), normalize_pdf_text_for_fpdf(part.get('hns_code', '')), 
                format_pdf_number(part.get('estimate_amt', 0.0)), format_pdf_number(part.get('bill_amt', 0.0)), format_pdf_number(part.get('total_parts_amt', 0.0)),   
                normalize_pdf_text_for_fpdf(part.get('type_part', '')), normalize_pdf_text_for_fpdf(dep_pc_display), format_pdf_number(part.get('depr', 0.0)),              
                format_pdf_number(part.get('net_base', 0.0)), normalize_pdf_text_for_fpdf(f"{part.get('original_gst_pc', 0):.0f}%"), format_pdf_number(part.get('total_gst', 0.0)),         
                normalize_pdf_text_for_fpdf(imt_23_display), format_pdf_number(part.get('imt_23_amt', 0.0)), format_pdf_number(part.get('net_amt', 0.0))          
            ]
            dummy_pdf = FPDF(); dummy_pdf.add_page(); dummy_pdf.set_font("Helvetica", '', base_font_size_page2 - 1)
            max_lines = 1
            for j, txt in enumerate(part_data):
                lines = dummy_pdf.multi_cell(parts_widths[j], line_h_page2, str(txt), dry_run=True, output="LINES")
                max_lines = max(max_lines, len(lines))
            row_h = max_lines * line_h_page2 + table_cell_padding_y
            is_last_row = (idx == len(final_parts_calculated) - 1); needed_height = row_h
            if is_last_row: needed_height += (line_h_page2 + table_cell_padding_y) 
            if pdf.get_y() + needed_height > pdf.h - pdf.b_margin:
                pdf.add_page(orientation='L'); add_pdf_header(pdf)
                draw_table_row(pdf, parts_headers, parts_widths, line_h_page2, border=1, align='C', fill=True, text_color=(0,0,0), fill_color=(200,200,200), alignments=alignments_parts_headers, font_style='B', is_header=True, current_font_size=base_font_size_page2 -1)
                pdf.set_text_color(0,0,0)
            draw_table_row(pdf, part_data, parts_widths, line_h_page2, border=1, alignments=alignments_parts_rows, current_font_size=base_font_size_page2 -1)
        
        parts_total_row = ['', '', '', 'TOTAL', '', format_pdf_number(parts_total_estimate), format_pdf_number(parts_total_bill), format_pdf_number(parts_total_assessed), '', '', format_pdf_number(parts_depr_sum_final), format_pdf_number(parts_total_assessed - parts_depr_sum_final), '', format_pdf_number(parts_total_gst_final), '', format_pdf_number(parts_total_imt23), format_pdf_number(parts_net_amt_final)]        
        draw_table_row(pdf, parts_total_row, parts_widths, line_h_page2, border='T', alignments=alignments_parts_rows, font_style='B', current_font_size=base_font_size_page2 -1)
        pdf.ln(line_h_page2); pdf.set_auto_page_break(auto=True, margin=10)

        # --- Summary Section (Landscape) ---
        summary_start_y = pdf.get_y()
        if pdf.h - summary_start_y < 110: 
            pdf.add_page(orientation='L'); add_pdf_header(pdf); summary_start_y = pdf.get_y()
        
        left_col_x = pdf.l_margin; left_col_width = 80
        pdf.set_xy(left_col_x, summary_start_y)
        pdf.set_font("Helvetica", 'B', base_font_size_page2)
        pdf.cell(left_col_width/2, line_h_page2, "Estimates", border=1, new_x="RIGHT", new_y="TOP", align='L')
        pdf.cell(left_col_width/2, line_h_page2, "Amount", border=1, new_x="LMARGIN", new_y="NEXT", align='R')
        pdf.set_font("Helvetica", '', base_font_size_page2)
        
        est_labour_val = float(est_labour_override) if est_labour_override and is_number(est_labour_override) else labour_rr_dent_sum
        est_paint_val = float(est_paint_override) if est_paint_override and is_number(est_paint_override) else labour_sum_painting
        est_parts_val = float(est_parts_override) if est_parts_override and is_number(est_parts_override) else parts_total_estimate
        
        pdf.cell(left_col_width/2, line_h_page2, "Labour Charges", border=1, new_x="RIGHT", new_y="TOP", align='L')
        pdf.cell(left_col_width/2, line_h_page2, format_pdf_number(est_labour_val), border=1, new_x="LMARGIN", new_y="NEXT", align='R')
        pdf.cell(left_col_width/2, line_h_page2, "Paint cost", border=1, new_x="RIGHT", new_y="TOP", align='L')
        pdf.cell(left_col_width/2, line_h_page2, format_pdf_number(est_paint_val), border=1, new_x="LMARGIN", new_y="NEXT", align='R')
        pdf.cell(left_col_width/2, line_h_page2, "Cost of Parts", border=1, new_x="RIGHT", new_y="TOP", align='L')
        pdf.cell(left_col_width/2, line_h_page2, format_pdf_number(est_parts_val), border=1, new_x="LMARGIN", new_y="NEXT", align='R') 
        pdf.set_font("Helvetica", 'B', base_font_size_page2)
        approx_total = est_labour_val + est_paint_val + est_parts_val
        pdf.cell(left_col_width/2, line_h_page2, "Approximate Total", border=1, new_x="RIGHT", new_y="TOP", align='L')
        pdf.set_fill_color(255, 255, 0)
        pdf.cell(left_col_width/2, line_h_page2, format_pdf_number(approx_total), border=1, new_x="LMARGIN", new_y="NEXT", align='R', fill=True)

        right_col_x = pdf.l_margin + left_col_width + 5
        cols_liability = [55, 35, 42, 45] 
        pdf.set_xy(right_col_x, summary_start_y)
        
        pdf.set_fill_color(59, 130, 246); pdf.set_text_color(255,255,255)
        pdf.set_font("Helvetica", 'B', base_font_size_page2 - 1.5) 
        
        current_x = right_col_x
        header_labels = ["Descriptions", "Assessed Amount", "Total GST on A/Amount", "Liability Amount Inclu. GST"]
        for idx, h in enumerate(header_labels):
            pdf.set_xy(current_x, pdf.get_y())
            pdf.cell(cols_liability[idx], line_h_page2 + 2, normalize_pdf_text_for_fpdf(h), border=1, new_x="RIGHT", new_y="TOP", align='C', fill=True)
            current_x += cols_liability[idx]
        pdf.ln(line_h_page2 + 2); pdf.set_text_color(0,0,0)

        def add_new_summary_row(desc, assessed, gst, liability, bold=False, fill_color=None):
            pdf.set_x(right_col_x)
            if fill_color: pdf.set_fill_color(*fill_color)
            else: pdf.set_fill_color(255, 255, 255)
            
            pdf.set_font("Helvetica", 'B' if bold else '', base_font_size_page2)
            
            pdf.cell(cols_liability[0], line_h_page2, normalize_pdf_text_for_fpdf(desc), border=1, new_x="RIGHT", new_y="TOP", align='L', fill=bool(fill_color))
            pdf.cell(cols_liability[1], line_h_page2, format_pdf_number(assessed) if assessed != '' else '', border=1, new_x="RIGHT", new_y="TOP", align='R', fill=bool(fill_color))
            pdf.cell(cols_liability[2], line_h_page2, format_pdf_number(gst) if gst != '' else '', border=1, new_x="RIGHT", new_y="TOP", align='R', fill=bool(fill_color))
            pdf.cell(cols_liability[3], line_h_page2, format_pdf_number(liability) if liability != '' else '', border=1, new_x="LMARGIN", new_y="NEXT", align='R', fill=bool(fill_color))

        def add_less_row(label, val):
            pdf.set_x(right_col_x)
            pdf.set_fill_color(255, 255, 255)
            pdf.set_font("Helvetica", '', base_font_size_page2)
            pdf.cell(sum(cols_liability[:3]), line_h_page2, label, border=1, new_x="RIGHT", new_y="TOP", align='R')
            pdf.cell(cols_liability[3], line_h_page2, format_pdf_number(val), border=1, new_x="LMARGIN", new_y="NEXT", align='R')

        labour_assessed = labour_rr_dent_sum
        labour_gst = labour_assessed * 0.18 if labour_tax_type_main != 'Zero' else 0.0
        labour_liability = labour_assessed + labour_gst
        add_new_summary_row("TOTAL LABOUR", labour_assessed, labour_gst, labour_liability)

        paint_assessed = net_paint_liability
        paint_gst = paint_assessed * 0.18 if labour_tax_type_main != 'Zero' else 0.0
        paint_liability = paint_assessed + paint_gst
        add_new_summary_row("TOTAL PAINT", paint_assessed, paint_gst, paint_liability)

        cat_data = {'M': {'gst': 0.0, 'liability': 0.0}, 'G': {'gst': 0.0, 'liability': 0.0}, 'P': {'gst': 0.0, 'liability': 0.0}}
        for part in final_parts_calculated:
            p_type = str(part.get('type_part', 'M')).strip().upper()
            if p_type not in ['M', 'G', 'P']: p_type = 'M'
            
            p_net = float(part.get('net_amt', 0.0))
            gst_rate = float(part.get('original_gst_pc', 0.0))
            
            if gst_rate > 0:
                p_base_component = p_net / (1 + (gst_rate / 100.0))
                p_tax_component = p_net - p_base_component
            else:
                p_base_component = p_net
                p_tax_component = 0.0
                
            cat_data[p_type]['liability'] += p_net
            cat_data[p_type]['gst'] += p_tax_component

        m_assessed = cat_data['M']['liability'] - cat_data['M']['gst']
        add_new_summary_row("TOTAL METAL PARTS", m_assessed, cat_data['M']['gst'], cat_data['M']['liability'])
        g_assessed = cat_data['G']['liability'] - cat_data['G']['gst']
        add_new_summary_row("TOTAL GLASS PARTS", g_assessed, cat_data['G']['gst'], cat_data['G']['liability'])
        p_assessed = cat_data['P']['liability'] - cat_data['P']['gst']
        add_new_summary_row("TOTAL PLASTIC PARTS", p_assessed, cat_data['P']['gst'], cat_data['P']['liability'])

        total_liability = labour_liability + paint_liability + cat_data['M']['liability'] + cat_data['G']['liability'] + cat_data['P']['liability']
        pdf.set_x(right_col_x)
        pdf.set_fill_color(59, 130, 246); pdf.set_text_color(255,255,255); pdf.set_font("Helvetica", 'B', base_font_size_page2)
        pdf.cell(sum(cols_liability[:3]), line_h_page2, "Total :", border=1, new_x="RIGHT", new_y="TOP", align='R', fill=True)
        pdf.cell(cols_liability[3], line_h_page2, format_pdf_number(total_liability), border=1, new_x="LMARGIN", new_y="NEXT", align='R', fill=True)
        pdf.set_text_color(0,0,0)

        add_less_row("Less : Salvage", salvage_val_numeric)
        add_less_row("Less: Compulsory excess", excess_final)
        add_less_row("Less: Impose excess", impose_excess_final)
        
        net_settlement = total_liability - salvage_val_numeric - excess_final - impose_excess_final
        add_less_row("Net settlement Amount :", net_settlement)
        
        if policy_type == 'NIL_DEPN' and nd_deduction_amount > 0:
            nd_label = f"Less: {nd_deduction_pc:g}% on assessed amount as per ND policy norms"
            add_less_row(nd_label, nd_deduction_amount)
            net_settlement -= nd_deduction_amount
        
        if towing_charges > 0:
            add_less_row("Add: Towing Charges", towing_charges)
            net_settlement += towing_charges
        
        sig_height_block = 35 
        if pdf.get_y() + line_h_page2 + sig_height_block + 15 > pdf.page_break_trigger:
            pdf.add_page(orientation='L')
            add_pdf_header(pdf)
        
        pdf.set_x(right_col_x)
        pdf.set_fill_color(59, 130, 246); pdf.set_text_color(255,255,255); pdf.set_font("Helvetica", 'B', base_font_size_page2)
        pdf.cell(sum(cols_liability[:3]), line_h_page2, "Net settlement Amount Round off:", border=1, new_x="RIGHT", new_y="TOP", align='R', fill=True)
        pdf.cell(cols_liability[3], line_h_page2, format_pdf_number(round(net_settlement)), border=1, new_x="LMARGIN", new_y="NEXT", align='R', fill=True)
        pdf.set_text_color(0,0,0)

        final_y = pdf.get_y() + 5
        if parts_table_note:
            pdf.set_y(final_y)
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", 'B', base_font_size_page2)
            pdf.multi_cell(0, line_h_page2, parts_table_note, border=0, align='L')
            final_y = pdf.get_y() + 2

        if enclosures_text:
            pdf.set_font("Helvetica", '', base_font_size_page2)
            pdf.set_x(pdf.l_margin)
            lines = pdf.multi_cell(0, line_h_page2, enclosures_text, dry_run=True, output="LINES")
            enc_h = len(lines) * line_h_page2 + 10
            
            if final_y + enc_h + sig_height_block > pdf.page_break_trigger:
                pdf.add_page(orientation='L')
                add_pdf_header(pdf)
                final_y = pdf.get_y() + 5
            
            pdf.set_y(final_y)
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", 'B', base_font_size_page2)
            pdf.cell(0, line_h_page2, "Enclosures:", border=0, new_x="LMARGIN", new_y="NEXT", align='L')
            pdf.set_font("Helvetica", '', base_font_size_page2)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, line_h_page2, enclosures_text, border=0, align='L')
            final_y = pdf.get_y() + 5
        
        gap_stamp = 40
        sig_lines_height = line_h_page2 * 3
        if pdf.get_y() + gap_stamp + sig_lines_height > pdf.page_break_trigger:
            pdf.add_page(orientation='L')
            add_pdf_header(pdf)
            pdf.set_y(pdf.get_y() + 30)
        else:
            pdf.set_y(pdf.get_y() + gap_stamp)
        pdf.set_x(pdf.w - pdf.r_margin - 60); pdf.set_font("Helvetica", 'B', base_font_size_page2); pdf.cell(60, line_h_page2, normalize_pdf_text_for_fpdf(u.full_name), border=0, new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.set_x(pdf.w - pdf.r_margin - 60); pdf.set_font("Helvetica", '', 9); pdf.cell(60, line_h_page2, "( Surveyor and Loss Assessor )", border=0, new_x="LMARGIN", new_y="NEXT", align='C')

        # --- Re-inspection Page ---
        if report_type_raw == 'Re-inspection Report':
            pdf.add_page(orientation='P'); pdf.set_margins(10, 10, 10); add_pdf_header(pdf); pdf.set_auto_page_break(auto=False, margin=10) 
            pdf.set_font("Helvetica", 'B', 14); pdf.cell(0, 10, "RE-INSPECTION REPORT", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C'); pdf.ln(5)
            pdf.set_font("Helvetica", 'B', 10); pdf.cell(15, 5, "To,", border=0, new_x=XPos.RIGHT, new_y=YPos.TOP); pdf.set_font("Helvetica", '', 10)
            start_y_addr = pdf.get_y(); insurer_address = get_survey_val('insurer'); pdf.set_xy(pdf.l_margin + 15, start_y_addr); pdf.multi_cell(0, 5, insurer_address, border=0, align='L'); pdf.ln(5)
            pdf.set_font("Helvetica", 'B', 10); pdf.cell(15, 5, "Sub:", border=0, new_x=XPos.RIGHT, new_y=YPos.TOP); pdf.set_font("Helvetica", '', 10); pdf.cell(0, 5, f"Re-inspection of repaired vehicle bearing Regn. No. {get_survey_val('vehicle_regn_no')}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT); pdf.ln(5)
            pdf.set_font("Helvetica", '', 9); col1_w = 40; col2_w = 60; col3_w = 40; col4_w = 50 
            
            def draw_grid_row(label1, val1, label2=None, val2=None):
                h = 7; pdf.set_font("Helvetica", 'B', 9); pdf.cell(col1_w, h, label1, border=1, new_x="RIGHT", new_y="TOP", align='L')
                pdf.set_font("Helvetica", '', 9); pdf.cell(col2_w, h, val1, border=1, new_x="RIGHT", new_y="TOP", align='L')
                if label2: 
                    pdf.set_font("Helvetica", 'B', 9); pdf.cell(col3_w, h, label2, border=1, new_x="RIGHT", new_y="TOP", align='L')
                    pdf.set_font("Helvetica", '', 9); pdf.cell(col4_w, h, val2, border=1, new_x="LMARGIN", new_y="NEXT", align='L')
                else: 
                    pdf.ln(h)
            
            draw_grid_row("Policy No. :", get_survey_val('policy_no'), "Claim No. :", get_survey_val('claim_no'))
            draw_grid_row("Date of Accident :", get_survey_val('accident_datetime'), "Date of Survey :", get_survey_val('accident_survey_date'))
            pdf.set_font("Helvetica", 'B', 9); pdf.cell(col1_w, 7, "Insured :", border=1, new_x="RIGHT", new_y="TOP", align='L')
            x_val = pdf.get_x(); y_val = pdf.get_y()
            pdf.set_font("Helvetica", '', 9); insured_val = get_survey_val('insured'); width_val = col2_w + col3_w + col4_w; pdf.set_xy(x_val, y_val); pdf.multi_cell(width_val, 7, insured_val, border=1, align='L'); pdf.set_x(pdf.l_margin)
            draw_grid_row("Chassis No. :", get_survey_val('vehicle_chassis_no'), "Engine No. :", get_survey_val('vehicle_engine_no')); pdf.ln(5)
            pdf.set_font("Helvetica", '', 10); intro_text = "As per instruction received from your office, I visited the repairer's workshop. I have inspected the subject vehicle after repairs and verified the replaced parts. The details are as follows:"; pdf.multi_cell(0, 5, intro_text, border=0, align='L'); pdf.ln(5)
            re_cols = [12, 108, 30, 40]; re_headers = ["SL", "Name of the Parts", "Salvage", "Remarks"]; re_aligns = ['C', 'L', 'C', 'C']
            draw_table_row(pdf, re_headers, re_cols, 7, border=1, align='C', fill=True, text_color=(0,0,0), fill_color=(220,220,220), alignments=re_aligns, font_style='B', is_header=True, current_font_size=9); pdf.set_text_color(0,0,0)
            
            for part in final_parts_calculated:
                sl = str(part.get('sl_no')); name = part.get('part_name_display', ''); salvage = part.get('salvage_produce', 'YES'); remarks = part.get('remarks', 'REPLACED BY NEW'); row_data = [sl, name, salvage, remarks]
                if pdf.get_y() > 260: pdf.add_page(orientation='P'); add_pdf_header(pdf); draw_table_row(pdf, re_headers, re_cols, 7, border=1, align='C', fill=True, text_color=(0,0,0), fill_color=(220,220,220), alignments=re_aligns, font_style='B', is_header=True, current_font_size=9)
                draw_table_row(pdf, row_data, re_cols, 6, border=1, alignments=re_aligns, current_font_size=9)
            pdf.ln(5); pdf.set_font("Helvetica", 'B', 10); pdf.cell(0, 5, "Observations / Remarks:", border=0, new_x="LMARGIN", new_y="NEXT", align='L')
            pdf.set_font("Helvetica", '', 10); pdf.multi_cell(0, 5, reinspection_note, border=0, align='L'); pdf.ln(10)
            if pdf.get_y() > 250: pdf.add_page(orientation='P'); add_pdf_header(pdf)
            pdf.set_x(pdf.w - pdf.r_margin - 60); pdf.set_font("Helvetica", 'B', 10); pdf.cell(60, 5, normalize_pdf_text_for_fpdf(u.full_name), border=0, new_x="LMARGIN", new_y="NEXT", align='C')
            pdf.set_x(pdf.w - pdf.r_margin - 60); pdf.set_font("Helvetica", '', 9); pdf.cell(60, 5, "( Surveyor and Loss Assessor )", border=0, new_x="LMARGIN", new_y="NEXT", align='C')
            pdf.set_auto_page_break(auto=True, margin=15)

    # --- Page 4: Survey Fee Bill ---
    pdf.add_page(orientation='P'); pdf.set_margins(10, 10, 10); add_pdf_header(pdf); pdf.set_font("Helvetica", size=base_font_size_page3); usable_width_page3 = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.set_font("Helvetica", 'B', 14); pdf.cell(0, 10, normalize_pdf_text_for_fpdf("SURVEY FEE BILL"), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C'); pdf.ln(5)
    pdf.set_font("Helvetica", '', base_font_size_page3)
    ref_no_text_val = normalize_pdf_text_for_fpdf(f"Ref. No - {get_survey_val('report_no')}"); date_text_val = normalize_pdf_text_for_fpdf(f"Date- {get_survey_val('report_date')}"); date_width = pdf.get_string_width(date_text_val) + 2
    pdf.cell(usable_width_page3 - date_width, line_h_page3, ref_no_text_val, border=0, new_x=XPos.RIGHT, new_y=YPos.TOP); pdf.cell(date_width, line_h_page3, date_text_val, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='R')
    
    current_y_before_to = pdf.get_y() + line_h_page3 * 0.25; pdf.set_y(current_y_before_to)
    pdf.cell(10, line_h_page3, normalize_pdf_text_for_fpdf("To"), border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)
    address_start_x = pdf.l_margin + 10; pdf.set_xy(address_start_x, current_y_before_to) 
    insurer_address_full_raw = get_survey_val('insurer')
    insurer_address_full = normalize_pdf_text_for_fpdf(insurer_address_full_raw)
    insurer_address_lines = [line.strip() for line in insurer_address_full.split(',') if line.strip()]
    for idx, line in enumerate(insurer_address_lines):
        if pdf.get_y() + line_h_page3 > pdf.page_break_trigger - 10: 
            pdf.add_page(orientation='P'); add_pdf_header(pdf); pdf.set_font("Helvetica", '', base_font_size_page3); pdf.set_xy(address_start_x, pdf.get_y())
        pdf.multi_cell(usable_width_page3 - (address_start_x - pdf.l_margin), line_h_page3, line, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L') 
        if idx < len(insurer_address_lines) - 1: pdf.set_x(address_start_x)
    
    if p3_company_gstin:
        pdf.set_x(address_start_x)
        pdf.set_font("Helvetica", 'B', base_font_size_page3)
        pdf.cell(0, line_h_page3, normalize_pdf_text_for_fpdf(f"GSTIN: {p3_company_gstin}"), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_x(pdf.l_margin); pdf.ln(line_h_page3 * 0.5)
    if p3_customer_gstin:
        pdf.set_font("Helvetica", 'B', base_font_size_page3)
        pdf.cell(pdf.get_string_width("INSURED GST NO- ") + 1, line_h_page3, normalize_pdf_text_for_fpdf("INSURED GST NO- "), border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", '', base_font_size_page3)
        pdf.multi_cell(0, line_h_page3, p3_customer_gstin, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        pdf.ln(line_h_page3 * 0.25) 
        
    table_data_p3_header = [("Policy No:", get_survey_val('policy_no')), ("Claim No.-", get_survey_val('claim_no')), ("Regd No:", get_survey_val('vehicle_regn_no')), ("Insured :", get_survey_val('insured'))]
    label_col_width_p3_info_table = 30; value_col_width_p3_info_table = usable_width_page3 - label_col_width_p3_info_table
    for label_raw, value in table_data_p3_header:
        label = normalize_pdf_text_for_fpdf(label_raw) 
        if value:
            row_height_est = calculate_height([label, value], [label_col_width_p3_info_table, value_col_width_p3_info_table], base_font_size_page3, line_h_page3, table_cell_padding_y/2, ['', 'B'])
            if pdf.get_y() + row_height_est > pdf.page_break_trigger -10: 
                pdf.add_page(orientation='P'); add_pdf_header(pdf); pdf.set_font("Helvetica", '', base_font_size_page3)
            pdf.set_font("Helvetica", '', base_font_size_page3)
            pdf.cell(label_col_width_p3_info_table, line_h_page3, label, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_font("Helvetica", 'B', base_font_size_page3)
            pdf.multi_cell(value_col_width_p3_info_table, line_h_page3, value, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', max_line_height=line_h_page3) 
            
    pdf.ln(line_h_page3); pdf.set_font("Helvetica", '', base_font_size_page3); fee_name_width = usable_width_page3 * 0.75; fee_amount_width = usable_width_page3 * 0.25
    for item in p3_valid_fee_items: 
        if pdf.get_y() + line_h_page3 > pdf.page_break_trigger-10: pdf.add_page(orientation='P'); add_pdf_header(pdf); pdf.set_font("Helvetica", '', base_font_size_page3)
        pdf.cell(fee_name_width, line_h_page3, item['name'], border=1, new_x="RIGHT", new_y="TOP")
        pdf.cell(fee_amount_width, line_h_page3, format_pdf_number(item['amount']), border=1, align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
    if pdf.get_y() + line_h_page3 > pdf.page_break_trigger-10: pdf.add_page(orientation='P'); add_pdf_header(pdf); pdf.set_font("Helvetica", '', base_font_size_page3)
    photo_desc_raw = f"{p3_photo_copies_count} photograph copies @ Rs 10/- per Photograph"
    photo_desc = normalize_pdf_text_for_fpdf(photo_desc_raw)
    pdf.cell(fee_name_width, line_h_page3, photo_desc, border=1, new_x="RIGHT", new_y="TOP")
    pdf.cell(fee_amount_width, line_h_page3, format_pdf_number(p3_photo_total_charge), border=1, align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    if p3_total_before_gst != 0:
        pdf.set_font("Helvetica", '', base_font_size_page3)
        if p3_apply_gst:
            gst_lines_needed = 3 if labour_tax_type_main != 'IGST' else 2
            if pdf.get_y() + (line_h_page3 * gst_lines_needed) > pdf.page_break_trigger-10: pdf.add_page(orientation='P'); add_pdf_header(pdf); pdf.set_font("Helvetica", '', base_font_size_page3)
            pdf.cell(fee_name_width, line_h_page3, normalize_pdf_text_for_fpdf("Sub Total"), border='LR', new_x="RIGHT", new_y="TOP", align='R')
            pdf.cell(fee_amount_width, line_h_page3, format_pdf_number(p3_total_before_gst), border='LR', align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
            if labour_tax_type_main == 'IGST':
                if p3_igst != 0: 
                    pdf.cell(fee_name_width, line_h_page3, normalize_pdf_text_for_fpdf("Add, 18% IGST"), border='LR', new_x="RIGHT", new_y="TOP", align='R')
                    pdf.cell(fee_amount_width, line_h_page3, format_pdf_number(p3_igst), border='LR', align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            else:
                if p3_cgst != 0: 
                    pdf.cell(fee_name_width, line_h_page3, normalize_pdf_text_for_fpdf("Add, 9% CGST"), border='LR', new_x="RIGHT", new_y="TOP", align='R')
                    pdf.cell(fee_amount_width, line_h_page3, format_pdf_number(p3_cgst), border='LR', align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                if p3_sgst != 0: 
                    pdf.cell(fee_name_width, line_h_page3, normalize_pdf_text_for_fpdf("Add, 9% SGST"), border='LR', new_x="RIGHT", new_y="TOP", align='R')
                    pdf.cell(fee_amount_width, line_h_page3, format_pdf_number(p3_sgst), border='LR', align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            if pdf.get_y() + line_h_page3 > pdf.page_break_trigger-10: pdf.add_page(orientation='P'); add_pdf_header(pdf); pdf.set_font("Helvetica", '', base_font_size_page3)
        
        pdf.set_font("Helvetica", 'B', base_font_size_page3)
        pdf.cell(fee_name_width, line_h_page3, normalize_pdf_text_for_fpdf("Total Rupees"), border=1, new_x="RIGHT", new_y="TOP", align='R')
        pdf.cell(fee_amount_width, line_h_page3, format_pdf_number(p3_grand_total), border=1, align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
    pdf.ln(line_h_page3 * 0.5)
    
    # --- Surveyor Bank Details ---
    if surveyor_details:
        if pdf.get_y() + (line_h_page3 * 8) > pdf.page_break_trigger: pdf.add_page(orientation='P'); add_pdf_header(pdf)
        pdf.set_font("Helvetica", 'B', base_font_size_page3)
        start_x = pdf.l_margin
        col1_w = 25; col2_w = 60
        
        def add_bank_row(lbl, val):
            pdf.set_x(start_x)
            pdf.cell(col1_w, line_h_page3, normalize_pdf_text_for_fpdf(lbl), border=0, new_x="RIGHT", new_y="TOP", align='L')
            pdf.cell(col2_w, line_h_page3, normalize_pdf_text_for_fpdf(val), border=0, new_x="LMARGIN", new_y="NEXT", align='L')

        add_bank_row("GSTIN :", surveyor_details.get('gstin', ''))
        add_bank_row("PAN :", surveyor_details.get('pan', ''))
        add_bank_row("Bank Name :", surveyor_details.get('bank_name', ''))
        add_bank_row("A/c NO. :", surveyor_details.get('account_no', ''))
        add_bank_row("MICR No. :", surveyor_details.get('micr', ''))
        add_bank_row("IFS Code :", surveyor_details.get('ifsc', ''))
        
        state_val = surveyor_details.get('state_code', '(19)')
        code_val = surveyor_details.get('surveyor_code', '2075995')
        pdf.set_xy(start_x + col1_w + col2_w + 10, pdf.get_y() - (line_h_page3 * 6)) 
        pdf.cell(50, line_h_page3, normalize_pdf_text_for_fpdf(f"State : {state_val}"), border=0, new_x="LMARGIN", new_y="NEXT", align='L')
        pdf.set_x(start_x + col1_w + col2_w + 10)
        pdf.cell(50, line_h_page3, normalize_pdf_text_for_fpdf(f"Insurer's Surveyor Code No.: {code_val}"), border=0, new_x="LMARGIN", new_y="NEXT", align='L')
        pdf.set_y(pdf.get_y() + (line_h_page3 * 5))

    pdf.ln(line_h_page3 * 0.5) 
    if p3_grand_total_in_words and p3_grand_total != 0: 
        words_height_est = calculate_height([p3_grand_total_in_words], [usable_width_page3 - (pdf.get_string_width("Rupees ( In Words)- ") + 1)], base_font_size_page3, line_h_page3, table_cell_padding_y/2, ['B'])
        if pdf.get_y() + words_height_est > pdf.page_break_trigger-10: pdf.add_page(orientation='P'); add_pdf_header(pdf)
        pdf.set_font("Helvetica", '', base_font_size_page3); label_text_raw = "Rupees ( In Words)-"; label_text = normalize_pdf_text_for_fpdf(label_text_raw); current_label_width = pdf.get_string_width(label_text + " ") + 1
        pdf.cell(current_label_width, line_h_page3, label_text, border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", 'B', base_font_size_page3)
        pdf.multi_cell(usable_width_page3 - current_label_width, line_h_page3, p3_grand_total_in_words, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        
    pdf.ln(line_h_page3 * 0.5); pdf.set_font("Helvetica", '', base_font_size_page3)
    if pdf.get_y() + line_h_page3 > pdf.page_break_trigger-10: pdf.add_page(orientation='P'); add_pdf_header(pdf); pdf.set_font("Helvetica", '', base_font_size_page3)
    label_text_raw = "Estimated Amount = Rs."; label_text = normalize_pdf_text_for_fpdf(label_text_raw); current_label_width = pdf.get_string_width(label_text + " ") + 1
    pdf.cell(current_label_width, line_h_page3, label_text, border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font("Helvetica", 'B', base_font_size_page3)
    pdf.cell(usable_width_page3 - current_label_width, line_h_page3, format_pdf_number(p3_estimated_amount), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", '', base_font_size_page3); pdf.ln(line_h_page3 * 0.25) 
    
    # --- Final Assessed Amount & Signature ---
    sig_block_width = usable_width_page3 * 0.5
    sig_start_x = pdf.w - pdf.r_margin - sig_block_width
    sig_height_est = line_h_page3 * 7 
    assessed_amt_height = line_h_page3 * 3 if net_liability_final != 0 else 0
    gap_lines = 2
    total_block_needed = assessed_amt_height + (line_h_page3 * gap_lines) + sig_height_est

    
    if pdf.get_y() + total_block_needed > pdf.page_break_trigger: 
        pdf.add_page(orientation='P'); add_pdf_header(pdf); pdf.set_font("Helvetica", '', base_font_size_page3)
    
    if net_liability_final != 0: 
        pdf.set_font("Helvetica", '', base_font_size_page3)
        if policy_type == 'NIL_DEPN' and nd_deduction_amount > 0:
            nd_label_raw = f"Less: {nd_deduction_pc:g}% on assessed amount as per ND policy norms"
            nd_label_text = normalize_pdf_text_for_fpdf(nd_label_raw)
            nd_label_width = pdf.get_string_width(nd_label_text + " ") + 1
            pdf.cell(nd_label_width, line_h_page3, nd_label_text, border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_font("Helvetica", 'B', base_font_size_page3)
            pdf.cell(usable_width_page3 - nd_label_width, line_h_page3, format_pdf_number(nd_deduction_amount), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", '', base_font_size_page3)
        
        if towing_charges > 0:
            tow_label_raw = "Add: Towing Charges"
            tow_label_text = normalize_pdf_text_for_fpdf(tow_label_raw)
            tow_label_width = pdf.get_string_width(tow_label_text + " ") + 1
            pdf.cell(tow_label_width, line_h_page3, tow_label_text, border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_font("Helvetica", 'B', base_font_size_page3)
            pdf.cell(usable_width_page3 - tow_label_width, line_h_page3, format_pdf_number(towing_charges), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", '', base_font_size_page3)
        
        label_text_raw = "Net settlement Amount Round off:"; label_text = normalize_pdf_text_for_fpdf(label_text_raw); current_label_width = pdf.get_string_width(label_text + " ") + 1
        pdf.cell(current_label_width, line_h_page3, label_text, border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("Helvetica", 'B', base_font_size_page3)
        pdf.cell(usable_width_page3 - current_label_width, line_h_page3, format_pdf_number(net_liability_final), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(line_h_page3 * gap_lines)
    sig_included = data.get('include_signature', True) if isinstance(data, dict) else True
    if sig_included:
        sig_img_path = _private_signature_path(user_id)
        if sig_img_path:
            try:
                pdf.image(sig_img_path, x=sig_start_x + (sig_block_width - 40) / 2, y=pdf.get_y(), w=40)
                pdf.ln(18)
            except Exception:
                pass
            finally:
                _remove_temporary_signature(sig_img_path)

    pdf.set_x(sig_start_x); pdf.set_font("Helvetica", 'B', base_font_size_page3)
    pdf.cell(sig_block_width, line_h_page3, normalize_pdf_text_for_fpdf(u.full_name), border=0, new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_x(sig_start_x); pdf.set_font("Helvetica", '', base_font_size_page3)
    pdf.cell(sig_block_width, line_h_page3, "( Surveyor and Loss Assessor )", border=0, new_x="LMARGIN", new_y="NEXT", align='C')

    # --- Add Photo Pages ---
    def _extract_photos(sec_data):
        if isinstance(sec_data, dict):
            imgs = sec_data.get('images', [])
            per_p = sec_data.get('per_page', 4)
            return (imgs if isinstance(imgs, list) else []), per_p
        elif isinstance(sec_data, list):
            return sec_data, 4
        return [], 4

    p1_imgs, p1_per = _extract_photos(photos_data.get('first_inspection'))
    p2_imgs, p2_per = _extract_photos(photos_data.get('dismantling'))
    p3_imgs, p3_per = _extract_photos(photos_data.get('reinspection'))

    add_photo_section(pdf, "First inspection photo", get_survey_val('vehicle_regn_no'), p1_imgs, p1_per)
    add_photo_section(pdf, "Dismantling/follow up photo", get_survey_val('vehicle_regn_no'), p2_imgs, p2_per)
    add_photo_section(pdf, "Re-inspection photo", get_survey_val('vehicle_regn_no'), p3_imgs, p3_per)

    pdf_bytes = bytes(pdf.output())
    report_no = final_survey_data.get('report_no', 'SurveyReport')
    vehicle_no = final_survey_data.get('vehicle_regn_no', '')
    
    # Auto-upload privately to Google Drive
    drive_link = None
    try:
        filename_base = "".join(c for c in vehicle_no if c.isalnum() or c in ('_', '-')).rstrip() if vehicle_no.strip() else 'SurveyReport'
        filename_pdf = f"{filename_base}.pdf"
        drive_link = db.upload_report_pdf(pdf_bytes, filename_pdf, vehicle_no)
    except Exception as drive_err:
        print(f"Warning: Service Account Drive upload error: {drive_err}")

    return {
        "pdf_bytes": pdf_bytes,
        "report_no": report_no,
        "vehicle_no": vehicle_no,
        "drive_link": drive_link
    }


def render_fee_report(fee_data, user_data_snapshot, user_id, include_signature=True):
    """
    Generates a standalone Fee Invoice / Bill PDF.
    """
    u = UserSnapshot(user_data_snapshot)
    pdf = PDF(orientation='P', unit='mm', format='A4')
    pdf.alias_nb_pages()
    pdf.set_margins(12, 12, 12)
    pdf.add_page()

    add_pdf_header(pdf)

    line_h = 6
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 10, "FEE INVOICE / PROFESSIONAL BILL", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.ln(3)

    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(30, line_h, "Invoice No :", border=0)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(65, line_h, normalize_pdf_text_for_fpdf(fee_data.get('invoice_no', '')), border=0)
    
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(30, line_h, "Invoice Date :", border=0)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, line_h, normalize_pdf_text_for_fpdf(fee_data.get('invoice_date', '')), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(30, line_h, "Insurer Name :", border=0)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(65, line_h, normalize_pdf_text_for_fpdf(fee_data.get('insurer_name', '')), border=0)

    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(30, line_h, "Insured Name :", border=0)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, line_h, normalize_pdf_text_for_fpdf(fee_data.get('insured_name', '')), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(30, line_h, "Policy No :", border=0)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(65, line_h, normalize_pdf_text_for_fpdf(fee_data.get('policy_no', '')), border=0)

    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(30, line_h, "Claim No :", border=0)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, line_h, normalize_pdf_text_for_fpdf(fee_data.get('claim_no', '')), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(30, line_h, "Vehicle No :", border=0)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, line_h, normalize_pdf_text_for_fpdf(fee_data.get('vehicle_no', '')), border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(5)

    pdf.set_font("Helvetica", 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(20, 8, "Sl No", border=1, align='C', fill=True)
    pdf.cell(115, 8, "Description / Particulars", border=1, align='L', fill=True)
    pdf.cell(50, 8, "Amount (Rs.)", border=1, align='R', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    items = fee_data.get('items', [])
    if not items:
        items = []
        prof = float(fee_data.get('professional_fee', 0.0))
        survey_type = fee_data.get('survey_type') or 'Survey Fee'
        taxable = float(fee_data.get('taxable_amount', 0.0))
        
        if prof > 0:
            items.append({"name": f"Professional Fees ({survey_type})", "amount": prof})
        elif taxable > 0:
            items.append({"name": f"Professional Fees ({survey_type})", "amount": taxable})

        conv = float(fee_data.get('conveyance_fee', 0.0))
        if conv > 0:
            items.append({"name": "Conveyance & Traveling Charges", "amount": conv})

        photo = float(fee_data.get('photocopy_amount', 0.0))
        if photo > 0:
            items.append({"name": "Photocopy & Miscellaneous Charges", "amount": photo})

        if not items:
            items = [{"name": "Professional Survey & Loss Assessment Fees", "amount": taxable}]


    pdf.set_font("Helvetica", '', 10)
    sl = 1
    for it in items:
        pdf.cell(20, 8, str(sl), border=1, align='C')
        pdf.cell(115, 8, normalize_pdf_text_for_fpdf(it.get('name', '')), border=1, align='L')
        pdf.cell(50, 8, f"{float(it.get('amount', 0.0)):.2f}", border=1, align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        sl += 1

    taxable_amt = float(fee_data.get('taxable_amount', 0.0))
    gst_pc = float(fee_data.get('gst_pc', 18.0))
    gst_amt = float(fee_data.get('gst_amount', taxable_amt * (gst_pc / 100.0)))
    total_amt = float(fee_data.get('total_amount', taxable_amt + gst_amt))

    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(135, 8, "Taxable Amount", border=1, align='R')
    pdf.cell(50, 8, f"{taxable_amt:.2f}", border=1, align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.cell(135, 8, f"GST @ {gst_pc:g}%", border=1, align='R')
    pdf.cell(50, 8, f"{gst_amt:.2f}", border=1, align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.cell(135, 8, "Total Amount (Including GST)", border=1, align='R', fill=True)
    pdf.cell(50, 8, f"{total_amt:.2f}", border=1, align='R', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(5)
    in_words = number_to_words_indian(total_amt)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(0, 8, f"Amount in Words: {in_words}", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(15)
    sig_block_width = 80
    sig_start_x = 195 - 12 - sig_block_width

    sig_included = fee_data.get('include_signature', include_signature)
    if sig_included:
        sig_img_path = _private_signature_path(user_id)
        if sig_img_path:
            try:
                pdf.image(sig_img_path, x=sig_start_x + (sig_block_width - 40) / 2, y=pdf.get_y(), w=40)
                pdf.ln(18)
            except Exception:
                pass
            finally:
                _remove_temporary_signature(sig_img_path)

    pdf.set_x(sig_start_x)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(sig_block_width, 6, normalize_pdf_text_for_fpdf(u.full_name), border=0, new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_x(sig_start_x)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(sig_block_width, 6, "( Surveyor and Loss Assessor )", border=0, new_x="LMARGIN", new_y="NEXT", align='C')

    pdf_bytes = bytes(pdf.output())
    return {
        "pdf_bytes": pdf_bytes,
        "invoice_no": fee_data.get('invoice_no', 'FeeBill'),
        "vehicle_no": fee_data.get('vehicle_no', '')
    }
