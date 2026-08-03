# modules/gemini.py
import os
import re
import json
from google import genai
from google.genai import types
from google.genai.errors import APIError

EXPECTED_FIELDS = [
    "report_no", "report_date", "policy_no", "claim_no", "policy_validity",
    "insurer", "insured", "insured_contact_name", "insured_contact_no", "hypothecation", "idv", "policy_type_label",
    # Vehicle fields
    "vehicle_regn_no", "vehicle_regn_date", "vehicle_chassis_no", "vehicle_engine_no",
    "vehicle_make_model", "vehicle_type_body", "vehicle_cf_validity", "vehicle_seating",
    "vehicle_bhp_cc", "vehicle_pre_accident_condition", "vehicle_ulw", "vehicle_rlw",
    "vehicle_permit_no", "vehicle_permit_type", "vehicle_permit_validity",
    "vehicle_route_area", "vehicle_tax_token", "vehicle_tax_validity",
    "vehicle_odometer", "vehicle_colour", "class_of_vehicle", "regn_cert_no", "vehicle_cc",
    # DL fields
    "dl_name", "dl_no", "dl_issue_date", "dl_validity", "dl_issuing_authority",
    "dl_endorsement", "dl_type", "dl_dob",
    # Docs compared fields
    "doc_regn_cert", "doc_dl", "doc_tax_token", "doc_permit_compared",
    "doc_fitness_certificate", "doc_load_challan",
    # Load/Goods Details
    "load_nature_packing", "load_weight_goods", "load_origin_destination",
    "load_lr_invoice_no", "load_transport_name", "load_date",
    # Accident fields
    "accident_datetime", "accident_assign_received", "accident_survey_date",
    "accident_place", "accident_survey_place",
    # Police fields
    "police_reported_to", "police_diary_case_no", "police_date_reported",
    # Other fields
    "tp_details", "accident_cause", "damages_extent", "remark",
    "tp_injury_loss", "injury_driver_occupant", "damages_consistent"
]

def _score_model_for_intelligence(name):
    """Dynamically score models to prioritize pure intelligence/reasoning capabilities."""
    n = name.lower()
    score = 0
    m = re.search(r'(\d+)\.(\d+)', n)
    if m:
        major = int(m.group(1))
        minor = int(m.group(2))
        score += (major * 1000000) + (minor * 100000)
    if "pro" in n:
        score += 300000
    elif "flash-lite" in n:
        score += 0
    elif "flash" in n:
        score += 100000
    if any(kw in n for kw in ["thinking", "reasoning", "deep-think", "high"]):
        score += 90000
    elif "low" in n:
        score -= 150000
    if "exp" in n or "experimental" in n:
        score += 0
    elif "preview" in n:
        score += 20
    else:
        score += 50
    date_match = re.search(r'-(\d{4,8})', n)
    if date_match:
        val = int(date_match.group(1))
        score += (val % 20)
    return score

def get_best_models(client):
    """Query available models from Gemini API, rank them and return a sorted list."""
    default_models = sorted(['gemini-1.5-pro', 'gemini-1.5-flash'], key=lambda x: _score_model_for_intelligence(x), reverse=True)
    try:
        models = []
        for m in client.models.list():
            # Check supported action
            actions = getattr(m, 'supported_actions', []) or getattr(m, 'supported_generation_methods', [])
            if any("generateContent" in a for a in actions):
                clean_name = m.name.split('/')[-1] if '/' in m.name else m.name
                score = _score_model_for_intelligence(clean_name)
                models.append((clean_name, score))
        if not models:
            return default_models
        models.sort(key=lambda x: x[1], reverse=True)
        return [name for name, score in models]
    except Exception as e:
        print(f"[MODEL-SELECT] Error fetching models: {e}. Using defaults.")
        return default_models

def get_client_and_models(api_key, user_model=None):
    """Return a per-job Google GenAI client and primary/secondary model names."""
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=api_key)
    
    if user_model:
        primary = user_model
        secondary = user_model
    else:
        ranked = get_best_models(client)
        primary = ranked[0] if ranked else 'gemini-1.5-pro'
        secondary = ranked[1] if len(ranked) > 1 else primary

    return client, primary, secondary

