import os
import io
import csv
import json
import secrets
import requests
import uuid
from urllib.parse import urlparse
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, send_file, abort, redirect, url_for, flash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from fpdf.errors import FPDFException
import re
import click
import base64
from db import db as sheets_db # We kept the variable name the same so it acts as standard drop-in replacement!

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

load_dotenv()

# --- Flask App Setup ---
app = Flask(__name__)
from werkzeug.middleware.proxy_fix import ProxyFix
# Fix for Vercel to handle secure cookies
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# --- Rate Limiting (Flask-Limiter) ---
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )
except ImportError:
    # Fallback in case requirements haven't been fully updated during dev
    class DummyLimiter:
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    limiter = DummyLimiter()

# --- SECURITY: SECRET_KEY must be set via environment variable ---
_secret_key = os.getenv("FLASK_SECRET_KEY")
if not _secret_key:
    if os.getenv("FLASK_ENV") == "development" or os.getenv("TESTING"):
        _secret_key = "dev-only-insecure-key-" + secrets.token_hex(16)
        print("WARNING: Using auto-generated SECRET_KEY for development. Set FLASK_SECRET_KEY for production.")
    else:
        raise ValueError("CRITICAL: FLASK_SECRET_KEY environment variable is not set. Refusing to start in production without it.")
app.config['SECRET_KEY'] = _secret_key

# --- SECURITY: Limit upload size to 100MB (user requested revert) ---
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

# --- SECURITY: Secure session cookies ---
app.config['SESSION_COOKIE_SECURE'] = True       # Only send over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True      # JavaScript cannot access cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'    # Prevent CSRF via cross-site requests
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)
app.config['REMEMBER_COOKIE_SECURE'] = True
app.config['REMEMBER_COOKIE_HTTPONLY'] = True

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' 
login_manager.login_message_category = 'info'

# --- Database Models (Adapted for Sheets) ---
class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data.get('id'))
        self.username = user_data.get('username')
        self.password_hash = user_data.get('password_hash')
        self.full_name = user_data.get('full_name')
        self.qualifications = user_data.get('qualifications')
        self.designation = user_data.get('designation')
        self.license_no = user_data.get('license_no')
        self.expiry_date = user_data.get('expiry_date')
        self.membership_no = user_data.get('membership_no')
        self.address_line_1 = user_data.get('address_line_1')
        self.address_line_2 = user_data.get('address_line_2')
        self.address_line_3 = user_data.get('address_line_3')
        self.contact_no = user_data.get('contact_no')
        self.email = user_data.get('email')

    def get_id(self):
        return self.id

    def __repr__(self):
        return f'<User {self.username}>'

# SavedReport class is no longer needed as an Object, we handle dicts directly or simple wrapper if needed.
# But existing code might rely on it if I don't catch all usages. 
# For now, I will return dicts from sheets_db and adapt logic.

# --- Flask-Login User Loader ---
@login_manager.user_loader
def load_user(user_id):
    user_data = sheets_db.get_user_by_id(user_id)
    if user_data:
        return User(user_data)
    return None

# --- Gemini API Configuration ---
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file.")

genai.configure(api_key=API_KEY)
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 65536, 
  "response_mime_type": "text/plain",
}
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# Use a model known for function calling or reliable JSON output if available
# For this example, we'll parse JSON from text response.
model = genai.GenerativeModel(
    model_name='gemini-3.1-pro-preview',
    safety_settings=safety_settings,
    generation_config=generation_config
    )

# Secondary model for fallback
secondary_model = genai.GenerativeModel(
    model_name='gemini-3.1-flash-lite-preview',
    safety_settings=safety_settings,
    generation_config=generation_config
)

# --- In-memory storage for generated files (Temporary before download) ---
generated_data_store = {}

# --- Define the expected fields based on the template ---
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

# --- Gemini Prompt Function ---
def build_gemini_prompt():
    """Creates the detailed prompt for Gemini extraction for both Survey Report and Assessment details."""
    # Prompt remains the same as before
    prompt = """
    You are an expert data extraction assistant specializing in Indian motor insurance claim documents.
    Analyze the provided PDF document which contains various supporting documents like Registration Certificate (RC), Driving License (DL), Insurance Policy, Claim Form, Repair Estimate/Pre-Invoice/Tax Invoice, etc.
    Your goal is to extract specific information for BOTH a Motor Final Survey Report AND a Repair Assessment Summary, ensuring all descriptive text is in English.

    **IMPORTANT INSTRUCTIONS:**
    1.  **Prioritize Typed Text & Clarity:** Strongly prefer machine-written/printed text. Choose the most clearly legible and complete value if multiple sources exist. Use handwritten only if typed is missing/illegible/overridden.
    2.  **Multi-line Data:** Combine multi-line data for a single field into one string.
    3.  **Transcribe to English:** Transcribe free-form text (addresses, descriptions, places, remarks, cause, damages, TP details, authority names, route area) to English if originally non-English. Extract names, IDs, technical specs as they are.
    4.  **Missing Information:** Use an empty string "" if information cannot be reliably found. Do NOT guess or provide defaults like 'Average', 'Not Known', 'Not Reported', 'N/A', 'No ( As Per Claim Form )', etc. Return "" for these. The application will handle defaults later. Specifically return "" for `vehicle_pre_accident_condition`, `dl_endorsement`, `police_reported_to`, `police_diary_case_no`, `police_date_reported`, `tp_details`, `accident_cause`, `damages_extent`, `remark`, `tp_injury_loss`, `injury_driver_occupant`, `damages_consistent` and all `load_*` fields if not found.
    5.  **Permit & Load Details:** Look for commercial vehicle permit and goods/load details. If found, populate `vehicle_permit_*`, `doc_permit_compared`, `doc_load_challan`, and all `load_*` fields. If private or no permit/load found, return "" for these.
    6.  **Tax Token:** Look for the Tax Token number, often labeled as Application Number or Receipt Number. Extract this value for `vehicle_tax_token`.
    7.  **Assessment Data Source:** Extract assessment data (Parts, Summary) primarily from the **Job Card Retail - Tax Invoice** or **Pre-Invoice** section of the PDF. Labour totals are NOT required from AI.
    8.  **Labour Extraction (Table 12):** DO NOT extract labour totals (Painting/Denting). This will be handled by user input.
    9.  **Parts Extraction (Table 13):** Extract EACH line item from the "Parts" section of the invoice. Include: Description (as Part Name), Quantity (Qty), Taxable Amount (calculate per unit if total is given), and Tax % (GST Rate).
    10. **Summary Extraction:** Extract "Deductibles" (or similar term like Excess/Compulsory Excess) and "Salvage" amount if mentioned in the invoice summary.
    
    Return the extracted data STRICTLY in JSON format with the following nested structure:
    
    {
      "survey_report_data": {
        "report_no": "...",
        "report_date": "...", // Format DD.MM.YYYY
        "policy_no": "...",
        "claim_no": "...",
        "policy_validity": "...", // Format: "DD.MM.YYYY to DD.MM.YYYY"
        "insurer": "...", // Full name & address (transcribed)
        "insured": "...", // Full name & address (transcribed)
        "insured_contact_name": "...", // Name of contact person for insured, if different from insured name. "" if not found.
        "insured_contact_no": "...", // Contact phone number for insured. "" if not found.
        "hypothecation": "...", // Financer name. "" if none.
        "idv": "...", // Insured Declared Value, number as string
        "policy_type_label": "...", // e.g., "Regular Policy", "Nil Depreciation"
        "vehicle_regn_no": "...", // a.
        "vehicle_regn_date": "...", // b. DD.MM.YYYY
        "vehicle_chassis_no": "...", // c.
        "vehicle_engine_no": "...", // d.
        "vehicle_make_model": "...", // e.
        "vehicle_type_body": "...", // f.
        "vehicle_cf_validity": "...", // g. DD.MM.YYYY
        "vehicle_seating": "...", // h. Number
        "vehicle_bhp_cc": "...", // i. e.g., "1197 cc"
        "vehicle_pre_accident_condition": "...", // j. Transcribed. "" if not found.
        "vehicle_ulw": "...", // k. e.g., "918 kg"
        "vehicle_rlw": "...", // l. e.g., "1355 kg"
        "vehicle_permit_no": "...", // m. "" if none/N/A.
        "vehicle_permit_type": "...", // n. "" if none/N/A.
        "vehicle_permit_validity": "...", // o. "" if none/N/A.
        "vehicle_route_area": "...", // p. Transcribed. "" if none/N/A.
        "vehicle_tax_token": "...", // q/m. Look for Application No., if not available then Receipt No., "" if none.
        "vehicle_tax_validity": "...", // r/n. "" if none.
        "vehicle_odometer": "...", // s/o. "" if not found.
        "vehicle_colour": "...", // t/p. "" if not found.
        "class_of_vehicle": "...", // e.g., "LMV", "Private Car"
        "regn_cert_no": "...", // RC document/certificate number
        "vehicle_cc": "...", // e.g., "2184"
        "dl_name": "...", // a.
        "dl_no": "...", // b.
        "dl_issue_date": "...", // c. DD.MM.YYYY
        "dl_validity": "...", // d. DD.MM.YYYY
        "dl_issuing_authority": "...", // e. Transcribed.
        "dl_endorsement": "...", // f. "" if not found.
        "dl_type": "...", // g.
        "dl_dob": "...", // h. DD.MM.YYYY
        "doc_regn_cert": "...", // a. YES/NO/- or ""
        "doc_dl": "...", // b. YES/NO/- or ""
        "doc_tax_token": "...", // c. YES/NO/- or ""
        "doc_permit_compared": "...", // d. YES/NO/- or "" if none/N/A.
        "doc_fitness_certificate": "...", // YES/NO/- or ""
        "doc_load_challan": "...", // YES/NO/- or ""
        "load_nature_packing": "...", // "" if not applicable
        "load_weight_goods": "...", // "" if not applicable
        "load_origin_destination": "...", // "" if not applicable
        "load_lr_invoice_no": "...", // "" if not applicable
        "load_transport_name": "...", // "" if not applicable
        "load_date": "...", // DD.MM.YYYY or ""
        "accident_datetime": "...", // a. e.g., "26.03.2025 at 07:00 Am"
        "accident_assign_received": "...", // b. DD.MM.YYYY
        "accident_survey_date": "...", // c. DD.MM.YYYY at HH:MM
        "accident_place": "...", // d. Transcribed.
        "accident_survey_place": "...", // e. Workshop address (transcribed).
        "police_reported_to": "...", // a. Transcribed. "" if not found.
        "police_diary_case_no": "...", // b. "" if not found.
        "police_date_reported": "...", // c. DD.MM.YYYY. "" if not found.
        "tp_details": "...", // 9. Transcribed. "" if not found.
        "accident_cause": "...", // 10. Transcribed. "" if not found.
        "damages_extent": "...", // 11. Transcribed. "" if not found.
        "remark": "...", // Transcribed. "" if not found.
        "tp_injury_loss": "...", // Short sentence or ""
        "injury_driver_occupant": "...", // Short sentence or ""
        "damages_consistent": "..." // "yes", "no", or ""
      },
      "assessment_data": {
        "customer_gstin": "...", // Extracted Customer GSTIN/UIN, or "" if not found
        "parts": [ // Array of extracted parts
          {
            "part_name": "...", // Description from invoice
            "qty": "...", // Quantity (numeric string or "")
            "part_amt": "...", // Taxable Amount PER UNIT (numeric string or ""). Calculate if necessary.
            "gst_pc": "..." // GST Percentage (numeric string like "18", "28", or "")
          }
          // ... more parts
        ],
        "deductibles": "...", // Extracted Deductibles/Excess amount (numeric string or "")
        "salvage": "..." // Extracted Salvage amount (numeric string or "")
      }
    }

    Ensure the output is ONLY the JSON object, without any introductory text, explanations, or markdown formatting like ```json ... ```. Use "" for any field where the information cannot be reliably extracted. For numeric fields in assessment_data, return numbers as strings, or "" if not found.
    """
    return prompt

def build_invoice_gemini_prompt():
    """Creates a focused prompt for Gemini to extract parts data AND Customer GSTIN from an invoice."""
    prompt = """
    You are an expert data extraction assistant specializing in Indian motor repair invoices/estimates.
    Analyze the provided PDF document which should be a Tax Invoice, Pre-Invoice, or Repair Estimate.
    Your goal is to extract:
    1.  The line items listed under the "Parts" or "Materials" section.
    2.  The Customer's GSTIN/UIN if available on the invoice (often labeled as "GSTIN", "Customer GSTIN", or similar).

    **IMPORTANT INSTRUCTIONS:**
    1.  **Focus:** Extract ONLY the parts list and the Customer GSTIN/UIN. Ignore labour charges, summaries, other addresses, vehicle details etc.
    2.  **Data Points (Parts):** For EACH part line item, extract:
        *   Part Name/Description
        *   Quantity (Qty)
        *   Taxable Amount (Rate per unit, or calculate if only total is given)
        *   Tax Rate Percentage (GST Rate %, e.g., "18", "28")
    3.  **Customer GSTIN/UIN:** Look for the recipient's (customer's) GSTIN. If multiple GSTINs are present, prioritize the one clearly associated with the customer or "Bill To" party. If not found, return "".
    4.  **Formatting:** Use numeric values where possible for Qty, Amount, and Tax Rate. If a value is not found or unclear, use an empty string "" or 0 where appropriate (0 for numeric fields if missing).
    5.  **Structure:** Return the extracted data STRICTLY in JSON format as follows:

    {
      "customer_gstin": "...", // Extracted Customer GSTIN/UIN, or "" if not found
      "parts": [ // Array of extracted parts
        {
          "part_name": "...", // Description from invoice
          "qty": "...", // Quantity (numeric string or "")
          "part_amt": "...", // Taxable Amount PER UNIT (numeric string or ""). Calculate if necessary.
          "gst_pc": "..." // GST Percentage (numeric string like "18", "28", or "")
        },
        // ... more parts
      ]
    }

    Ensure the output is ONLY the JSON object, without any introductory text, explanations, or markdown formatting like ```json ... ```. If no parts table is found, return {"customer_gstin": "", "parts": []}.
    """
    return prompt

# --- Gemini Response Parser ---
def parse_gemini_response(response_text):
    """
    Attempts to parse JSON from Gemini's text response, handling nested structure,
    performing initial calculations, attempting fixes, and preparing data for editable fields.
    """
    try:
        # Basic cleanup and fixes
        if response_text.strip().startswith("```json"):
            response_text = response_text.strip()[7:-3].strip()
        elif response_text.strip().startswith("```"):
             response_text = response_text.strip()[3:-3].strip()
        response_text = response_text.strip()
        response_text = re.sub(r',\s*([}\]])', r'\1', response_text) 
        response_text = re.sub(r'(\s*)"(\w+)":\s*undefined', r'\1"\2": ""', response_text)
        response_text = re.sub(r'(\s*)"(\w+)":\s*null', r'\1"\2": ""', response_text)

        data = json.loads(response_text)

        survey_data_raw = data.get('survey_report_data', {})
        extracted_survey_data = {key: survey_data_raw.get(key, '') for key in EXPECTED_FIELDS}
        for key, value in extracted_survey_data.items():
            if value is None: extracted_survey_data[key] = ''

        assessment_data_raw = data.get('assessment_data', {})
        
        # Initialize page3_details with customer_gstin from AI if present
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
            'impose_excess': 0.0, # New Field
            'salvage': "-",
            'net_liability': 0.0,
            'user_labour_rows': [], 
            'header_gst': '', 
            'header_vehicle_year': '', 
            'policy_type': 'NORMAL', 
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
                    "hns_code": "", # New Field
                    "estimate_amt": gross_amt, # Default to Gross
                    "bill_amt": total_parts_amt, # Default to Base
                    "type_part": "", 
                    "qty": qty, 
                    "part_amt": part_amt, 
                    "original_gst_pc": original_gst_pc,
                    "gst_applicable": gst_applicable,
                    "total_parts_amt": total_parts_amt, 
                    "total_gst": total_gst, 
                    "gross_amt": gross_amt, 
                    "depr": 0.0, 
                    "imt_23_amt": 0.0, # New Field
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
                     parsed_deductible = float(deductibles_raw)
                     extracted_assessment_data['deductibles'] = parsed_deductible
                 except ValueError:
                     extracted_assessment_data['deductibles'] = 1000.0
            else:
                 extracted_assessment_data['deductibles'] = 1000.0
        except Exception as e:
             extracted_assessment_data['deductibles'] = 1000.0

        try:
            salvage_raw = str(assessment_data_raw.get('salvage', '')).strip()
            if salvage_raw:
                try: extracted_assessment_data['salvage'] = float(salvage_raw)
                except ValueError: extracted_assessment_data['salvage'] = salvage_raw 
            else:
                 extracted_assessment_data['salvage'] = "-" 
        except Exception as e:
            extracted_assessment_data['salvage'] = "-"

        final_data = {
            "survey_report": extracted_survey_data,
            "assessment": extracted_assessment_data
        }
        return final_data

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error after attempting fixes: {e}")
        error_detail = f"Failed to parse JSON response from AI. Check logs. Error: {e}."
        raise ValueError(error_detail)
    except Exception as e:
        print(f"Error during parsing: {e}")
        import traceback
        traceback.print_exc()
        raise ValueError(f"An unexpected error occurred during response parsing. Error: {e}")

