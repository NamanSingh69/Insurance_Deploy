# modules/report_assessment.py

def get_backend_depreciation_rate(part_type, vehicle_year_str):
    """Calculates depreciation rate based on part type and vehicle age bucket integer."""
    part_type = str(part_type).strip().upper()
    try:
        year_bucket = int(vehicle_year_str) if vehicle_year_str else 0
    except ValueError:
        year_bucket = 0

    if part_type == 'G':
        return 0.0
    if part_type == 'P':
        return 50.0
    if part_type == 'M':
        if year_bucket <= 0: return 0.0
        elif year_bucket == 1: return 5.0
        elif year_bucket == 2: return 10.0
        elif year_bucket == 3: return 15.0
        elif year_bucket == 4: return 25.0
        elif year_bucket == 5: return 35.0
        elif 6 <= year_bucket <= 10: return 40.0
        elif year_bucket > 10: return 50.0
    return 0.0

def calculate_report_assessment_summary(assessment_data, survey_data):
    """
    Recalculates the entire assessment payload, populating all totals and writing
    calculated values back to parts and labour fields.
    """
    policy_type = assessment_data.get('policy_type', 'NORMAL')
    header_vehicle_year = assessment_data.get('header_vehicle_year', '')
    
    # 1. Page 3 Details (Fees and survey costs)
    page3_details = assessment_data.get('page3_details', {})
    customer_gstin = page3_details.get('customer_gstin', '')
    estimated_amount = 0.0
    try:
        est_str = str(page3_details.get('estimated_amount', '0')).replace(',', '')
        if est_str: estimated_amount = float(est_str)
    except (ValueError, TypeError):
        pass

    fee_items = page3_details.get('fee_items', [])
    photo_copies_str = str(page3_details.get('photo_copies_count', '0')).strip()
    photo_copies_count = int(photo_copies_str) if photo_copies_str.isdigit() else 0
    photo_total_charge = photo_copies_count * 10.0
    
    fees_subtotal = 0.0
    for item in fee_items:
        try:
            amt = float(str(item.get('amount', '0')).replace(',', ''))
            fees_subtotal += amt
        except (ValueError, TypeError):
            pass
            
    p3_total_before_gst = fees_subtotal + photo_total_charge
    p3_cgst = 0.0; p3_sgst = 0.0; p3_igst = 0.0
    labour_tax_type = assessment_data.get('labour_tax_type', 'CGST/SGST')

    if page3_details.get('apply_gst', True):
        if labour_tax_type == 'IGST':
            p3_igst = p3_total_before_gst * 0.18
        else:
            p3_cgst = p3_total_before_gst * 0.09
            p3_sgst = p3_total_before_gst * 0.09

    page3_gross_total = p3_total_before_gst + p3_cgst + p3_sgst + p3_igst
    
    # Update Page 3 back in dict
    page3_details['estimated_amount'] = estimated_amount
    page3_details['photo_copies_count'] = photo_copies_count
    
    # 2. Labour calculation
    labour_paint_depn_input = 0.0
    try:
        labour_paint_depn_input = float(assessment_data.get('labour_paint_depn', 0.0))
    except (ValueError, TypeError):
        pass

    user_labour_rows = assessment_data.get('user_labour_rows', [])
    total_removing = 0.0
    total_denting = 0.0
    total_painting = 0.0

    def safe_float(val, default=0.0):
        try: return float(str(val).replace(',', ''))
        except (ValueError, TypeError): return default

    for row in user_labour_rows:
        total_removing += safe_float(row.get('removing_refitting'))
        total_denting += safe_float(row.get('denting_repairing'))
        total_painting += safe_float(row.get('painting'))

    # Paint depreciation logic
    paint_depr_to_use = 0.0 if policy_type in ('NIL_DEPN', 'NIL_DEPN_PLUS') else labour_paint_depn_input
    net_paint_after_dep = max(0.0, total_painting - paint_depr_to_use)
    
    # Labour IMT 23 flag
    labour_imt_applied = assessment_data.get('labour_imt_applied', False)
    labour_imt_deduction = net_paint_after_dep * 0.5 if labour_imt_applied else 0.0
    net_paint_liability = net_paint_after_dep - labour_imt_deduction
    
    taxable_labour = total_removing + total_denting + net_paint_liability
    
    l_cgst = 0.0; l_sgst = 0.0; l_igst = 0.0
    if labour_tax_type != 'Zero':
        if labour_tax_type == 'IGST':
            l_igst = taxable_labour * 0.18
        else:
            l_cgst = taxable_labour * 0.09
            l_sgst = taxable_labour * 0.09
            
    labour_grand_total = taxable_labour + l_cgst + l_sgst + l_igst

    # 3. Parts calculation
    parts = assessment_data.get('parts', [])
    parts_total_base = 0.0
    parts_total_gst = 0.0
    parts_grand_total = 0.0
    parts_net_total = 0.0

    for part in parts:
        qty = safe_float(part.get('qty'), 1.0)
        part_amt = safe_float(part.get('part_amt'), 0.0)
        part_type = str(part.get('type_part', '')).strip()
        gst_applicable = part.get('gst_applicable', False)
        original_gst_pc = safe_float(part.get('original_gst_pc'), 0.0)
        imt_applied = part.get('imt_applied', False)

        total_parts_amt = qty * part_amt
        parts_total_base += total_parts_amt

        # Depreciation rate
        depr_rate = get_backend_depreciation_rate(part_type, header_vehicle_year)
        
        # User depr override
        saved_depr_val = safe_float(part.get('depr', '-1.0'), -1.0)
        
        if policy_type in ('NIL_DEPN', 'NIL_DEPN_PLUS'):
            depr_amt = 0.0
        elif saved_depr_val >= 0:
            depr_amt = saved_depr_val
        else:
            depr_amt = total_parts_amt * (depr_rate / 100.0)

        net_base = total_parts_amt - depr_amt
        total_gst = net_base * (original_gst_pc / 100.0) if gst_applicable else 0.0
        parts_total_gst += total_gst
        
        gross_post_dep = net_base + total_gst
        parts_grand_total += gross_post_dep

        imt_23_amt = gross_post_dep * 0.5 if imt_applied else 0.0
        net_amt = gross_post_dep - imt_23_amt
        parts_net_total += net_amt

        # Write back to part dictionary for persistence
        part['qty'] = qty
        part['part_amt'] = part_amt
        part['total_parts_amt'] = total_parts_amt
        part['depr'] = depr_amt
        part['total_gst'] = total_gst
        part['gross_amt'] = gross_post_dep
        part['imt_23_amt'] = imt_23_amt
        part['net_amt'] = net_amt

    # 4. Final totals
    deductibles = safe_float(assessment_data.get('deductibles'), 1000.0)
    impose_excess = safe_float(assessment_data.get('impose_excess'), 0.0)
    salvage = safe_float(assessment_data.get('salvage'), 0.0)
    
    net_liability = (labour_grand_total + parts_net_total) - deductibles - impose_excess - salvage
    
    # Apply ND deduction (only for NIL_DEPN policy)
    nd_deduction_amount = safe_float(assessment_data.get('nd_deduction_amount'), 0.0)
    towing_charges = safe_float(assessment_data.get('towing_charges'), 0.0)
    if policy_type == 'NIL_DEPN' and nd_deduction_amount > 0:
        net_liability -= nd_deduction_amount
    if towing_charges > 0:
        net_liability += towing_charges

    # Update assessment_data dict
    assessment_data['labour_painting_total'] = total_painting
    assessment_data['labour_denting_total'] = total_denting
    assessment_data['labour_total_base'] = total_removing + total_denting + net_paint_liability
    assessment_data['labour_cgst'] = l_cgst
    assessment_data['labour_sgst'] = l_sgst
    assessment_data['labour_igst'] = l_igst
    assessment_data['labour_grand_total'] = labour_grand_total
    
    assessment_data['parts_total_base'] = parts_total_base
    assessment_data['parts_total_gst'] = parts_total_gst
    assessment_data['parts_grand_total'] = parts_grand_total
    assessment_data['parts_net_total'] = parts_net_total
    
    assessment_data['deductibles'] = deductibles
    assessment_data['impose_excess'] = impose_excess
    assessment_data['net_liability'] = net_liability
    
    # Update page3 figures in nested structure
    page3_details['estimated_amount'] = estimated_amount
    page3_details['page3_cgst'] = p3_cgst
    page3_details['page3_sgst'] = p3_sgst
    page3_details['page3_igst'] = p3_igst
    page3_details['page3_gross_total'] = page3_gross_total

    return {
        'page3_gross_total': page3_gross_total,
        'page3_cgst': p3_cgst,
        'page3_sgst': p3_sgst,
        'page3_igst': p3_igst,
        'assessed_amount': net_liability,
        'estimated_amount': estimated_amount,
        'customer_gstin': customer_gstin
    }

def normalize_and_recalculate_report(report_data_dict):
    """Normalize and recalculate the report dictionary payload in place."""
    survey_data = report_data_dict.get('survey_report', {})
    assessment_data = report_data_dict.get('assessment', {})
    calculate_report_assessment_summary(assessment_data, survey_data)
    return report_data_dict