def build_gemini_prompt():
    """Creates the detailed prompt for Gemini extraction."""
    return """
    You are an expert data extraction assistant specializing in Indian motor insurance claim documents.
    Analyze the provided PDF document which contains various supporting documents like Registration Certificate (RC), Driving License (DL), Insurance Policy, Claim Form, Repair Estimate/Pre-Invoice/Tax Invoice, etc.
    Your goal is to extract specific information for BOTH a Motor Final Survey Report AND a Repair Assessment Summary, ensuring all descriptive text is in English.

    **IMPORTANT INSTRUCTIONS:**
    1.  **Prioritize Typed Text & Clarity:** Strongly prefer machine-written/printed text. Choose the most clearly legible and complete value if multiple sources exist. Use handwritten only if typed is missing/illegible/overridden.
    2.  **Multi-line Data:** Combine multi-line data for a single field into one string.
    3.  **Transcribe to English:** Transcribe free-form text (addresses, descriptions, places, remarks, cause, damages, TP details, authority names, route area) to English if originally non-English. Extract names, IDs, technical specs as they are.
    4.  **Missing Information:** Use an empty string "" if information cannot be reliably found. Do NOT guess or provide defaults. Return "" for these. Specifically return "" for `vehicle_pre_accident_condition`, `dl_endorsement`, `police_reported_to`, `police_diary_case_no`, `police_date_reported`, `tp_details`, `accident_cause`, `damages_extent`, `remark`, `tp_injury_loss`, `injury_driver_occupant`, `damages_consistent` and all `load_*` fields if not found.
    5.  **Permit & Load Details:** Look for commercial vehicle permit and goods/load details. If found, populate `vehicle_permit_*`, `doc_permit_compared`, `doc_load_challan`, and all `load_*` fields. If private or no permit/load found, return "" for these.
    6.  **Tax Token:** Look for the Tax Token number, often labeled as Application Number or Receipt Number. Extract this value for `vehicle_tax_token`.
    7.  **Assessment Data Source:** Extract assessment data primarily from the **Job Card Retail - Tax Invoice** or **Pre-Invoice** section of the PDF.
    8.  **Labour Extraction (Table 12):** DO NOT extract labour totals (Painting/Denting).
    9.  **Parts Extraction (Table 13):** Extract EACH line item from the "Parts" section of the invoice. Include: Description (as Part Name), Quantity (Qty), Taxable Amount (calculate per unit if total is given), and Tax % (GST Rate).
    10. **Summary Extraction:** Extract "Deductibles" and "Salvage" amount if mentioned in the invoice summary.
    
    Return the extracted data STRICTLY in JSON format with the following nested structure:
    
    {
      "survey_report_data": {
        "report_no": "...",
        "report_date": "...", // Format DD.MM.YYYY
        "policy_no": "...",
        "claim_no": "...",
        "policy_validity": "...", // Format: "DD.MM.YYYY to DD.MM.YYYY"
        "insurer": "...",
        "insured": "...",
        "insured_contact_name": "...",
        "insured_contact_no": "...",
        "hypothecation": "...",
        "idv": "...",
        "policy_type_label": "...",
        "vehicle_regn_no": "...",
        "vehicle_regn_date": "...",
        "vehicle_chassis_no": "...",
        "vehicle_engine_no": "...",
        "vehicle_make_model": "...",
        "vehicle_type_body": "...",
        "vehicle_cf_validity": "...",
        "vehicle_seating": "...",
        "vehicle_bhp_cc": "...",
        "vehicle_pre_accident_condition": "...",
        "vehicle_ulw": "...",
        "vehicle_rlw": "...",
        "vehicle_permit_no": "...",
        "vehicle_permit_type": "...",
        "vehicle_permit_validity": "...",
        "vehicle_route_area": "...",
        "vehicle_tax_token": "...",
        "vehicle_tax_validity": "...",
        "vehicle_odometer": "...",
        "vehicle_colour": "...",
        "class_of_vehicle": "...",
        "regn_cert_no": "...",
        "vehicle_cc": "...",
        "dl_name": "...",
        "dl_no": "...",
        "dl_issue_date": "...",
        "dl_validity": "...",
        "dl_issuing_authority": "...",
        "dl_endorsement": "...",
        "dl_type": "...",
        "dl_dob": "...",
        "doc_regn_cert": "...",
        "doc_dl": "...",
        "doc_tax_token": "...",
        "doc_permit_compared": "...",
        "doc_fitness_certificate": "...",
        "doc_load_challan": "...",
        "load_nature_packing": "...",
        "load_weight_goods": "...",
        "load_origin_destination": "...",
        "load_lr_invoice_no": "...",
        "load_transport_name": "...",
        "load_date": "...",
        "accident_datetime": "...",
        "accident_assign_received": "...",
        "accident_survey_date": "...",
        "accident_place": "...",
        "accident_survey_place": "...",
        "police_reported_to": "...",
        "police_diary_case_no": "...",
        "police_date_reported": "...",
        "tp_details": "...",
        "accident_cause": "...",
        "damages_extent": "...",
        "remark": "...",
        "tp_injury_loss": "...",
        "injury_driver_occupant": "...",
        "damages_consistent": "..."
      },
      "assessment_data": {
        "customer_gstin": "...",
        "parts": [
          {
            "part_name": "...",
            "qty": "...",
            "part_amt": "...",
            "gst_pc": "..."
          }
        ],
        "deductibles": "...",
        "salvage": "..."
      }
    }

    Ensure the output is ONLY the JSON object, without any introductory text, explanations, or markdown formatting like ```json ... ```. Use "" for any field where the information cannot be reliably extracted.
    """