def parse_invoice_gemini_response(response_text):
    """
    Attempts to parse JSON containing parts data and customer_gstin from Gemini's invoice response.
    """
    try:
        # Basic cleanup (similar to main parser)
        if response_text.strip().startswith("```json"):
            response_text = response_text.strip()[7:-3].strip()
        elif response_text.strip().startswith("```"):
             response_text = response_text.strip()[3:-3].strip()
        response_text = response_text.strip()
        response_text = re.sub(r',\s*([}\]])', r'\1', response_text) # Remove trailing commas
        response_text = re.sub(r'(\s*)"(\w+)":\s*undefined', r'\1"\2": ""', response_text) # undefined -> ""
        response_text = re.sub(r'(\s*)"(\w+)":\s*null', r'\1"\2": ""', response_text) # null -> ""

        data = json.loads(response_text)

        customer_gstin = str(data.get('customer_gstin', '')).strip()
        parts_list_raw = data.get('parts', [])
        if not isinstance(parts_list_raw, list):
             raise ValueError("Expected 'parts' key to contain a list.")

        extracted_parts = []
        for idx, part_raw in enumerate(parts_list_raw):
            if not isinstance(part_raw, dict):
                print(f"Warning: Skipping non-dict item in parts list: {part_raw}")
                continue
            extracted_part = {
                "part_name": str(part_raw.get('part_name', '')).strip(),
                "qty": str(part_raw.get('qty', '1')).strip(), 
                "part_amt": str(part_raw.get('part_amt', '0')).strip(), 
                "gst_pc": str(part_raw.get('gst_pc', '0')).replace('%','').strip() 
            }
            extracted_parts.append(extracted_part)

        return {"customer_gstin": customer_gstin, "parts": extracted_parts}

    except json.JSONDecodeError as e:
        print(f"Invoice JSON Decode Error: {e}")
        print(f"Processed Invoice Response Text:\n---\n{response_text}\n---")
        raise ValueError(f"Failed to parse JSON from invoice AI response. Error: {e}")
    except Exception as e:
        print(f"Error during invoice response parsing: {e}")
        import traceback
        traceback.print_exc()
        raise ValueError(f"An unexpected error occurred during invoice response parsing: {e}")

def normalize_pdf_text_for_fpdf(text_val):
    """
    Replaces common problematic Unicode characters with their CP1252 equivalents
    or a standard ASCII alternative for FPDF's default fonts.
    This primarily targets characters that look like hyphens but are not the standard ASCII hyphen.
    """
    if not isinstance(text_val, str):
        text_val = str(text_val) # Ensure it's a string

    # Replace various dashes/hyphens with a standard hyphen (U+002D)
    text_val = text_val.replace('–', '-')  # En dash (U+2013)
    text_val = text_val.replace('—', '-')  # Em dash (U+2014)
    text_val = text_val.replace('−', '-')  # Minus sign (U+2212)
    
    # Aggressively replace all characters outside latin-1 to prevent fpdf.errors.FPDFUnicodeEncodingException
    text_val = text_val.encode('latin-1', 'replace').decode('latin-1')
    return text_val

def format_pdf_number(value):
    """Formats a number for PDF output. Shows '0' if zero, else formats to 2 decimal places."""
    try:
        num = float(value)
        if abs(num) < 0.001:
            return '0'
        else:
            return f"{num:.2f}"
    except (ValueError, TypeError):
         val_str = str(value)
         if val_str.strip() == '0':
             return '0'
         return normalize_pdf_text_for_fpdf(val_str)

# --- Security: URL Validation Helper ---
def _is_safe_redirect_url(target):
    """Validate that a redirect URL is safe (relative, same-host only)."""
    if not target:
        return False
    parsed = urlparse(target)
    # Only allow relative URLs (no scheme/netloc) that don't start with //
    return not parsed.scheme and not parsed.netloc and not target.startswith('//')

# --- Security: SSRF Allowlist for Proxy Endpoints ---
_ALLOWED_UPLOAD_DOMAINS = {'www.googleapis.com', 'googleapis.com'}

def _is_allowed_upload_url(url):
    """Validate that the upload URL targets only allowed Google API domains."""
    try:
        parsed = urlparse(url)
        return parsed.scheme == 'https' and parsed.hostname in _ALLOWED_UPLOAD_DOMAINS
    except Exception:
        return False

# --- Security Headers ---
@app.after_request
def set_security_headers(response):
    """Add security headers to every response."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    # HSTS: only set if on HTTPS (Vercel always serves HTTPS)
    if request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# --- Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_data = sheets_db.get_user_by_username(username)
        
        if user_data and bcrypt.check_password_hash(user_data['password_hash'], password):
            user = User(user_data)
            login_user(user, remember=True)
            # SECURITY: Validate 'next' parameter to prevent open redirect (VULN-04)
            next_page = request.args.get('next')
            if next_page and _is_safe_redirect_url(next_page):
                redirect_target = next_page
            else:
                redirect_target = url_for('index')
            flash('Login Successful!', 'success')
            return redirect(redirect_target)
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- Google OAuth2 Configuration ---
GOOGLE_OAUTH_CLIENT_ID = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
GOOGLE_OAUTH_SCOPES = ['https://www.googleapis.com/auth/drive.file']

@app.route('/auth/google')
@login_required
def google_auth():
    """Initiate Google OAuth2 flow for Drive access."""
    from flask import session
    if not GOOGLE_OAUTH_CLIENT_ID or not GOOGLE_OAUTH_CLIENT_SECRET:
        return jsonify({'error': 'Google OAuth not configured'}), 500
    
    # Determine redirect URI based on request
    if request.host.startswith('localhost') or request.host.startswith('127.0.0.1'):
        redirect_uri = url_for('google_auth_callback', _external=True)
    else:
        redirect_uri = f"https://{request.host}/auth/google/callback"
    
    # SECURITY: Generate OAuth state token to prevent CSRF on callback (VULN-07)
    oauth_state = secrets.token_urlsafe(32)
    session['oauth_state'] = oauth_state
    
    auth_url = (
        'https://accounts.google.com/o/oauth2/v2/auth?'
        f'client_id={GOOGLE_OAUTH_CLIENT_ID}&'
        f'redirect_uri={redirect_uri}&'
        'response_type=code&'
        f'scope={" ".join(GOOGLE_OAUTH_SCOPES)}&'
        'access_type=offline&'
        'prompt=consent&'
        f'state={oauth_state}'
    )
    return redirect(auth_url)

@app.route('/auth/google/callback')
@login_required
def google_auth_callback():
    """Handle OAuth2 callback and store tokens."""
    from flask import session
    
    code = request.args.get('code')
    error = request.args.get('error')
    returned_state = request.args.get('state')
    
    # SECURITY: Verify OAuth state token to prevent CSRF (VULN-07)
    expected_state = session.pop('oauth_state', None)
    if not returned_state or returned_state != expected_state:
        flash('OAuth security verification failed. Please try again.', 'error')
        return redirect(url_for('index'))
    
    if error:
        flash(f'Google authorization failed: {error}', 'error')
        return redirect(url_for('index'))
    
    if not code:
        flash('No authorization code received', 'error')
        return redirect(url_for('index'))
    
    # Determine redirect URI (must match the one used in auth request)
    if request.host.startswith('localhost') or request.host.startswith('127.0.0.1'):
        redirect_uri = url_for('google_auth_callback', _external=True)
    else:
        redirect_uri = f"https://{request.host}/auth/google/callback"
    
    # Exchange code for tokens
    token_response = requests.post(
        'https://oauth2.googleapis.com/token',
        data={
            'client_id': GOOGLE_OAUTH_CLIENT_ID,
            'client_secret': GOOGLE_OAUTH_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri
        }
    )
    
    if token_response.status_code != 200:
        flash('Failed to get access token from Google', 'error')
        return redirect(url_for('index'))
    
    tokens = token_response.json()
    
    # Store tokens in session
    session['google_access_token'] = tokens.get('access_token')
    session['google_refresh_token'] = tokens.get('refresh_token')
    session['google_token_expiry'] = tokens.get('expires_in', 3600)
    
    flash('Successfully connected to Google Drive!', 'success')
    return redirect(url_for('index'))

@app.route('/auth/google/status')
@login_required
def google_auth_status():
    """Check if user has connected Google Drive."""
    from flask import session
    has_token = 'google_access_token' in session and session['google_access_token']
    return jsonify({'connected': has_token})

@app.route('/auth/google/disconnect', methods=['POST'])
@login_required
def google_auth_disconnect():
    """Disconnect Google Drive."""
    from flask import session
    session.pop('google_access_token', None)
    session.pop('google_refresh_token', None)
    session.pop('google_token_expiry', None)
    return jsonify({'success': True, 'message': 'Disconnected from Google Drive'})

@app.route('/get_user_upload_url', methods=['POST'])
@login_required
def get_user_upload_url():
    """Get upload URL using user's OAuth token (for large files)."""
    from flask import session
    
    access_token = session.get('google_access_token')
    if not access_token:
        return jsonify({'error': 'Not connected to Google Drive. Please connect first.'}), 401
    
    data = request.get_json()
    filename = data.get('filename')
    mime_type = data.get('mime_type', 'application/pdf')
    
    if not filename:
        return jsonify({'error': 'Filename required'}), 400
    
    # Initiate resumable upload with user's token
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'X-Upload-Content-Type': mime_type,
    }
    
    metadata = {
        'name': filename,
        'mimeType': mime_type
    }
    
    response = requests.post(
        'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable',
        headers=headers,
        json=metadata
    )
    
    if response.status_code == 200:
        upload_url = response.headers.get('Location')
        return jsonify({'url': upload_url, 'access_token': access_token})
    elif response.status_code == 401:
        # Token expired, try to refresh
        refresh_token = session.get('google_refresh_token')
        if refresh_token:
            # Attempt token refresh
            refresh_response = requests.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'client_id': GOOGLE_OAUTH_CLIENT_ID,
                    'client_secret': GOOGLE_OAUTH_CLIENT_SECRET,
                    'refresh_token': refresh_token,
                    'grant_type': 'refresh_token'
                }
            )
            if refresh_response.status_code == 200:
                new_tokens = refresh_response.json()
                session['google_access_token'] = new_tokens.get('access_token')
                # Retry upload URL request
                headers['Authorization'] = f"Bearer {new_tokens.get('access_token')}"
                retry_response = requests.post(
                    'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable',
                    headers=headers,
                    json=metadata
                )
                if retry_response.status_code == 200:
                    upload_url = retry_response.headers.get('Location')
                    return jsonify({'url': upload_url, 'access_token': new_tokens.get('access_token')})
        
        session.pop('google_access_token', None)
        return jsonify({'error': 'Google Drive authorization expired. Please reconnect.'}), 401
    else:
        print(f"Failed to get user upload URL: {response.text}")
        return jsonify({'error': f'Failed to initiate upload: {response.status_code}'}), 500

# --- Main Application Routes ---
@app.route('/')
@login_required
def index():
    return render_template('index.html')



@app.route('/get_gemini_upload_url', methods=['POST'])
def get_gemini_upload_url():
    data = request.get_json()
    filename = data.get('filename', 'document.pdf')
    size = data.get('size')
    mime_type = data.get('mime_type', 'application/pdf')
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return jsonify({"error": "No API key"}), 500
        
    headers = {
        'X-Goog-Upload-Protocol': 'resumable',
        'X-Goog-Upload-Command': 'start',
        'X-Goog-Upload-Header-Content-Length': str(size),
        'X-Goog-Upload-Header-Content-Type': mime_type,
        'Content-Type': 'application/json'
    }
    
    metadata = {
        'file': {
            'display_name': filename
        }
    }
    
    url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={api_key}"
    resp = requests.post(url, headers=headers, json=metadata)
    
    if resp.status_code != 200:
        return jsonify({"error": f"Failed to get upload URL: {resp.text}"}), 500
        
    upload_url = resp.headers.get('X-Goog-Upload-URL')
    return jsonify({"url": upload_url})

def download_drive_file_with_token(access_token, file_id):
    """Downloads file content from Drive using the user's OAuth access token."""
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(
            f'https://www.googleapis.com/drive/v3/files/{file_id}?alt=media',
            headers=headers
        )
        if response.status_code == 200:
            return response.content
        else:
            print(f"Failed to download file {file_id} with user token: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error downloading file with user token: {e}")
        return None

