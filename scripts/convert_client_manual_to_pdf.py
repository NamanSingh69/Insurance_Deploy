"""
Convert docs/CLIENT_USER_MANUAL_AND_CHANGELOG.md to a highly detailed, professional PDF
with embedded high-resolution screenshots, formatted tables, mathematical formulas, and branding.
"""
import os
import sys
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
        
        # Check if box exceeds page
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
        
        # Estimated height for 175mm width (typically 16:9 or 16:10 -> ~90-100mm)
        img_height = 82
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
    pdf.cell(0, 5, 'Production Platform: https://skinsurance.tech  |  Release Version: v2.2.0 (August 2026)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
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
    pdf.cell(140, 4.5, 'Sk Anowar Ali (Motor Surveyor & Loss Assessor)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_x(18)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.cell(35, 4.5, 'Licence & Contact:', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font('Helvetica', '', 8.5)
    pdf.cell(140, 4.5, 'SLA-121784 | Mobile: 8777370714 | Email: skanowarali93@gmail.com', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_x(18)
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.cell(35, 4.5, 'Scope of Release:', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font('Helvetica', '', 8.5)
    pdf.cell(140, 4.5, 'Requirements R1-R6, Role Partitioning, GST Fee Calculations & Zero-Friction CI/CD', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(5)
    
    # Section 1
    pdf.section_heading('1. Executive Summary & Enhancements Overview')
    pdf.paragraph(
        "This release delivers major upgrades to the Motor Survey Management platform at skinsurance.tech. "
        "The system provides complete operational automation for survey job tracking, document collection reminders, "
        "master insurer directory setup, whole-rupee professional fee calculations, and vehicle damage photo uploads."
    )
    
    pdf.sub_heading('Summary of Core Enhancements (R1 - R6)')
    pdf.bullet_point("R1 - In-Place Dashboard Drilldown", "Clicking any KPI card filters claims immediately below the cards without losing context.")
    pdf.bullet_point("R2 - Missing Documents Checklist Modal", "Granular document tracking with dynamic custom items and multi-cycle reminder notices.")
    pdf.bullet_point("R3 - Insurer Master Management", "Centralized directory for Insurer addresses, GSTINs, default rates, and billing prefixes.")
    pdf.bullet_point("R4 - Smart Auto-Prefix & Invoicing", "Auto-derives standard acronyms (NIC, OGI, UIIC) and fetches sequential invoice numbers.")
    pdf.bullet_point("R5 - Fee Stepper & Live Summary", "Whole-rupee precision (step=1) and real-time live card showing Taxable, 18% GST, and Gross Total.")
    pdf.bullet_point("R6 - Photo Upload Diagnostics", "Batch drag-and-drop HD vehicle photo uploader with client-side throttling to prevent false quota errors.")
    pdf.bullet_point("Role Security & Redaction", "Employee role (USER) is completely restricted from fee registers, billing routes, and financial KPIs.")
    pdf.bullet_point("Automated Push-to-Deploy", "Direct GitHub webhook pipeline deploying code updates in ~3 seconds with dynamic cache-busting.")
    
    # ==================== PAGE 2: R1 & R2 ====================
    pdf.add_page()
    pdf.section_heading('2. Feature Walkthrough & Visual Proof')
    
    pdf.sub_heading('Feature 1: Operational Dashboard & In-Place Drilldown (Requirement R1)')
    pdf.bullet_point("Where to Find", "Click the 'Dashboard' navigation tab on the top menu.")
    pdf.bullet_point("How it Works", "Clicking any KPI metric card (e.g. Documents Awaited) highlights the card with a blue border (.active-metric-card) and opens the filtered claims table directly below the KPI grid in #dashboard-drilldown-section.")
    
    r1_img = os.path.join(docs_dir, 'evidence_r1_dashboard_drilldown.png')
    pdf.embed_screenshot(r1_img, 'Requirement R1: In-place claim drilldown rendered directly below dashboard KPI cards')
    
    pdf.ln(1)
    pdf.sub_heading('Feature 2: Missing Documents Checklist & Reminders Modal (Requirement R2)')
    pdf.bullet_point("Where to Find", "In the Claim Register, click the 'Docs' button on any active claim row.")
    pdf.bullet_point("How it Works", "Opens a checklist modal showing required documents (RC, DL, Policy, Claim Form, FIR, Estimate). Allows adding custom documents and tracks 7-day 3-cycle reminder notices.")
    
    r2_img = os.path.join(docs_dir, 'evidence_r2_docs_modal.png')
    pdf.embed_screenshot(r2_img, 'Requirement R2: Pending documents checklist modal with instant status toggles and reminder tracking')
    
    # ==================== PAGE 3: R3 & R4 ====================
    pdf.add_page()
    pdf.sub_heading('Feature 3: Master Insurer Directory & Setup (Requirement R3)')
    pdf.bullet_point("Where to Find", "In the Survey Fee Register, click '+ Manage Insurer Masters' (.open-insurer-master-modal-btn).")
    pdf.bullet_point("How it Works", "Allows storing Insurer Name, Branch Address, GSTIN, Default Rate/Km, and Invoice Prefix. Selecting an insurer auto-fills all billing and address fields.")
    
    r3_img = os.path.join(docs_dir, 'evidence_r3_insurer_master_btn.png')
    pdf.embed_screenshot(r3_img, 'Requirement R3: Master insurer configuration modal for managing branch offices, GSTINs, and default rates')
    
    pdf.ln(1)
    pdf.sub_heading('Feature 4: Smart Auto-Prefix & Sequential Invoice Numbering (Requirement R4)')
    pdf.bullet_point("Where to Find", "In the Survey Fee Register form under the Insurer input field.")
    pdf.bullet_point("How it Works", "Typing 'National Insurance Company' auto-derives 'NIC' prefix and auto-fills the next sequential invoice number (e.g. NIC-0001).")
    
    r4_img = os.path.join(docs_dir, 'evidence_r4_auto_invoice_prefix.png')
    pdf.embed_screenshot(r4_img, 'Requirement R4: Smart uppercase acronym auto-prefixing (NIC-0001, OGI-0001) and sequential numbering')
    
    # ==================== PAGE 4: R5 & R6 ====================
    pdf.add_page()
    pdf.sub_heading('Feature 5: Professional Fee Stepper & Live Calculation Summary (Requirement R5)')
    pdf.bullet_point("Where to Find", "In the Survey Fee Register form under professional fee and conveyance inputs.")
    pdf.bullet_point("How it Works", "Enforces whole-rupee increments (step=1). Real-time summary card dynamically computes Taxable Amount, 18% GST, and Gross Total.")
    
    pdf.callout_box(
        "Live Calculation Mathematical Formula",
        "Taxable Amount = Professional Fee + Total Conveyance + Photocopy Charges\n"
        "GST (18%) = Taxable Amount x 0.18\n"
        "Gross Total = Taxable Amount + GST (18%)\n"
        "Example: Rs. 1,500 (Prof) + Rs. 500 (Conv) + Rs. 200 (Photo) = Rs. 2,200 Taxable | Rs. 396 GST | Rs. 2,596 Gross Total"
    )
    
    r5_img = os.path.join(docs_dir, 'evidence_r5_live_fee_calculation.png')
    pdf.embed_screenshot(r5_img, 'Requirement R5: Integer rupee fee inputs and live calculation summary card with 18% GST computation')
    
    pdf.ln(1)
    pdf.sub_heading('Feature 6: Damage Photo Upload Diagnostics & Throttling (Requirement R6)')
    pdf.bullet_point("Where to Find", "In the Upload & Documents section under Vehicle Damage Photos.")
    pdf.bullet_point("How it Works", "Supports drag-and-drop batch upload of HD photos with client-side rate limit throttling to eliminate false storage quota errors.")
    
    r6_img = os.path.join(docs_dir, 'evidence_r6_photo_upload.png')
    pdf.embed_screenshot(r6_img, 'Requirement R6: Vehicle damage photo upload dropzone with real-time thumbnail previews and throttling')
    
    # ==================== PAGE 5: ROLE REDACTION & SYSTEM DEPLOYMENT ====================
    pdf.add_page()
    pdf.sub_heading('Feature 7: Dual-Role Team Permissions & Financial Redaction')
    pdf.bullet_point("Administrator Role (NAMAN)", "Full unrestricted access to operational claims, fee registers, GST exports, user accounts, and billing masters.")
    pdf.bullet_point("Employee Role (USER)", "Operational access for claim registrations and report drafting. Survey Fee Register tab and revenue metrics are completely hidden and API blocked (403 Forbidden).")
    
    role_img = os.path.join(docs_dir, 'evidence_employee_financial_redaction.png')
    pdf.embed_screenshot(role_img, 'Role Partitioning: Complete financial fee register redaction and revenue KPI hiding for employee accounts')
    
    pdf.section_heading('3. Automated Backups & System Maintenance')
    pdf.bullet_point("Daily Nightly Backup Cron", "Automatically executes pg_dump to /root/backups/ every night and purges backups older than 14 days.")
    pdf.bullet_point("Automated SSL Renewal", "Let's Encrypt SSL certificates renew automatically via certbot.timer on Nginx.")
    pdf.bullet_point("Push-to-Deploy Webhook", "Every GitHub commit automatically triggers /api/deploy-webhook, updating the site in ~3 seconds.")
    
    webhook_img = os.path.join(docs_dir, 'webhook_delivery_1_1786828833808.png')
    pdf.embed_screenshot(webhook_img, 'Automated CI/CD: Verified GitHub Webhook push-to-deploy pipeline (HTTP 200 OK in 0.75s)')
    
    # ==================== PAGE 6: USER CREDENTIALS & SUMMARY ====================
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
        "Client Operational Advice",
        "- Password Customization: Passwords can be changed anytime via Settings -> User Profile.\n"
        "- Browser Caching: Asset cache-busting (?v=commit_sha) ensures updates reflect immediately without clearing browser cache.\n"
        "- Client Support: For assistance or custom report template modifications, contact the developer."
    )
    
    # Save outputs
    output_pdf_docs = os.path.join(docs_dir, 'CLIENT_USER_MANUAL_AND_CHANGELOG.pdf')
    output_pdf_downloads = os.path.join(downloads_dir, 'CLIENT_USER_MANUAL_AND_CHANGELOG.pdf')
    
    pdf.output(output_pdf_docs)
    pdf.output(output_pdf_downloads)
    print(f"[SUCCESS]: Generated {output_pdf_docs} ({os.path.getsize(output_pdf_docs)} bytes)")
    print(f"[SUCCESS]: Generated {output_pdf_downloads} ({os.path.getsize(output_pdf_downloads)} bytes)")

if __name__ == '__main__':
    generate_pdf()