def build_invoice_gemini_prompt():
    """Creates a focused prompt for Gemini to extract parts data AND Customer GSTIN from an invoice."""
    return """
    You are an expert data extraction assistant specializing in Indian motor repair invoices/estimates.
    Analyze the provided PDF document which should be a Tax Invoice, Pre-Invoice, or Repair Estimate.
    Your goal is to extract:
    1.  The line items listed under the "Parts" or "Materials" section.
    2.  The Customer's GSTIN/UIN if available on the invoice.

    **IMPORTANT INSTRUCTIONS:**
    1.  **Focus:** Extract ONLY the parts list and the Customer GSTIN/UIN. Ignore labour charges, summaries, other addresses, vehicle details etc.
    2.  **Data Points (Parts):** For EACH part line item, extract:
        *   Part Name/Description
        *   Quantity (Qty)
        *   Taxable Amount (Rate per unit, or calculate if only total is given)
        *   Tax Rate Percentage (GST Rate %, e.g., "18", "28")
    3.  **Customer GSTIN/UIN:** Look for the recipient's (customer's) GSTIN. If multiple GSTINs are present, prioritize the one clearly associated with the customer or "Bill To" party. If not found, return "".
    4.  **Formatting:** Use numeric values where possible for Qty, Amount, and Tax Rate. If a value is not found or unclear, use an empty string "" or 0 where appropriate.
    5.  **Structure:** Return the extracted data STRICTLY in JSON format as follows:

    {
      "customer_gstin": "...",
      "parts": [
        {
          "part_name": "...",
          "qty": "...",
          "part_amt": "...",
          "gst_pc": "..."
        }
      ]
    }

    Ensure the output is ONLY the JSON object, without any introductory text, explanations, or markdown formatting like ```json ... ```. If no parts table is found, return {"customer_gstin": "", "parts": []}.
    """

def _clean_json_string(text):
    if not text:
        return "{}"
    text = text.strip()
    match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', text)
    if match:
        text = match.group(1)
    else:
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            text = text[first_brace:last_brace+1]
    text = re.sub(r',\s*([}\]])', r'\1', text)
    text = re.sub(r'(\s*)"(\w+)":\s*undefined', r'\1"\2": ""', text)
    text = re.sub(r'(\s*)"(\w+)":\s*null', r'\1"\2": ""', text)
    return text.strip()