def _find_or_create_drive_folder(access_token, folder_name, parent_id=None):
    """Finds a folder by name in Drive (under optional parent), or creates it."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    headers = {'Authorization': f'Bearer {access_token}'}
    search_resp = requests.get(
        'https://www.googleapis.com/drive/v3/files',
        headers=headers,
        params={'q': query, 'fields': 'files(id,name)', 'spaces': 'drive'}
    )
    
    if search_resp.status_code == 200:
        files = search_resp.json().get('files', [])
        if files:
            return files[0]['id']
    
    # Create the folder
    metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        metadata['parents'] = [parent_id]
    
    create_resp = requests.post(
        'https://www.googleapis.com/drive/v3/files',
        headers={**headers, 'Content-Type': 'application/json'},
        json=metadata
    )
    
    if create_resp.status_code == 200:
        return create_resp.json().get('id')
    
    print(f"Failed to create folder '{folder_name}': {create_resp.status_code} - {create_resp.text}")
    return None

def upload_pdf_to_drive(access_token, pdf_bytes, filename, folder_name):
    """
    Uploads a PDF to the user's Drive inside 'Survey Reports/{folder_name}/'.
    If a file with the same name exists in that folder, it is replaced.
    Returns the web view link on success, None on failure.
    """
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # 1. Find or create "Survey Reports" root folder
        root_folder_id = _find_or_create_drive_folder(access_token, 'Survey Reports')
        if not root_folder_id:
            print("Failed to find/create 'Survey Reports' folder")
            return None
        
        # 2. Find or create vehicle subfolder
        vehicle_folder_id = _find_or_create_drive_folder(access_token, folder_name, root_folder_id)
        if not vehicle_folder_id:
            print(f"Failed to find/create '{folder_name}' folder")
            return None
        
        # 3. Check if file already exists in that folder (to update instead of duplicate)
        query = f"name='{filename}' and '{vehicle_folder_id}' in parents and trashed=false"
        search_resp = requests.get(
            'https://www.googleapis.com/drive/v3/files',
            headers=headers,
            params={'q': query, 'fields': 'files(id)', 'spaces': 'drive'}
        )
        
        existing_file_id = None
        if search_resp.status_code == 200:
            files = search_resp.json().get('files', [])
            if files:
                existing_file_id = files[0]['id']
        
        # 4. Upload or update the PDF
        if existing_file_id:
            # Update existing file content
            upload_resp = requests.patch(
                f'https://www.googleapis.com/upload/drive/v3/files/{existing_file_id}?uploadType=media&fields=id,webViewLink',
                headers={**headers, 'Content-Type': 'application/pdf'},
                data=pdf_bytes
            )
        else:
            # Create new file with multipart upload
            import json as json_module
            boundary = '----DriveUploadBoundary'
            metadata = json_module.dumps({
                'name': filename,
                'parents': [vehicle_folder_id],
                'mimeType': 'application/pdf'
            })
            
            body = (
                f'--{boundary}\r\n'
                f'Content-Type: application/json; charset=UTF-8\r\n\r\n'
                f'{metadata}\r\n'
                f'--{boundary}\r\n'
                f'Content-Type: application/pdf\r\n\r\n'
            ).encode('utf-8') + pdf_bytes + f'\r\n--{boundary}--'.encode('utf-8')
            
            upload_resp = requests.post(
                'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,webViewLink',
                headers={**headers, 'Content-Type': f'multipart/related; boundary={boundary}'},
                data=body
            )
        
        if upload_resp.status_code in (200, 201):
            result = upload_resp.json()
            return result.get('webViewLink', f"https://drive.google.com/file/d/{result.get('id')}/view")
        else:
            print(f"Drive upload failed: {upload_resp.status_code} - {upload_resp.text}")
            return None
            
    except Exception as e:
        print(f"Error uploading PDF to Drive: {e}")
        import traceback; traceback.print_exc()
        return None

@app.route('/upload_report_to_drive', methods=['POST'])
@login_required
def upload_report_to_drive():
    """Upload the generated report PDF to Google Drive (service account)."""
    data = request.get_json()
    request_id = data.get('request_id')
    
    if not request_id or request_id not in generated_data_store:
        return jsonify({'error': 'Report not found. Please generate the report first.'}), 404
    
    report_data = generated_data_store[request_id]
    pdf_bytes = report_data.get('pdf_report')
    vehicle_no = report_data.get('vehicle_no', '').strip()
    report_no = report_data.get('report_no', 'SurveyReport')
    
    if not pdf_bytes:
        return jsonify({'error': 'No PDF data found for this report.'}), 400
    
    filename_base = "".join(c for c in vehicle_no if c.isalnum() or c in ('_', '-')).rstrip() if vehicle_no else report_no.replace(' ', '_').replace('/', '-')
    filename = f"{filename_base}.pdf"
    folder_name_to_use = "".join(c for c in vehicle_no if c.isalnum() or c in ('_', '-', ' ')).strip() if vehicle_no else 'Unknown_Vehicle'
    
    from flask import session
    access_token = session.get('google_access_token')
    
    drive_link = None
    if access_token:
        # Upload to user's personal drive
        drive_link = upload_pdf_to_drive(access_token, pdf_bytes, filename, folder_name_to_use)
        
    if not drive_link:
        # Fallback to service account
        drive_link = sheets_db.upload_report_pdf(pdf_bytes, filename, vehicle_no if vehicle_no else 'Unknown_Vehicle')
    
    if drive_link:
        return jsonify({'success': True, 'drive_link': drive_link, 'message': f'Report uploaded to Drive!'})
    else:
        return jsonify({'error': 'Failed to upload report to Google Drive. Check server logs.'}), 500

@app.route('/process_pdf', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def process_pdf():
    # Handle multipart/form-data (Standard) OR JSON (Direct Gemini Upload)
    pdf_content = None
    pdf_part = None
    
    if request.content_type == 'application/json':
        data = request.get_json()
        gemini_file_uri = data.get('gemini_file_uri')
        mime_type = data.get('mime_type', 'application/pdf')
        if not gemini_file_uri:
            return jsonify({"error": "No gemini_file_uri provided"}), 400
        
        # We don't need to load the content, Gemini already has it
        pdf_part = {
            "file_data": {
                "mime_type": mime_type,
                "file_uri": gemini_file_uri
            }
        }
             
    elif 'pdf_file' in request.files:
        file = request.files['pdf_file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        if file and file.mimetype == 'application/pdf':
            pdf_content = file.read()
            pdf_part = {"mime_type": "application/pdf", "data": pdf_content}
        else:
             return jsonify({"error": "Invalid file type. Please upload a PDF."}), 400
    else:
         return jsonify({"error": "No file provided"}), 400

    # Common Processing
    try:
        prompt = build_gemini_prompt()
        prompt_part = {"text": prompt}

        # Generate content using the configured model
        try:
            response = model.generate_content([prompt_part, pdf_part], stream=False)
        except ResourceExhausted as e:
            print(f"Primary model hit rate limit: {e}. Switching to secondary model (gemini-2.5-pro).")
            response = secondary_model.generate_content([prompt_part, pdf_part], stream=False)

        # Handle potential lack of response parts or blocked content
        if not response.parts:
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    reason = response.prompt_feedback.block_reason.name
                    print(f"Gemini response blocked. Reason: {reason}")
                    return jsonify({"error": f"Content generation blocked due to safety settings ({reason}). Please check the input document."}), 400
                else:
                    # Sometimes Gemini might just return no parts without a specific block reason
                    print("Gemini returned an empty response with no specific block reason.")
                    # Attempt to get text from the response object directly if possible
                    try:
                        response_text = response.text
                        if not response_text:
                            return jsonify({"error": "Received an empty response from the AI model. Please try again or check the document."}), 500
                        # If we got text, try parsing it anyway
                        print("Received text despite no parts, attempting parse...")
                    except Exception: # Broad exception if .text access fails
                            return jsonify({"error": "Received an empty or invalid response from the AI model. Please try again or check the document."}), 500
        else:
                response_text = response.text # Get text from the first part

        # Parse the combined data
        combined_data = parse_gemini_response(response_text)

        # --- Apply Defaults to Survey Report Data if field is empty ---
        survey_data = combined_data.get('survey_report', {})
        if not survey_data.get('vehicle_pre_accident_condition'): survey_data['vehicle_pre_accident_condition'] = "Average"
        if not survey_data.get('dl_endorsement'): survey_data['dl_endorsement'] = "Not Known"
        if not survey_data.get('police_reported_to'): survey_data['police_reported_to'] = "Not Reported"
        if not survey_data.get('police_diary_case_no'): survey_data['police_diary_case_no'] = "N/A"
        # police_date_reported default is handled by AI returning ""
        if not survey_data.get('tp_details'): survey_data['tp_details'] = "No ( As Per Claim Form )"
        if not survey_data.get('damages_extent'): survey_data['damages_extent'] = "The Spare Parts which are included in Assessment column, found pressed/deformed/torn/ distorted &/or broken."
        if not survey_data.get('remark'): survey_data['remark'] = "The declaration of the accident appeared consistent with the nature of the damages sustained"
        # --- End Apply Defaults ---

        return jsonify(combined_data)

    except ValueError as ve:
            print(f"Value Error during processing: {ve}")
            if "Failed to parse JSON response" in str(ve) or "unexpected error occurred during response parsing" in str(ve):
                return jsonify({"error": "Failed to parse the AI response. Please try again or check the document."}), 500
            else:
                return jsonify({"error": "An error occurred while processing the document."}), 400
    except genai.types.BlockedPromptException as bpe:
            print(f"Gemini API Error - Blocked Prompt: {bpe}")
            return jsonify({"error": "Content generation blocked by API. Please check the document content."}), 400
    except Exception as e:
        print(f"Error processing PDF with Gemini: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred during AI processing. Please try again."}), 500

# --- Depreciation Calculation Helper ---
def get_backend_depreciation_rate(part_type, vehicle_year_str):
    """
    Calculates depreciation rate based on part type and vehicle age in total months.
    The frontend will calculate total months and map it to a "year bucket" integer.
    """
    part_type = str(part_type).strip().upper()
    try:
        # The string now represents the "year bucket" from the rules (0, 1, 2, etc.)
        year_bucket = int(vehicle_year_str) if vehicle_year_str else 0
    except ValueError:
        year_bucket = 0 # Default to 0 if not a valid integer

    if part_type == 'G':
        return 0.0
    if part_type == 'P':
        return 50.0
    if part_type == 'M':
        if year_bucket <= 0: return 0.0   # Vehicle Age <= 6 months (Year 0)
        elif year_bucket == 1: return 5.0   # > 6 months to 1 year (Year 1)
        elif year_bucket == 2: return 10.0  # > 1 year to 2 years (Year 2)
        elif year_bucket == 3: return 15.0  # > 2 years to 3 years (Year 3)
        elif year_bucket == 4: return 25.0  # > 3 years to 4 years (Year 4)
        elif year_bucket == 5: return 35.0  # > 4 years to 5 years (Year 5)
        elif 6 <= year_bucket <= 10: return 40.0 # > 5 years to 10 years (Year 6-10)
        elif year_bucket > 10: return 50.0  # > 10 years (Year 11+)
        else: return 0.0 # Default for unexpected year
    return 0.0 # Default for unknown type

@app.route('/process_invoice', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def process_invoice():
    pdf_content = None

    if request.content_type == 'application/json':
        data = request.get_json()
        drive_file_id = data.get('drive_file_id')
        if not drive_file_id:
             return jsonify({"error": "No drive_file_id provided"}), 400
        
        # Fetch content from Service Account Drive (proxy)
        pdf_content = sheets_db.get_file_content(drive_file_id)
        if not pdf_content:
             return jsonify({"error": "Failed to retrieve file content from Drive. Check console."}), 500
             
    elif 'invoice_pdf_file' in request.files:
        file = request.files['invoice_pdf_file']
        if file.filename == '':
            return jsonify({"error": "No selected invoice file"}), 400
        if file and file.mimetype == 'application/pdf':
            pdf_content = file.read()
        else:
             return jsonify({"error": "Invalid file type. Please upload a PDF for the invoice."}), 400
    else:
         return jsonify({"error": "No invoice file provided"}), 400

    try:
        prompt = build_invoice_gemini_prompt() # Use the NEW invoice-specific prompt
        pdf_part = {"mime_type": "application/pdf", "data": pdf_content}
        prompt_part = {"text": prompt}

        # Generate content using the same model configuration
        try:
            response = model.generate_content([prompt_part, pdf_part], stream=False)
        except ResourceExhausted as e:
            print(f"Primary model hit rate limit: {e}. Switching to secondary model (gemini-2.5-pro) for invoice.")
            response = secondary_model.generate_content([prompt_part, pdf_part], stream=False)

        # Handle potential blocked content or empty response (similar to process_pdf)
        if not response.parts:
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                reason = response.prompt_feedback.block_reason.name
                print(f"Invoice Gemini response blocked. Reason: {reason}")
                return jsonify({"error": f"Invoice content generation blocked ({reason})."}), 400
            else:
                try:
                    response_text = response.text
                    if not response_text:
                        return jsonify({"error": "Received empty response from AI for invoice."}), 500
                except Exception:
                        return jsonify({"error": "Received invalid response from AI for invoice."}), 500
        else:
            response_text = response.text

        # Parse using the NEW invoice-specific parser
        invoice_parts_data = parse_invoice_gemini_response(response_text)

        return jsonify(invoice_parts_data) # Return only the parts data

    except ValueError as ve:
        print(f"Value Error during invoice processing: {ve}")
        return jsonify({"error": "Failed to process the invoice. Please try again."}), 500
    except genai.types.BlockedPromptException as bpe:
        print(f"Gemini API Error - Blocked Invoice Prompt: {bpe}")
        return jsonify({"error": "Invoice content generation blocked by API."}), 400
    except Exception as e:
        print(f"Error processing invoice PDF with Gemini: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred during invoice processing. Please try again."}), 500
    
def number_to_words_indian(number_val):
    """
    Converts a number to Indian English words (basic version: lakhs, thousands, hundreds).
    Example: 12345.67 -> "RUPEES TWELVE THOUSAND THREE HUNDRED FORTY FIVE AND PAISE SIXTY SEVEN ONLY"
    Handles up to 99,99,99,999.99
    """
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

def _calculate_report_assessment_summary(assessment_data_raw, survey_data_raw):
    """
    Helper to recalculate key assessment figures from stored JSON data.
    Returns a dict with:
        page3_gross_total, page3_cgst, page3_sgst, page3_igst, assessed_amount (Net Liability)
    """
    summary = {
        'page3_gross_total': 0.0,
        'page3_cgst': 0.0,
        'page3_sgst': 0.0,
        'page3_igst': 0.0,
        'assessed_amount': 0.0,
        'estimated_amount': 0.0, 
        'customer_gstin': '' 
    }

    try:
        page3_details_raw = assessment_data_raw.get('page3_details', {})
        summary['customer_gstin'] = page3_details_raw.get('customer_gstin', '')
        summary['estimated_amount'] = float(str(page3_details_raw.get('estimated_amount', '0')).replace(',', '')) if page3_details_raw.get('estimated_amount') else 0.0

        p3_fee_items_raw = page3_details_raw.get('fee_items', [])
        p3_photo_copies_str = str(page3_details_raw.get('photo_copies_count', '0')).strip()
        labour_tax_type_main = assessment_data_raw.get('labour_tax_type', 'CGST/SGST') 

        p3_photo_copies_count = int(p3_photo_copies_str) if p3_photo_copies_str.isdigit() else 0
        p3_photo_total_charge = p3_photo_copies_count * 10.0
        
        p3_fees_subtotal = 0.0
        for item_raw in p3_fee_items_raw:
            amount_str = str(item_raw.get('amount', '0')).replace(',', '')
            try:
                amount = float(amount_str)
                if amount != 0.0:
                     p3_fees_subtotal += amount
            except (ValueError, TypeError):
                pass
        
        p3_total_before_gst = p3_fees_subtotal + p3_photo_total_charge
        p3_cgst_calc = 0.0; p3_sgst_calc = 0.0; p3_igst_calc = 0.0
        
        if labour_tax_type_main == 'IGST': 
            p3_igst_calc = p3_total_before_gst * 0.18
        else: # CGST/SGST (survey fee GST is always 18%, even when labour tax is Zero)
            p3_cgst_calc = p3_total_before_gst * 0.09
            p3_sgst_calc = p3_total_before_gst * 0.09
        
        summary['page3_cgst'] = p3_cgst_calc
        summary['page3_sgst'] = p3_sgst_calc
        summary['page3_igst'] = p3_igst_calc
        summary['page3_gross_total'] = p3_total_before_gst + p3_cgst_calc + p3_sgst_calc + p3_igst_calc

        labour_paint_depn_input = float(assessment_data_raw.get('labour_paint_depn', 0.0))
        policy_type = assessment_data_raw.get('policy_type', 'NORMAL')
        header_vehicle_year = assessment_data_raw.get('header_vehicle_year', '')
        user_labour_rows = assessment_data_raw.get('user_labour_rows', [])
        
        # New: Labour IMT flag
        labour_imt_applied = assessment_data_raw.get('labour_imt_applied', False)

        # Recalculate Labour Totals
        total_removing = 0.0
        total_denting = 0.0
        total_painting = 0.0

        for row in user_labour_rows:
            def safe_float(val_str, default=0.0):
                try: return float(str(val_str).replace(',', ''))
                except (ValueError, TypeError): return default
            
            removing = safe_float(row.get('removing_refitting')); 
            denting = safe_float(row.get('denting_repairing')); 
            painting = safe_float(row.get('painting'))
            
            total_removing += removing
            total_denting += denting
            total_painting += painting

        # Paint Logic
        final_paint_depn_to_use = labour_paint_depn_input
        if policy_type == 'NIL_DEPN':
            final_paint_depn_to_use = 0.0
        
        net_paint_after_dep = total_painting - final_paint_depn_to_use
        
        # IMT 23 Logic (50% on Net Paint)
        labour_imt_deduction = 0.0
        if labour_imt_applied and net_paint_after_dep > 0:
            labour_imt_deduction = net_paint_after_dep * 0.5
        
        net_paint_liability = net_paint_after_dep - labour_imt_deduction
        
        # Taxable Labour
        taxable_labour = total_removing + total_denting + net_paint_liability
        
        # GST Calculation
        labour_gst_amount = 0.0
        if labour_tax_type_main != 'Zero':
            labour_gst_amount = taxable_labour * 0.18
        
        labour_grand_total_final = taxable_labour + labour_gst_amount

        updated_parts = assessment_data_raw.get('parts', [])
        parts_net_amt_final_calc = 0.0
        for part in updated_parts:
            qty = float(part.get('qty', 1.0))
            part_amt = float(part.get('part_amt', 0.0))
            part_type = str(part.get('type_part', '')).strip()
            gst_applicable = part.get('gst_applicable', False)
            original_gst_pc = float(part.get('original_gst_pc', 0.0))
            imt_applied = part.get('imt_applied', False)
            
            # Base Assessed
            total_parts_amt = qty * part_amt
            
            # Depreciation
            depr_rate = get_backend_depreciation_rate(part_type, header_vehicle_year)
            
            # Handle user override for depr
            saved_depr_val_str = str(part.get('depr', '-1.0')).strip()
            try: saved_depr_val = float(saved_depr_val_str)
            except ValueError: saved_depr_val = -1.0
            
            final_depr_amount = 0.0
            if policy_type == 'NIL_DEPN':
                 final_depr_amount = 0.0
            elif saved_depr_val >= 0:
                 final_depr_amount = saved_depr_val
            else:
                 final_depr_amount = total_parts_amt * (depr_rate / 100.0) if total_parts_amt > 0 else 0.0
            
            # Net Base (Assessed - Dep)
            net_base = total_parts_amt - final_depr_amount
            
            # GST on Net Base
            total_gst = net_base * (original_gst_pc / 100.0) if gst_applicable else 0.0
            
            # Gross Post-Dep (Net Base + GST)
            gross_post_dep = net_base + total_gst
            
            # IMT 23 on Gross Post-Dep
            imt_23_amt = 0.0
            if imt_applied:
                 imt_23_amt = gross_post_dep * 0.5

            # Final Net Amount
            net_amt = gross_post_dep - imt_23_amt
            parts_net_amt_final_calc += net_amt
            
        excess_final_calc = float(assessment_data_raw.get('deductibles', 1000.0))
        impose_excess_calc = float(assessment_data_raw.get('impose_excess', 0.0)) # New Field
        salvage_raw_calc = assessment_data_raw.get('salvage', '0')
        salvage_val_numeric_calc = 0.0
        try:
            salvage_val_numeric_calc = float(str(salvage_raw_calc).replace(',', ''))
        except (ValueError, TypeError):
            pass 
        
        summary['assessed_amount'] = (labour_grand_total_final + parts_net_amt_final_calc) - excess_final_calc - impose_excess_calc - salvage_val_numeric_calc

    except Exception as e:
        print(f"Error in _calculate_report_assessment_summary: {e}")
        summary = {
            'page3_gross_total': 0.0, 'page3_cgst': 0.0, 'page3_sgst': 0.0, 'page3_igst': 0.0,
            'assessed_amount': 0.0, 'estimated_amount': 0.0, 'customer_gstin': ''
        }
    return summary

# --- Custom PDF Class with Page Numbers ---
class PDFWithPageNumbers(FPDF):
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Set font
        self.set_font('Helvetica', 'I', 8)
        # Page number
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

@app.route('/get_user_profile', methods=['GET'])
@login_required
def get_user_profile():
    user = current_user
    return jsonify({
        "full_name": user.full_name,
        "qualifications": user.qualifications,
        "designation": user.designation,
        "license_no": user.license_no,
        "expiry_date": user.expiry_date,
        "membership_no": user.membership_no,
        "address_line_1": user.address_line_1,
        "address_line_2": user.address_line_2,
        "address_line_3": user.address_line_3,
        "contact_no": user.contact_no,
        "email": user.email
    })

@app.route('/update_user_profile', methods=['POST'])
@login_required
def update_user_profile():
    data = request.get_json()
    try:
        # For Sheets MVP: Updating user profile is complex (need to find row and update columns).
        # We will skip saving to sheet for now to avoid breakage, or implement later.
        # Ideally: sheets_db.update_user(current_user.id, data)
        print("User profile update requested (Not implemented for Sheets MVP):", data)
        
        # update current session user object temporarily
        current_user.full_name = data.get('full_name', current_user.full_name)
        # ... others
        
        return jsonify({"success": True, "message": "Profile updated locally (Sheet update not implemented in MVP)."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Photo Upload Route ---
@app.route('/upload_photo', methods=['POST'])
@login_required
def upload_photo():
    if 'photo' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
        # Read file content
        content = file.read()
        # Upload to Drive
        result = sheets_db.upload_image_to_drive(content, filename, file.mimetype)
        
        if result and result.get('id'):
            # Return a proxy URL that will serve the image through the backend
            # This avoids CORS issues and Google Drive redirect problems
            proxy_url = f"/proxy_image/{result.get('id')}"
            return jsonify({'success': True, 'url': proxy_url})
        else:
            return jsonify({'error': 'Failed to upload to Drive'}), 500

# --- Photo Proxy Route ---
@app.route('/proxy_image/<file_id>')
@login_required
def proxy_image(file_id):
    """Serves images from Google Drive through the backend proxy."""
    # SECURITY: Validate file_id format to prevent injection (VULN-06)
    import re as re_module
    if not re_module.match(r'^[a-zA-Z0-9_-]+$', file_id):
        abort(400)
    
    content = sheets_db.get_file_content(file_id)
    if content:
        # Detect image type from content (basic check for common types)
        mime_type = 'image/jpeg'  # default
        if content[:8] == b'\x89PNG\r\n\x1a\n':
            mime_type = 'image/png'
        elif content[:4] == b'GIF8':
            mime_type = 'image/gif'
        elif content[:4] == b'RIFF' and content[8:12] == b'WEBP':
            mime_type = 'image/webp'
        
        return send_file(io.BytesIO(content), mimetype=mime_type)
    else:
        abort(404)

# --- File Generation Route ---
@app.route('/generate_files', methods=['POST'])
@login_required
def generate_files():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data received"}), 400

        # --- Data Extraction ---
        survey_data = data.get('survey_report', {})
        assessment_data = data.get('assessment', {})
        
        # Extract Photo Data
        photos_data = data.get('photos', {})

        page3_details_raw = assessment_data.get('page3_details', {})
        p3_customer_gstin_raw = page3_details_raw.get('customer_gstin', '')
        p3_company_gstin_raw = page3_details_raw.get('company_gstin', '') 
        p3_fee_items_raw = page3_details_raw.get('fee_items', [])
        p3_estimated_amount_str = str(page3_details_raw.get('estimated_amount', '0')).strip()
        
        # Surveyor Bank Details
        surveyor_details = page3_details_raw.get('surveyor_details', {})

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

        labour_paint_depn_input = float(assessment_data.get('labour_paint_depn', 0.0))
        note_text_final_raw = assessment_data.get('note_text', "Note :- The subject policy covered with Depn. waiver")
        payment_to_text_final_raw = assessment_data.get('payment_to_text', "REPAIRER")
        salvage_raw_data = assessment_data.get('salvage', '0') 

        # Estimate Overrides
        est_labour_override = assessment_data.get('est_labour_override', '')
        est_paint_override = assessment_data.get('est_paint_override', '')
        est_parts_override = assessment_data.get('est_parts_override', '')

        final_survey_data = {key: survey_data.get(key, '') for key in EXPECTED_FIELDS}
        
        def get_survey_val(key):
            raw_value = final_survey_data.get(key, '')
            return normalize_pdf_text_for_fpdf(raw_value)

        header_vehicle_year = normalize_pdf_text_for_fpdf(header_vehicle_year_raw)
        note_text_final = normalize_pdf_text_for_fpdf(note_text_final_raw)
        payment_to_text_final = normalize_pdf_text_for_fpdf(payment_to_text_final_raw)
        reinspection_note = normalize_pdf_text_for_fpdf(reinspection_note_raw)
        p3_customer_gstin = normalize_pdf_text_for_fpdf(p3_customer_gstin_raw)
        p3_company_gstin = normalize_pdf_text_for_fpdf(p3_company_gstin_raw)
        salvage_raw = normalize_pdf_text_for_fpdf(salvage_raw_data)
        report_type = normalize_pdf_text_for_fpdf(report_type_raw)
        claim_type = normalize_pdf_text_for_fpdf(claim_type_raw)
        # Fix: Normalize potentially long/special char texts
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

        # --- Labour Recalculation (Page 2) ---
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
        
        # Logic: 
        # 1. Paint Dep (12.5% default)
        labour_paint_depn_final = labour_paint_depn_input 
        if policy_type == 'NIL_DEPN':
            labour_paint_depn_final = 0.0
        
        net_paint_after_dep = labour_sum_painting - labour_paint_depn_final
        
        # 2. IMT 23 (50% on Net Paint)
        labour_imt_deduction = 0.0
        if labour_imt_applied and net_paint_after_dep > 0:
            labour_imt_deduction = net_paint_after_dep * 0.5
        
        net_paint_liability = net_paint_after_dep - labour_imt_deduction
        
        # 3. Taxable Labour
        labour_rr_dent_sum = labour_sum_removing + labour_sum_denting
        taxable_labour = labour_rr_dent_sum + net_paint_liability
        
        # 4. GST
        labour_gst_amount = 0.0
        if labour_tax_type_main != 'Zero':
            labour_gst_amount = taxable_labour * 0.18
        
        # 5. Final
        labour_grand_total_final = taxable_labour + labour_gst_amount
        
        # --- Parts Recalculation (Page 3) & Material Liability ---
        parts_total_base_final = 0.0; parts_total_gst_final = 0.0; parts_grand_total_final = 0.0; parts_net_amt_final = 0.0; parts_depr_sum_final = 0.0
        parts_total_estimate = 0.0; parts_total_bill = 0.0; parts_total_assessed = 0.0; parts_total_imt23 = 0.0
        
        liability_metal = 0.0; liability_glass = 0.0; liability_plastic = 0.0

        final_parts_calculated = []
        for part in updated_parts:
            try:
                qty = float(part.get('qty', 1.0)); part_amt = float(part.get('part_amt', 0.0)); part_type = str(part.get('type_part', '')).strip().upper()
                gst_applicable = part.get('gst_applicable', False); original_gst_pc = float(part.get('original_gst_pc', 0.0))
                imt_applied = part.get('imt_applied', False) 
                
                estimate_amt = float(part.get('estimate_amt', 0.0))
                bill_amt = float(part.get('bill_amt', 0.0))
                
                depr_amount_from_frontend_str = str(part.get('depr', '-1.0')).strip()
                depr_amount_from_frontend = -1.0
                try: depr_amount_from_frontend = float(depr_amount_from_frontend_str)
                except ValueError: pass 

                # Base Assessed
                total_parts_amt = qty * part_amt 
                
                # Depreciation
                final_depr_amount_to_use = 0.0
                if policy_type == 'NIL_DEPN': final_depr_amount_to_use = 0.0
                elif depr_amount_from_frontend >= 0: final_depr_amount_to_use = depr_amount_from_frontend
                else: 
                    calculated_depr_rate = get_backend_depreciation_rate(part_type, header_vehicle_year)
                    final_depr_amount_to_use = total_parts_amt * (calculated_depr_rate / 100.0) if total_parts_amt > 0 else 0.0
                
                # Net Base (Assessed - Dep)
                net_base = total_parts_amt - final_depr_amount_to_use
                
                # GST on Net Base
                total_gst = net_base * (original_gst_pc / 100.0) if gst_applicable else 0.0
                
                # Gross Post-Dep (Net Base + GST)
                gross_post_dep = net_base + total_gst

                # IMT 23 on Gross Post-Dep
                imt_23_amt = 0.0
                if imt_applied:
                    imt_23_amt = gross_post_dep * 0.5
                
                # Final Net Amount
                net_amt = gross_post_dep - imt_23_amt

                if part_type == 'M': liability_metal += net_amt
                elif part_type == 'G': liability_glass += net_amt
                elif part_type == 'P': liability_plastic += net_amt

                part_name_display = normalize_pdf_text_for_fpdf(part.get('part_name', ''))
                
                output_part = part.copy() 
                output_part['total_parts_amt'] = total_parts_amt; output_part['total_gst'] = total_gst; output_part['gross_amt'] = gross_post_dep
                output_part['depr'] = final_depr_amount_to_use; output_part['net_amt'] = net_amt; output_part['part_name_display'] = part_name_display
                output_part['estimate_amt'] = estimate_amt; output_part['bill_amt'] = bill_amt; output_part['imt_23_amt'] = imt_23_amt
                output_part['net_base'] = net_base # Store for PDF
                
                output_part['salvage_produce'] = normalize_pdf_text_for_fpdf(part.get('salvage_produce', 'YES'))
                output_part['remarks'] = normalize_pdf_text_for_fpdf(part.get('remarks', 'REPLACED BY NEW'))

                final_parts_calculated.append(output_part)
                
                parts_total_base_final += total_parts_amt; parts_total_gst_final += total_gst; parts_grand_total_final += gross_post_dep; parts_net_amt_final += net_amt
                parts_depr_sum_final += final_depr_amount_to_use
                parts_total_estimate += estimate_amt; parts_total_bill += bill_amt; parts_total_assessed += total_parts_amt; parts_total_imt23 += imt_23_amt

            except (ValueError, TypeError) as e: print(f"Warning: Error processing part {part.get('sl_no')} for output. Skipping totals. Error: {e}")

        excess_final = float(assessment_data.get('deductibles', 1000.0))
        impose_excess_final = float(assessment_data.get('impose_excess', 0.0)) # New Field
        try: salvage_val_numeric = float(str(salvage_raw).replace(',', ''))
        except (ValueError, TypeError): salvage_val_numeric = 0.0
        
        net_liability_final = (labour_grand_total_final + parts_net_amt_final) - excess_final - impose_excess_final - salvage_val_numeric
        
        # --- Page 4 (Tax Invoice) Calculations ---
        p3_photo_total_charge = p3_photo_copies_count * 10.0
        p3_fees_subtotal = 0.0
        p3_valid_fee_items = []
        for item_raw in p3_fee_items_raw:
            name_raw = str(item_raw.get('name', '')).strip()
            name = normalize_pdf_text_for_fpdf(name_raw)
            amount_str = str(item_raw.get('amount', '0')).replace(',', '')
            try:
                amount = float(amount_str)
                if amount != 0.0:
                    p3_valid_fee_items.append({'name': name, 'amount': amount})
                    p3_fees_subtotal += amount
            except (ValueError, TypeError): pass
            
        p3_total_before_gst = p3_fees_subtotal + p3_photo_total_charge
        p3_cgst = 0.0; p3_sgst = 0.0; p3_igst = 0.0
        
        if labour_tax_type_main == 'IGST': 
            p3_igst = p3_total_before_gst * 0.18
        else: # CGST/SGST (survey fee GST is always 18%, even when labour tax is Zero)
            p3_cgst = p3_total_before_gst * 0.09; p3_sgst = p3_total_before_gst * 0.09
            
        p3_grand_total = p3_total_before_gst + p3_cgst + p3_sgst + p3_igst
        p3_grand_total_in_words_raw = number_to_words_indian(p3_grand_total)
        p3_grand_total_in_words = normalize_pdf_text_for_fpdf(p3_grand_total_in_words_raw)
        p3_estimated_amount = 0.0
        try: p3_estimated_amount = float(p3_estimated_amount_str.replace(',', ''))
        except ValueError: p3_estimated_amount = 0.0

        # --- PDF Setup ---
        pdf = PDFWithPageNumbers(orientation='P', unit='mm', format='A4')
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=15)
        base_font_size_page1 = 10; base_font_size_page2 = 10; base_font_size_page3 = 9 
        line_h_page1 = 5.5; line_h_page2 = 5.5; line_h_page3 = 5    
        table_cell_padding_y = 0.8
        header_image_path = os.path.join(app.static_folder, 'header.png')
        header_image_height = 30; header_bottom_margin = 10

        # --- Helper Functions ---
        def add_pdf_header(pdf_obj):
            if pdf_obj.page_no() == 1:
                # Retrieve user details from current_user
                u = current_user
                
                # --- Left Side ---
                pdf_obj.set_y(10)
                pdf_obj.set_x(10)
                
                # Name (Red)
                pdf_obj.set_text_color(239, 68, 68) # Red
                pdf_obj.set_font('Helvetica', 'B', 16)
                pdf_obj.cell(0, 8, normalize_pdf_text_for_fpdf(u.full_name), 0, 1, 'L')
                
                # Qualifications (Black)
                pdf_obj.set_text_color(0, 0, 0)
                pdf_obj.set_font('Helvetica', '', 9)
                pdf_obj.cell(0, 5, normalize_pdf_text_for_fpdf(u.qualifications), 0, 1, 'L')
                
                # Designation (Red)
                pdf_obj.set_text_color(239, 68, 68)
                pdf_obj.set_font('Helvetica', 'B', 10)
                pdf_obj.cell(0, 5, normalize_pdf_text_for_fpdf(u.designation), 0, 1, 'L')
                
                # License & Expiry & Membership (Black)
                pdf_obj.set_text_color(0, 0, 0)
                pdf_obj.set_font('Helvetica', '', 9)
                pdf_obj.cell(0, 5, normalize_pdf_text_for_fpdf(f"Licence No: {u.license_no}"), 0, 1, 'L')
                pdf_obj.cell(0, 5, normalize_pdf_text_for_fpdf(f"Expiry on: {u.expiry_date}"), 0, 1, 'L')
                pdf_obj.cell(0, 5, normalize_pdf_text_for_fpdf(f"IIISLA Membership No-{u.membership_no}"), 0, 1, 'L')

                # --- Right Side (Address) ---
                # Helper for right alignment
                def right_text(txt, y_offset=0, color=(0,0,0), bold=False):
                    pdf_obj.set_y(10 + y_offset)
                    pdf_obj.set_x(120) # Start from middle-right
                    pdf_obj.set_font('Helvetica', 'B' if bold else '', 9)
                    pdf_obj.set_text_color(*color)
                    pdf_obj.cell(80, 5, normalize_pdf_text_for_fpdf(txt), 0, 0, 'R')

                right_text(u.address_line_1, 0)
                right_text(u.address_line_2, 5)
                right_text(u.address_line_3, 10)

                
                # Cell (Label Black, Value Red) - Dynamic positioning to remove gap
                cell_val = normalize_pdf_text_for_fpdf(u.contact_no)
                cell_lbl = "Cell: "
                pdf_obj.set_font('Helvetica', 'B', 9); val_w = pdf_obj.get_string_width(cell_val)
                pdf_obj.set_font('Helvetica', '', 9); lbl_w = pdf_obj.get_string_width(cell_lbl)
                start_x = 200 - (lbl_w + val_w) # 200 is right margin alignment
                
                pdf_obj.set_y(25)
                pdf_obj.set_x(start_x)
                pdf_obj.set_text_color(0,0,0); pdf_obj.cell(lbl_w, 5, cell_lbl, 0, 0, 'L')
                pdf_obj.set_text_color(239, 68, 68); pdf_obj.set_font('Helvetica', 'B', 9); pdf_obj.cell(val_w, 5, cell_val, 0, 1, 'L')

                # Email (Label Black, Value Red) - Dynamic positioning to remove gap
                email_val = normalize_pdf_text_for_fpdf(u.email)
                email_lbl = "Email: "
                pdf_obj.set_font('Helvetica', 'B', 9); val_w = pdf_obj.get_string_width(email_val)
                pdf_obj.set_font('Helvetica', '', 9); lbl_w = pdf_obj.get_string_width(email_lbl)
                start_x = 200 - (lbl_w + val_w)
                
                pdf_obj.set_y(30)
                pdf_obj.set_x(start_x)
                pdf_obj.set_text_color(0,0,0); pdf_obj.cell(lbl_w, 5, email_lbl, 0, 0, 'L')
                pdf_obj.set_text_color(239, 68, 68); pdf_obj.set_font('Helvetica', 'B', 9); pdf_obj.cell(val_w, 5, email_val, 0, 1, 'L')

                # --- Bottom Line (Blue) ---
                pdf_obj.set_draw_color(59, 130, 246) # Blue
                pdf_obj.set_line_width(0.5)
                pdf_obj.line(10, 42, 200, 42)
                
                # Reset
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
                pdf_obj.cell(80, 5, normalize_pdf_text_for_fpdf(report_text), 0, 0, 'L')
                right_margin_x = pdf_obj.w - pdf_obj.r_margin
                pdf_obj.set_xy(right_margin_x - 80, current_y)
                pdf_obj.cell(80, 5, normalize_pdf_text_for_fpdf(vehicle_text), 0, 1, 'R')
                pdf_obj.ln(10)

        def draw_table_row(data, widths, height_per_line, border='TBLR', align='C', fill=False, text_color=(0,0,0), fill_color=(255,255,255), alignments=None, font_style='', is_header=False, current_font_size=base_font_size_page2 -1):
            pdf.set_fill_color(*fill_color); pdf.set_text_color(*text_color)
            base_table_font_size = current_font_size; header_font_size = current_font_size 
            max_lines = 1
            for i, item in enumerate(data):
                w = widths[i]
                temp_item_str_original = format_pdf_number(item) if isinstance(item, (int, float)) else str(item)
                temp_item_str = normalize_pdf_text_for_fpdf(temp_item_str_original)
                pdf.set_font("Helvetica", 'B' if is_header else (font_style if font_style else ''), base_table_font_size)
                lines = pdf.multi_cell(w, height_per_line, temp_item_str, border=0, align=alignments[i] if alignments else align, dry_run=True, output="LINES", max_line_height=height_per_line)
                max_lines = max(max_lines, len(lines))
            total_row_height = max_lines * height_per_line + table_cell_padding_y 
            if pdf.get_y() + total_row_height > pdf.h - pdf.b_margin:
                pdf.add_page(orientation=pdf.def_orientation); add_pdf_header(pdf); pdf.set_fill_color(*fill_color); pdf.set_text_color(*text_color)
            x_start = pdf.get_x(); y_start = pdf.get_y()
            if fill: pdf.rect(x_start, y_start, sum(widths), total_row_height, 'F')
            current_x = x_start
            for i, item in enumerate(data):
                w = widths[i]; cell_align = alignments[i] if alignments else align
                if isinstance(item, (int, float)): item_str = format_pdf_number(item)
                else: item_str = normalize_pdf_text_for_fpdf(str(item))
                cell_font_style = font_style if font_style else ('B' if is_header else '')
                cell_font_size = header_font_size if is_header else base_table_font_size
                pdf.set_font("Helvetica", cell_font_style, cell_font_size)
                pdf.set_xy(current_x, y_start + table_cell_padding_y / 2) 
                pdf.multi_cell(w, height_per_line, item_str, border=0, align=cell_align, padding=(0, 1), max_line_height=height_per_line) 
                current_x += w
            line_x = x_start; line_y = y_start; row_width = sum(widths); row_height = total_row_height
            is_full_border = (isinstance(border, int) and border == 1) or (isinstance(border, str) and border.upper() == 'TBLR')
            draw_top = is_full_border or (isinstance(border, str) and 'T' in border.upper()); draw_bottom = is_full_border or (isinstance(border, str) and 'B' in border.upper())
            draw_left = is_full_border or (isinstance(border, str) and 'L' in border.upper()); draw_right = is_full_border or (isinstance(border, str) and 'R' in border.upper())
            pdf.set_draw_color(0,0,0) 
            if draw_top: pdf.line(line_x, line_y, line_x + row_width, line_y)
            if draw_bottom: pdf.line(line_x, line_y + row_height, line_x + row_width, line_y + row_height)
            if draw_left: pdf.line(line_x, line_y, line_x, line_y + row_height)
            if draw_right: pdf.line(line_x + row_width, line_y, line_x + row_width, line_y + row_height)
            if is_full_border: 
                temp_x = x_start
                for i in range(len(widths) - 1): temp_x += widths[i]; pdf.line(temp_x, line_y, temp_x, line_y + row_height)
            pdf.set_y(y_start + total_row_height); pdf.set_x(x_start) 
            return total_row_height

        def calculate_height(texts, widths, font_size, line_height, padding, font_style=None):
            max_lines = 1; temp_pdf = FPDF(); temp_pdf.add_page()
            for i, text in enumerate(texts):
                current_style = font_style[i] if isinstance(font_style, list) and i < len(font_style) else (font_style if font_style else '')
                temp_pdf.set_font("Helvetica", current_style, font_size)
                normalized_text_for_calc = normalize_pdf_text_for_fpdf(str(text) if text is not None else '')
                lines = temp_pdf.multi_cell(widths[i], line_height, normalized_text_for_calc, dry_run=True, output="LINES", max_line_height=line_height)
                max_lines = max(max_lines, len(lines))
            del temp_pdf
            return max_lines * line_height + padding

        def add_plain_pair(label1, val1, label2, val2, label_width, val_width, font_size=base_font_size_page1, line_h=line_h_page1):
            start_y = pdf.get_y()
            
            # Normalize text
            norm_label1 = normalize_pdf_text_for_fpdf(label1)
            norm_val1 = normalize_pdf_text_for_fpdf(str(val1))
            norm_label2 = normalize_pdf_text_for_fpdf(label2) if label2 else ""
            norm_val2 = normalize_pdf_text_for_fpdf(str(val2)) if val2 else ""
            
            # Combine into single markdown strings: **Label:** Value
            # This removes the fixed column gap, allowing value to start immediately after label
            text1 = f"**{norm_label1}** {norm_val1}"
            text2 = f"**{norm_label2}** {norm_val2}" if label2 else ""
            
            # Total width for the column is the sum of the allocated label and value widths
            col_total_width = label_width + val_width
            
            # Calculate height for column 1 using the current PDF context (dry_run)
            # We use the main pdf object to ensure font/markdown calculations are accurate
            pdf.set_font("Helvetica", '', font_size)
            lines1 = pdf.multi_cell(col_total_width, line_h, text1, markdown=True, dry_run=True, output="LINES", max_line_height=line_h)
            h1 = len(lines1) * line_h
            
            # Calculate height for column 2
            h2 = 0
            if label2:
                 lines2 = pdf.multi_cell(col_total_width, line_h, text2, markdown=True, dry_run=True, output="LINES", max_line_height=line_h)
                 h2 = len(lines2) * line_h
            
            max_h = max(h1, h2) + table_cell_padding_y
            
            # Check page break
            if pdf.get_y() + max_h > pdf.page_break_trigger: 
                pdf.add_page(); add_pdf_header(pdf); start_y = pdf.get_y()
            
            # Render Column 1
            pdf.set_xy(pdf.l_margin, start_y)
            pdf.set_font("Helvetica", '', font_size)
            pdf.multi_cell(col_total_width, line_h, text1, markdown=True, border=0, align='L', max_line_height=line_h)
            
            # Render Column 2
            if label2:
                pdf.set_xy(pdf.l_margin + col_total_width, start_y)
                pdf.set_font("Helvetica", '', font_size)
                pdf.multi_cell(col_total_width, line_h, text2, markdown=True, border=0, align='L', max_line_height=line_h)
            
            pdf.set_y(start_y + max_h)
            return pdf.get_y()

        def add_section_header(text):
            # Check if enough space remains (e.g., 30mm) to avoid orphaned headers
            if pdf.get_y() > pdf.h - pdf.b_margin - 30:
                pdf.add_page(orientation=pdf.def_orientation)
                add_pdf_header(pdf)
            pdf.ln(2); pdf.set_font("Helvetica", 'B', base_font_size_page1)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.cell(0, line_h_page1 * 1.5, normalize_pdf_text_for_fpdf(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y()); pdf.ln(1); pdf.set_font("Helvetica", '', base_font_size_page1)

        def add_photo_section(pdf_obj, title, vehicle_no, photos_list, photos_per_page):
            if not photos_list:
                return
            margin = 10
            # Reduced page height calculation to shift photos upward and prevent footer overlap
            # Changed subtraction from -20 to -35 to reserve more space at the bottom
            page_width = 210 - (2 * margin)
            page_height = 297 - (2 * margin) - 35 
            
            cols = 2
            try: photos_per_page = int(photos_per_page)
            except: photos_per_page = 4
            if photos_per_page == 4: rows = 2
            elif photos_per_page == 6: rows = 3
            elif photos_per_page == 8: rows = 4
            else: rows = 2 
            
            img_width = (page_width - 5) / cols
            img_height = (page_height - 5) / rows 
            
            start_y = 0
            for i, photo_b64 in enumerate(photos_list):
                if i % photos_per_page == 0:
                    pdf_obj.add_page(orientation='P'); add_pdf_header(pdf_obj)
                    pdf_obj.set_font("Helvetica", 'B', 12)
                    pdf_obj.cell(0, 10, normalize_pdf_text_for_fpdf(f"{title} ({vehicle_no})"), 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
                    # Reduced line break after title to pull photos up slightly
                    pdf_obj.ln(1) 
                    start_y = pdf_obj.get_y()
                
                pos_in_page = i % photos_per_page; row = pos_in_page // cols; col = pos_in_page % cols
                x = pdf_obj.l_margin + (col * (img_width + 5)); y = start_y + (row * (img_height + 5))
                x = pdf_obj.l_margin + (col * (img_width + 5)); y = start_y + (row * (img_height + 5))
                try:
                    img_stream = None
                    if photo_b64.startswith('/proxy_image/'):
                        # It is a proxy URL - extract file ID and fetch directly
                        file_id = photo_b64.replace('/proxy_image/', '')
                        img_data = sheets_db.get_file_content(file_id)
                        if img_data:
                            img_stream = io.BytesIO(img_data)
                        else:
                            print(f"Failed to fetch image from Drive: {file_id}")
                            pdf_obj.set_xy(x, y); pdf_obj.set_font("Helvetica", '', 8); pdf_obj.cell(img_width, img_height, "Error loading image", 1, 0, 'C')
                            continue
                    elif photo_b64.startswith('http'):
                        # It is a URL (legacy Drive Link or external URL)
                        try:
                            headers = {'User-Agent': 'Mozilla/5.0'}
                            response = requests.get(photo_b64, headers=headers)
                            response.raise_for_status()
                            img_stream = io.BytesIO(response.content)
                        except Exception as e:
                            print(f"Failed to download image from URL: {photo_b64} - {e}")
                            pdf_obj.set_xy(x, y); pdf_obj.set_font("Helvetica", '', 8); pdf_obj.cell(img_width, img_height, "Error DL Image", 1, 0, 'C')
                            continue
                            
                    elif ',' in photo_b64: 
                        # Base64 with data URI prefix
                        photo_b64_data = photo_b64.split(',')[1]
                        img_data = base64.b64decode(photo_b64_data); img_stream = io.BytesIO(img_data)
                    else:
                        # Raw Base64 or cleanup
                        img_data = base64.b64decode(photo_b64); img_stream = io.BytesIO(img_data)
                    
                    if img_stream:
                        pdf_obj.image(img_stream, x=x, y=y, w=img_width, h=img_height)
                        
                except Exception as e:
                    pdf_obj.set_xy(x, y); pdf_obj.set_font("Helvetica", '', 8); pdf_obj.cell(img_width, img_height, "Error loading image", 1, 0, 'C')

        # --- Page 1: Survey Report (Portrait) ---
        pdf.add_page(); pdf.set_margins(10, 10, 10); add_pdf_header(pdf)
        
        # Spot Report Logic for Header
        is_spot_report = (report_type_raw == 'Spot Report')
        if is_spot_report:
            combined_heading = normalize_pdf_text_for_fpdf("Spot/Preliminary Survey Report")
        elif report_type_raw == 'Re-inspection Report':
            # User Request: Display Final Survey Report on first page for Re-inspection
            combined_heading = normalize_pdf_text_for_fpdf(f"Final Survey Report ({claim_type})")
        else:
            combined_heading = normalize_pdf_text_for_fpdf(f"{report_type} ({claim_type})")
            
        pdf.set_font("Helvetica", 'B', 12); pdf.cell(0, 8, combined_heading, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C'); pdf.ln(6)
        pdf.set_font("Helvetica", size=base_font_size_page1)
        usable_width = pdf.w - 2 * pdf.l_margin; col_width = usable_width / 2; label_w = 30; val_w = col_width - label_w
        add_plain_pair("Report No.:", get_survey_val('report_no'), "Date:", get_survey_val('report_date'), label_w, val_w)
        pdf.ln(1); pdf.set_font("Helvetica", size=base_font_size_page1 - 0.5)
        disclaimer = normalize_pdf_text_for_fpdf("This Motor Survey Report is issued without prejudice in respect of cause, nature & extent of Loss/damage & subject to to the terms and conditions of the insurance policy")
        pdf.multi_cell(0, line_h_page1, disclaimer, 0, 'L'); pdf.ln(2)
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
        for i in range(0, len(doc_items), 2):
            item1 = doc_items[i]; item2 = doc_items[i+1] if i+1 < len(doc_items) else (None, None)
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
        pdf.ln(2); pdf.set_font("Helvetica", 'B', base_font_size_page1); pdf.cell(15, line_h_page1, "Remark:", 0, 0)
        pdf.set_font("Helvetica", '', base_font_size_page1); pdf.multi_cell(0, line_h_page1, get_survey_val('remark'), 0, 'L')
        
        # Contd... logic: Only show if NOT a spot report
        pdf.ln(1); 
        if not is_spot_report:
            pdf.set_x(pdf.w - pdf.r_margin - 20); pdf.cell(20, line_h_page1, normalize_pdf_text_for_fpdf("contd..."), align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        # --- BRANCH: Spot Report vs Final/Re-inspection ---
        if is_spot_report:
            # Spot Report Narrative (Continue on same page)
            pdf.ln(5) # Add some spacing after Remark
            
            # CHANGE: Use base_font_size_page1 (7.2) to match previous text
            pdf.set_font("Helvetica", '', base_font_size_page1)
            
            # 1. Spot Report Narrative
            if spot_report_text:
                pdf.multi_cell(0, 5, spot_report_text, 0, 'L')
            else:
                default_spot_text = "Since it is Spot/ Preliminary survey the above damages were observed without dismantling the vehicle. More damages may be unearthing after dismantling the vehicle & its parts.\n\nTotal N Nos. photographs of the insured accidentally damaged vehicle were snapped by the undersigned during the course of Spot/ Preliminary survey which are attached with my report."
                pdf.multi_cell(0, 5, normalize_pdf_text_for_fpdf(default_spot_text), 0, 'L')
            
            pdf.ln(10) # Gap between text and footer section
            
            y_footer_start = pdf.get_y()
            
            # Check for page break safety
            if y_footer_start > 250: 
                pdf.add_page(orientation='P'); add_pdf_header(pdf)
                y_footer_start = pdf.get_y()

            # 2. Enclosures (Left Side)
            pdf.set_xy(pdf.l_margin, y_footer_start)
            pdf.set_font("Helvetica", 'B', base_font_size_page1) # Bold, matching size
            pdf.cell(0, 5, "Enclosures:", 0, 1, 'L')
            
            pdf.set_font("Helvetica", '', base_font_size_page1) # Regular, matching size
            final_spot_enclosures = spot_report_enclosures if spot_report_enclosures else "1. Digital Photos\n2. Professional Bill"
            pdf.multi_cell(80, 5, final_spot_enclosures, 0, 'L')

            # 3. Signature (Right Side)
            # Align top of signature block roughly with Enclosures
            pdf.set_xy(pdf.w - pdf.r_margin - 60, y_footer_start + 5) 
            
            # Add space for Stamp/Signature image overlap
            pdf.ln(10) 
            
            pdf.set_x(pdf.w - pdf.r_margin - 60)
            pdf.set_font("Helvetica", 'B', 10) # Signature stays slightly larger/standard
            pdf.cell(60, 5, normalize_pdf_text_for_fpdf(current_user.full_name), 0, 1, 'C')
            
            pdf.set_x(pdf.w - pdf.r_margin - 60)
            pdf.set_font("Helvetica", '', 9)
            pdf.cell(60, 5, "( Surveyor and Loss Assessor )", 0, 1, 'C')
            
        else:
            # --- Page 2: Labour Charges (Portrait) ---
            pdf.add_page(); pdf.set_margins(10, 10, 10); add_pdf_header(pdf); pdf.set_font("Helvetica", size=base_font_size_page2); usable_width_page2 = pdf.w - pdf.l_margin - pdf.r_margin
            top_info_y = pdf.get_y() 
            pdf.set_font("Helvetica", 'B', base_font_size_page2)
            gst_text = normalize_pdf_text_for_fpdf(f"GST: {header_gst_display}"); year_text_val = normalize_pdf_text_for_fpdf(f"Vehicle Year: {header_vehicle_year}")
            pdf.set_xy(pdf.l_margin, top_info_y); pdf.cell(60, line_h_page2, gst_text, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_x(pdf.l_margin); pdf.cell(60, line_h_page2, year_text_val, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(line_h_page2 * 1.5)
            pdf.set_font("Helvetica", 'B', base_font_size_page1); pdf.cell(0, line_h_page2, normalize_pdf_text_for_fpdf("12) Allocation of Labour charges:"), 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT); pdf.ln(line_h_page2 * 0.5)
            
            # Updated Columns: Name, R&R, Dent, Paint
            labour_widths = [80, 35, 35, 35]
            labour_headers_raw = ['Name of the parts', 'Removing/Refitting', 'Denting/Repairing', 'Painting']
            labour_headers = [normalize_pdf_text_for_fpdf(h) for h in labour_headers_raw]
            alignments_labour_headers = ['C', 'C', 'C', 'C']
            alignments_labour_rows = ['L', 'R', 'R', 'R']
            
            draw_table_row(labour_headers, labour_widths, line_h_page2, border=1, align='C', fill=True, text_color=(0,0,0), fill_color=(220,220,220), alignments=alignments_labour_headers, font_style='B', is_header=True, current_font_size=base_font_size_page2 -1)
            
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
                if pdf.get_y() + estimated_row_height > pdf.page_break_trigger: pdf.add_page(); add_pdf_header(pdf); draw_table_row(labour_headers, labour_widths, line_h_page2, border=1, align='C', fill=True, text_color=(0,0,0), fill_color=(220,220,220), alignments=alignments_labour_headers, font_style='B', is_header=True, current_font_size=base_font_size_page2 -1)
                draw_table_row(row_data, labour_widths, line_h_page2, border=1, alignments=alignments_labour_rows, current_font_size=base_font_size_page2 -1)
            
            # Total Row for Columns
            total_row_data_base_labour = [
                normalize_pdf_text_for_fpdf('TOTAL, Rs'),
                format_pdf_number(labour_sum_removing),
                format_pdf_number(labour_sum_denting),
                format_pdf_number(labour_sum_painting)
            ]
            draw_table_row(total_row_data_base_labour, labour_widths, line_h_page2, border='T', alignments=alignments_labour_rows, font_style='B', current_font_size=base_font_size_page2 -1)
            
            # --- Appended Calculation Rows (Integrated Table) ---
            calc_widths = [150, 35] # Merged first 3 columns, Value in 4th
            calc_alignments = ['L', 'R']
            
            # Helper to draw calculation rows
            def draw_calc_row(label, value, bold=False):
                row_data = [normalize_pdf_text_for_fpdf(label), format_pdf_number(value)]
                font_style = 'B' if bold else ''
                draw_table_row(row_data, calc_widths, line_h_page2, border=1, alignments=calc_alignments, font_style=font_style, current_font_size=base_font_size_page2 -1)

            # 1. Less 12.5% Dep
            draw_calc_row("Less: 12.5% (on paint material)", labour_paint_depn_final)
            
            # 2. Less 50% IMT 23
            if labour_imt_deduction > 0:
                draw_calc_row("Less: 50% Liability (As per IMT 23 Norms)", labour_imt_deduction)

            # 3. Total Painting Charges - Net Liability for Paint
            draw_calc_row("Total Painting Charges", net_paint_liability, bold=True)
                
            # 4. Add Labour (R&R + Dent)
            draw_calc_row("Add: Labour (R&R + Dent)", labour_rr_dent_sum)
            
            # 5. Taxable Total (Bold)
            draw_calc_row("Total Taxable Labour", taxable_labour, bold=True)
            
            # 6. Add GST
            if labour_tax_type_main != 'Zero':
                draw_calc_row("Add: 18% GST", labour_gst_amount)
            
            # 7. Final Amount (Bold)
            draw_calc_row("Final Labour Liability", labour_grand_total_final, bold=True)
            
            pdf.ln(line_h_page2 * 1.5)
            
            # --- Page 3: Landscape Table 13 ---
            pdf.add_page(orientation='L'); pdf.set_margins(10, 10, 10); add_pdf_header(pdf)
            pdf.set_auto_page_break(auto=False, margin=10) 
            pdf.set_font("Helvetica", size=base_font_size_page2)
            pdf.set_font("Helvetica", 'B', base_font_size_page1); pdf.cell(0, line_h_page2, normalize_pdf_text_for_fpdf("14. Cost of Spare Parts at MRP. :"), 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT); pdf.ln(line_h_page2 * 0.5)
            parts_widths = [8, 8, 8, 55, 15, 19, 19, 19, 11, 8, 15, 23, 10, 15, 8, 15, 25]
            parts_headers_raw = ['Sl', 'E\nNo', 'Bill\nSL', 'Parts Descriptions', 'HNS\nCODE', 'Estimate\nAmount', 'Bill\nAmount', 'Assessed\nAmount', 'Parts\nType', 'Dep\n%', 'Dep.\nAMT', 'Net.\nAmount', 'GST\n%', 'GST\nAmount', 'IMT\n23', 'IMT-23\nAMT', 'Net AMT\nIncl. GST']
            parts_headers = [normalize_pdf_text_for_fpdf(h) for h in parts_headers_raw]
            alignments_parts_headers = ['C'] * 17
            alignments_parts_rows = ['C', 'C', 'C', 'L', 'C', 'R', 'R', 'R', 'C', 'C', 'R', 'R', 'C', 'R', 'C', 'R', 'R']
            
            draw_table_row(parts_headers, parts_widths, line_h_page2, border=1, align='C', fill=True, text_color=(0,0,0), fill_color=(200,200,200), alignments=alignments_parts_headers, font_style='B', is_header=True, current_font_size=base_font_size_page2 -1)
            pdf.set_text_color(0,0,0) 

            for i, part in enumerate(final_parts_calculated):
                sl_no_str = normalize_pdf_text_for_fpdf(str(int(part.get('sl_no', 0))))
                est_sl_no_str = normalize_pdf_text_for_fpdf(part.get('est_sl_no', sl_no_str))
                bill_sl_no_str = normalize_pdf_text_for_fpdf(part.get('bill_sl_no', sl_no_str))
                dep_pc_display = "0%"
                if part.get('total_parts_amt', 0) > 0 and part.get('depr', 0) > 0:
                    rate = (part.get('depr', 0) / part.get('total_parts_amt', 0)) * 100
                    dep_pc_display = f"{rate:.0f}%"
                elif policy_type == 'NIL_DEPN': dep_pc_display = "NIL"
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
                is_last_row = (i == len(final_parts_calculated) - 1); needed_height = row_h
                if is_last_row: needed_height += (line_h_page2 + table_cell_padding_y) 
                if pdf.get_y() + needed_height > pdf.h - pdf.b_margin:
                    pdf.add_page(orientation='L'); add_pdf_header(pdf)
                    draw_table_row(parts_headers, parts_widths, line_h_page2, border=1, align='C', fill=True, text_color=(0,0,0), fill_color=(200,200,200), alignments=alignments_parts_headers, font_style='B', is_header=True, current_font_size=base_font_size_page2 -1)
                    pdf.set_text_color(0,0,0)
                draw_table_row(part_data, parts_widths, line_h_page2, border=1, alignments=alignments_parts_rows, current_font_size=base_font_size_page2 -1)
            
            # Total Row
            parts_total_row = ['', '', '', 'TOTAL', '', format_pdf_number(parts_total_estimate), format_pdf_number(parts_total_bill), format_pdf_number(parts_total_assessed), '', '', format_pdf_number(parts_depr_sum_final), format_pdf_number(parts_total_assessed - parts_depr_sum_final), '', format_pdf_number(parts_total_gst_final), '', format_pdf_number(parts_total_imt23), format_pdf_number(parts_net_amt_final)]        
            draw_table_row(parts_total_row, parts_widths, line_h_page2, border='T', alignments=alignments_parts_rows, font_style='B', current_font_size=base_font_size_page2 -1)
            pdf.ln(line_h_page2); pdf.set_auto_page_break(auto=True, margin=10)

            # --- Summary Section (Landscape) ---
            summary_start_y = pdf.get_y()
            # INCREASED THRESHOLD: Was 80, now 110 to ensure meaningful summary fits or start new page
            if pdf.h - summary_start_y < 110: 
                pdf.add_page(orientation='L'); add_pdf_header(pdf); summary_start_y = pdf.get_y()
            
            # Left Column: Estimates
            left_col_x = pdf.l_margin; left_col_width = 80
            pdf.set_xy(left_col_x, summary_start_y)
            pdf.set_font("Helvetica", 'B', base_font_size_page2)
            pdf.cell(left_col_width/2, line_h_page2, "Estimates", 1, 0, 'L'); pdf.cell(left_col_width/2, line_h_page2, "Amount", 1, 1, 'R')
            pdf.set_font("Helvetica", '', base_font_size_page2)
            
            # Determine values to use (Override or Calculated)
            est_labour_val = float(est_labour_override) if est_labour_override and is_number(est_labour_override) else labour_rr_dent_sum
            est_paint_val = float(est_paint_override) if est_paint_override and is_number(est_paint_override) else labour_sum_painting
            est_parts_val = float(est_parts_override) if est_parts_override and is_number(est_parts_override) else parts_total_estimate
            
            pdf.cell(left_col_width/2, line_h_page2, "Labour Charges", 1, 0, 'L'); pdf.cell(left_col_width/2, line_h_page2, format_pdf_number(est_labour_val), 1, 1, 'R')
            pdf.cell(left_col_width/2, line_h_page2, "Paint cost", 1, 0, 'L'); pdf.cell(left_col_width/2, line_h_page2, format_pdf_number(est_paint_val), 1, 1, 'R')
            pdf.cell(left_col_width/2, line_h_page2, "Cost of Parts", 1, 0, 'L'); pdf.cell(left_col_width/2, line_h_page2, format_pdf_number(est_parts_val), 1, 1, 'R') 
            pdf.set_font("Helvetica", 'B', base_font_size_page2)
            approx_total = est_labour_val + est_paint_val + est_parts_val
            pdf.cell(left_col_width/2, line_h_page2, "Approximate Total", 1, 0, 'L'); pdf.set_fill_color(255, 255, 0)
            pdf.cell(left_col_width/2, line_h_page2, format_pdf_number(approx_total), 1, 1, 'R', fill=True)
            left_col_end_y = pdf.get_y()

            # Right Column: NEW Particulars of Liability Table
            # Layout: Descriptions | Assessed Amount | Total GST on A/Amount | Liability Amount Inclu. GST
            right_col_x = pdf.l_margin + left_col_width + 5
            
            # UPDATED FIXED WIDTHS: Reduced Desc, Increased others to fit text
            # Total width: 55 + 35 + 42 + 45 = 177mm (Fits in remaining ~190mm space)
            cols_liability = [55, 35, 42, 45] 
            
            headers_liability = ["Particulars of Liability", "Assessed Amount", "Total GST on A/Amount", "Liability Amount Inclu. GST"]
            aligns_liability = ['L', 'R', 'R', 'R']
            
            pdf.set_xy(right_col_x, summary_start_y)
            
            # Table Headers
            current_x = right_col_x
            header_labels = ["Descriptions", "Assessed Amount", "Total GST on A/Amount", "Liability Amount Inclu. GST"]
            # Color header blue-ish like image
            pdf.set_fill_color(59, 130, 246); pdf.set_text_color(255,255,255) # Blue background, White text
            
            # Use smaller font for headers to prevent overlap
            pdf.set_font("Helvetica", 'B', base_font_size_page2 - 1.5) 
            
            for i, h in enumerate(header_labels):
                pdf.set_xy(current_x, pdf.get_y())
                # Normalize text to handle special chars if any
                safe_h = normalize_pdf_text_for_fpdf(h)
                pdf.cell(cols_liability[i], line_h_page2 + 2, safe_h, 1, 0, 'C', fill=True)
                current_x += cols_liability[i]
            pdf.ln(line_h_page2 + 2); pdf.set_text_color(0,0,0)

            def add_new_summary_row(desc, assessed, gst, liability, bold=False, fill_color=None):
                pdf.set_x(right_col_x)
                if fill_color: pdf.set_fill_color(*fill_color)
                else: pdf.set_fill_color(255, 255, 255)
                
                # Reset font to normal size for data rows
                pdf.set_font("Helvetica", 'B' if bold else '', base_font_size_page2)
                
                # Draw cells
                c_x = right_col_x
                pdf.cell(cols_liability[0], line_h_page2, normalize_pdf_text_for_fpdf(desc), 1, 0, 'L', fill=bool(fill_color))
                c_x += cols_liability[0]; pdf.set_x(c_x)
                pdf.cell(cols_liability[1], line_h_page2, format_pdf_number(assessed) if assessed != '' else '', 1, 0, 'R', fill=bool(fill_color))
                c_x += cols_liability[1]; pdf.set_x(c_x)
                pdf.cell(cols_liability[2], line_h_page2, format_pdf_number(gst) if gst != '' else '', 1, 0, 'R', fill=bool(fill_color))
                c_x += cols_liability[2]; pdf.set_x(c_x)
                pdf.cell(cols_liability[3], line_h_page2, format_pdf_number(liability) if liability != '' else '', 1, 1, 'R', fill=bool(fill_color))

            # 1. Labour
            labour_assessed = labour_rr_dent_sum
            labour_gst = 0.0
            if labour_tax_type_main != 'Zero':
                labour_gst = labour_assessed * 0.18
            labour_liability = labour_assessed + labour_gst
            add_new_summary_row("TOTAL LABOUR", labour_assessed, labour_gst, labour_liability)

            # 2. Paint
            # Logic: "Net Paint Liability" (after Dep/IMT) is the assessed amount. 18% tax on that.
            paint_assessed = net_paint_liability
            paint_gst = 0.0
            if labour_tax_type_main != 'Zero':
                 paint_gst = paint_assessed * 0.18
            paint_liability = paint_assessed + paint_gst
            add_new_summary_row("TOTAL PAINT", paint_assessed, paint_gst, paint_liability)

            # 3. Parts (Metal, Glass, Plastic)
            cat_data = {'M': {'gst': 0.0, 'liability': 0.0}, 'G': {'gst': 0.0, 'liability': 0.0}, 'P': {'gst': 0.0, 'liability': 0.0}}
            
            for part in final_parts_calculated:
                p_type = str(part.get('type_part', 'M')).strip().upper()
                if p_type not in ['M', 'G', 'P']: p_type = 'M'
                
                p_net = float(part.get('net_amt', 0.0))
                gst_rate = float(part.get('original_gst_pc', 0.0))
                
                p_base_component = 0.0
                p_tax_component = 0.0
                
                # Split Liability back into Base and Tax components for display
                if gst_rate > 0:
                    p_base_component = p_net / (1 + (gst_rate / 100.0))
                    p_tax_component = p_net - p_base_component
                else:
                    p_base_component = p_net
                    p_tax_component = 0.0
                    
                cat_data[p_type]['liability'] += p_net
                cat_data[p_type]['gst'] += p_tax_component

            # Metal
            m_assessed = cat_data['M']['liability'] - cat_data['M']['gst']
            add_new_summary_row("TOTAL METAL PARTS", m_assessed, cat_data['M']['gst'], cat_data['M']['liability'])
            
            # Glass
            g_assessed = cat_data['G']['liability'] - cat_data['G']['gst']
            add_new_summary_row("TOTAL GLASS PARTS", g_assessed, cat_data['G']['gst'], cat_data['G']['liability'])
            
            # Plastic
            p_assessed = cat_data['P']['liability'] - cat_data['P']['gst']
            add_new_summary_row("TOTAL PLASTIC PARTS", p_assessed, cat_data['P']['gst'], cat_data['P']['liability'])

            # Total Row
            total_liability = labour_liability + paint_liability + cat_data['M']['liability'] + cat_data['G']['liability'] + cat_data['P']['liability']
            # Blue background row like image
            pdf.set_x(right_col_x)
            pdf.set_fill_color(59, 130, 246); pdf.set_text_color(255,255,255); pdf.set_font("Helvetica", 'B', base_font_size_page2)
            pdf.cell(sum(cols_liability[:3]), line_h_page2, "Total :", 1, 0, 'R', fill=True)
            pdf.cell(cols_liability[3], line_h_page2, format_pdf_number(total_liability), 1, 1, 'R', fill=True)
            pdf.set_text_color(0,0,0)

            # Less Rows
            def add_less_row(label, val):
                pdf.set_x(right_col_x)
                pdf.set_fill_color(255, 255, 255); pdf.set_font("Helvetica", '', base_font_size_page2)
                pdf.cell(sum(cols_liability[:3]), line_h_page2, label, 1, 0, 'R')
                pdf.cell(cols_liability[3], line_h_page2, format_pdf_number(val), 1, 1, 'R')

            add_less_row("Less : Salvage", salvage_val_numeric)
            add_less_row("Less: Compulsory excess", excess_final)
            add_less_row("Less: Impose excess", impose_excess_final)
            
            # Net Settlement
            net_settlement = total_liability - salvage_val_numeric - excess_final - impose_excess_final
            add_less_row("Net settlement Amount :", net_settlement)
            
            # Round off (Blue Row) - SAFETY CHECK FOR SIGNATURE
            # Ensure this row + Signature height fits on the page. 
            # If not, break page here so this row travels with the signature.
            sig_height_block = 35 # Height for signature block
            
            # FIXED: Added logic to break page if not enough space for Round Off + Signature
            if pdf.get_y() + line_h_page2 + sig_height_block + 15 > pdf.page_break_trigger:
                pdf.add_page(orientation='L')
                add_pdf_header(pdf)
                # Keep X alignment on new page
            
            pdf.set_x(right_col_x)
            pdf.set_fill_color(59, 130, 246); pdf.set_text_color(255,255,255); pdf.set_font("Helvetica", 'B', base_font_size_page2)
            pdf.cell(sum(cols_liability[:3]), line_h_page2, "Net settlement Amount Round off:", 1, 0, 'R', fill=True)
            pdf.cell(cols_liability[3], line_h_page2, format_pdf_number(round(net_settlement)), 1, 1, 'R', fill=True)
            pdf.set_text_color(0,0,0)

            # Optional Note & Enclosures
            final_y = pdf.get_y() + 5
            
            if parts_table_note:
                pdf.set_y(final_y)
                pdf.set_x(pdf.l_margin) # Reset X to left margin
                pdf.set_font("Helvetica", 'B', base_font_size_page2)
                pdf.multi_cell(0, line_h_page2, parts_table_note, 0, 'L')
                final_y = pdf.get_y() + 2

            if enclosures_text:
                # Calculate needed height for enclosures
                pdf.set_font("Helvetica", '', base_font_size_page2)
                pdf.set_x(pdf.l_margin) # Reset X explicitly for dry run
                lines = pdf.multi_cell(0, line_h_page2, enclosures_text, dry_run=True, output="LINES")
                enc_h = len(lines) * line_h_page2 + 10 # Title + Lines
                
                if final_y + enc_h + sig_height_block > pdf.page_break_trigger:
                    pdf.add_page(orientation='L')
                    add_pdf_header(pdf)
                    final_y = pdf.get_y() + 5
                
                pdf.set_y(final_y)
                pdf.set_x(pdf.l_margin)
                pdf.set_font("Helvetica", 'B', base_font_size_page2)
                pdf.cell(0, line_h_page2, "Enclosures:", 0, 1, 'L')
                pdf.set_font("Helvetica", '', base_font_size_page2)
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(0, line_h_page2, enclosures_text, 0, 'L')
                final_y = pdf.get_y() + 5
            
            # Print Signature (Guaranteed to have content above it now)
            # Add gap for Stamp (Requested by User)
            gap_stamp = 40
            sig_lines_height = line_h_page2 * 3
            
            if pdf.get_y() + gap_stamp + sig_lines_height > pdf.page_break_trigger:
                pdf.add_page(orientation='L')
                add_pdf_header(pdf)
                pdf.set_y(pdf.get_y() + 30) # Gap on new page
            else:
                pdf.set_y(pdf.get_y() + gap_stamp)
            pdf.set_x(pdf.w - pdf.r_margin - 60); pdf.cell(60, line_h_page2, normalize_pdf_text_for_fpdf(current_user.full_name), 0, 1, 'C')
            pdf.set_x(pdf.w - pdf.r_margin - 60); pdf.cell(60, line_h_page2, "( Surveyor and Loss Assessor )", 0, 1, 'C')

            # --- Re-inspection Report Page (Optional) ---
            if report_type_raw == 'Re-inspection Report':
                pdf.add_page(orientation='P'); pdf.set_margins(10, 10, 10); add_pdf_header(pdf); pdf.set_auto_page_break(auto=False, margin=10) 
                pdf.set_font("Helvetica", 'B', 14); pdf.cell(0, 10, "RE-INSPECTION REPORT", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C'); pdf.ln(5)
                pdf.set_font("Helvetica", 'B', 10); pdf.cell(15, 5, "To,", 0, new_x=XPos.RIGHT, new_y=YPos.TOP); pdf.set_font("Helvetica", '', 10)
                start_y_addr = pdf.get_y(); insurer_address = get_survey_val('insurer'); pdf.set_xy(pdf.l_margin + 15, start_y_addr); pdf.multi_cell(0, 5, insurer_address, 0, 'L'); pdf.ln(5)
                pdf.set_font("Helvetica", 'B', 10); pdf.cell(15, 5, "Sub:", 0, new_x=XPos.RIGHT, new_y=YPos.TOP); pdf.set_font("Helvetica", '', 10); pdf.cell(0, 5, f"Re-inspection of repaired vehicle bearing Regn. No. {get_survey_val('vehicle_regn_no')}", 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT); pdf.ln(5)
                pdf.set_font("Helvetica", '', 9); col1_w = 40; col2_w = 60; col3_w = 40; col4_w = 50 
                def draw_grid_row(label1, val1, label2=None, val2=None):
                    h = 7; pdf.set_font("Helvetica", 'B', 9); pdf.cell(col1_w, h, label1, 1, 0, 'L'); pdf.set_font("Helvetica", '', 9); pdf.cell(col2_w, h, val1, 1, 0, 'L')
                    if label2: pdf.set_font("Helvetica", 'B', 9); pdf.cell(col3_w, h, label2, 1, 0, 'L'); pdf.set_font("Helvetica", '', 9); pdf.cell(col4_w, h, val2, 1, 1, 'L')
                    else: pdf.ln(h)
                draw_grid_row("Policy No. :", get_survey_val('policy_no'), "Claim No. :", get_survey_val('claim_no')); draw_grid_row("Date of Accident :", get_survey_val('accident_datetime'), "Date of Survey :", get_survey_val('accident_survey_date'))
                pdf.set_font("Helvetica", 'B', 9); pdf.cell(col1_w, 7, "Insured :", 1, 0, 'L'); x_val = pdf.get_x(); y_val = pdf.get_y()
                pdf.set_font("Helvetica", '', 9); insured_val = get_survey_val('insured'); width_val = col2_w + col3_w + col4_w; pdf.set_xy(x_val, y_val); pdf.multi_cell(width_val, 7, insured_val, 1, 'L'); pdf.set_x(pdf.l_margin)
                draw_grid_row("Chassis No. :", get_survey_val('vehicle_chassis_no'), "Engine No. :", get_survey_val('vehicle_engine_no')); pdf.ln(5)
                pdf.set_font("Helvetica", '', 10); intro_text = "As per instruction received from your office, I visited the repairer's workshop. I have inspected the subject vehicle after repairs and verified the replaced parts. The details are as follows:"; pdf.multi_cell(0, 5, intro_text, 0, 'L'); pdf.ln(5)
                re_cols = [12, 108, 30, 40]; re_headers = ["SL", "Name of the Parts", "Salvage", "Remarks"]; re_aligns = ['C', 'L', 'C', 'C']
                draw_table_row(re_headers, re_cols, 7, border=1, align='C', fill=True, text_color=(0,0,0), fill_color=(220,220,220), alignments=re_aligns, font_style='B', is_header=True, current_font_size=9); pdf.set_text_color(0,0,0)
                for part in final_parts_calculated:
                    sl = str(part.get('sl_no')); name = part.get('part_name_display', ''); salvage = part.get('salvage_produce', 'YES'); remarks = part.get('remarks', 'REPLACED BY NEW'); row_data = [sl, name, salvage, remarks]
                    if pdf.get_y() > 260: pdf.add_page(orientation='P'); add_pdf_header(pdf); draw_table_row(re_headers, re_cols, 7, border=1, align='C', fill=True, text_color=(0,0,0), fill_color=(220,220,220), alignments=re_aligns, font_style='B', is_header=True, current_font_size=9)
                    draw_table_row(row_data, re_cols, 6, border=1, alignments=re_aligns, current_font_size=9)
                pdf.ln(5); pdf.set_font("Helvetica", 'B', 10); pdf.cell(0, 5, "Observations / Remarks:", 0, 1, 'L'); pdf.set_font("Helvetica", '', 10); pdf.multi_cell(0, 5, reinspection_note, 0, 'L'); pdf.ln(10)
                if pdf.get_y() > 250: pdf.add_page(orientation='P'); add_pdf_header(pdf)
                pdf.set_x(pdf.w - pdf.r_margin - 60); pdf.set_font("Helvetica", 'B', 10); pdf.cell(60, 5, normalize_pdf_text_for_fpdf(current_user.full_name), 0, 1, 'C'); pdf.set_x(pdf.w - pdf.r_margin - 60); pdf.set_font("Helvetica", '', 9); pdf.cell(60, 5, "( Surveyor and Loss Assessor )", 0, 1, 'C'); pdf.set_auto_page_break(auto=True, margin=15)

            # --- Page 4: Survey Fee Bill (Portrait) ---
        pdf.add_page(orientation='P'); pdf.set_margins(10, 10, 10); add_pdf_header(pdf); pdf.set_font("Helvetica", size=base_font_size_page3); usable_width_page3 = pdf.w - pdf.l_margin - pdf.r_margin
        pdf.set_font("Helvetica", 'B', 14); pdf.cell(0, 10, normalize_pdf_text_for_fpdf("SURVEY FEE BILL"), 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C'); pdf.ln(5)
        pdf.set_font("Helvetica", '', base_font_size_page3)
        ref_no_text_val = normalize_pdf_text_for_fpdf(f"Ref. No - {get_survey_val('report_no')}"); date_text_val = normalize_pdf_text_for_fpdf(f"Date- {get_survey_val('report_date')}"); date_width = pdf.get_string_width(date_text_val) + 2
        pdf.cell(usable_width_page3 - date_width, line_h_page3, ref_no_text_val, 0, new_x=XPos.RIGHT, new_y=YPos.TOP); pdf.cell(date_width, line_h_page3, date_text_val, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='R')
        current_y_before_to = pdf.get_y() + line_h_page3 * 0.25; pdf.set_y(current_y_before_to); pdf.cell(10, line_h_page3, normalize_pdf_text_for_fpdf("To"), 0, new_x=XPos.RIGHT, new_y=YPos.TOP); address_start_x = pdf.l_margin + 10; pdf.set_xy(address_start_x, current_y_before_to) 
        insurer_address_full_raw = get_survey_val('insurer'); insurer_address_full = normalize_pdf_text_for_fpdf(insurer_address_full_raw); insurer_address_lines = [line.strip() for line in insurer_address_full.split(',') if line.strip()]
        for i, line in enumerate(insurer_address_lines):
            if pdf.get_y() + line_h_page3 > pdf.page_break_trigger - 10: pdf.add_page(orientation='P'); add_pdf_header(pdf); pdf.set_font("Helvetica", '', base_font_size_page3); pdf.set_xy(address_start_x, pdf.get_y())
            pdf.multi_cell(usable_width_page3 - (address_start_x - pdf.l_margin), line_h_page3, line, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L') 
            if i < len(insurer_address_lines) -1 : pdf.set_x(address_start_x)
        
        # Company GSTIN under address
        if p3_company_gstin:
            pdf.set_x(address_start_x)
            pdf.set_font("Helvetica", 'B', base_font_size_page3)
            pdf.cell(0, line_h_page3, normalize_pdf_text_for_fpdf(f"GSTIN: {p3_company_gstin}"), 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_x(pdf.l_margin); pdf.ln(line_h_page3 * 0.5)
        if p3_customer_gstin:
            pdf.set_font("Helvetica", 'B', base_font_size_page3); pdf.cell(pdf.get_string_width("INSURED GST NO- ") + 1, line_h_page3, normalize_pdf_text_for_fpdf("INSURED GST NO- "), 0, new_x=XPos.RIGHT, new_y=YPos.TOP); pdf.set_font("Helvetica", '', base_font_size_page3); pdf.multi_cell(0, line_h_page3, p3_customer_gstin, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L'); pdf.ln(line_h_page3 * 0.25) 
        table_data_p3_header = [("Policy No:", get_survey_val('policy_no')), ("Claim No.-", get_survey_val('claim_no')), ("Regd No:", get_survey_val('vehicle_regn_no')), ("Insured :", get_survey_val('insured'))]
        label_col_width_p3_info_table = 30; value_col_width_p3_info_table = usable_width_page3 - label_col_width_p3_info_table
        for label_raw, value in table_data_p3_header:
            label = normalize_pdf_text_for_fpdf(label_raw) 
            if value:
                row_height_est = calculate_height([label, value], [label_col_width_p3_info_table, value_col_width_p3_info_table], base_font_size_page3, line_h_page3, table_cell_padding_y/2, ['', 'B'])
                if pdf.get_y() + row_height_est > pdf.page_break_trigger -10 : pdf.add_page(orientation='P'); add_pdf_header(pdf); pdf.set_font("Helvetica", '', base_font_size_page3)
                pdf.set_font("Helvetica", '', base_font_size_page3); pdf.cell(label_col_width_p3_info_table, line_h_page3, label, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP); pdf.set_font("Helvetica", 'B', base_font_size_page3); pdf.multi_cell(value_col_width_p3_info_table, line_h_page3, value, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L', max_line_height=line_h_page3) 
        pdf.ln(line_h_page3); pdf.set_font("Helvetica", '', base_font_size_page3); fee_name_width = usable_width_page3 * 0.75; fee_amount_width = usable_width_page3 * 0.25
        for item in p3_valid_fee_items: 
            if pdf.get_y() + line_h_page3 > pdf.page_break_trigger-10: pdf.add_page(orientation='P'); add_pdf_header(pdf); pdf.set_font("Helvetica", '', base_font_size_page3)
            pdf.cell(fee_name_width, line_h_page3, item['name'], border=1); pdf.cell(fee_amount_width, line_h_page3, format_pdf_number(item['amount']), border=1, align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if pdf.get_y() + line_h_page3 > pdf.page_break_trigger-10: pdf.add_page(orientation='P'); add_pdf_header(pdf); pdf.set_font("Helvetica", '', base_font_size_page3)
        photo_desc_raw = f"{p3_photo_copies_count} photograph copies @ Rs 10/- per Photograph"; photo_desc = normalize_pdf_text_for_fpdf(photo_desc_raw)
        pdf.cell(fee_name_width, line_h_page3, photo_desc, border=1); pdf.cell(fee_amount_width, line_h_page3, format_pdf_number(p3_photo_total_charge), border=1, align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if p3_total_before_gst != 0:
            pdf.set_font("Helvetica", '', base_font_size_page3); gst_lines_needed = 3 if labour_tax_type_main != 'IGST' else 2
            if pdf.get_y() + (line_h_page3 * gst_lines_needed) > pdf.page_break_trigger-10: pdf.add_page(orientation='P'); add_pdf_header(pdf); pdf.set_font("Helvetica", '', base_font_size_page3)
            pdf.cell(fee_name_width, line_h_page3, normalize_pdf_text_for_fpdf("Sub Total"), border='LR', align='R'); pdf.cell(fee_amount_width, line_h_page3, format_pdf_number(p3_total_before_gst), border='LR', align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
            if labour_tax_type_main == 'IGST':
                if p3_igst != 0: pdf.cell(fee_name_width, line_h_page3, normalize_pdf_text_for_fpdf("Add, 18% IGST"), border='LR', align='R'); pdf.cell(fee_amount_width, line_h_page3, format_pdf_number(p3_igst), border='LR', align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            else: # Survey fee GST is always 18% (CGST/SGST), even when labour tax is Zero
                if p3_cgst != 0: pdf.cell(fee_name_width, line_h_page3, normalize_pdf_text_for_fpdf("Add, 9% CGST"), border='LR', align='R'); pdf.cell(fee_amount_width, line_h_page3, format_pdf_number(p3_cgst), border='LR', align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                if p3_sgst != 0: pdf.cell(fee_name_width, line_h_page3, normalize_pdf_text_for_fpdf("Add, 9% SGST"), border='LR', align='R'); pdf.cell(fee_amount_width, line_h_page3, format_pdf_number(p3_sgst), border='LR', align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
            pdf.set_font("Helvetica", 'B', base_font_size_page3); pdf.cell(fee_name_width, line_h_page3, normalize_pdf_text_for_fpdf("Total Rupees"), border=1, align='R'); pdf.cell(fee_amount_width, line_h_page3, format_pdf_number(p3_grand_total), border=1, align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(line_h_page3 * 0.5)
        
        # --- Surveyor Bank Details (Bottom of Page 4) ---
        if surveyor_details:
            # Check space for bank details (approx 8 lines)
            if pdf.get_y() + (line_h_page3 * 8) > pdf.page_break_trigger: pdf.add_page(orientation='P'); add_pdf_header(pdf)
            
            pdf.set_font("Helvetica", 'B', base_font_size_page3)
            
            # Left Column: GSTIN, PAN, Bank Name, A/c, MICR, IFSC
            start_x = pdf.l_margin
            col1_w = 25; col2_w = 60
            
            def add_bank_row(label, value):
                pdf.set_x(start_x)
                pdf.cell(col1_w, line_h_page3, normalize_pdf_text_for_fpdf(label), 0, 0, 'L')
                pdf.cell(col2_w, line_h_page3, normalize_pdf_text_for_fpdf(value), 0, 1, 'L')

            add_bank_row("GSTIN :", surveyor_details.get('gstin', ''))
            add_bank_row("PAN :", surveyor_details.get('pan', ''))
            add_bank_row("Bank Name :", surveyor_details.get('bank_name', ''))
            add_bank_row("A/c NO. :", surveyor_details.get('account_no', ''))
            add_bank_row("MICR No. :", surveyor_details.get('micr', ''))
            add_bank_row("IFS Code :", surveyor_details.get('ifsc', ''))
            
            # Right Column: Surveyor Code & State
            state_val = surveyor_details.get('state_code', '(19)')
            code_val = surveyor_details.get('surveyor_code', '2075995')

            # Position for Right Column (adjust Y to align with top of bank details)
            pdf.set_xy(start_x + col1_w + col2_w + 10, pdf.get_y() - (line_h_page3 * 6)) 
            
            pdf.cell(50, line_h_page3, normalize_pdf_text_for_fpdf(f"State : {state_val}"), 0, 1, 'L')
            
            pdf.set_x(start_x + col1_w + col2_w + 10)
            pdf.cell(50, line_h_page3, normalize_pdf_text_for_fpdf(f"Insurer's Surveyor Code No.: {code_val}"), 0, 1, 'L')
            
            # Reset Y to below bank details
            pdf.set_y(pdf.get_y() + (line_h_page3 * 5))

        pdf.ln(line_h_page3 * 0.5) 
        if p3_grand_total_in_words and p3_grand_total != 0 : 
            words_height_est = calculate_height([p3_grand_total_in_words], [usable_width_page3 - (pdf.get_string_width("Rupees ( In Words)- ") + 1)], base_font_size_page3, line_h_page3, table_cell_padding_y/2, ['B'])
            if pdf.get_y() + words_height_est > pdf.page_break_trigger-10: pdf.add_page(orientation='P'); add_pdf_header(pdf)
            pdf.set_font("Helvetica", '', base_font_size_page3); label_text_raw = "Rupees ( In Words)-"; label_text = normalize_pdf_text_for_fpdf(label_text_raw); current_label_width = pdf.get_string_width(label_text + " ") + 1
            pdf.cell(current_label_width, line_h_page3, label_text, 0, new_x=XPos.RIGHT, new_y=YPos.TOP); pdf.set_font("Helvetica", 'B', base_font_size_page3); pdf.multi_cell(usable_width_page3 - current_label_width, line_h_page3, p3_grand_total_in_words, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        pdf.ln(line_h_page3 * 0.5); pdf.set_font("Helvetica", '', base_font_size_page3)
        if pdf.get_y() + line_h_page3 > pdf.page_break_trigger-10: pdf.add_page(orientation='P'); add_pdf_header(pdf); pdf.set_font("Helvetica", '', base_font_size_page3)
        label_text_raw = "Estimated Amount = Rs."; label_text = normalize_pdf_text_for_fpdf(label_text_raw); current_label_width = pdf.get_string_width(label_text + " ") + 1
        pdf.cell(current_label_width, line_h_page3, label_text, 0, new_x=XPos.RIGHT, new_y=YPos.TOP); pdf.set_font("Helvetica", 'B', base_font_size_page3); pdf.cell(usable_width_page3 - current_label_width, line_h_page3, format_pdf_number(p3_estimated_amount), 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT); pdf.set_font("Helvetica", '', base_font_size_page3); pdf.ln(line_h_page3 * 0.25) 
        # --- Final Assessed Amount & Signature Block ---
        # Calculate combined height for "Assessed Amount" + Gap + Signature to keep them together
        sig_block_width = usable_width_page3 * 0.5
        sig_start_x = pdf.w - pdf.r_margin - sig_block_width
        sig_height_est = line_h_page3 * 4 # Signature block height approx
        
        # Check if we need to print "Assessed Amount"
        assessed_amt_height = line_h_page3 if net_liability_final != 0 else 0
        
        # Total logic block height: Assessed Amt (if any) + Gap (2 lines) + Signature
        gap_lines = 2
        total_block_needed = assessed_amt_height + (line_h_page3 * gap_lines) + sig_height_est
        
        # Check page break trigger for the WHOLE block
        if pdf.get_y() + total_block_needed > pdf.page_break_trigger: 
            pdf.add_page(orientation='P'); add_pdf_header(pdf); pdf.set_font("Helvetica", '', base_font_size_page3)
        
        # 1. Print Assessed Amount (if applicable)
        if net_liability_final != 0: 
            pdf.set_font("Helvetica", '', base_font_size_page3)
            label_text_raw = "Net settlement Amount Round off:"; label_text = normalize_pdf_text_for_fpdf(label_text_raw); current_label_width = pdf.get_string_width(label_text + " ") + 1
            pdf.cell(current_label_width, line_h_page3, label_text, 0, new_x=XPos.RIGHT, new_y=YPos.TOP); pdf.set_font("Helvetica", 'B', base_font_size_page3); pdf.cell(usable_width_page3 - current_label_width, line_h_page3, format_pdf_number(net_liability_final), 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        # 2. Gap
        pdf.ln(line_h_page3 * gap_lines)
        
        # 3. Signature
        pdf.set_x(sig_start_x); pdf.set_font("Helvetica", 'B', base_font_size_page3); pdf.cell(sig_block_width, line_h_page3, normalize_pdf_text_for_fpdf(current_user.full_name), 0, 1, 'C')
        pdf.set_x(sig_start_x); pdf.set_font("Helvetica", '', base_font_size_page3); pdf.cell(sig_block_width, line_h_page3, "( Surveyor and Loss Assessor )", 0, 1, 'C')

        # --- Add Photo Pages ---
        add_photo_section(pdf, "First inspection photo", get_survey_val('vehicle_regn_no'), photos_data.get('first_inspection', {}).get('images', []), photos_data.get('first_inspection', {}).get('per_page', 4))
        add_photo_section(pdf, "Dismantling/follow up photo", get_survey_val('vehicle_regn_no'), photos_data.get('dismantling', {}).get('images', []), photos_data.get('dismantling', {}).get('per_page', 4))
        add_photo_section(pdf, "Re-inspection photo", get_survey_val('vehicle_regn_no'), photos_data.get('reinspection', {}).get('images', []), photos_data.get('reinspection', {}).get('per_page', 4))

        pdf_bytes = pdf.output()
        request_id = str(uuid.uuid4())
        vehicle_no_raw = final_survey_data.get('vehicle_regn_no', '')
        # Store vehicle_regn_no for filename generation
        generated_data_store[request_id] = { 
            "pdf_report": pdf_bytes, 
            "report_no": final_survey_data.get('report_no', 'SurveyReport'),
            "vehicle_no": vehicle_no_raw
        }

        # Auto-upload to Google Drive (if user connected their personal Drive via Settings)
        drive_link = None
        try:
            filename_base = "".join(c for c in vehicle_no_raw if c.isalnum() or c in ('_', '-')).rstrip() if vehicle_no_raw.strip() else 'SurveyReport'
            filename_pdf = f"{filename_base}.pdf"
            
            from flask import session
            access_token = session.get('google_access_token')
            if access_token:
                folder_name_to_use = "".join(c for c in vehicle_no_raw if c.isalnum() or c in ('_', '-', ' ')).strip() if vehicle_no_raw else 'Unknown_Vehicle'
                drive_link = upload_pdf_to_drive(access_token, pdf_bytes, filename_pdf, folder_name_to_use)
                if drive_link:
                    print(f"Report auto-uploaded to User's Personal Drive: {drive_link}")
                else:
                    print("Warning: Auto-upload to User's Personal Drive failed.")
                    
            if not drive_link:
                # Fallback to service account Drive (if available/working)
                drive_link = sheets_db.upload_report_pdf(pdf_bytes, filename_pdf, vehicle_no_raw)
                if drive_link:
                    print(f"Report auto-uploaded to Service Account Drive: {drive_link}")
                else:
                    print("Warning: Auto-upload to Service Account Drive failed (non-critical).")
        except Exception as drive_err:
            print(f"Warning: Drive auto-upload error (non-critical): {drive_err}")

        return jsonify({"request_id": request_id, "drive_link": drive_link})
    except FPDFException as fpdf_err:
        print(f"FPDF Error generating files: {fpdf_err}")
        import traceback; traceback.print_exc()
        return jsonify({"error": f"An error occurred during PDF generation: {fpdf_err}"}), 500
    except Exception as e:
        print(f"Error generating files: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": f"An unexpected error occurred during file generation: {e}"}), 500
    

# --- Download Route ---
@app.route('/download/<file_type>/<request_id>')
@login_required
def download_file(file_type, request_id):
    if request_id not in generated_data_store:
        abort(404, description="Request ID not found or expired.")

    data = generated_data_store[request_id]
    
    # Use Vehicle No for filename if available, else fallback to Report No
    vehicle_no = data.get('vehicle_no', '').strip()
    if vehicle_no:
        filename_base = "".join(c for c in vehicle_no if c.isalnum() or c in ('_', '-')).rstrip()
    else:
        report_no = data.get('report_no', 'SurveyReport').replace(' ', '_').replace('/','-')
        filename_base = "".join(c for c in report_no if c.isalnum() or c in ('_', '-')).rstrip() or 'SurveyReport'

    if file_type == 'report_pdf':
        filename = f"{filename_base}.pdf"
        mimetype = 'application/pdf'
        file_content = io.BytesIO(data['pdf_report'])
    else:
        abort(400, description="Invalid file type requested.")

    return send_file(
        file_content,
        mimetype=mimetype,
        as_attachment=False if request.args.get('preview') else True, # Allow inline for preview
        download_name=filename
    )

# --- Database Interaction Routes ---
@app.route('/save_report', methods=['POST'])
@login_required
def save_report():
    try:
        data = request.get_json()
        if not data or 'survey_report' not in data or 'assessment' not in data:
            return jsonify({"error": "Invalid data format received"}), 400

        survey_report = data.get('survey_report', {})
        report_no = survey_report.get('report_no', '').strip()
        
        if not report_no:
            return jsonify({"error": "Report Number cannot be empty"}), 400

        # Delegate saving to Sheets Helper
        # This helper handles checking for existing report by report_no + user_id and updates/creates row
        try:
            sheets_db.save_report(current_user.id, data)
            flash(f'Report "{report_no}" saved successfully (to Supabase Database).', 'success')
            return jsonify({"success": True, "message": "Report saved."})
        except Exception as sheet_error:
            print(f"Database Error: {sheet_error}")
            return jsonify({"error": f"Failed to save to Database: {str(sheet_error)}"}), 500

    except Exception as e:
        print(f"Error saving report: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": f"An unexpected error occurred while saving: {e}"}), 500
    

@app.route('/get_saved_reports', methods=['GET'])
@login_required
def get_saved_reports():
    try:
        # Optimized: Fetch only metadata columns (faster, less data)
        reports = sheets_db.get_user_reports_metadata_only(current_user.id)
        
        # Search functionality (In-memory filtering for MVP)
        search_query = request.args.get('q')
        if search_query:
            search_query = search_query.lower()
            filtered_reports = []
            for r in reports:
                # Check fields
                if (search_query in str(r.get('vehicle_no', '')).lower() or
                    search_query in str(r.get('report_no', '')).lower() or
                    search_query in str(r.get('insured_name', '')).lower()):
                    filtered_reports.append(r)
            reports = filtered_reports
            
        # Sort by date (desc) - parsing ISO string
        try:
            reports.sort(key=lambda x: datetime.fromisoformat(x.get('saved_at')) if x.get('saved_at') else datetime.min, reverse=True)
        except Exception:
            pass # sorting might fail if bad dates

        reports_list = [
            {
                'id': r.get('id'), # This ID is the row index or generated ID
                'report_no': r.get('report_no'),
                'insured_name': r.get('insured_name'),
                'vehicle_no': r.get('vehicle_no'),
                'saved_at': datetime.fromisoformat(r.get('saved_at')).strftime('%Y-%m-%d %H:%M:%S') if r.get('saved_at') else 'N/A'
            } for r in reports
        ]
        return jsonify(reports_list)
    except Exception as e:
        print(f"Error fetching saved reports: {e}")
        return jsonify({"error": f"Failed to fetch reports: {e}"}), 500
    

@app.route('/load_report/<report_id>', methods=['GET'])
@login_required
def load_report(report_id):
    try:
        # report_id is passed as int, but stored as whatever in sheets (int probably)
        # We need to find the specific report in the user's list or by ID
        # Since API doesn't have direct "get by id", we can reuse get_user_reports and filter 
        # OR implement get_report_by_id in sheets_db. 
        # For MVP, filtering user reports is safe enough for small data.
        
        reports = sheets_db.get_user_reports(current_user.id)
        target_report = None
        for r in reports:
            if str(r.get('id')) == str(report_id):
                target_report = r
                break
        
        if target_report:
            try:
                report_data = json.loads(target_report.get('report_data_json'))
            except (json.JSONDecodeError, TypeError, ValueError):
                # Fallback if json string is malformed or empty
                report_data = {} 
            return jsonify(report_data)
        else:
            return jsonify({"error": "Report not found or access denied"}), 404
    except Exception as e:
        print(f"Error loading report {report_id}: {e}")
        return jsonify({"error": f"Failed to load report: {e}"}), 500

@app.route('/api/generate_report_no', methods=['POST'])
@login_required
def generate_report_no():
    try:
        data = request.get_json()
        insurer_name = data.get('insurer', '').upper()
        
        # Map known insurers to prefixes
        prefix = "REP"
        if "NATIONAL INSURANCE" in insurer_name:
            prefix = "NIC"
        elif "NEW INDIA" in insurer_name:
            prefix = "NIA"
        elif "ORIENTAL" in insurer_name:
            prefix = "OIC"
        elif "UNITED INDIA" in insurer_name:
            prefix = "UIIC"
        
        current_year = str(datetime.now().year)
        
        # Fetch user's existing reports to find the highest sequence number for this prefix and year
        reports_metadata = sheets_db.get_user_reports_metadata_only(current_user.id)
        
        max_seq = 0
        search_pattern = f"{prefix}/{current_year}/"
        
        for report in reports_metadata:
            report_num = str(report.get('report_no', ''))
            if report_num.startswith(search_pattern):
                try:
                    # Extract the sequence part (e.g., from "NIC/2026/01", extract "01")
                    seq_str = report_num.split('/')[-1]
                    seq_num = int(seq_str)
                    if seq_num > max_seq:
                        max_seq = seq_num
                except ValueError:
                    continue
        
        new_seq = max_seq + 1
        new_report_no = f"{prefix}/{current_year}/{new_seq:02d}"
        
        return jsonify({"report_no": new_report_no}), 200
        
    except Exception as e:
        print(f"Error generating report number: {e}")
        return jsonify({"error": "Failed to generate report number"}), 500

@app.route('/delete_report/<report_id>', methods=['DELETE'])
@login_required
def delete_report(report_id):
    try:
        data = request.get_json()
        password = data.get('password')
        
        if not password:
             return jsonify({"error": "Password is required to delete a report."}), 400
             
        # Check password against current user (stored in session/sheets)
        # current_user.password_hash came from sheets_db during login
        if not bcrypt.check_password_hash(current_user.password_hash, password):
             return jsonify({"error": "Incorrect password."}), 403

        # Deletion in Sheets is risky (shifting rows). 
        # For MVP, we will NOT delete to prevent data corruption.
        # Alternatively, we could clear the row content or mark as "deleted" column.
        if sheets_db.delete_report(report_id, current_user.id):
             return jsonify({"message": "Report deleted successfully"}), 200
        else:
             return jsonify({"error": "Failed to delete report or not found"}), 404
        
    except Exception as e:
        print(f"Error deleting report {report_id}: {e}")
        return jsonify({"error": f"Failed to delete report: {e}"}), 500

@app.route('/download_consolidated_csv', methods=['GET'])
@login_required
def download_consolidated_csv():
    try:
        from_date_str = request.args.get('from_date')
        to_date_str = request.args.get('to_date')

        if not from_date_str or not to_date_str:
            return jsonify({"error": "Both from_date and to_date are required."}), 400

        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            # For to_date, include the whole day by setting time to end of day
            to_date_dt = datetime.strptime(to_date_str, '%Y-%m-%d')
            to_date_end_of_day = datetime.combine(to_date_dt.date(), datetime.max.time())
        except ValueError:
            return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD."}), 400

        # Fetch all from sheets and filter
        all_reports = sheets_db.get_user_reports(current_user.id)
        reports = []
        for r in all_reports:
            # Filter by date and included flag
            # Dates in sheet are ISO format string or similar
            saved_at_str = r.get('saved_at')
            if not saved_at_str: continue
            try:
                saved_at = datetime.fromisoformat(saved_at_str)
                # Check Include Flag (Sheets stores as boolean or string 'TRUE'/'FALSE')
                # include_flag = r.get('include_in_consolidated')
                # Strict filtering removed to allow all reports since default was False previously
                # if str(include_flag).upper() != 'TRUE' and include_flag is not True:
                #      continue
                
                # Check Date Range
                if saved_at >= datetime.combine(from_date, datetime.min.time()) and saved_at <= to_date_end_of_day:
                    reports.append(r)
            except (ValueError, TypeError): 
                continue

        # Sort
        reports.sort(key=lambda x: datetime.fromisoformat(x.get('saved_at')) if x.get('saved_at') else datetime.min)
        
        # reports object is now a list of dicts, unlike SQLAlchemy objects
        # Update usage below in simple content (report.report_data_json -> report['report_data_json'])
        # I'll update the loop below as well.

        if not reports:
             pass 

        output = io.StringIO()
        csv_writer = csv.writer(output)

        headers = [
            "Sl No", "Date", "Name of the Insurer", "Voucher No.", "GSTIN/UIN",
            "GROSS TOTAL", "CGST", "SGST", "IGST",
            "Estimated Amount", "Assessed Amount"
        ]
        csv_writer.writerow(headers)
        
        sl_no_counter = 1
        for report in reports:
            try:
                report_data = json.loads(report.get('report_data_json'))
                survey_data = report_data.get('survey_report', {})
                assessment_data = report_data.get('assessment', {})

                # Use the helper to get calculated summary values
                calculated_summary = _calculate_report_assessment_summary(assessment_data, survey_data)

                report_date_val = survey_data.get('report_date', 'N/A')
                insurer_name_val = survey_data.get('insurer', 'N/A')
                voucher_no_val = survey_data.get('report_no', 'N/A')
                
                customer_gstin_val = calculated_summary.get('customer_gstin', 'N/A') if calculated_summary.get('customer_gstin') else 'N/A'

                page3_gross_total_val = f"{calculated_summary.get('page3_gross_total', 0.0):.2f}"
                
                page3_cgst_val = f"{calculated_summary.get('page3_cgst', 0.0):.2f}" if calculated_summary.get('page3_cgst', 0.0) > 0 else 'N/A'
                page3_sgst_val = f"{calculated_summary.get('page3_sgst', 0.0):.2f}" if calculated_summary.get('page3_sgst', 0.0) > 0 else 'N/A'
                page3_igst_val = f"{calculated_summary.get('page3_igst', 0.0):.2f}" if calculated_summary.get('page3_igst', 0.0) > 0 else 'N/A'

                estimated_amount_val = f"{calculated_summary.get('estimated_amount', 0.0):.2f}" if calculated_summary.get('estimated_amount') else 'N/A'
                assessed_amount_val = f"{calculated_summary.get('assessed_amount', 0.0):.2f}"

                row_data = [
                    sl_no_counter,
                    report_date_val,
                    insurer_name_val,
                    voucher_no_val,
                    customer_gstin_val,
                    page3_gross_total_val,
                    page3_cgst_val,
                    page3_sgst_val,
                    page3_igst_val,
                    estimated_amount_val,
                    assessed_amount_val
                ]
                csv_writer.writerow(row_data)
                sl_no_counter += 1
            except Exception as e_inner:
                print(f"Skipping report ID {report.get('id')} due to error during processing for CSV: {e_inner}")
                # Optionally write a placeholder row indicating an error for this report
                csv_writer.writerow([sl_no_counter, 'ERROR', f"Error processing report ID {report.get('id')}", '', '', '', '', '', '', '', ''])
                sl_no_counter += 1


        output.seek(0)
        
        filename = f"Consolidated_Reports_{from_date_str}_to_{to_date_str}.csv"
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"Error generating consolidated CSV: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred while generating the CSV. Please try again."}), 500

# --- Initial User Creation Helper (Manual Trigger via API or Script recommended for Sheets) ---
# Since we removed DB init, users must be added to the Sheet manually or via a new CLI command.
@app.cli.command('create-default-user')
def create_default_user():
    """Create the default user in Google Sheets if not exists."""
    # SECURITY: Read credentials from environment variables (VULN-01)
    username = os.getenv('ADMIN_USERNAME')
    password = os.getenv('ADMIN_PASSWORD')
    
    if not username or not password:
        print("ERROR: ADMIN_USERNAME and ADMIN_PASSWORD must be set as environment variables.")
        return
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    existing = sheets_db.get_user_by_username(username)
    if not existing:
        user_data = {
            'username': username,
            'password_hash': hashed_password,
            'full_name': os.getenv('USER_FULL_NAME', 'Default User'),
            'qualifications': os.getenv('USER_QUALIFICATIONS', ''),
            'designation': os.getenv('USER_DESIGNATION', 'Surveyor & Loss Assessor'),
            'license_no': os.getenv('USER_LICENSE_NO', ''),
            'expiry_date': os.getenv('USER_EXPIRY_DATE', ''),
            'membership_no': os.getenv('USER_MEMBERSHIP_NO', ''),
            'address_line_1': os.getenv('USER_ADDRESS_1', ''),
            'address_line_2': os.getenv('USER_ADDRESS_2', ''),
            'address_line_3': os.getenv('USER_ADDRESS_3', ''),
            'contact_no': os.getenv('USER_CONTACT_NO', ''),
            'email': os.getenv('USER_EMAIL', '')
        }
        sheets_db.create_user(user_data)
        print(f"Default user '{username}' created in Sheets.")
    else:
        print(f"User '{username}' already exists in Sheets.")

# --- Run Application ---
if __name__ == '__main__':
    # Use waitress or gunicorn for production
    # from waitress import serve
    is_dev = os.getenv('FLASK_ENV') == 'development'
    app.run(debug=is_dev, host='0.0.0.0', port=5000)

 # .\.venv\Scripts\activate 
 # pytest tests/
