"""
Comprehensive Client User Manual & Operational Reference Guide PDF Generator
Prepared for: Sk Anowar Ali (Motor Surveyor & Loss Assessor)
Platform: https://skinsurance.tech (Version 2.2 Production)
"""
import os
import sys
from fpdf import FPDF
from fpdf.enums import XPos, YPos

class PDFUserGuide(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_fill_color(15, 23, 42) # Slate Dark Blue
            self.rect(0, 0, 210, 14, 'F')
            self.set_font('Helvetica', 'B', 8.5)
            self.set_text_color(255, 255, 255)
            self.set_xy(10, 3)
            self.cell(140, 8, 'MOTOR SURVEY MANAGEMENT SYSTEM - CLIENT USER MANUAL', new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.set_xy(150, 3)
            self.cell(50, 8, 'https://skinsurance.tech', align='R', new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.ln(11)

    def footer(self):
        self.set_y(-14)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 8, f'Page {self.page_no()} of {{nb}}  |  Sk Anowar Ali (Licence No.: SLA-121784, Mobile: 8777370714)', align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)

    def chapter_title(self, num, title):
        self.set_font('Helvetica', 'B', 12)
        self.set_fill_color(241, 245, 249) # Light Slate Fill
        self.set_text_color(15, 23, 42) # Slate Dark
        self.cell(0, 8, f'  {num}. {title}', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def sub_heading(self, text):
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(30, 58, 138) # Navy Blue
        self.cell(0, 5.5, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def paragraph(self, text):
        self.set_font('Helvetica', '', 9)
        self.set_text_color(51, 65, 85) # Slate Gray
        self.multi_cell(0, 4.5, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def callout_box(self, title, text, bg_color=(238, 242, 255), text_color=(30, 58, 138)):
        self.set_fill_color(*bg_color)
        self.set_draw_color(199, 210, 254)
        self.set_font('Helvetica', 'B', 9.5)
        self.set_text_color(*text_color)
        
        lines = self.multi_cell(180, 4.2, f"{title}\n{text}", dry_run=True, output="LINES")
        box_height = max(16, len(lines) * 4.4 + 6)
        
        self.rect(12, self.get_y(), 186, box_height, 'DF')
        curr_y = self.get_y()
        self.set_xy(15, curr_y + 2.5)
        self.set_font('Helvetica', 'B', 9)
        self.cell(0, 4.5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(15)
        self.set_font('Helvetica', '', 8.5)
        self.multi_cell(180, 4.2, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(curr_y + box_height + 3)

def build_pdf():
    pdf = PDFUserGuide()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=16)
    
    # ==================== PAGE 1: COVER & OVERVIEW ====================
    pdf.add_page()
    
    # Cover Header Banner
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 48, 'F')
    
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(14, 9)
    pdf.cell(0, 8, 'MOTOR SURVEY MANAGEMENT SYSTEM', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(56, 189, 248) # Sky Blue
    pdf.set_x(14)
    pdf.cell(0, 6, 'Client User Manual & Comprehensive Operational Guide', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font('Helvetica', '', 8.5)
    pdf.set_text_color(203, 213, 225)
    pdf.set_x(14)
    pdf.cell(0, 5, 'Production Platform: https://skinsurance.tech  |  Release Version: 2.2 (August 2026)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_y(54)
    
    # Metadata Block
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(14, 52, 182, 26, 'DF')
    pdf.set_xy(18, 54)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(38, 5, 'Client Surveyor:', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(140, 5, 'Sk Anowar Ali (Motor Surveyor & Loss Assessor)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_x(18)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(38, 5, 'Licence & Contact:', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(140, 5, 'SLA-121784 | Phone: 8777370714 | Email: skanowarali93@gmail.com', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_x(18)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(38, 5, 'Scope & Modules:', new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(140, 5, 'Dashboard Drilldown, Claim Register, Master Insurers, Fee Calculator & Reminders', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.ln(7)
    
    # Section 1: Overview
    pdf.chapter_title(1, 'Executive Platform Overview & Capabilities')
    pdf.paragraph(
        "The Motor Survey Management System (skinsurance.tech) is a specialized web application engineered for "
        "independent motor insurance surveyors and team operations. It streamlines the full survey workflow from "
        "email appointment parsing to AI-assisted report compilation, vehicle damage photo organization, missing document "
        "tracking, and automated GST-compliant survey fee billing."
    )
    
    pdf.callout_box(
        "Core Capabilities Summary",
        "1. In-Place Dashboard Drilldown: Instant claim filtering below KPI metric cards without losing workspace context.\n"
        "2. Missing Documents Checklist Modal: Granular tracking with multi-cycle automated client reminders.\n"
        "3. Insurer Master Directory: Stored GSTINs, branch addresses, default rates, and smart invoice auto-prefixes.\n"
        "4. Professional Fee Billing Engine: Whole rupee precision, flat/distance conveyance, photocopy & live 18% GST.\n"
        "5. Dual-Role Security Model: Complete financial data redaction for employee accounts.\n"
        "6. Automated Push-to-Deploy CI/CD: Instant zero-downtime updates with automatic asset cache-busting."
    )
    
    pdf.ln(2)
    
    # Section 2: Team Roles
    pdf.chapter_title(2, 'Team Roles & Security Partitioning')
    pdf.paragraph(
        "The application provides workspace multi-tenancy to ensure operational staff and surveyors can work together "
        "without compromising sensitive fee earnings or commercial accounting records."
    )
    
    pdf.sub_heading('A. Role Permission Matrix')
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_fill_color(226, 232, 240)
    pdf.cell(45, 6, 'Capability / Feature', 1, 0, 'L', True)
    pdf.cell(70, 6, 'Administrator (NAMAN)', 1, 0, 'L', True)
    pdf.cell(65, 6, 'Employee (USER)', 1, 1, 'L', True)
    
    pdf.set_font('Helvetica', '', 8)
    roles_table = [
        ("Dashboard Claims", "Full View & In-Place Drilldown", "Full View & In-Place Drilldown"),
        ("Financial Revenue KPIs", "Visible (Total Invoiced, Cash Received)", "Completely Hidden & Redacted"),
        ("Claim Register & Reports", "Create, Edit, Finalize, PDF Download", "Create, Edit, Draft, PDF Download"),
        ("Survey Fee Register", "Full Access (Create, Edit, Delete, Bill)", "Hidden (Tab removed, 403 Forbidden)"),
        ("Insurer Master Setup", "Add, Edit, Configure Default Rates", "No Access"),
        ("GSTR-1 / CA Exports", "Full Excel & B2B CSV Export", "No Access"),
    ]
    for row in roles_table:
        pdf.cell(45, 5.2, row[0], 1, 0, 'L')
        pdf.cell(70, 5.2, row[1], 1, 0, 'L')
        pdf.cell(65, 5.2, row[2], 1, 1, 'L')
        
    # ==================== PAGE 2: DASHBOARD & CLAIM REGISTER ====================
    pdf.add_page()
    
    pdf.chapter_title(3, 'Operational Dashboard & In-Place Drilldown (R1)')
    pdf.paragraph(
        "The Operational Dashboard presents high-level volume metrics for survey jobs. Clicking any metric card triggers "
        "an in-place drilldown table rendered directly below the metric grid in #dashboard-drilldown-section."
    )
    
    pdf.sub_heading('A. Interactive KPI Metric Cards')
    pdf.paragraph(
        "- Total Claims: Shows all lifetime or period-scoped claims.\n"
        "- Pending Claims: Filters claims with active statuses (Inspection Pending, Documents Awaited, Under Preparation).\n"
        "- Documents Awaited: Immediate access to claims stalled due to missing policyholder paperwork.\n"
        "- Active Highlight: When a card is clicked, it receives an active blue highlight border (.active-metric-card)."
    )
    
    pdf.sub_heading('B. In-Place Table Operations')
    pdf.paragraph(
        "The drilldown table features an integrated search input allowing instant filtering across Claim Number, Vehicle "
        "Registration, Insured Name, and Insurer Name. Users can close the drilldown at any time via the 'Close' button."
    )
    
    pdf.ln(2)
    pdf.chapter_title(4, 'Claim Register & Missing Documents Checklist (R2)')
    pdf.paragraph(
        "The Claim Register provides a shared operational log for all motor survey appointments. Clicking the 'Docs' "
        "action button on any row opens the Missing Documents Checklist & Reminders modal."
    )
    
    pdf.sub_heading('A. Standard & Custom Document Checklist Items')
    pdf.paragraph(
        "The modal enables field surveyors and office staff to track standard documents: RC Copy, Driving Licence, "
        "Insurance Policy Copy, Duly Filled Claim Form, Police FIR/GD Entry, Repair Estimate, and Satisfaction Voucher. "
        "Additional custom documents can be added on a per-claim basis with one click."
    )
    
    pdf.sub_heading('B. Automated 7-Day / 3-Cycle Client Reminders')
    pdf.paragraph(
        "When documents remain pending, the system tracks reminder notice cycles:\n"
        "1. 1st Reminder Notice: Friendly reminder sent after 7 days.\n"
        "2. 2nd Reminder Notice: Formal reminder after 14 days.\n"
        "3. Final Reminder Notice: Final intimation before reporting to the insurer.\n"
        "Staff can generate ready-to-send WhatsApp messages and email drafts directly from the modal."
    )
    
    # ==================== PAGE 3: INSURER MASTERS & SMART INVOICING ====================
    pdf.add_page()
    
    pdf.chapter_title(5, 'Master Insurer Setup & Smart Invoice Auto-Prefixing (R3 & R4)')
    pdf.paragraph(
        "To eliminate repetitive manual data entry, the system features a dedicated Master Insurer Directory and an "
        "intelligent invoice prefix auto-derivation engine."
    )
    
    pdf.sub_heading('A. Master Insurer Directory Setup (R3)')
    pdf.paragraph(
        "Accessed via '+ Manage Insurer Masters' in the Survey Fee Register. Allows storing:\n"
        "- Insurer Name: Full company name (e.g., National Insurance Co. Ltd., Oriental General Insurance).\n"
        "- Branch / Divisional Office Address: Specific office billing address.\n"
        "- GSTIN: 15-digit GST Identification Number.\n"
        "- Default Rate/Km: Standard conveyance reimbursement rate (e.g., Rs. 10/Km).\n"
        "- Custom Invoice Prefix: Pre-assigned invoice abbreviation (e.g., NIC, OGI, UIIC, NIA)."
    )
    
    pdf.sub_heading('B. Smart Auto-Prefix & Sequential Numbering (R4)')
    pdf.paragraph(
        "When creating or editing a fee bill, typing or selecting the Insurer automatically derives the standard acronym "
        "prefix and requests the next sequential invoice number from the database. For example:\n"
        "- 'National Insurance Company' -> Auto-fills Prefix: 'NIC-0001'\n"
        "- 'Oriental General Insurance' -> Auto-fills Prefix: 'OGI-0001'\n"
        "- 'United India Insurance Company' -> Auto-fills Prefix: 'UIIC-0001'"
    )
    
    pdf.ln(2)
    pdf.chapter_title(6, 'Professional Fee Billing Engine & Live GST Calculations (R5)')
    pdf.paragraph(
        "The Survey Fee Register accurately computes surveyor fee entitlements with integer rupee precision and real-time "
        "breakdown summaries."
    )
    
    pdf.sub_heading('A. Fee Component Breakdown')
    pdf.paragraph(
        "1. Professional Survey Fee: Whole rupee input (step=1) for survey, spot, or re-inspection fees.\n"
        "2. Conveyance Charges (Combined Mode):\n"
        "   - Flat Rate: Direct whole rupee entry.\n"
        "   - Km Formula: One-way Distance (Km) x 2 (Round Trip) x Number of Visits x Rate/Km.\n"
        "3. Photocopy & Miscellaneous Charges: Out-of-pocket documentation and courier expenses.\n"
        "4. Live 18% GST Calculation: Automatically computes 18% GST on the taxable subtotal."
    )
    
    pdf.callout_box(
        "Live Calculation Mathematical Formula",
        "Taxable Amount = Professional Fee + Total Conveyance + Photocopy Charges\n"
        "GST Amount (18%) = Taxable Amount x 18 / 100\n"
        "Gross Bill Total = Taxable Amount + GST Amount (18%)\n\n"
        "Example: Professional (Rs. 1,500) + Conveyance (Rs. 500) + Photo (Rs. 200) = Taxable Rs. 2,200\n"
        "GST (18%) = Rs. 396  -->  Gross Total = Rs. 2,596 (Dynamically displayed in live breakdown card)"
    )
    
    # ==================== PAGE 4: PHOTO UPLOAD, CI/CD & SUPPORT ====================
    pdf.add_page()
    
    pdf.chapter_title(7, 'Vehicle Damage Photo Management & Upload Throttling (R6)')
    pdf.paragraph(
        "The photo management module allows high-resolution vehicle damage photos to be organized, captioned, and embedded "
        "into survey reports with optimized upload throughput."
    )
    
    pdf.sub_heading('A. Adaptive Throttling & Diagnostic System')
    pdf.paragraph(
        "- Batch Upload Support: Drag-and-drop multiple HD vehicle photos simultaneously.\n"
        "- Rate Limit Protection: Client-side adaptive throttling prevents false Google Drive quota alerts and 429 throttling.\n"
        "- Server-Side Storage: Photos are securely stored in private application asset storage and backed up."
    )
    
    pdf.ln(2)
    pdf.chapter_title(8, 'Automated CI/CD, Daily Backups & Operational Reference')
    
    pdf.sub_heading('A. Zero-Friction Push-to-Deploy')
    pdf.paragraph(
        "All software enhancements pushed to GitHub automatically deploy live to https://skinsurance.tech in under 4 seconds "
        "via a secure HTTPS webhook. Asset cache-busting ensures immediate browser updates without hard-refreshing."
    )
    
    pdf.sub_heading('B. Automated Disaster Recovery & Backups')
    pdf.paragraph(
        "A daily cron job creates compressed PostgreSQL database backups in /root/backups/ and automatically purges archives "
        "older than 14 days to preserve VPS disk space."
    )
    
    pdf.sub_heading('C. Key Access Credentials')
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_fill_color(226, 232, 240)
    pdf.cell(50, 6, 'Account Role', 1, 0, 'L', True)
    pdf.cell(50, 6, 'Username', 1, 0, 'L', True)
    pdf.cell(40, 6, 'Default Password', 1, 0, 'L', True)
    pdf.cell(40, 6, 'Primary Purpose', 1, 1, 'L', True)
    
    pdf.set_font('Helvetica', '', 8)
    pdf.cell(50, 5.5, 'Administrator', 1, 0, 'L')
    pdf.cell(50, 5.5, 'NAMAN', 1, 0, 'L')
    pdf.cell(40, 5.5, '69420', 1, 0, 'L')
    pdf.cell(40, 5.5, 'Full Workspace & Finance', 1, 1, 'L')
    
    pdf.cell(50, 5.5, 'Employee / Field Staff', 1, 0, 'L')
    pdf.cell(50, 5.5, 'USER', 1, 0, 'L')
    pdf.cell(40, 5.5, 'UH65A#DF', 1, 0, 'L')
    pdf.cell(40, 5.5, 'Claims & Reports Only', 1, 1, 'L')
    
    pdf.ln(6)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 5, 'Client Support & Helpdesk:', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 8.5)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(0, 4.5, 'Platform URL: https://skinsurance.tech  |  Client Surveyor: Sk Anowar Ali (Phone: 8777370714)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'downloads', 'Motor_Survey_Software_User_Guide.pdf')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf.output(output_path)
    print(f"[PDF BUILD SUCCESS]: {output_path} ({os.path.getsize(output_path)} bytes)")

if __name__ == '__main__':
    build_pdf()
