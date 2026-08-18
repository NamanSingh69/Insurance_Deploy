"""
Convert docs/CLIENT_USER_MANUAL_AND_CHANGELOG.md to a comprehensive, professional PDF
with embedded high-resolution screenshots, formatted tables, mathematical formulas, and branding.
"""
import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    import fpdf
    import PIL
except ImportError:
    sys.path.insert(0, os.path.join(base_dir, 'test_deps'))
    sys.path.insert(0, os.path.join(base_dir, 'venv', 'lib', 'site-packages'))

from fpdf import FPDF
from fpdf.enums import XPos, YPos

class ClientManualPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        if self.page_no() > 1:
            self.set_fill_color(15, 23, 42) # Slate Dark Blue
            self.rect(0, 0, 210, 13, 'F')
            self.set_font('Helvetica', 'B', 8.5)
            self.set_text_color(255, 255, 255)
            self.set_xy(12, 2.5)
            self.cell(140, 8, 'MOTOR SURVEY MANAGEMENT SOFTWARE - CLIENT USER MANUAL & RELEASE NOTES', new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.set_xy(150, 2.5)
            self.cell(48, 8, 'https://skinsurance.tech', align='R', new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.ln(10)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 6, f'Page {self.page_no()} of {{nb}}  |  Sk Anowar Ali (Licence: SLA-121784, Mobile: 8777370714)', align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)

    def section_heading(self, title):
        self.ln(3)
        self.set_font('Helvetica', 'B', 12)
        self.set_fill_color(241, 245, 249)
        self.set_text_color(15, 23, 42)
        self.cell(0, 8, f'  {title}', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def sub_heading(self, text):
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(30, 58, 138)
        self.cell(0, 5.5, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def paragraph(self, text):
        self.set_font('Helvetica', '', 9)
        self.set_text_color(51, 65, 85)
        self.multi_cell(0, 4.4, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1.5)

    def bullet_point(self, title, description):
        self.set_font('Helvetica', 'B', 8.5)
        self.set_text_color(30, 41, 59)
        self.cell(4, 4.2, chr(149), new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(self.get_string_width(f" {title}: ") + 2, 4.2, f" {title}: ", new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_font('Helvetica', '', 8.5)
        self.set_text_color(71, 85, 105)
        remaining_width = 210 - self.get_x() - 14
        self.multi_cell(remaining_width, 4.2, description, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def callout_box(self, title, text, bg_color=(238, 242, 255), border_color=(199, 210, 254), title_color=(30, 58, 138)):
        self.set_fill_color(*bg_color)
        self.set_draw_color(*border_color)
        
        lines = self.multi_cell(180, 4.2, f"{title}\n{text}", dry_run=True, output="LINES")
        box_height = max(16, len(lines) * 4.4 + 6)
        
        if self.get_y() + box_height > 280:
            self.add_page()
            
        self.rect(12, self.get_y(), 186, box_height, 'DF')
        curr_y = self.get_y()
        self.set_xy(15, curr_y + 2.5)
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(*title_color)
        self.cell(0, 4.5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(15)
        self.set_font('Helvetica', '', 8.5)
        self.set_text_color(51, 65, 85)
        self.multi_cell(180, 4.2, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(curr_y + box_height + 3)

    def embed_screenshot(self, image_path, caption, img_width=175):
        if not os.path.exists(image_path):
            return
        
        img_height = 80
        if self.get_y() + img_height + 12 > 280:
            self.add_page()
            
        curr_y = self.get_y()
        self.set_fill_color(248, 250, 252)
        self.set_draw_color(226, 232, 240)
        self.rect(13, curr_y, 184, img_height + 10, 'DF')
        
        self.image(image_path, x=17.5, y=curr_y + 3, w=img_width, h=img_height)
        
        self.set_xy(15, curr_y + img_height + 3.5)
        self.set_font('Helvetica', 'I', 7.5)
        self.set_text_color(100, 116, 139)
        self.cell(180, 5, f'Figure: {caption}', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(curr_y + img_height + 12)

def generate_pdf():
    pdf = ClientManualPDF()
    pdf.alias_nb_pages()
    
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')
    downloads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'downloads')
    os.makedirs(downloads_dir, exist_ok=True)
    
    # ==================== PAGE 1: COVER & EXECUTIVE SUMMARY ====================
    pdf.add_page()
    
    # Title Banner
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 46, 'F')
    
    pdf.set_font('Helvetica', 'B', 17)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(14, 8)
    pdf.cell(0, 8, 'MOTOR SURVEY MANAGEMENT SOFTWARE', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(56, 189, 248)
    pdf.set_x(14)
    pdf.cell(0, 6, 'Client User Manual, Feature Changelog & Visual Release Guide', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font('Helvetica', '', 8.5)
    pdf.set_text_color(203, 213, 225)
    pdf.set_x(14)
    pdf.cell(0, 5, 'Production Platform: https://skinsurance.tech  |  Release Version: v2.3.0 (August 2026 Production Build)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_y(52)
    
    # Metadata Card
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(14, 50, 182, 24, 'DF')
    pdf.set_xy(18, 52)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(35, 4.5, 'Client / Surveyor:', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font('Helvetica', '', 8.5)
    pdf.cell(140, 4.5, 'Sk Anowar Ali (Licensed Motor Surveyor & Loss Assessor)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_x(18)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.cell(35, 4.5, 'Licence & Contact:', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font('Helvetica', '', 8.5)
    pdf.cell(140, 4.5, 'SLA-121784 | Mobile: 8777370714 | Email: skanowarali93@gmail.com', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_x(18)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.cell(35, 4.5, 'Scope of Release:', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font('Helvetica', '', 8.5)
    pdf.cell(140, 4.5, 'Word Fee Bill Generator, Dual Invoicing, Document Reminders, Photo Fixes, Role Security & CI/CD', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(5)
    
    # Section 1
    pdf.section_heading('1. Executive Summary & Enhancements Overview')
    pdf.paragraph(
        "This production release (v2.3.0) delivers a complete operational upgrade to the Motor Survey Management platform at skinsurance.tech. "
        "The system provides complete operational automation for survey job tracking, document collection reminders, "
        "master insurer directory setup, official Word-replica professional fee billing, and vehicle damage photo attachments."
    )
    
    pdf.sub_heading('Summary of Core Enhancements')
    pdf.bullet_point("1. Word Template Fee Bill Generator", "Pixel-perfect replica of the official Word template (rgi fees with signature.docx) with checkbox line items, automatic conveyance formulas, 18% GST, and digital seal/signature toggles.")
    pdf.bullet_point("2. Dual Fee Invoicing Workflow", "Seamlessly generate fee bills linked to claim survey reports (Report No. auto-linked) or standalone fee bills with sequential numbers (NIC-0001, OGI-0001).")
    pdf.bullet_point("3. In-Place Dashboard Drilldown", "Clicking any KPI card filters claims immediately below the cards without losing workspace context.")
    pdf.bullet_point("4. Missing Documents Checklist Modal", "Granular document tracking with dynamic custom items and 3-cycle automated reminder notices.")
    pdf.bullet_point("5. Insurer Master Management", "Centralized directory for Insurer addresses, GSTINs, default rates, and billing prefixes.")
    pdf.bullet_point("6. Damage Photo Upload & PDF Fix", "Drag-and-drop HD photo uploader with normalized PDF embedding, eliminating 'Error loading image' issues.")
    pdf.bullet_point("7. Role Security & Financial Redaction", "Employee role (USER) is completely restricted from fee registers, billing routes, and financial revenue KPIs.")
    pdf.bullet_point("8. Automated 1-Click CI/CD", "Direct push-to-deploy pipeline running over authenticated HTTPS webhooks with automated asset cache-busting.")
    
    # ==================== PAGE 2: FEE BILL GENERATOR & WORKFLOW ====================
    pdf.add_page()
    pdf.section_heading('2. Feature Walkthrough & Operating Guide')
    
    pdf.sub_heading('Feature 1: Official Motor Survey Fee Bill Generator (Word Template Replica)')
    pdf.bullet_point("Where to Find", "In the top navigation bar, open the 'Survey Fee Register' tab (#tab-fees).")
    pdf.bullet_point("How it Works", "Select dynamic line-item checkboxes for Final Survey Fees, Local/KM Conveyance, 2nd Visit Conveyance, Re-inspection, Photos, Halting charges, and Other charges. Calculates Taxable Subtotal, SAC Code 997162, 18% GST, and Gross Total.")
    
    fee_form_img = os.path.join(docs_dir, 'admin_02_fee_register_form.png')
    pdf.embed_screenshot(fee_form_img, 'Survey Fee Register Form with Checkbox Line Items & Live Calculations')
    
    pdf.callout_box(
        "Official Conveyance & GST Calculation Formula",
        "Conveyance Formula: <From> to <To> (<One-Way KM> x 2 = <Total KM> km @ Rs. <Rate>/-)\n"
        "Taxable Amount = Selected Fee Items (Survey + Conveyance + Photos + Halting + Misc)\n"
        "GST Amount (18%) = Taxable Amount x 0.18\n"
        "Gross Bill Total = Taxable Amount + GST Amount (18%)\n"
        "Example: Rs. 1,500 (Survey) + Rs. 500 (Conv) + Rs. 200 (Photo) = Rs. 2,200 Taxable | Rs. 396 GST | Rs. 2,596 Gross Total"
    )
    
    # ==================== PAGE 3: PREVIEW BILL & DUAL INVOICING ====================
    pdf.add_page()
    pdf.sub_heading('Feature 2: Word Template Replica PDF Output & Dual Invoicing')
    pdf.bullet_point("Word Template Replica", "Generates pixel-perfect fee bills matching rgi fees with signature.docx including Surveyor Header, Insurer GSTIN, 2-Column Claim info, and Bank Account Footer.")
    pdf.bullet_point("Dual Invoicing Workflow", "Supports Claim-linked bills (Report No. auto-linked) and Standalone bills with sequential Bill No. (e.g. NIC-0001).")
    
    fee_preview_img = os.path.join(docs_dir, 'admin_03_preview_fee_bill_page_1.png')
    pdf.embed_screenshot(fee_preview_img, 'Official Word-Replica Fee Bill Generated PDF Output with Stamp & Bank Details')
    
    # ==================== PAGE 4: DASHBOARD, MASTERS & PHOTOS ====================
    pdf.add_page()
    pdf.sub_heading('Feature 3: Operational Dashboard & Role-Based Permissions')
    pdf.bullet_point("Dashboard Drilldown", "Clicking any KPI card highlights it and renders the filtered claims table directly below without reloading.")
    pdf.bullet_point("Role Security", "Admin (NAMAN) has full access to financial tools, while Employee (USER) has financial fee registers redacted for business privacy.")
    
    navbar_img = os.path.join(docs_dir, 'admin_01_navbar_badge.png')
    pdf.embed_screenshot(navbar_img, 'Top Navigation Bar with Admin Role Badge and Tab Access')
    
    pdf.ln(1)
    pdf.sub_heading('Feature 4: Insurer Masters, Documents Checklist & Photo Fixes')
    pdf.bullet_point("Master Insurer Directory", "Stores company GSTINs, branch addresses, default rates, and auto-prefix rules.")
    pdf.bullet_point("Documents Checklist", "Granular checklist with 7-day automated client reminder notices.")
    pdf.bullet_point("Photo Embedding Fix", "Stream normalization in background workers guarantees clean rendering in survey reports.")
    
    pdf.section_heading('3. Automated Backups & System Maintenance')
    pdf.bullet_point("Daily Nightly Backup Cron", "Automatically dumps and compresses the PostgreSQL database every night to /root/backups/ with 14-day rotation.")
    pdf.bullet_point("Automated SSL Renewal", "Let's Encrypt SSL certificates renew automatically via certbot.timer on Nginx.")
    pdf.bullet_point("1-Click Push-to-Deploy", "Running 'python scripts/deploy.py' triggers the authenticated webhook on the VPS in ~3 seconds.")
    
    webhook_img = os.path.join(docs_dir, 'webhook_delivery_1_1786828833808.png')
    pdf.embed_screenshot(webhook_img, 'Automated CI/CD: Verified GitHub Webhook push-to-deploy pipeline (HTTP 200 OK in 0.75s)')
    
    # ==================== PAGE 6: CREDENTIALS & CLIENT ADVICE ====================
    pdf.add_page()
    pdf.section_heading('4. User Credentials & Access Summary')
    pdf.paragraph("The table below details default login credentials and permission scopes configured on https://skinsurance.tech:")
    
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_fill_color(226, 232, 240)
    pdf.cell(38, 6, 'Account Role', 1, 0, 'L', True, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(35, 6, 'Username', 1, 0, 'L', True, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(35, 6, 'Default Password', 1, 0, 'L', True, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(74, 6, 'Permitted Capabilities', 1, 1, 'L', True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font('Helvetica', '', 8)
    pdf.cell(38, 6, 'Administrator', 1, 0, 'L', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(35, 6, 'NAMAN', 1, 0, 'L', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(35, 6, '69420', 1, 0, 'L', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(74, 6, 'Full Access (Operations, Fee Register, GSTR-1, Settings)', 1, 1, 'L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.cell(38, 6, 'Employee / Staff', 1, 0, 'L', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(35, 6, 'USER', 1, 0, 'L', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(35, 6, 'UH65A#DF', 1, 0, 'L', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(74, 6, 'Operational Access (Claim Register, Survey Reports, PDF Download)', 1, 1, 'L', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(5)
    pdf.callout_box(
        "Client Operational Advice & Google OAuth Setup",
        "- Google OAuth Redirect URIs: Set Web application URIs to:\n"
        "  * Google Drive: https://skinsurance.tech/auth/google/callback\n"
        "  * Gmail Sync: https://skinsurance.tech/auth/gmail/callback\n"
        "- Password Customization: Passwords can be changed anytime via Settings -> User Profile.\n"
        "- Cache-Busting: All updates reflect immediately without needing to clear browser cache.\n"
        "- Developer Contact: For support or custom report adjustments, reach out directly."
    )
    
    output_pdf_docs = os.path.join(docs_dir, 'CLIENT_USER_MANUAL_AND_CHANGELOG.pdf')
    output_pdf_downloads = os.path.join(downloads_dir, 'CLIENT_USER_MANUAL_AND_CHANGELOG.pdf')
    
    pdf.output(output_pdf_docs)
    pdf.output(output_pdf_downloads)
    print(f"[SUCCESS]: Generated {output_pdf_docs} ({os.path.getsize(output_pdf_docs)} bytes)")
    print(f"[SUCCESS]: Generated {output_pdf_downloads} ({os.path.getsize(output_pdf_downloads)} bytes)")

if __name__ == '__main__':
    generate_pdf()