def parse_gemini_response(response_text):
    """Parse JSON from Gemini's text response, applying defaults and structural mappings."""
    try:
        cleaned_text = _clean_json_string(response_text)
        data = json.loads(cleaned_text)

        survey_data_raw = data.get('survey_report_data', {})
        extracted_survey_data = {key: survey_data_raw.get(key, '') for key in EXPECTED_FIELDS}
        for key, value in extracted_survey_data.items():
            if value is None: extracted_survey_data[key] = ''

        assessment_data_raw = data.get('assessment_data', {})
        customer_gstin_from_ai = str(assessment_data_raw.get('customer_gstin', '')).strip()

        extracted_assessment_data = {
            'labour_painting_total': 0.0, 
            'labour_denting_total': 0.0, 
            'labour_total_base': 0.0, 
            'labour_cgst': 0.0, 
            'labour_sgst': 0.0, 
            'labour_igst': 0.0, 
            'labour_grand_total': 0.0, 
            'labour_paint_depn': 0.0, 
            'labour_grand_total_adjusted': 0.0, 
            'parts': [],
            'parts_total_base': 0.0,
            'parts_total_gst': 0.0,
            'parts_grand_total': 0.0,
            'parts_net_total': 0.0, 
            'deductibles': 1000.0,
            'impose_excess': 0.0,
            'salvage': "-",
            'net_liability': 0.0,
            'user_labour_rows': [], 
            'header_gst': '', 
            'header_vehicle_year': '', 
            'policy_type': 'NORMAL', 
            'nd_deduction_pc': 5,
            'nd_deduction_amount': 0,
            'towing_charges': 0,
            'report_type': 'Final Survey Report', 
            'claim_type': 'Cashless', 
            'labour_tax_type': 'CGST/SGST',
            'page3_details': {
                'customer_gstin': customer_gstin_from_ai, 
                'fee_items': [], 
                'estimated_amount': '',
                'photo_copies_count': '',
                'include_in_consolidated': False 
            },
            'note_text': "Note :- The subject policy covered with Depn. waiver", 
            'payment_to_text': "REPAIRER" 
        }

        parts_list_raw = assessment_data_raw.get('parts', [])
        processed_parts = []
        for idx, part_raw in enumerate(parts_list_raw):
            if not isinstance(part_raw, dict): continue
            try:
                qty_str = str(part_raw.get('qty', '1')).strip()
                part_amt_str = str(part_raw.get('part_amt', '0')).strip()
                gst_pc_str = str(part_raw.get('gst_pc', '0')).replace('%','').strip()

                qty = float(qty_str) if qty_str else 1.0
                part_amt = float(part_amt_str) if part_amt_str else 0.0
                original_gst_pc = float(gst_pc_str) if gst_pc_str else 0.0

                gst_applicable = original_gst_pc > 0
                total_parts_amt = qty * part_amt
                total_gst = total_parts_amt * (original_gst_pc / 100.0) if gst_applicable else 0.0
                gross_amt = total_parts_amt + total_gst
                net_amt = gross_amt

                processed_part = {
                    "sl_no": idx + 1,
                    "est_sl_no": "", 
                    "bill_sl_no": "", 
                    "part_name": str(part_raw.get('part_name', '')),
                    "hns_code": "",
                    "estimate_amt": gross_amt,
                    "bill_amt": total_parts_amt,
                    "type_part": "", 
                    "qty": qty, 
                    "part_amt": part_amt, 
                    "original_gst_pc": original_gst_pc,
                    "gst_applicable": gst_applicable,
                    "total_parts_amt": total_parts_amt, 
                    "total_gst": total_gst, 
                    "gross_amt": gross_amt, 
                    "depr": 0.0, 
                    "imt_23_amt": 0.0,
                    "net_amt": net_amt 
                }
                processed_parts.append(processed_part)
            except (ValueError, TypeError) as e:
                print(f"Warning: Could not parse part data for item {idx}: {part_raw}. Error: {e}")
        extracted_assessment_data['parts'] = processed_parts

        try:
            deductibles_raw = str(assessment_data_raw.get('deductibles', '')).strip()
            if deductibles_raw:
                 try:
                     extracted_assessment_data['deductibles'] = float(deductibles_raw)
                 except ValueError:
                     extracted_assessment_data['deductibles'] = 1000.0
            else:
                 extracted_assessment_data['deductibles'] = 1000.0
        except Exception:
             extracted_assessment_data['deductibles'] = 1000.0

        try:
            salvage_raw = str(assessment_data_raw.get('salvage', '')).strip()
            if salvage_raw:
                try: extracted_assessment_data['salvage'] = float(salvage_raw)
                except ValueError: extracted_assessment_data['salvage'] = salvage_raw 
            else:
                 extracted_assessment_data['salvage'] = "-" 
        except Exception:
            extracted_assessment_data['salvage'] = "-"

        return {
            "survey_report": extracted_survey_data,
            "assessment": extracted_assessment_data
        }

    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON response from AI. Error: {e}")
    except Exception as e:
        raise ValueError(f"An unexpected error occurred during response parsing. Error: {e}")

