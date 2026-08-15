"""
Script to generate a comprehensive PDF user guide & feature manual for SK Anowar Ali Client.
"""
import os
import sys
from fpdf import FPDF

class PDFUserGuide(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_fill_color(30, 41, 59) # Slate Dark Blue
            self.rect(0, 0, 210, 15, 'F')
            self.set_font('Helvetica', 'B', 8.5)
            self.set_text_color(255, 255, 255)
            self.set_xy(10, 3.5)
            self.cell(140, 8, 'MOTOR SURVEY MANAGEMENT SYSTEM - CLIENT USER MANUAL & FEATURE GUIDE')
            self.set_xy(150, 3.5)
            self.cell(50, 8, 'skinsurance.tech', align='R')
            self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 10, f'Page {self.page_no()} of {{nb}}  |  Sk Anowar Ali (Licence No.: SLA-121784, Mobile: 8777370714)', align='C')

    def chapter_title(self, num, title):
        self.set_font('Helvetica', 'B', 13)
        self.set_fill_color(241, 245, 249) # Light Slate Fill
        self.set_text_color(15, 23, 42) # Slate Dark
        self.cell(0, 9, f'  {num}. {title}', fill=True, new_x='LMARGIN', new_y='NEXT')
        self.ln(2)

    def sub_heading(self, text):
        self.set_font('Helvetica', 'B', 10.5)
        self.set_text_color(30, 58, 138) # Navy Blue
        self.cell(0, 6, text, new_x='LMARGIN', new_y='NEXT')
        self.ln(1)

    def paragraph(self, text):
        self.set_font('Helvetica', '', 9.5)
        self.set_text_color(51, 65, 85) # Slate Gray
        self.multi_cell(0, 4.8, text)
        self.ln(2)

    def callout_box(self, title, text, bg_color=(238, 242, 255), text_color=(30, 58, 138)):
        self.set_fill_color(*bg_color)
        self.set_draw_color(199, 210, 254)
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(*text_color)
        
        # Calculate height
        self.set_font('Helvetica', '', 9)
        lines = self.multi_cell(180, 4.5, f"{title}\n{text}", split_only=True)
        box_height = max(18, len(lines) * 4.8 + 8)
        
        self.rect(12, self.get_y(), 186, box_height, 'DF')
        curr_y = self.get_y()
        self.set_xy(15, curr_y + 3)
        self.set_font('Helvetica', 'B', 9.5)
        self.cell(0, 5, title, new_x='LMARGIN', new_y='NEXT')
        self.set_x(15)
        self.set_font('Helvetica', '', 9)
        self.multi_cell(180, 4.5, text)
        self.set_y(curr_y + box_height + 4)