def parse_invoice_gemini_response(response_text):
    """Parse JSON containing parts data and customer_gstin from Gemini's invoice response."""
    try:
        cleaned_text = _clean_json_string(response_text)
        data = json.loads(cleaned_text)
        customer_gstin = str(data.get('customer_gstin', '')).strip()
        parts_list_raw = data.get('parts', [])
        if not isinstance(parts_list_raw, list):
             raise ValueError("Expected 'parts' key to contain a list.")

        extracted_parts = []
        for idx, part_raw in enumerate(parts_list_raw):
            if not isinstance(part_raw, dict): continue
            extracted_part = {
                "part_name": str(part_raw.get('part_name', '')).strip(),
                "qty": str(part_raw.get('qty', '1')).strip(), 
                "part_amt": str(part_raw.get('part_amt', '0')).strip(), 
                "gst_pc": str(part_raw.get('gst_pc', '0')).replace('%','').strip() 
            }
            extracted_parts.append(extracted_part)

        return {"customer_gstin": customer_gstin, "parts": extracted_parts}

    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from invoice AI response. Error: {e}")
    except Exception as e:
        raise ValueError(f"An unexpected error occurred during invoice response parsing: {e}")

def execute_gemini_task(api_key, pdf_part, user_model=None, is_invoice=False):
    """Perform content generation using google-genai with failover to secondary model."""
    client, primary, secondary = get_client_and_models(api_key, user_model)
    
    prompt = build_invoice_gemini_prompt() if is_invoice else build_gemini_prompt()
    prompt_part = types.Part.from_text(text=prompt)

    # Reconstruct input Part based on type
    if isinstance(pdf_part, dict) and 'file_data' in pdf_part:
        input_part = types.Part.from_uri(
            file_uri=pdf_part['file_data']['file_uri'],
            mime_type=pdf_part['file_data']['mime_type']
        )
    elif isinstance(pdf_part, dict) and 'data' in pdf_part:
        input_part = types.Part.from_bytes(
            data=pdf_part['data'],
            mime_type=pdf_part['mime_type']
        )
    else:
        raise ValueError("Invalid pdf_part input structure.")

    config = types.GenerateContentConfig(
        temperature=1.0,
        top_p=0.95,
        top_k=64,
        max_output_tokens=65536,
        response_mime_type="text/plain",
        safety_settings=[
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
    )

    response = None
    try:
        response = client.models.generate_content(
            model=primary,
            contents=[prompt_part, input_part],
            config=config
        )
    except Exception as e:
        print(f"Primary model ({primary}) generation failed: {e}. Trying secondary model ({secondary}).")
        response = client.models.generate_content(
            model=secondary,
            contents=[prompt_part, input_part],
            config=config
        )

    if not response or not response.text:
        raise ValueError("Received an empty or invalid response from the Gemini API.")

    response_text = response.text
    if is_invoice:
        return parse_invoice_gemini_response(response_text)
    else:
        return parse_gemini_response(response_text)