def build_pdf():
    pdf = PDFUserGuide()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    
    # ------------------ COVER / PAGE 1 ------------------
    pdf.add_page()
    
    # Cover Header Banner
    pdf.set_fill_color(15, 23, 42) # Deep Slate
    pdf.rect(0, 0, 210, 52, 'F')
    
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(14, 10)
    pdf.cell(0, 9, 'MOTOR SURVEY MANAGEMENT SYSTEM', new_x='LMARGIN', new_y='NEXT')
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(56, 189, 248) # Sky Blue Accent
    pdf.set_x(14)
    pdf.cell(0, 7, 'Complete Client User Manual & Feature Operational Guide', new_x='LMARGIN', new_y='NEXT')
    
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(203, 213, 225)
    pdf.set_x(14)
    pdf.cell(0, 6, 'Live Platform: https://skinsurance.tech  |  Release Version: 2.0 (August 2026)', new_x='LMARGIN', new_y='NEXT')
    
    pdf.set_y(60)
    
    # Metadata Info Block
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(14, 58, 182, 28, 'DF')
    pdf.set_xy(18, 61)
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(42, 5.5, 'Client Name:')
    pdf.set_font('Helvetica', '', 9.5)
    pdf.cell(135, 5.5, 'Sk Anowar Ali (Motor Surveyor & Loss Assessor)', new_x='LMARGIN', new_y='NEXT')
    
    pdf.set_x(18)
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.cell(42, 5.5, 'SLA Licence No:')
    pdf.set_font('Helvetica', '', 9.5)
    pdf.cell(135, 5.5, 'SLA-121784 | Contact: 8777370714 | Email: skanowarali93@gmail.com', new_x='LMARGIN', new_y='NEXT')
    
    pdf.set_x(18)
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.cell(42, 5.5, 'Document Scope:')
    pdf.set_font('Helvetica', '', 9.5)
    pdf.cell(135, 5.5, 'Shared Workspaces, Gmail Intimation Review, Fee Breakdown, Reminders & GST', new_x='LMARGIN', new_y='NEXT')
    
    pdf.ln(8)
    
    # Executive Summary
    pdf.chapter_title(1, 'Executive Overview & Platform Capabilities')
    pdf.paragraph(
        "The Motor Survey Management System at skinsurance.tech is a high-performance web platform designed "
        "specifically for professional motor surveyors and loss assessors. It automates the end-to-end lifecycle "
        "of motor insurance claim management - from email intimation parsing and shared team workspaces to AI-powered "
        "survey report generation, fee calculations, missing document checklists, and automated SLA reminders."
    )
    
    pdf.callout_box(
        "Key Platform Highlights",
        "- Shared Operational Workspaces: Multi-user admin & employee role permissions.\n"
        "- Gmail Appointment Sync & Review: Extract appointments with pre-save Add/Cancel options.\n"
        "- Comprehensive Fee Register: Convenience route, total KM, per KM rate, & photocopy breakdown.\n"
        "- Dynamic Pending Documents Checklist: Case-by-case custom items & status tracking.\n"
        "- Automated 7-Day 3-Cycle Reminders: Automatic notices via Email, WhatsApp link, & Claim Manager alert.\n"
        "- 10-Column GST Excel Export: Full financial compliance workbook generation."
    )
    
    pdf.ln(3)
    
    # Chapter 2: Workspaces
    pdf.chapter_title(2, 'Motor Survey Workspaces & Team Role Security')
    pdf.paragraph(
        "The application provides a unified operational workspace allowing survey office staff and field surveyors "
        "to collaborate seamlessly while maintaining strict financial privacy and data security."
    )
    
    pdf.sub_heading('A. Admin vs Employee Role Access Levels')
    
    # Access Table
    pdf.set_font('Helvetica', 'B', 8.5)
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(48, 6.5, ' Feature Module', 1, fill=True)
    pdf.cell(66, 6.5, ' Admin Role (Surveyor)', 1, fill=True)
    pdf.cell(66, 6.5, ' Employee Role (Office Assistant)', 1, new_x='LMARGIN', new_y='NEXT', fill=True)
    
    table_data = [
        ('Claim Register', 'Full Access (Create/Edit/Status)', 'Full Operational Access (Create/Status)'),
        ('Fee Register & Billing', 'Full Access (Create/Edit/Excel Export)', 'HIDDEN (Redacted for Security)'),
        ('Financial Dashboard', 'Full Visibility (Gross & Outstanding)', 'HIDDEN'),
        ('Gmail Appointment Sync', 'Full Domain Control & Sync', 'Allowed if granted by Admin'),
        ('Employee Management', 'Create, Lock/Unlock, Reset Password', 'No Access'),
    ]
    
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(51, 65, 85)
    for idx, (mod, adm, emp) in enumerate(table_data):
        bg = (248, 250, 252) if idx % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.cell(48, 5.5, f' {mod}', 1, fill=True)
        pdf.cell(66, 5.5, f' {adm}', 1, fill=True)
        pdf.cell(66, 5.5, f' {emp}', 1, new_x='LMARGIN', new_y='NEXT', fill=True)
        
    pdf.ln(4)
    pdf.paragraph(
        "How to view and use Employee Management: As Admin, open the Settings modal. Under 'Employee Accounts', "
        "you can add office assistants, toggle their Gmail Sync permission checkbox, lock/unlock accounts instantly, "
        "or issue temporary password resets."
    )
    
    # ------------------ PAGE 2 ------------------
    pdf.add_page()
    
    # Chapter 3: Gmail Intimation Review
    pdf.chapter_title(3, 'Interactive Gmail Appointment Import Review Cards')
    pdf.paragraph(
        "As specifically requested, the system does NOT force auto-import of emails directly into your claim register "
        "without your prior review. When syncing Gmail, appointment emails are parsed and presented as interactive "
        "Review Cards, allowing you to explicitly inspect details before choosing to Add or Cancel each appointment."
    )
    
    pdf.callout_box(
        "How to Use Gmail Appointment Import Review",
        "Step 1: Click 'Connect & Sync Gmail' on the Gmail Appointment Import banner at the top of your workspace.\n"
        "Step 2: The system scans unread emails from your approved insurer domains (e.g. sbigeneral.in, nic.co.in).\n"
        "Step 3: Review the extracted appointment cards displaying:\n"
        "        - Email Subject & Sender Email\n"
        "        - Extracted Metadata Grid: Claim No., Policy No., Insurer, Insured, Contact, Vehicle No.\n"
        "        - Email Text Body Preview\n"
        "Step 4: Click '+ Add to Claim Register' to create/merge the claim draft into your active register.\n"
        "Step 5: Click 'Cancel' to dismiss unwanted or non-appointment emails so they are removed from your import list."
    )
    
    pdf.ln(3)
    
    # Chapter 4: Fee Register
    pdf.chapter_title(4, 'Survey Fee Register with Convenience & Photocopy Breakdown')
    pdf.paragraph(
        "The Fee Register has been updated to accommodate all surveyor billing requirements, specifically including "
        "convenience mileage calculation (Route, Total KM, Rate per KM) and dedicated photocopy amount entry."
    )
    
    pdf.sub_heading('A. Fee Calculation Formula & Taxable Amount Structure')
    pdf.paragraph(
        "1. Convenience Fee = Total KM x Rate per KM\n"
        "   Example: Krishnanagar to Kolkata (100 x 2 (up & down) = 200 KM @ Rs 10/- per KM) = Rs 2,000/-\n"
        "2. Taxable Amount = Professional Fee + Convenience Fee + Photocopy Amount\n"
        "3. GST Amount = Taxable Amount x GST % (Default: 18%)\n"
        "4. Gross Invoice Value = Taxable Amount + GST Amount"
    )
    
    # Sample Fee Table Illustration
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(30, 58, 138)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(35, 5.5, ' Particulars', 1, fill=True)
    pdf.cell(75, 5.5, ' Description / Inputs', 1, fill=True)
    pdf.cell(35, 5.5, ' Rate / %', 1, fill=True)
    pdf.cell(35, 5.5, ' Amount (Rs)', 1, new_x='LMARGIN', new_y='NEXT', align='R', fill=True)
    
    fee_sample = [
        ('Professional Fee', 'Survey & Inspection Charges', 'Flat Fee', '1,500.00'),
        ('Convenience Fee', 'Krishnanagar to Kolkata (200 KM)', 'Rs 10.00 / KM', '2,000.00'),
        ('Photocopy Charges', 'Documents Photocopy & Printing', 'Actuals', '150.00'),
        ('TAXABLE AMOUNT', 'Subtotal (Professional + Convenience + Photocopy)', '-', '3,650.00'),
        ('GST Amount', 'Integrated / Central + State GST', '18.00 %', '657.00'),
        ('GROSS VALUE', 'Total Invoice Gross Amount payable by Insurer', '-', '4,307.00'),
    ]
    
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(51, 65, 85)
    for item, desc, rate, amt in fee_sample:
        is_bold = 'AMOUNT' in item or 'GROSS' in item
        pdf.set_font('Helvetica', 'B' if is_bold else '', 8)
        pdf.set_fill_color(241, 245, 249) if is_bold else pdf.set_fill_color(255, 255, 255)
        pdf.cell(35, 5.5, f' {item}', 1, fill=True)
        pdf.cell(75, 5.5, f' {desc}', 1, fill=True)
        pdf.cell(35, 5.5, f' {rate}', 1, fill=True)
        pdf.cell(35, 5.5, f' {amt} ', 1, new_x='LMARGIN', new_y='NEXT', align='R', fill=True)

    pdf.ln(3)
    pdf.sub_heading('B. 10-Column Automated GST Excel Export')
    pdf.paragraph(
        "As Admin, click 'Download Fees Excel' at any time. The system generates an official Microsoft Excel workbook "
        "containing all 10 required financial columns: Invoice No, Invoice Date, Insurer Name, GSTIN, Insured Name, "
        "Claim No, Professional Fee, Conveyance, Taxable Amount, GST Amount, Gross Value, Received, and Outstanding."
    )
    
    # ------------------ PAGE 3 ------------------
    pdf.add_page()
    
    # Chapter 5: Missing Docs
    pdf.chapter_title(5, 'Dynamic Missing Documents Checklist Modal')
    pdf.paragraph(
        "Because document requirements vary depending on case-by-case claim scenarios, every claim in your register now "
        "features a dedicated 'Docs' action button that opens an interactive Missing Documents Checklist Modal."
    )
    
    pdf.callout_box(
        "How to Manage Pending Document Checklists",
        "Step 1: Open the Claim Register and locate the target claim.\n"
        "Step 2: Click the 'Docs' button next to the claim row.\n"
        "Step 3: Toggle checkboxes for default documents received (Claim Form, RC Copy, DL, Road Tax, Repair Estimate).\n"
        "Step 4: For case-specific requirements, type the custom document name (e.g. 'Fitness Certificate', 'Permit A') "
        "into the input box and click '+ Add Item'.\n"
        "Step 5: Click 'Save Checklist' to persist state."
    )
    
    pdf.ln(3)
    
    # Chapter 6: Reminders
    pdf.chapter_title(6, 'Automated 7-Day Recurring Pending Document Reminders')
    pdf.paragraph(
        "To enforce SLA compliance and prompt policyholders/insurers for missing paperwork, the system includes an "
        "automated notification schedule. Reminders are dispatched every 7 days up to a maximum of 3 total cycles, "
        "after which the process automatically stops."
    )
    
    pdf.sub_heading('A. Reminder Cycle Escalation Wording')
    
    rem_types = [
        ('1st Notice / Reminder (Day 7)', 'Standard formal request listing missing documents and requesting early submission to prevent survey report delays.'),
        ('2nd Reminder (Day 14)', 'High-priority alert: "...this is the second time reminder, so please treat this with high priority; otherwise we assume you are not interested in taking the claim, and the insurance company may close the claim..."'),
        ('3rd & Final Notice (Day 21)', 'Final warning notice: "...this is the third time reminder... insurance company may close the claim without further notice." (Automated reminders stop after Cycle 3).'),
    ]
    for r_title, r_desc in rem_types:
        pdf.set_font('Helvetica', 'B', 8.5)
        pdf.set_text_color(30, 58, 138)
        pdf.cell(0, 4.5, f'- {r_title}', new_x='LMARGIN', new_y='NEXT')
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 4, f'   {r_desc}')
        pdf.ln(1)

    pdf.ln(2)
    pdf.sub_heading('B. Notification Channels & Claim Manager Option')
    pdf.paragraph(
        "- Email Dispatch: Automatically emails the insured and/or the Claim Manager.\n"
        "- Claim Manager Fields: Option to enter Claim Manager Email and Phone number per reminder.\n"
        "- WhatsApp Integration: Click 'Send via WhatsApp' to open pre-formatted text directly in WhatsApp Web/App.\n"
        "- Copy Wording: Click 'Copy Text' to copy formatted reminder text to clipboard for SMS or letter printing."
    )
    
    pdf.ln(3)
    
    # ------------------ PAGE 4 ------------------
    pdf.add_page()
    
    # Chapter 7: Ambiguity & Questions
    pdf.chapter_title(7, 'Client Review: Ambiguity Clarifications & Open Questions')
    pdf.paragraph(
        "To ensure all present and future workflow requirements perfectly align with your operational needs, "
        "please review the following clarifying questions and share your feedback:"
    )
    
    questions = [
        ("Q1. WhatsApp / SMS Direct Gateway Integration",
         "Currently, the system provides pre-formatted WhatsApp click-to-chat links and copyable text. Would you like "
         "direct API integration (e.g. Fast2SMS or WhatsApp Business API) for 100% automated SMS dispatch without opening WhatsApp?"),
        
        ("Q2. Manual Reminder Frequency Override",
         "The standard reminder schedule runs every 7 days up to 3 times. Would you like an option to override this interval "
         "for specific urgent claims (e.g. 3-day or 5-day custom reminder cycles)?"),
        
        ("Q3. Standalone Fee Bill PDF Generation",
         "Fee breakdown is currently integrated into the Final Survey Report PDF. Would you also like a dedicated standalone "
         "Tax Invoice PDF generator specifically for issuing separate fee bills to insurance companies?"),
        
        ("Q4. Insurer-Specific Format Preferences",
         "Are there any specific report layout formats or customized photo sheet grids required by specific insurance companies "
         "(e.g. National Insurance vs SBI General vs Digit Insurance)?"),
    ]
    
    for q_title, q_body in questions:
        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(203, 213, 225)
        pdf.rect(14, pdf.get_y(), 182, 22, 'DF')
        curr_y = pdf.get_y()
        
        pdf.set_xy(17, curr_y + 2)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 4.5, q_title, new_x='LMARGIN', new_y='NEXT')
        
        pdf.set_x(17)
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(71, 85, 105)
        pdf.multi_cell(176, 3.8, q_body)
        
        pdf.set_y(curr_y + 25)

    pdf.ln(3)
    
    # Chapter 8: Conclusion & Sign-off
    pdf.chapter_title(8, 'Summary of Completed Deliverables & Contact')
    pdf.paragraph(
        "All features requested in recent discussions and WhatsApp communications have been fully implemented, "
        "tested with 149 automated verification checks, and deployed to your live server at skinsurance.tech."
    )
    
    pdf.callout_box(
        "Surveyor Sign-off & Support Details",
        "Sk Anowar Ali - Motor Surveyor & Loss Assessor\n"
        "Licence No.: SLA-121784  |  Membership No.: L/E/10721  |  Expiry Date: 13-12-2026\n"
        "Address: Natungram, P.O- Sondanga, P.S Nabadwip, City - Krishnanagar, Dist-Nadia, W.B.-741125\n"
        "Mobile: 8777370714  |  Email: skanowarali93@gmail.com\n"
        "Live Website: https://skinsurance.tech",
        bg_color=(240, 253, 244),
        text_color=(22, 101, 52)
    )
    
    output_path = os.path.abspath(os.path.join('downloads', 'Motor_Survey_Software_User_Guide.pdf'))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf.output(output_path)
    print(f"PDF generated successfully at: {output_path}")

if __name__ == '__main__':
    build_pdf()
