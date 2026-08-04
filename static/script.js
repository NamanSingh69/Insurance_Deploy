document.addEventListener('DOMContentLoaded', () => {
    // Attach the server-issued CSRF token to every same-origin state-changing
    // request, including JSON and multipart FormData submissions.
    const nativeFetch = window.fetch.bind(window);
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    window.fetch = (input, init = {}) => {
        const requestUrl = typeof input === 'string' ? input : input.url;
        const requestMethod = (init.method || (typeof input === 'string' ? 'GET' : input.method) || 'GET').toUpperCase();
        const target = new URL(requestUrl, window.location.origin);
        if (csrfToken && target.origin === window.location.origin && !['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(requestMethod)) {
            const headers = new Headers(init.headers || (typeof input === 'string' ? undefined : input.headers));
            headers.set('X-CSRFToken', csrfToken);
            init = { ...init, headers };
        }
        return nativeFetch(input, init);
    };

    // DOM elements
    const uploadSection = document.getElementById('upload-section');
    const previewSection = document.getElementById('preview-section');
    const downloadSection = document.getElementById('download-section');
    const statusContainer = document.getElementById('status-container'); // Container for all messages
    const statusDiv = document.getElementById('status');
    const statusMessage = document.getElementById('status-message');
    const pdfFileInput = document.getElementById('pdf-file');
    const pdfDropzone = document.getElementById('pdf-dropzone');
    const browseButton = document.getElementById('browse-button');
    const selectedFileName = document.getElementById('selected-file-name');
    const processButton = document.getElementById('process-button');
    const previewForm = document.getElementById('preview-form');
    const generateButton = document.getElementById('generate-button');
    const saveProgressButton = document.getElementById('save-progress-button'); // Save button
    const downloadLinksDiv = document.getElementById('download-links');
    const backToUploadButton = document.getElementById('back-to-upload');
    const startNewButton = document.getElementById('start-new');
    const uploadProgressContainer = document.getElementById('upload-progress-container');
    const uploadProgress = document.getElementById('upload-progress');
    const labourDetailsTbody = document.getElementById('labour-details-tbody');
    const addLabourRowButton = document.getElementById('add-labour-row');
    const partsDetailsTbody = document.getElementById('parts-details-tbody');
    const addPartRowButton = document.getElementById('add-part-row'); // Add Part button
    const partsTotalBaseFooter = document.getElementById('parts-total-base-footer');
    const partsTotalGstFooter = document.getElementById('parts-total-gst-footer');
    const partsGrandTotalFooter = document.getElementById('parts-grand-total-footer');
    const partsDeprSumFooter = document.getElementById('parts-depr-sum-footer');
    const partsNetTotalFooter = document.getElementById('parts-net-total-footer');
    const summaryAddLabour = document.getElementById('summary-add-labour');
    const summaryAddParts = document.getElementById('summary-add-parts');
    const summaryLessExcess = document.getElementById('summary-less-excess');
    const summaryNetLiability = document.getElementById('summary-net-liability');
    const assessmentSalvageInput = document.getElementById('assessment-salvage');
    const assessmentDeductiblesInput = document.getElementById('assessment-deductibles');
    const assessmentHeaderGstInput = document.getElementById('assessment-header-gst');
    const assessmentHeaderVehicleYearInput = document.getElementById('assessment-header-vehicle-year');
    const assessmentReportTypeDropdown = document.getElementById('assessment-report-type');
    const assessmentClaimTypeDropdown = document.getElementById('assessment-claim-type');
    const displayVehicleAge = document.getElementById('display-vehicle-age'); // New display field
    const assessmentLabourPaintDepnInput = document.getElementById('assessment-labour_paint_depn');
    const savedReportsTbody = document.getElementById('saved-reports-tbody'); // Saved reports table body
    const loadingSpinner = document.getElementById('loading-spinner'); // Loading spinner
    const selectedInvoiceFileName = document.getElementById('selected-invoice-file-name');
    const uploadInvoiceButton = document.getElementById('upload-invoice-button');
    const invoiceStatusDiv = document.getElementById('invoice-status'); // Specific status for invoice upload
    const invoiceUploadSection = document.getElementById('invoice-upload-section'); // Optional: for showing/hiding
    const invoiceFileInput = document.getElementById('invoice-file-input');
    const invoiceDropzone = document.getElementById('invoice-dropzone'); // *** ADDED ***
    const browseInvoiceButton = document.getElementById('browse-invoice-button');
    const assessmentPolicyTypeDropdown = document.getElementById('assessment-policy-type');
    const assessmentLabourTaxTypeDropdown = document.getElementById('assessment-labour-tax-type');
    const labourCgstRow = document.getElementById('labour-cgst-row');
    const labourSgstRow = document.getElementById('labour-sgst-row');
    const labourIgstRow = document.getElementById('labour-igst-row');
    const labourIgstDisplayField = document.getElementById('assessment-labour_igst');
    const page3CustomerGstinInput = document.getElementById('page3-customer-gstin');
    const page3EstimatedAmountInput = document.getElementById('page3-estimated-amount');
    const page3PhotoCopiesCountInput = document.getElementById('page3-photo-copies-count');
    const page3PhotoChargesDisplay = document.getElementById('page3-photo-charges-display');
    const page3FeeItemsTbody = document.getElementById('page3-fee-items-tbody');
    const addPage3FeeItemRowButton = document.getElementById('add-page3-fee-item-row');
    const page3SubtotalDisplay = document.getElementById('page3-subtotal-display');
    const page3CgstDisplay = document.getElementById('page3-cgst-display');
    const page3SgstDisplay = document.getElementById('page3-sgst-display');
    const page3IgstDisplay = document.getElementById('page3-igst-display');
    const page3CgstRowDisplay = document.getElementById('page3-cgst-row-display'); // Container div
    const page3SgstRowDisplay = document.getElementById('page3-sgst-row-display'); // Container div
    const page3IgstRowDisplay = document.getElementById('page3-igst-row-display');   // Container div
    const page3GrandTotalDisplay = document.getElementById('page3-grand-total-display');
    const page3GrandTotalWordsDisplay = document.getElementById('page3-grand-total-words-display');
    const consolidatedCsvDateFromInput = document.getElementById('consolidated-csv-date-from');
    const consolidatedCsvDateToInput = document.getElementById('consolidated-csv-date-to');
    const downloadConsolidatedCsvButton = document.getElementById('download-consolidated-csv-button');

    // Store assessment data globally
    let currentAssessmentData = null;
    let currentReportId = null; // To track if we loaded a report (display row ID)
    let currentDbReportId = null; // The Postgres UUID of the currently-loaded report (for safe updates)
    let currentClaimMeta = { status: 'new_appointment', survey_type: 'final' };

    // Step indicators
    const stepUpload = document.getElementById('step-upload');
    const stepReview = document.getElementById('step-review');
    const stepDownload = document.getElementById('step-download');


    // --- Helper Functions ---
    function showStatus(message, type = 'processing', isFlash = false) {
        // Clear existing dynamic status
        statusDiv.classList.add('hidden');
        statusMessage.textContent = '';

        if (isFlash) {
            // Create a new flash message element
            const flashDiv = document.createElement('div');
            flashDiv.className = `status status-${type}`; // Use status class for styling
            const icon = document.createElement('i');
            icon.className = `fas ${type === 'error' ? 'fa-exclamation-triangle' : type === 'success' ? 'fa-check-circle' : 'fa-info-circle'} status-icon`;
            const text = document.createElement('span');
            text.textContent = message;
            flashDiv.append(icon, text);
            statusContainer.insertBefore(flashDiv, statusContainer.firstChild); // Add to top
            // Auto-remove after 5 seconds
            setTimeout(() => {
                flashDiv.style.opacity = '0';
                setTimeout(() => flashDiv.remove(), 500); // Remove after fade out
            }, 5000);
        } else {
            // Use the dedicated status div
            statusMessage.textContent = message;
            statusDiv.className = `status status-${type}`;
            const iconElement = statusDiv.querySelector('.status-icon');
            if (iconElement) {
                iconElement.className = `fas ${type === 'error' ? 'fa-exclamation-circle' : type === 'success' ? 'fa-check-circle' : 'fa-info-circle'} status-icon`;
            }
            statusDiv.classList.remove('hidden');
            if (type === 'success') {
                setTimeout(hideStatus, 5000);
            }
        }
    }

    function showInvoiceStatus(message, type = 'processing') {
        invoiceStatusDiv.textContent = message;
        invoiceStatusDiv.className = `status status-${type}`; // Reuse status styles
        invoiceStatusDiv.classList.remove('hidden');
        // Auto-hide after 5 seconds if not processing
        if (type !== 'processing') {
            setTimeout(() => { invoiceStatusDiv.classList.add('hidden'); }, 5000);
        }
    }

    function hideStatus() {
        statusDiv.classList.add('hidden');
    }

    function updateSteps(activeStep) {
        [stepUpload, stepReview, stepDownload].forEach(step => step.classList.remove('active', 'completed'));
        switch (activeStep) {
            case 'upload': stepUpload.classList.add('active'); break;
            case 'review': stepUpload.classList.add('completed'); stepReview.classList.add('active'); break;
            case 'download': stepUpload.classList.add('completed'); stepReview.classList.add('completed'); stepDownload.classList.add('active'); break;
        }
    }

    function formatCurrency(value) {
        const number = parseFloat(value);
        if (isNaN(number)) return '0';
        if (number === 0) return '0';
        return number.toFixed(2);
    }
    function formatQty(value) {
        const number = parseFloat(value);
        return isNaN(number) ? '0' : parseFloat(number.toFixed(3)).toString();
    }
    function parseFormattedNumber(value) {
        if (typeof value !== 'string') return parseFloat(value) || 0.0;
        const cleanedValue = value.replace(/[^0-9.-]+/g, "");
        return parseFloat(cleanedValue) || 0.0;
    }
    function formatInputOnBlur(event, formatter = formatCurrency) { // Default to formatCurrency
        const input = event.target;
        // Use the provided formatter function (which now handles '0')
        const value = parseFormattedNumber(input.value);
        input.value = formatter(value);
    }

    // --- Dropzone & File Input ---
    browseButton.addEventListener('click', () => pdfFileInput.click());
    pdfFileInput.addEventListener('change', handleFileSelect);
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => pdfDropzone.addEventListener(eventName, preventDefaults, false));
    ['dragenter', 'dragover'].forEach(eventName => pdfDropzone.addEventListener(eventName, () => pdfDropzone.classList.add('active')));
    ['dragleave', 'drop'].forEach(eventName => pdfDropzone.addEventListener(eventName, () => pdfDropzone.classList.remove('active')));
    pdfDropzone.addEventListener('drop', handleFileDrop);

    // --- NEW: Invoice Dropzone Event Listeners ---
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        invoiceDropzone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false); // Prevent browser default behavior for whole page
    });
    ['dragenter', 'dragover'].forEach(eventName => {
        invoiceDropzone.addEventListener(eventName, () => invoiceDropzone.classList.add('active'), false);
    });
    ['dragleave', 'drop'].forEach(eventName => {
        invoiceDropzone.addEventListener(eventName, () => invoiceDropzone.classList.remove('active'), false);
    });
    invoiceDropzone.addEventListener('drop', handleInvoiceFileDrop, false); // *** ADDED Drop Handler ***

    function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }

    function handleFileSelect(e) {
        const file = e.target.files[0];
        updateFileUI(file);
    }

    function handleFileDrop(e) {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        if (file) {
            pdfFileInput.files = dt.files; // Assign dropped file to input
            updateFileUI(file);
        }
    }

    function updateFileUI(file) {
        if (file && file.type === 'application/pdf') {
            selectedFileName.textContent = file.name;
            pdfDropzone.classList.add('active'); // Keep active style
            processButton.disabled = false;
            hideStatus(); // Clear any previous errors
        } else {
            showStatus('Please select/drop a valid PDF file.', 'error');
            pdfFileInput.value = ''; // Clear input
            selectedFileName.textContent = '';
            pdfDropzone.classList.remove('active');
            processButton.disabled = true;
        }
    }

    browseInvoiceButton.addEventListener('click', () => invoiceFileInput.click());
    invoiceFileInput.addEventListener('change', handleInvoiceFileSelect);

    function handleInvoiceFileSelect(e) {
        const file = e.target.files[0];
        updateInvoiceFileUI(file);
    }

    function updateInvoiceFileUI(file) {
        // Use the specific status div for invoice errors
        const showInvoiceStatus = (message, type = 'error') => {
            invoiceStatusDiv.textContent = message;
            invoiceStatusDiv.className = `status status-${type}`;
            invoiceStatusDiv.classList.remove('hidden');
        };
        const hideInvoiceStatus = () => {
            invoiceStatusDiv.classList.add('hidden');
            invoiceStatusDiv.textContent = '';
        };

        if (file && file.type === 'application/pdf') {
            selectedInvoiceFileName.textContent = `Selected: ${file.name}`;
            uploadInvoiceButton.disabled = false;
            hideInvoiceStatus(); // Clear previous invoice errors
        } else {
            if (file) { // Only show error if a file was selected but wasn't PDF
                showInvoiceStatus('Please select a valid PDF file for the invoice.');
            } else {
                hideInvoiceStatus(); // Hide if no file selected
            }
            invoiceFileInput.value = ''; // Clear input
            selectedInvoiceFileName.textContent = '';
            uploadInvoiceButton.disabled = true;
        }
    }

    function handleInvoiceFileDrop(e) {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        if (file) {
            invoiceFileInput.files = dt.files;
            updateInvoiceFileUI(file);
        }
    }

    // --- Display Preview Data ---
    function displayPreview(combinedData, loadedReportId = null, loadedDbReportId = null) {
        previewForm.reset();
        labourDetailsTbody.innerHTML = '';
        partsDetailsTbody.innerHTML = '';
        if (page3FeeItemsTbody) page3FeeItemsTbody.innerHTML = '';
        currentReportId = loadedReportId;
        currentDbReportId = loadedDbReportId; // Store the Postgres UUID for safe updates
        currentClaimMeta = combinedData?.claim_meta || { status: 'new_appointment', survey_type: 'final' };

        // --- FIX: Reset Global Photo State ---
        uploadedPhotos.first_inspection = [];
        uploadedPhotos.dismantling = [];
        uploadedPhotos.reinspection = [];

        // --- FIX: Load Photos from Data ---
        const loadedPhotos = combinedData.photos || {};

        if (loadedPhotos.first_inspection) {
            uploadedPhotos.first_inspection = Array.isArray(loadedPhotos.first_inspection.images) ? [...loadedPhotos.first_inspection.images] : [];
            const layoutSelect = document.getElementById('photos-layout-first');
            if (layoutSelect) layoutSelect.value = loadedPhotos.first_inspection.per_page || '4';
        }

        if (loadedPhotos.dismantling) {
            uploadedPhotos.dismantling = Array.isArray(loadedPhotos.dismantling.images) ? [...loadedPhotos.dismantling.images] : [];
            const layoutSelect = document.getElementById('photos-layout-dismantling');
            if (layoutSelect) layoutSelect.value = loadedPhotos.dismantling.per_page || '4';
        }

        if (loadedPhotos.reinspection) {
            uploadedPhotos.reinspection = Array.isArray(loadedPhotos.reinspection.images) ? [...loadedPhotos.reinspection.images] : [];
            const layoutSelect = document.getElementById('photos-layout-reinspection');
            if (layoutSelect) layoutSelect.value = loadedPhotos.reinspection.per_page || '4';
        }

        // --- FIX: Render Photos UI ---
        renderPhotos('first_inspection');
        renderPhotos('dismantling');
        renderPhotos('reinspection');

        const surveyData = combinedData.survey_report || {};
        const assessmentData = combinedData.assessment || {};
        currentAssessmentData = JSON.parse(JSON.stringify(assessmentData));

        currentAssessmentData.parts = currentAssessmentData.parts || [];
        currentAssessmentData.user_labour_rows = currentAssessmentData.user_labour_rows || [];
        currentAssessmentData.user_labour_rows.forEach(row => {
            if (typeof row.labour_row_gst_pc === 'undefined') {
                row.labour_row_gst_pc = 18;
            }
        });

        currentAssessmentData.note_text = currentAssessmentData.note_text ?? "Note :- The subject policy covered with Depn. waiver";
        currentAssessmentData.payment_to_text = currentAssessmentData.payment_to_text ?? "REPAIRER";
        const loadedPaintDepn = currentAssessmentData.labour_paint_depn;
        currentAssessmentData.labour_paint_depn = loadedPaintDepn ?? null;
        currentAssessmentData.policy_type = currentAssessmentData.policy_type || 'NORMAL';
        currentAssessmentData.nd_deduction_pc = currentAssessmentData.nd_deduction_pc ?? 5;
        currentAssessmentData.nd_deduction_amount = currentAssessmentData.nd_deduction_amount ?? null;
        currentAssessmentData.towing_charges = currentAssessmentData.towing_charges ?? 0;
        currentAssessmentData.report_type = currentAssessmentData.report_type || 'Final Survey Report';
        currentAssessmentData.claim_type = currentAssessmentData.claim_type || 'Cashless';
        currentAssessmentData.labour_tax_type = currentAssessmentData.labour_tax_type || 'CGST/SGST';

        const imt23Checkbox = document.getElementById('assessment-labour-imt-23');
        if (imt23Checkbox) {
            imt23Checkbox.checked = currentAssessmentData.labour_imt_applied === true;
        }

        const loadedSalvage = currentAssessmentData.salvage;
        const salvageIsNumeric = !isNaN(parseFloat(loadedSalvage));
        currentAssessmentData.salvage = salvageIsNumeric ? parseFloat(loadedSalvage) : 0.0;

        currentAssessmentData.page3_details = currentAssessmentData.page3_details || {
            customer_gstin: '',
            company_gstin: '',
            fee_items: [],
            estimated_amount: '',
            photo_copies_count: '',
            include_in_consolidated: false,
            surveyor_details: {}
        };
        if (typeof currentAssessmentData.page3_details.include_in_consolidated === 'undefined') {
            currentAssessmentData.page3_details.include_in_consolidated = false;
        }

        const defaultFeeItems = [
            { name: "Final Survey Fees", amount: 0 },
            { name: "Conveyance for Final Survey", amount: 0 },
            { name: "Spot Survey", amount: 0 },
            { name: "Conveyance for Spot Survey", amount: 0 },
            { name: "Post Repair Inspection Fees", amount: 0 },
            { name: "Conveyance for Post Repair Inspection Fees", amount: 0 },
            { name: "Other Expenses", amount: 0 }
        ];

        if (!currentAssessmentData.page3_details.fee_items || currentAssessmentData.page3_details.fee_items.length === 0) {
            currentAssessmentData.page3_details.fee_items = JSON.parse(JSON.stringify(defaultFeeItems));
        }

        for (const key in surveyData) {
            if (surveyData.hasOwnProperty(key)) {
                const inputElement = document.getElementById(`input-${key}`);
                if (inputElement) {
                    inputElement.value = surveyData[key] || '';
                }
            }
        }

        // --- Auto-generate Report Number if it's empty or doesn't match new format ---
        const reportNoInput = document.getElementById('input-report_no');
        const insurerInput = document.getElementById('input-insurer');
        if (reportNoInput && insurerInput) {
            const currentReportNo = reportNoInput.value.trim();
            const currentYear = new Date().getFullYear().toString();
            // Check if it's empty or clearly an old format (doesn't have /YYYY/ in it)
            if (!currentReportNo || !currentReportNo.includes(`/${currentYear}/`)) {
                fetch('/api/generate_report_no', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ insurer: insurerInput.value })
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.report_no) {
                            reportNoInput.value = data.report_no;
                        }
                    })
                    .catch(err => console.error("Failed to auto-generate report number:", err));
            }
        }

        assessmentHeaderGstInput.value = currentAssessmentData.header_gst || '';
        assessmentHeaderVehicleYearInput.value = currentAssessmentData.header_vehicle_year || '';
        document.getElementById('input-note_text').value = currentAssessmentData.note_text || '';
        document.getElementById('input-payment_to_text').value = currentAssessmentData.payment_to_text || '';
        document.getElementById('input-reinspection_note').value = currentAssessmentData.reinspection_note || '';
        document.getElementById('input-enclosures_text').value = currentAssessmentData.enclosures_text || '';
        document.getElementById('input-parts_table_note').value = currentAssessmentData.parts_table_note || '';
        document.getElementById('input-spot_report_text').value = currentAssessmentData.spot_report_text || document.getElementById('input-spot_report_text').defaultValue;
        document.getElementById('input-spot_report_enclosures').value = currentAssessmentData.spot_report_enclosures || document.getElementById('input-spot_report_enclosures').defaultValue;

        assessmentPolicyTypeDropdown.value = currentAssessmentData.policy_type;
        assessmentReportTypeDropdown.value = currentAssessmentData.report_type;
        assessmentClaimTypeDropdown.value = currentAssessmentData.claim_type;
        assessmentLabourTaxTypeDropdown.value = currentAssessmentData.labour_tax_type;

        if (currentAssessmentData.user_labour_rows && currentAssessmentData.user_labour_rows.length > 0) {
            currentAssessmentData.user_labour_rows.forEach(row => addLabourRow(row));
        } else {
            addLabourRow();
        }

        currentAssessmentData.parts.forEach(part => addPartRowToTable(part));

        const deductiblesValue = currentAssessmentData.deductibles;
        assessmentDeductiblesInput.value = (deductiblesValue === null || typeof deductiblesValue === 'undefined')
            ? ''
            : formatCurrency(deductiblesValue);
        assessmentSalvageInput.value = formatCurrency(currentAssessmentData.salvage);

        const imposeExcessValue = currentAssessmentData.impose_excess;
        const imposeExcessInput = document.getElementById('assessment-impose-excess');
        if (imposeExcessInput) {
            imposeExcessInput.value = (imposeExcessValue === null || typeof imposeExcessValue === 'undefined')
                ? ''
                : formatCurrency(imposeExcessValue);
        }

        // Restore ND deduction fields
        const ndDeductionPcInput = document.getElementById('assessment-nd-deduction-pc');
        const ndDeductionAmtInput = document.getElementById('assessment-nd-deduction-amt');
        if (ndDeductionPcInput) ndDeductionPcInput.value = currentAssessmentData.nd_deduction_pc ?? 5;
        if (ndDeductionAmtInput && currentAssessmentData.nd_deduction_amount != null) {
            ndDeductionAmtInput.value = formatCurrency(currentAssessmentData.nd_deduction_amount);
        }

        // Restore towing charges
        const towingChargesInput = document.getElementById('assessment-towing-charges');
        if (towingChargesInput) {
            const towingVal = currentAssessmentData.towing_charges;
            towingChargesInput.value = (towingVal === null || typeof towingVal === 'undefined' || towingVal === 0)
                ? ''
                : formatCurrency(towingVal);
        }

        // Restore estimate override fields
        const estLabourEl = document.getElementById('assessment-est-labour');
        const estPaintEl = document.getElementById('assessment-est-paint');
        const estPartsEl = document.getElementById('assessment-est-parts');
        if (estLabourEl) estLabourEl.value = currentAssessmentData.est_labour_override || '';
        if (estPaintEl) estPaintEl.value = currentAssessmentData.est_paint_override || '';
        if (estPartsEl) estPartsEl.value = currentAssessmentData.est_parts_override || '';

        if (page3CustomerGstinInput) page3CustomerGstinInput.value = currentAssessmentData.page3_details.customer_gstin || '';
        const page3CompanyGstinInput = document.getElementById('page3-company-gstin');
        if (page3CompanyGstinInput) page3CompanyGstinInput.value = currentAssessmentData.page3_details.company_gstin || '';

        if (page3EstimatedAmountInput) page3EstimatedAmountInput.value = formatCurrency(currentAssessmentData.page3_details.estimated_amount || 0);
        if (page3PhotoCopiesCountInput) page3PhotoCopiesCountInput.value = currentAssessmentData.page3_details.photo_copies_count || '';

        const includeInConsolidatedCheckbox = document.getElementById('page3-include-in-consolidated');
        if (includeInConsolidatedCheckbox) {
            includeInConsolidatedCheckbox.checked = currentAssessmentData.page3_details.include_in_consolidated === true;
        }
        const page3ApplyGstCheckbox = document.getElementById('page3-apply-gst');
        if (page3ApplyGstCheckbox) {
            page3ApplyGstCheckbox.checked = currentAssessmentData.page3_details.apply_gst !== false;
        }

        // Populate Surveyor Bank Details
        const surveyor = currentAssessmentData.page3_details.surveyor_details || {};
        const setVal = (id, val) => { const el = document.getElementById(id); if (el && val) el.value = val; };
        setVal('surveyor-gstin', surveyor.gstin);
        setVal('surveyor-pan', surveyor.pan);
        setVal('surveyor-bank-name', surveyor.bank_name);
        setVal('surveyor-account-no', surveyor.account_no);
        setVal('surveyor-micr', surveyor.micr);
        setVal('surveyor-ifsc', surveyor.ifsc);
        setVal('surveyor-state-code', surveyor.state_code || '(19)');
        setVal('surveyor-code', surveyor.surveyor_code || '2075995');

        if (currentAssessmentData.page3_details.fee_items && currentAssessmentData.page3_details.fee_items.length > 0) {
            currentAssessmentData.page3_details.fee_items.forEach(item => addPage3FeeItemRow(item));
        }
        else if (page3FeeItemsTbody && page3FeeItemsTbody.rows.length === 0) {
            addPage3FeeItemRow();
        }

        addRecalculationListeners();
        assessmentSalvageInput.addEventListener('blur', formatInputOnBlurWrapper);
        if (page3EstimatedAmountInput) page3EstimatedAmountInput.addEventListener('blur', formatInputOnBlurWrapper);

        updateDepreciationFieldStates();
        updateLabourTaxDisplay();
        handleReportTypeChange(); // Trigger Spot Report UI logic

        recalculateAll();

        uploadSection.classList.add('hidden');
        previewSection.classList.remove('hidden');
        downloadSection.classList.add('hidden');
        updateSteps('review');
        hideStatus();
        window.scrollTo(0, 0);
    }

    function handleReportTypeChange() {
        const reportType = assessmentReportTypeDropdown.value;
        const spotSection = document.getElementById('spot-report-section');
        const claimTypeGroup = document.getElementById('claim-type-group');
        const assessmentWrapper = document.getElementById('assessment-details-wrapper');

        // Ensure Bill details are always visible (page3-details-wrapper is not toggled here)

        if (reportType === 'Spot Report') {
            if (assessmentWrapper) assessmentWrapper.classList.add('hidden');
            spotSection.classList.remove('hidden');
            // Hide Claim Type dropdown as requested (only display Spot/Preliminary Report at top)
            if (claimTypeGroup) claimTypeGroup.classList.add('hidden');
        } else {
            if (assessmentWrapper) assessmentWrapper.classList.remove('hidden');
            spotSection.classList.add('hidden');
            if (claimTypeGroup) claimTypeGroup.classList.remove('hidden');
        }
    }

    // Add listener for Report Type change
    if (assessmentReportTypeDropdown) {
        assessmentReportTypeDropdown.addEventListener('change', handleReportTypeChange);
    }

    function addRecalculationListeners() {
        const triggerInputs = [
            assessmentLabourPaintDepnInput,
            assessmentSalvageInput,
            assessmentDeductiblesInput,
            document.getElementById('assessment-impose-excess'), // New listener
            assessmentHeaderVehicleYearInput,
            assessmentPolicyTypeDropdown,
            assessmentLabourTaxTypeDropdown,
            document.getElementById('assessment-labour-imt-23'),
            document.getElementById('assessment-nd-deduction-pc'),
            document.getElementById('assessment-nd-deduction-amt'),
            document.getElementById('assessment-towing-charges'),
            document.getElementById('page3-apply-gst'),
            page3EstimatedAmountInput,
            page3PhotoCopiesCountInput,
            document.getElementById('input-vehicle_regn_date'),
            document.getElementById('input-accident_survey_date'),
            document.getElementById('input-accident_assign_received'),
            document.getElementById('input-report_date')
        ];
        triggerInputs.forEach(input => {
            if (input) {
                const eventType = (input.tagName === 'SELECT' || input.type === 'checkbox') ? 'change' : 'input';
                // Remove existing listener before adding
                input.removeEventListener(eventType, recalculateAll);
                input.addEventListener(eventType, recalculateAll);

                if (input.classList.contains('number-input')) {
                    input.removeEventListener('blur', formatInputOnBlurWrapper);
                    input.addEventListener('blur', formatInputOnBlurWrapper);
                }
            }
        });

        // ND deduction amount: mark as manually overridden when user types directly
        const ndAmtInputEl = document.getElementById('assessment-nd-deduction-amt');
        if (ndAmtInputEl) {
            ndAmtInputEl.addEventListener('focus', () => {
                ndAmtInputEl.dataset.autoCalculated = 'false';
            });
        }
        // ND deduction %: reset amount to auto-calculate when % changes
        const ndPcInputEl = document.getElementById('assessment-nd-deduction-pc');
        if (ndPcInputEl) {
            ndPcInputEl.addEventListener('input', () => {
                if (ndAmtInputEl) ndAmtInputEl.dataset.autoCalculated = 'true';
            });
        }
    }

    function updateDepreciationFieldStates() {
        const policyVal = assessmentPolicyTypeDropdown.value;
        const isNilDepn = policyVal === 'NIL_DEPN' || policyVal === 'NIL_DEPN_PLUS';

        // Toggle ND deduction fields visibility (only for NIL_DEPN, not NIL_DEPN_PLUS)
        const ndPcGroup = document.getElementById('nd-deduction-pc-group');
        const ndAmtGroup = document.getElementById('nd-deduction-amt-group');
        if (ndPcGroup) ndPcGroup.style.display = (policyVal === 'NIL_DEPN') ? '' : 'none';
        if (ndAmtGroup) ndAmtGroup.style.display = (policyVal === 'NIL_DEPN') ? '' : 'none';

        // Labour Paint Depreciation
        assessmentLabourPaintDepnInput.readOnly = isNilDepn;
        if (isNilDepn) {
            assessmentLabourPaintDepnInput.value = formatCurrency(0);
            // Ensure data model is also updated if changed by UI state
            if (currentAssessmentData) currentAssessmentData.labour_paint_depn_user_override = 0;
        }
        // If NORMAL, it will be recalculated or use user input in recalculateLabourTotals

        // Parts Depreciation
        partsDetailsTbody.querySelectorAll('tr').forEach(row => {
            const deprInput = row.querySelector('.part-depr-input');
            if (deprInput) {
                deprInput.readOnly = isNilDepn;
                if (isNilDepn) {
                    deprInput.value = formatCurrency(0);
                    const slNo = deprInput.dataset.slNo;
                    if (slNo && currentAssessmentData && currentAssessmentData.parts) {
                        const part = currentAssessmentData.parts.find(p => p.sl_no == slNo);
                        if (part) part.depr_user_override = 0; // Store that UI forced it to 0
                    }
                }
            }
        });
    }

    function updateLabourTaxDisplay() {
        const selectedTaxType = assessmentLabourTaxTypeDropdown ? assessmentLabourTaxTypeDropdown.value : 'CGST/SGST';

        // Update label for the new flat GST input
        const labourGstInput = document.getElementById('assessment-labour_gst');
        if (labourGstInput) {
            const label = labourGstInput.previousElementSibling;
            if (label) {
                label.textContent = selectedTaxType === 'IGST' ? 'Add 18% IGST:' : 'Add 18% GST:';
            }
        }

        // Safe check for old rows to prevent "Cannot read properties of null" error
        // These variables (labourCgstRow, etc.) are defined at the top of the scope but are null in the new layout
        if (labourCgstRow) {
            if (selectedTaxType === 'IGST') labourCgstRow.classList.add('hidden');
            else labourCgstRow.classList.remove('hidden');
        }
        if (labourSgstRow) {
            if (selectedTaxType === 'IGST') labourSgstRow.classList.add('hidden');
            else labourSgstRow.classList.remove('hidden');
        }
        if (labourIgstRow) {
            if (selectedTaxType === 'IGST') labourIgstRow.classList.remove('hidden');
            else labourIgstRow.classList.add('hidden');
        }
    }

    // Wrapper to pass formatter
    function formatInputOnBlurWrapper(e) { formatInputOnBlur(e); }


    // --- Dynamic Labour Row Handling ---
    function addLabourRow(rowData = {}) {
        const newRow = labourDetailsTbody.insertRow();
        const removingRefitting = formatCurrency(rowData.removing_refitting || 0);
        const dentingRepairing = formatCurrency(rowData.denting_repairing || 0);
        const painting = formatCurrency(rowData.painting || 0);

        newRow.innerHTML = `
            <td><input type="text" name="labour_part_name" placeholder="Enter Part Name" value="${rowData.part_name || ''}"></td>
            <td><input type="text" name="labour_removing_refitting" class="number-input labour-cost-input" placeholder="0" value="${removingRefitting}"></td>
            <td><input type="text" name="labour_denting_repairing" class="number-input labour-cost-input" placeholder="0" value="${dentingRepairing}"></td>
            <td><input type="text" name="labour_painting" class="number-input labour-cost-input labour-painting-input" placeholder="0" value="${painting}"></td>
            <td><button type="button" class="btn btn-danger btn-sm remove-labour-row"><i class="fas fa-trash-alt"></i></button></td>
        `;

        newRow.querySelectorAll('.labour-cost-input').forEach(input => {
            input.addEventListener('input', () => {
                recalculateAll();
            });
            if (input.classList.contains('number-input')) {
                input.addEventListener('blur', formatInputOnBlurWrapper);
            }
        });
        newRow.querySelector('.remove-labour-row').addEventListener('click', function () {
            this.closest('tr').remove();
            recalculateAll();
        });
    }

    function updateLabourRowTotal(rowElement) {
        const removingInput = rowElement.querySelector('input[name="labour_removing_refitting"]');
        const dentingInput = rowElement.querySelector('input[name="labour_denting_repairing"]');
        const paintingInput = rowElement.querySelector('input[name="labour_painting"]');

        const rVal = parseFormattedNumber(removingInput?.value);
        const dVal = parseFormattedNumber(dentingInput?.value);
        const pVal = parseFormattedNumber(paintingInput?.value);

        const baseSumForRow = rVal + dVal + pVal;

        const gstSelect = rowElement.querySelector('select[name="labour_row_gst_pc"]');
        const gstPcForRow = gstSelect ? parseInt(gstSelect.value) : 0;

        let gstAmountForRow = 0;
        if (gstPcForRow === 18) {
            gstAmountForRow = baseSumForRow * 0.18;
        }

        const totalForRowWithGst = baseSumForRow + gstAmountForRow;

        const totalInput = rowElement.querySelector('input[name="labour_total"]');
        if (totalInput) {
            totalInput.value = formatCurrency(totalForRowWithGst);
        }
    }

    addLabourRowButton.addEventListener('click', () => addLabourRow()); // Pass no data for new row

    labourDetailsTbody.addEventListener('click', function (e) { // Event delegation for remove
        if (e.target.closest('.remove-labour-row')) {
            e.target.closest('tr').remove();
            recalculateAll(); // Recalculate when row removed
        }
    });

    // --- Page 3 Fee Items Table Handling ---
    function addPage3FeeItemRow(itemData = {}) {
        if (!page3FeeItemsTbody) return; // Guard if element doesn't exist
        const newRow = page3FeeItemsTbody.insertRow();
        const feeName = itemData.name || '';
        const feeAmount = formatCurrency(itemData.amount || 0);

        newRow.innerHTML = `
            <td><input type="text" name="page3_fee_name" placeholder="Enter Fee/Expense Name" value="${feeName}" class="page3-fee-input"></td>
            <td><input type="text" name="page3_fee_amount" class="number-input page3-fee-input" placeholder="0.00" value="${feeAmount}"></td>
            <td><button type="button" class="btn btn-danger btn-sm remove-page3-fee-row"><i class="fas fa-trash-alt"></i></button></td>
        `;

        newRow.querySelectorAll('.page3-fee-input').forEach(input => {
            input.addEventListener('input', recalculateAll); // Recalculate on any change
            if (input.classList.contains('number-input')) {
                input.addEventListener('blur', formatInputOnBlurWrapper);
            }
        });

        newRow.querySelector('.remove-page3-fee-row').addEventListener('click', function () {
            this.closest('tr').remove();
            recalculateAll();
        });
    }

    if (addPage3FeeItemRowButton) {
        addPage3FeeItemRowButton.addEventListener('click', () => addPage3FeeItemRow());
    }

    if (page3FeeItemsTbody) {
        page3FeeItemsTbody.addEventListener('click', function (e) {
            if (e.target.closest('.remove-page3-fee-row')) {
                e.target.closest('tr').remove();
                recalculateAll();
            }
        });
    }

    // --- Parts Table Handling ---
    function addPartRowToTable(part) {
        const slNo = part.sl_no;
        if (typeof slNo === 'undefined') return;
        const rowId = `part_row_${slNo}`;
        const newRow = partsDetailsTbody.insertRow();
        newRow.id = rowId;

        const rawQty = part.qty ?? 1;
        const rawPartAmt = part.part_amt ?? 0;
        const gstPcValue = part.original_gst_pc ?? 0;
        const partType = String(part.type_part || '').trim().toUpperCase();
        const imtApplied = part.imt_applied === true; // Boolean flag

        // Calculate initial values
        const vehicleYearStr = assessmentHeaderVehicleYearInput.value.trim();
        const gstApplicableInitial = parseFloat(gstPcValue) > 0;
        const totalPartsAmtInitial = parseFormattedNumber(rawQty) * parseFormattedNumber(rawPartAmt);
        const grossAmtInitial = totalPartsAmtInitial * (1 + (gstApplicableInitial ? (parseFloat(gstPcValue || 0) / 100) : 0));
        const calculatedDeprInitial = getJsDepreciationRate(partType, vehicleYearStr) * grossAmtInitial / 100.0;
        const initialDeprValue = part.depr ?? calculatedDeprInitial;

        // IMT Calculation Logic for Initial Display
        let imt23Amt = 0;
        if (imtApplied) {
            imt23Amt = (grossAmtInitial - initialDeprValue) * 0.5;
        }
        const initialNetValue = grossAmtInitial - initialDeprValue - imt23Amt;

        // Defaults for new fields
        const estimateAmt = part.estimate_amt ?? grossAmtInitial;
        const billAmt = part.bill_amt ?? totalPartsAmtInitial;
        const hnsCode = part.hns_code || '';
        const salvageProduce = part.salvage_produce || 'YES';
        const remarks = part.remarks || 'REPLACED BY NEW';

        // Store initial calculated depreciation
        newRow.dataset.calculatedDepr = formatCurrency(calculatedDeprInitial);

        // Type Dropdown
        const typeOptions = ["", "P", "M", "G"];
        let typeDropdownHtml = `<select name="part_type_${slNo}" class="part-input part-type-select" data-sl-no="${slNo}">`;
        typeOptions.forEach(opt => {
            const selected = (opt === partType) ? 'selected' : '';
            typeDropdownHtml += `<option value="${opt}" ${selected}>${opt || '-'}</option>`;
        });
        typeDropdownHtml += `</select>`;

        // Salvage Dropdown
        let salvageDropdownHtml = `<select name="part_salvage_${slNo}" class="part-input part-salvage-select" data-sl-no="${slNo}">
            <option value="YES" ${salvageProduce === 'YES' ? 'selected' : ''}>YES</option>
            <option value="NO" ${salvageProduce === 'NO' ? 'selected' : ''}>NO</option>
            <option value="NA" ${salvageProduce === 'NA' ? 'selected' : ''}>NA</option>
        </select>`;

        // Remarks Dropdown
        let remarksDropdownHtml = `<select name="part_remarks_${slNo}" class="part-input part-remarks-select" data-sl-no="${slNo}">
            <option value="REPLACED BY NEW" ${remarks === 'REPLACED BY NEW' ? 'selected' : ''}>REPLACED BY NEW</option>
            <option value="REPLACED BY OLD" ${remarks === 'REPLACED BY OLD' ? 'selected' : ''}>REPLACED BY OLD</option>
            <option value="REPAIRED" ${remarks === 'REPAIRED' ? 'selected' : ''}>REPAIRED</option>
        </select>`;

        newRow.innerHTML = `
            <td><input type="text" name="part_sl_no_${slNo}" value="${slNo}" class="part-input number-input part-slno-input" data-sl-no="${slNo}"></td>
            <td><input type="text" name="part_est_sl_no_${slNo}" value="${part.est_sl_no || slNo}" class="part-input part-est-slno-input" data-sl-no="${slNo}"></td>
            <td><input type="text" name="part_bill_sl_no_${slNo}" value="${part.bill_sl_no || slNo}" class="part-input part-bill-slno-input" data-sl-no="${slNo}"></td>
            <td><input type="text" name="part_name_${slNo}" value="${part.part_name || ''}" class="part-input part-name-input" data-sl-no="${slNo}"></td>
            
            <td><input type="text" name="part_hns_${slNo}" value="${hnsCode}" class="part-input part-hns-input" data-sl-no="${slNo}"></td>
            <td><input type="text" name="part_estimate_${slNo}" value="${formatCurrency(estimateAmt)}" class="part-input number-input part-estimate-input" data-sl-no="${slNo}"></td>
            <td><input type="text" name="part_bill_${slNo}" value="${formatCurrency(billAmt)}" class="part-input number-input part-bill-input" data-sl-no="${slNo}"></td>
            
            <td>${typeDropdownHtml}</td>
            <td><input type="text" name="part_gst_pc_${slNo}" value="${gstPcValue}" placeholder="e.g. 18" class="part-input number-input part-gst-pc-input" data-sl-no="${slNo}"></td>
            <td><input type="text" name="part_qty_${slNo}" value="${formatQty(rawQty)}" class="part-input number-input part-qty-input" data-sl-no="${slNo}"></td>
            <td><input type="text" name="part_amt_${slNo}" value="${formatCurrency(rawPartAmt)}" class="part-input number-input part-amt-input" data-sl-no="${slNo}"></td>
            
            <td id="part_total_amt_${slNo}" class="calculated-cell">${formatCurrency(totalPartsAmtInitial)}</td>
            <td id="part_total_gst_${slNo}" class="calculated-cell">${formatCurrency(part.total_gst)}</td>
            <td id="part_gross_amt_${slNo}" class="calculated-cell">${formatCurrency(part.gross_amt)}</td>
            
            <td><input type="text" name="part_depr_amt_${slNo}" value="${formatCurrency(initialDeprValue)}" class="part-input number-input part-depr-input" data-sl-no="${slNo}" placeholder="Amt"></td>
            
            <td style="text-align: center;"><input type="checkbox" name="part_imt_applied_${slNo}" class="part-imt-checkbox" data-sl-no="${slNo}" ${imtApplied ? 'checked' : ''}></td>
            
            <td>${salvageDropdownHtml}</td>
            <td>${remarksDropdownHtml}</td>
            
            <td id="part_net_amt_${slNo}" class="calculated-cell bold-result">${formatCurrency(initialNetValue)}</td>
            <td><button type="button" class="btn btn-danger btn-sm remove-part-row" data-sl-no="${slNo}"><i class="fas fa-trash-alt"></i></button></td>
        `;

        // --- Add event listeners ---
        const typeSelect = newRow.querySelector('.part-type-select');
        if (typeSelect) typeSelect.addEventListener('change', () => { recalculateAll(); });

        const imtCheckbox = newRow.querySelector('.part-imt-checkbox');
        if (imtCheckbox) imtCheckbox.addEventListener('change', () => { recalculateAll(); });

        newRow.querySelectorAll('input.part-input, select.part-salvage-select, select.part-remarks-select').forEach(input => {
            input.addEventListener('input', (e) => {
                recalculatePartRow(slNo, null);
                updatePartsTotals();
                updateSummaryCalculations();
            });

            if (input.classList.contains('number-input')) {
                let formatter;
                if (input.classList.contains('part-qty-input')) { formatter = formatQty; }
                else if (input.classList.contains('part-slno-input') || input.classList.contains('part-gst-pc-input')) { formatter = (v => v.replace(/[^0-9.]/g, '')); }
                else { formatter = formatCurrency; }
                input.addEventListener('blur', (e) => formatInputOnBlur(e, formatter));
            }
        });

        recalculatePartRow(slNo, part);
    }

    addPartRowButton.addEventListener('click', () => {
        if (!currentAssessmentData || !currentAssessmentData.parts) {
            currentAssessmentData = { ...currentAssessmentData, parts: [] };
        }
        const nextSlNo = currentAssessmentData.parts.length > 0
            ? Math.max(...currentAssessmentData.parts.map(p => parseInt(p.sl_no) || 0)) + 1
            : 1;
        const newPart = {
            sl_no: nextSlNo,
            est_sl_no: nextSlNo.toString(),
            bill_sl_no: nextSlNo.toString(),
            part_name: '',
            type_part: '',
            qty: 1,
            part_amt: 0,
            original_gst_pc: 28,
            gst_applicable: true,
            total_parts_amt: 0,
            total_gst: 0,
            gross_amt: 0,
            depr: 0,
            net_amt: 0
        };
        currentAssessmentData.parts.push(newPart);
        addPartRowToTable(newPart);
        recalculateAll();
    });

    partsDetailsTbody.addEventListener('click', function (e) {
        if (e.target.closest('.remove-part-row')) {
            const button = e.target.closest('.remove-part-row');
            const slNoToRemove = button.dataset.slNo;
            const rowToRemove = document.getElementById(`part_row_${slNoToRemove}`);
            if (rowToRemove) {
                rowToRemove.remove();
                if (currentAssessmentData && currentAssessmentData.parts) {
                    currentAssessmentData.parts = currentAssessmentData.parts.filter(p => p.sl_no != slNoToRemove);
                }
                recalculateAll();
            }
        }
    });

    function updatePartsTotals() {
        let totalBase = 0, totalGst = 0, totalGross = 0, totalNet = 0, totalDepr = 0;
        currentAssessmentData?.parts?.forEach(part => {
            totalBase += parseFloat(part.total_parts_amt || 0);
            totalGst += parseFloat(part.total_gst || 0);
            totalGross += parseFloat(part.gross_amt || 0);
            totalDepr += parseFloat(part.depr || 0);
            totalNet += parseFloat(part.net_amt || 0);
        });

        partsTotalBaseFooter.textContent = formatCurrency(totalBase);
        partsTotalGstFooter.textContent = formatCurrency(totalGst);
        partsGrandTotalFooter.textContent = formatCurrency(totalGross);
        if (partsDeprSumFooter) partsDeprSumFooter.textContent = formatCurrency(totalDepr);
        partsNetTotalFooter.textContent = formatCurrency(totalNet);

        if (currentAssessmentData) {
            currentAssessmentData.parts_total_base = totalBase;
            currentAssessmentData.parts_total_gst = totalGst;
            currentAssessmentData.parts_grand_total = totalGross;
            currentAssessmentData.parts_depr_sum = totalDepr;
            currentAssessmentData.parts_net_total = totalNet;
        }
    }

    // --- Recalculation Logic ---
    function recalculateAll() {
        updateVehicleAge();
        updateDepreciationFieldStates();
        updateLabourTaxDisplay();
        recalculateLabourTotals();
        recalculateAllParts();
        updatePartsTotals();
        updateSummaryCalculations();
        recalculatePage3Totals();
    }

    function recalculateLabourTotals() {
        if (!currentAssessmentData) return;

        let sumOfAllR = 0;
        let sumOfAllD = 0;
        let sumOfAllP = 0;

        labourDetailsTbody.querySelectorAll('tr').forEach(row => {
            const rVal = parseFormattedNumber(row.querySelector('input[name="labour_removing_refitting"]')?.value);
            const dVal = parseFormattedNumber(row.querySelector('input[name="labour_denting_repairing"]')?.value);
            const pVal = parseFormattedNumber(row.querySelector('input[name="labour_painting"]')?.value);

            sumOfAllR += rVal;
            sumOfAllD += dVal;
            sumOfAllP += pVal;
        });

        // Paint Depreciation (Default 12.5%)
        const paintDepnInput = assessmentLabourPaintDepnInput;
        let finalPaintDepnToUse;

        if (assessmentPolicyTypeDropdown.value === 'NIL_DEPN' || assessmentPolicyTypeDropdown.value === 'NIL_DEPN_PLUS') {
            finalPaintDepnToUse = 0.0;
            paintDepnInput.value = formatCurrency(0);
        } else {
            const newDefaultPaintDepn = sumOfAllP * 0.125; // 12.5% Default
            paintDepnInput.value = formatCurrency(newDefaultPaintDepn);
            finalPaintDepnToUse = newDefaultPaintDepn;
        }

        const netPaintAfterDep = sumOfAllP - finalPaintDepnToUse;

        // IMT-23 Calculation for Labour (50% on Net Paint)
        const imt23Checkbox = document.getElementById('assessment-labour-imt-23');
        const imt23Display = document.getElementById('assessment-labour-imt-23-amt');
        let labourImt23Amount = 0.0;

        if (imt23Checkbox && imt23Checkbox.checked && netPaintAfterDep > 0) {
            labourImt23Amount = netPaintAfterDep * 0.5;
        }

        if (imt23Display) {
            imt23Display.value = formatCurrency(labourImt23Amount);
        }

        const netPaintLiability = netPaintAfterDep - labourImt23Amount;

        // Taxable Labour = R&R + Dent + Net Paint Liability
        const taxableLabour = sumOfAllR + sumOfAllD + netPaintLiability;

        // GST Calculation
        let labourGstAmount = 0.0;
        const taxType = assessmentLabourTaxTypeDropdown.value;

        if (taxType !== 'Zero') {
            labourGstAmount = taxableLabour * 0.18;
        }

        const labourGrandTotalAdjusted = taxableLabour + labourGstAmount;

        // Update Data Model
        currentAssessmentData.labour_removing_total = sumOfAllR;
        currentAssessmentData.labour_denting_total = sumOfAllD;
        currentAssessmentData.labour_painting_total = sumOfAllP;
        currentAssessmentData.labour_total_base = taxableLabour;
        currentAssessmentData.labour_paint_depn = finalPaintDepnToUse;
        currentAssessmentData.labour_imt_23_amt = labourImt23Amount;
        currentAssessmentData.labour_grand_total_adjusted = labourGrandTotalAdjusted;

        // Update UI
        const displayPaintTotal = document.getElementById('display-labour-painting-total');
        if (displayPaintTotal) displayPaintTotal.value = formatCurrency(sumOfAllP);

        const displayNetPaint = document.getElementById('display-net-paint-liability');
        if (displayNetPaint) displayNetPaint.value = formatCurrency(netPaintLiability);

        const displayRRDent = document.getElementById('display-labour-rr-dent-total');
        if (displayRRDent) displayRRDent.value = formatCurrency(sumOfAllR + sumOfAllD);

        document.getElementById('assessment-labour_total_base').value = formatCurrency(taxableLabour);

        const displayGst = document.getElementById('assessment-labour_gst');
        if (displayGst) displayGst.value = formatCurrency(labourGstAmount);

        document.getElementById('assessment-labour_grand_total_adjusted').value = formatCurrency(labourGrandTotalAdjusted);

        // Hidden fields for compatibility
        document.getElementById('display-labour-removing-total').value = formatCurrency(sumOfAllR);
        document.getElementById('display-labour-denting-total').value = formatCurrency(sumOfAllD);
    }

    // --- Vehicle Age & Depreciation Calculation (JS) ---
    function parseDate(dateStr) {
        if (!dateStr || !/^\d{2}\.\d{2}\.\d{4}/.test(dateStr)) return null;
        const parts = dateStr.match(/^(\d{2})\.(\d{2})\.(\d{4})/);
        if (!parts) return null;
        return new Date(parts[3], parts[2] - 1, parts[1]);
    }

    function calculateVehicleAge(regnDateStr, surveyDateStr) {
        const startDate = parseDate(regnDateStr);
        let endDate = parseDate(surveyDateStr);

        if (!startDate || !endDate) return { years: 0, months: 0, days: 0, totalMonths: 0, display: "Invalid Dates" };

        // Handle cases where survey date might have time, strip it
        endDate = new Date(endDate.getFullYear(), endDate.getMonth(), endDate.getDate());

        if (endDate < startDate) return { years: 0, months: 0, days: 0, totalMonths: 0, display: "Survey date is before registration" };

        let years = endDate.getFullYear() - startDate.getFullYear();
        let months = endDate.getMonth() - startDate.getMonth();
        let days = endDate.getDate() - startDate.getDate();

        if (days < 0) {
            months--;
            const prevMonth = new Date(endDate.getFullYear(), endDate.getMonth(), 0);
            days += prevMonth.getDate();
        }
        if (months < 0) {
            years--;
            months += 12;
        }

        const totalMonths = (years * 12) + months + (days > 0 ? 1 : 0); // Add 1 month if any days have passed
        const display = `${years} yrs ${months} month ${days} days`;

        return { years, months, days, totalMonths, display };
    }

    function getDepreciationYear(totalMonths) {
        if (totalMonths <= 6) return 0;   // Year 0
        if (totalMonths <= 12) return 1;  // Year 1
        if (totalMonths <= 24) return 2;  // Year 2
        if (totalMonths <= 36) return 3;  // Year 3
        if (totalMonths <= 48) return 4;  // Year 4
        if (totalMonths <= 60) return 5;  // Year 5
        if (totalMonths <= 120) return Math.ceil(totalMonths / 12); // Years 6-10
        return 11; // Year 11+
    }

    function updateVehicleAge() {
        const regnDateInput = document.getElementById('input-vehicle_regn_date');
        const surveyDateInput = document.getElementById('input-accident_survey_date');
        const assignDateInput = document.getElementById('input-accident_assign_received');
        const reportDateInput = document.getElementById('input-report_date');

        let surveyDateStr = surveyDateInput.value.trim();
        if (!surveyDateStr) {
            surveyDateStr = assignDateInput.value.trim();
        }
        if (!surveyDateStr) {
            surveyDateStr = reportDateInput.value.trim();
        }

        const age = calculateVehicleAge(regnDateInput.value, surveyDateStr);
        const deprYear = getDepreciationYear(age.totalMonths);

        displayVehicleAge.value = age.display;

        // Only update the editable year field if it hasn't been manually changed by the user
        // or if the dates that calculate it have changed.
        const currentYearValue = assessmentHeaderVehicleYearInput.value;
        const previousDeprYear = assessmentHeaderVehicleYearInput.dataset.autoValue;

        if (currentYearValue === '' || currentYearValue === previousDeprYear) {
            assessmentHeaderVehicleYearInput.value = deprYear;
        }
        assessmentHeaderVehicleYearInput.dataset.autoValue = deprYear;
    }

    function getJsDepreciationRate(partType, vehicleYearStr) {
        partType = String(partType).trim().toUpperCase();
        const year_bucket = parseInt(vehicleYearStr) || 0;

        if (partType === 'G') return 0.0;
        if (partType === 'P') return 50.0;
        if (partType === 'M') {
            if (year_bucket <= 0) return 0.0;
            if (year_bucket === 1) return 5.0;
            if (year_bucket === 2) return 10.0;
            if (year_bucket === 3) return 15.0;
            if (year_bucket === 4) return 25.0;
            if (year_bucket === 5) return 35.0;
            if (year_bucket >= 6 && year_bucket <= 10) return 40.0;
            if (year_bucket > 10) return 50.0;
            return 0.0;
        }
        return 0.0;
    }

    function recalculatePartRow(slNo, part) {
        const partIndex = currentAssessmentData?.parts?.findIndex(p => p.sl_no == slNo);
        if (!part && partIndex !== -1 && currentAssessmentData?.parts) {
            part = currentAssessmentData.parts[partIndex];
        } else if (!part && (partIndex === -1 || !currentAssessmentData?.parts)) {
            return;
        } else if (part && partIndex !== -1 && currentAssessmentData?.parts) {
            currentAssessmentData.parts[partIndex] = part;
        }

        const row = document.getElementById(`part_row_${slNo}`);

        const slNoInput = row?.querySelector(`.part-slno-input`);
        const nameInput = row?.querySelector(`.part-name-input`);
        const typeSelect = row?.querySelector(`.part-type-select`);
        const gstPcInput = row?.querySelector(`.part-gst-pc-input`);
        const qtyInput = row?.querySelector(`.part-qty-input`);
        const amtInput = row?.querySelector(`.part-amt-input`);
        const deprInput = row?.querySelector(`.part-depr-input`);
        const imtCheckbox = row?.querySelector(`.part-imt-checkbox`);
        const salvageSelect = row?.querySelector(`.part-salvage-select`);
        const remarksSelect = row?.querySelector(`.part-remarks-select`);

        const currentSlNo = parseInt(slNoInput?.value || part.sl_no);
        const partName = (nameInput?.value || part.part_name || '').trim();
        const partType = (typeSelect?.value || part.type_part || '').trim().toUpperCase();
        const gstPc = parseFloat(gstPcInput?.value || part.original_gst_pc || 0);
        const qty = parseFormattedNumber(qtyInput?.value || part.qty);
        const partAmt = parseFormattedNumber(amtInput?.value || part.part_amt);
        const vehicleYearStr = assessmentHeaderVehicleYearInput.value.trim();
        const gstApplicable = gstPc > 0;
        const imtApplied = imtCheckbox ? imtCheckbox.checked : false;

        const costChanged = Math.abs(parseFormattedNumber(part.qty) - qty) > 0.001 || Math.abs(parseFormattedNumber(part.part_amt) - partAmt) > 0.01;
        const typeChanged = (part.type_part || '') !== partType;
        const yearChanged = part.lastCalculatedYear !== vehicleYearStr;
        const gstChanged = Math.abs(parseFloat(part.original_gst_pc || 0) - gstPc) > 0.01;
        const dependenciesChanged = costChanged || typeChanged || yearChanged || gstChanged;

        part.sl_no = currentSlNo;
        part.part_name = partName;
        part.type_part = partType;
        part.original_gst_pc = gstPc;
        part.qty = qty;
        part.part_amt = partAmt;
        part.gst_applicable = gstApplicable;
        part.lastCalculatedYear = vehicleYearStr;
        part.imt_applied = imtApplied;
        part.salvage_produce = salvageSelect ? salvageSelect.value : 'YES';
        part.remarks = remarksSelect ? remarksSelect.value : 'REPLACED BY NEW';

        // Base Assessed
        const totalPartsAmt = qty * partAmt;

        // Depreciation
        let finalDeprAmount;
        const isNilDepnPolicy = assessmentPolicyTypeDropdown.value === 'NIL_DEPN' || assessmentPolicyTypeDropdown.value === 'NIL_DEPN_PLUS';

        if (isNilDepnPolicy) {
            finalDeprAmount = 0.0;
            if (deprInput) {
                deprInput.value = formatCurrency(0);
            }
        } else {
            const calculatedDepr = totalPartsAmt > 0 ? (totalPartsAmt * (getJsDepreciationRate(partType, vehicleYearStr) / 100.0)) : 0.0;
            const currentDeprInputValueStr = deprInput?.value?.trim() || '';
            const currentDeprInputValue = parseFormattedNumber(currentDeprInputValueStr || '0');

            if (deprInput) {
                row.dataset.calculatedDepr = formatCurrency(calculatedDepr);
                deprInput.placeholder = `Calc: ${formatCurrency(calculatedDepr)}`;

                if (dependenciesChanged) {
                    finalDeprAmount = calculatedDepr;
                    if (document.activeElement !== deprInput) {
                        deprInput.value = formatCurrency(finalDeprAmount);
                    }
                } else if (currentDeprInputValueStr !== '') {
                    finalDeprAmount = currentDeprInputValue;
                } else {
                    finalDeprAmount = calculatedDepr;
                    if (document.activeElement !== deprInput) {
                        deprInput.value = formatCurrency(finalDeprAmount);
                    }
                }
            } else {
                finalDeprAmount = part.depr ?? calculatedDepr;
            }
        }

        // Net Base (Assessed - Dep)
        const netBase = totalPartsAmt - finalDeprAmount;

        // GST on Net Base
        const totalGst = gstApplicable ? (netBase * (gstPc / 100.0)) : 0.0;

        // Gross Post-Dep (Net Base + GST)
        const grossPostDep = netBase + totalGst;

        // For UI display "Gross Amt" column, we show Gross Post-Dep
        // (Note: HTML table header says "Gross Amt", logic changed from Base+GST to NetBase+GST)
        const grossAmtForUI = grossPostDep;

        // IMT 23 on Gross Post-Dep
        let imt23Amt = 0;
        if (imtApplied) {
            imt23Amt = grossPostDep * 0.5;
        }

        // Final Net Amount
        const netAmt = grossPostDep - imt23Amt;

        part.total_parts_amt = totalPartsAmt;
        part.total_gst = totalGst;
        part.gross_amt = grossAmtForUI;
        part.depr = finalDeprAmount;
        part.imt_23_amt = imt23Amt;
        part.net_amt = netAmt;

        if (row) {
            const totalAmtCell = row.querySelector(`#part_total_amt_${slNo}`);
            const totalGstCell = row.querySelector(`#part_total_gst_${slNo}`);
            const grossAmtCell = row.querySelector(`#part_gross_amt_${slNo}`);
            const netAmtCell = row.querySelector(`#part_net_amt_${slNo}`);

            if (totalAmtCell) totalAmtCell.textContent = formatCurrency(totalPartsAmt);
            if (totalGstCell) totalGstCell.textContent = formatCurrency(totalGst);
            if (grossAmtCell) grossAmtCell.textContent = formatCurrency(grossAmtForUI);
            if (netAmtCell) netAmtCell.textContent = formatCurrency(netAmt);
        }
    }

    function recalculateAllParts() {
        if (currentAssessmentData?.parts) {
            const slNosToRecalculate = currentAssessmentData.parts.map(p => p.sl_no);
            slNosToRecalculate.forEach(slNo => {
                const partObject = currentAssessmentData.parts.find(p => p.sl_no == slNo);
                if (partObject) {
                    recalculatePartRow(slNo, partObject);
                }
            });
        }
    }

    function updateSummaryCalculations() {
        if (!currentAssessmentData) return;
        const addLabour = parseFloat(currentAssessmentData.labour_grand_total_adjusted || 0);
        const addPartsNet = parseFloat(currentAssessmentData.parts_net_total || 0);
        const lessExcessInput = assessmentDeductiblesInput;
        const lessExcess = parseFormattedNumber(lessExcessInput?.value || 0);
        const salvageInput = assessmentSalvageInput;
        const salvageValue = parseFormattedNumber(salvageInput?.value || 0);

        const imposeExcessInput = document.getElementById('assessment-impose-excess');
        const imposeExcess = parseFormattedNumber(imposeExcessInput?.value || 0);

        // ND Deduction (only for NIL_DEPN policy)
        const ndDeductionPcInput = document.getElementById('assessment-nd-deduction-pc');
        const ndDeductionAmtInput = document.getElementById('assessment-nd-deduction-amt');
        const towingChargesInput = document.getElementById('assessment-towing-charges');
        const policyVal = assessmentPolicyTypeDropdown.value;

        let ndDeductionAmount = 0;
        if (policyVal === 'NIL_DEPN') {
            const ndPc = parseFloat(ndDeductionPcInput?.value || 5);
            const totalLiability = addLabour + addPartsNet;
            const autoNdAmount = totalLiability * (ndPc / 100.0);
            // If user hasn't manually overridden, use auto-calculated value
            const currentNdAmtStr = ndDeductionAmtInput?.value?.trim() || '';
            if (currentNdAmtStr === '' || ndDeductionAmtInput?.dataset.autoCalculated === 'true') {
                ndDeductionAmount = autoNdAmount;
                if (ndDeductionAmtInput) {
                    ndDeductionAmtInput.value = formatCurrency(autoNdAmount);
                    ndDeductionAmtInput.dataset.autoCalculated = 'true';
                }
            } else {
                ndDeductionAmount = parseFormattedNumber(currentNdAmtStr);
            }
        }

        const towingCharges = parseFormattedNumber(towingChargesInput?.value || 0);

        currentAssessmentData.deductibles = lessExcess;
        currentAssessmentData.salvage = salvageValue;
        currentAssessmentData.impose_excess = imposeExcess;
        currentAssessmentData.nd_deduction_pc = parseFloat(ndDeductionPcInput?.value || 5);
        currentAssessmentData.nd_deduction_amount = ndDeductionAmount;
        currentAssessmentData.towing_charges = towingCharges;

        const netLiability = (addLabour + addPartsNet) - lessExcess - imposeExcess - salvageValue - ndDeductionAmount + towingCharges;

        summaryAddLabour.value = formatCurrency(addLabour);
        summaryAddParts.value = formatCurrency(addPartsNet);
        summaryLessExcess.value = formatCurrency(lessExcess);
        summaryNetLiability.value = formatCurrency(netLiability);

        currentAssessmentData.net_liability = netLiability;
    }

    uploadInvoiceButton.addEventListener('click', handleInvoiceUpload);

    async function handleInvoiceUpload() {
        const file = invoiceFileInput.files[0];
        if (!file) {
            showInvoiceStatus('Please select an invoice PDF file first.', 'error');
            return;
        }

        showInvoiceStatus('Uploading and processing invoice securely...', 'processing');
        uploadInvoiceButton.disabled = true;
        uploadInvoiceButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing Invoice...';

        try {
            const formData = new FormData();
            formData.append('invoice_pdf_file', file);
            const response = await fetch('/process_invoice', { method: 'POST', body: formData });

            if (!response.ok) {
                let errorMsg = `Server error: ${response.status}`;
                try { const errorData = await response.json(); errorMsg = errorData.error || errorMsg; } catch (e) { }
                throw new Error(errorMsg);
            }

            const responseData = await response.json();
            const taskId = responseData.task_id;

            showInvoiceStatus('AI is analyzing invoice... This may take a minute.', 'processing');

            let invoiceResult = null;
            while (true) {
                await new Promise(resolve => setTimeout(resolve, 2000));
                const statusRes = await fetch(`/process_pdf/status/${taskId}`);
                if (!statusRes.ok) throw new Error(`Status check failed: ${statusRes.status}`);
                const statusData = await statusRes.json();
                if (statusData.status === 'completed') {
                    invoiceResult = statusData.result;
                    break;
                } else if (statusData.status === 'error') {
                    throw new Error(statusData.error || 'AI processing failed');
                }
            }

            if (!invoiceResult || typeof invoiceResult.parts === 'undefined') {
                throw new Error("Invalid response format received from invoice processing.");
            }

            if (page3CustomerGstinInput && typeof invoiceResult.customer_gstin !== 'undefined') {
                page3CustomerGstinInput.value = invoiceResult.customer_gstin;
                if (currentAssessmentData && currentAssessmentData.page3_details) {
                    currentAssessmentData.page3_details.customer_gstin = invoiceResult.customer_gstin;
                }
            }

            mergeInvoiceParts(invoiceResult.parts);
            showInvoiceStatus('Invoice parts merged successfully!', 'success');
            invoiceFileInput.value = '';
            selectedInvoiceFileName.textContent = '';
            uploadInvoiceButton.disabled = true;

        } catch (error) {
            console.error('Error processing invoice:', error);
            showInvoiceStatus(`Error processing invoice: ${error.message}`, 'error');
        } finally {
            uploadInvoiceButton.disabled = false;
            uploadInvoiceButton.innerHTML = '<i class="fas fa-cloud-upload-alt"></i> Upload & Merge Invoice Parts';
            if (!invoiceFileInput.files[0]) uploadInvoiceButton.disabled = true;

            setTimeout(() => {
                if (!invoiceStatusDiv.classList.contains('status-processing')) {
                    invoiceStatusDiv.classList.add('hidden');
                }
            }, 5000);
        }
    }

    function updatePage3TaxDisplay() {
        if (!assessmentLabourTaxTypeDropdown || !page3CgstRowDisplay || !page3SgstRowDisplay || !page3IgstRowDisplay) return;
        const selectedTaxType = assessmentLabourTaxTypeDropdown.value;
        const applyGst = document.getElementById('page3-apply-gst') ? document.getElementById('page3-apply-gst').checked : true;

        if (!applyGst) {
            page3CgstRowDisplay.classList.add('hidden');
            page3SgstRowDisplay.classList.add('hidden');
            page3IgstRowDisplay.classList.add('hidden');
        } else if (selectedTaxType === 'IGST') {
            page3CgstRowDisplay.classList.add('hidden');
            page3SgstRowDisplay.classList.add('hidden');
            page3IgstRowDisplay.classList.remove('hidden');
        } else {
            page3CgstRowDisplay.classList.remove('hidden');
            page3SgstRowDisplay.classList.remove('hidden');
            page3IgstRowDisplay.classList.add('hidden');
        }
    }

    function simpleNumberToWordsForUI(num) {
        if (isNaN(num) || num === null) return "Invalid Amount";
        if (num === 0) return "Zero";
        return `Approx. ${formatCurrency(num)}`;
    }

    function recalculatePage3Totals() {
        if (!currentAssessmentData || !page3PhotoCopiesCountInput || !page3SubtotalDisplay) return;

        updatePage3TaxDisplay();

        const photoCopiesCount = parseInt(page3PhotoCopiesCountInput.value) || 0;
        const photoCharges = photoCopiesCount * 10.0;
        if (page3PhotoChargesDisplay) page3PhotoChargesDisplay.value = formatCurrency(photoCharges);

        let feesSubtotal = 0;
        if (page3FeeItemsTbody) {
            page3FeeItemsTbody.querySelectorAll('tr').forEach(row => {
                const amountInput = row.querySelector('input[name="page3_fee_amount"]');
                feesSubtotal += parseFormattedNumber(amountInput?.value);
            });
        }

        const totalBeforeGst = feesSubtotal + photoCharges;
        page3SubtotalDisplay.value = formatCurrency(totalBeforeGst);

        let p3Cgst = 0, p3Sgst = 0, p3Igst = 0;
        const selectedTaxType = assessmentLabourTaxTypeDropdown.value;
        const applyGst = document.getElementById('page3-apply-gst') ? document.getElementById('page3-apply-gst').checked : true;

        if (applyGst) {
            if (selectedTaxType === 'IGST') {
                p3Igst = totalBeforeGst * 0.18;
            } else {
                p3Cgst = totalBeforeGst * 0.09;
                p3Sgst = totalBeforeGst * 0.09;
            }
        }

        if (page3CgstDisplay) page3CgstDisplay.value = formatCurrency(p3Cgst);
        if (page3SgstDisplay) page3SgstDisplay.value = formatCurrency(p3Sgst);
        if (page3IgstDisplay) page3IgstDisplay.value = formatCurrency(p3Igst);

        const grandTotalPage3 = totalBeforeGst + p3Cgst + p3Sgst + p3Igst;
        if (page3GrandTotalDisplay) page3GrandTotalDisplay.value = formatCurrency(grandTotalPage3);
        if (page3GrandTotalWordsDisplay) page3GrandTotalWordsDisplay.value = simpleNumberToWordsForUI(grandTotalPage3);

        currentAssessmentData.page3_details_calculated = {
            photo_charges: photoCharges,
            fees_subtotal: feesSubtotal,
            total_before_gst: totalBeforeGst,
            cgst: p3Cgst,
            sgst: p3Sgst,
            igst: p3Igst,
            grand_total: grandTotalPage3
        };
    }

    function mergeInvoiceParts(invoiceParts) {
        if (!currentAssessmentData) {
            console.error("Cannot merge parts, current assessment data is missing.");
            currentAssessmentData = { parts: [] };
        }
        if (!currentAssessmentData.parts) {
            currentAssessmentData.parts = [];
        }
        if (!Array.isArray(invoiceParts)) {
            console.error("Invoice parts data is not an array.");
            return;
        }

        console.log("Starting merge (always append). Existing parts before merge:", JSON.parse(JSON.stringify(currentAssessmentData.parts)));
        console.log("Invoice parts to append:", invoiceParts);

        const oldMasterList = currentAssessmentData.parts || [];
        const newMasterList = [];

        oldMasterList.forEach(existingPart => {
            newMasterList.push(existingPart);
        });

        invoiceParts.forEach(invoicePart => {
            const invoicePartName = String(invoicePart.part_name).trim();
            const gstPc = parseFloat(invoicePart.gst_pc);
            const gstApplicable = !isNaN(gstPc) && gstPc > 0;
            const qty = parseFormattedNumber(invoicePart.qty);
            const partAmt = parseFormattedNumber(invoicePart.part_amt);

            const newPartEntry = {
                sl_no: 0,
                est_sl_no: '', // Will be set during re-sequencing
                bill_sl_no: '', // Will be set during re-sequencing
                part_name: invoicePartName,
                type_part: '',
                qty: qty,
                part_amt: partAmt,
                gst_applicable: gstApplicable,
                original_gst_pc: !isNaN(gstPc) ? gstPc : 0,
                total_parts_amt: 0,
                total_gst: 0,
                gross_amt: 0,
                depr: null,
                net_amt: 0
            };
            newMasterList.push(newPartEntry);
            console.log(`Appending new part from invoice: "${invoicePartName}"`);
        });

        currentAssessmentData.parts = newMasterList;

        partsDetailsTbody.innerHTML = '';
        currentAssessmentData.parts.forEach((part, index) => {
            part.sl_no = index + 1;
            addPartRowToTable(part);
        });

        recalculateAll();

        console.log("Merge complete (always append). Final parts state:", JSON.parse(JSON.stringify(currentAssessmentData.parts)));
    }

    // --- Global Photo Storage ---
    const uploadedPhotos = {
        first_inspection: [],
        dismantling: [],
        reinspection: []
    };

    function renderPhotos(category) {
        const containerId = `photos-preview-${category === 'first_inspection' ? 'first' : category}`;
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = ''; // Clear current view

        uploadedPhotos[category].forEach((photoData, index) => {
            const photoItem = document.createElement('div');
            photoItem.className = 'photo-item';

            const img = document.createElement('img');
            img.src = photoData;

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'photo-delete-btn';
            deleteBtn.innerHTML = '<i class="fas fa-times"></i>';
            deleteBtn.type = 'button';
            deleteBtn.onclick = () => deletePhoto(category, index);

            photoItem.appendChild(img);
            photoItem.appendChild(deleteBtn);
            container.appendChild(photoItem);
        });
    }

    function deletePhoto(category, index) {
        uploadedPhotos[category].splice(index, 1);
        renderPhotos(category);
        // Reset file input value so the same file can be selected again if needed
        const inputId = `photos-input-${category === 'first_inspection' ? 'first' : category}`;
        const input = document.getElementById(inputId);
        if (input) input.value = '';
    }

    function compressImage(file, maxWidth = 800, quality = 0.5) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = event => {
                const img = new Image();
                img.src = event.target.result;
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    let width = img.width;
                    let height = img.height;

                    if (width > maxWidth) {
                        height = Math.round(height * maxWidth / width);
                        width = maxWidth;
                    }

                    canvas.width = width;
                    canvas.height = height;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, width, height);
                    // Return both base64 (for local preview) and blob (for upload)
                    const base64 = canvas.toDataURL('image/jpeg', quality);
                    canvas.toBlob((blob) => {
                        resolve({ base64, blob });
                    }, 'image/jpeg', quality);
                };
                img.onerror = error => reject(error);
            };
            reader.onerror = error => reject(error);
        });
    }

    async function uploadPhotoToServer(blob, filename) {
        /**
         * Upload a compressed photo to the server via /upload_photo.
         * Returns the proxy URL (e.g., /proxy_image/<id>) on success.
         */
        const formData = new FormData();
        formData.append('photo', blob, filename || 'photo.jpg');
        const response = await fetch('/upload_photo', { method: 'POST', body: formData });
        if (!response.ok) {
            let errMsg = `Upload failed: ${response.status} ${response.statusText}`;
            try {
                const errData = await response.json();
                if (errData && errData.error) errMsg = errData.error;
            } catch (e) {}
            throw new Error(errMsg);
        }
        const result = await response.json();
        if (result.success && result.url) return result.url;
        throw new Error(result.error || 'Upload returned no URL');
    }

    function handlePhotoSelection(event, category) {
        const files = event.target.files;
        if (files.length > 0) {
            showStatus(`Uploading ${files.length} photo(s)...`, 'processing');

            const uploadPromises = Array.from(files).map(async (file, index) => {
                try {
                    const { base64, blob } = await compressImage(file);
                    // Upload to server, get proxy URL
                    const proxyUrl = await uploadPhotoToServer(blob, file.name);
                    return { success: true, url: proxyUrl, filename: file.name };
                } catch (uploadErr) {
                    console.error(`Photo upload failed for ${file.name}:`, uploadErr);
                    return { success: false, filename: file.name, error: uploadErr.message || 'Unknown error' };
                }
            });

            Promise.all(uploadPromises).then(results => {
                const successes = results.filter(r => r.success);
                const failures = results.filter(r => !r.success);

                successes.forEach(r => {
                    uploadedPhotos[category].push(r.url);
                });
                renderPhotos(category);

                if (failures.length > 0) {
                    const failedNames = failures.map(f => f.filename).join(', ');
                    showStatus(`Uploaded ${successes.length} photo(s). Failed to upload: ${failedNames}. Check storage quota!`, 'error');
                    alert(`Failed to upload the following photo(s) to Google Drive:\n${failedNames}\n\nThis is usually caused by the Google Drive storage quota being full. Please contact administrator or run the cleanup script to free up space.`);
                } else {
                    showStatus(`${successes.length} photo(s) uploaded!`, 'success');
                }
            }).catch(err => {
                console.error("Photo processing error:", err);
                showStatus('Error processing photos', 'error');
            });
        }
    }

    // Add listeners for photo inputs
    const photoInputFirst = document.getElementById('photos-input-first');
    const photoInputDismantling = document.getElementById('photos-input-dismantling');
    const photoInputReinspection = document.getElementById('photos-input-reinspection');

    if (photoInputFirst) photoInputFirst.addEventListener('change', (e) => handlePhotoSelection(e, 'first_inspection'));
    if (photoInputDismantling) photoInputDismantling.addEventListener('change', (e) => handlePhotoSelection(e, 'dismantling'));
    if (photoInputReinspection) photoInputReinspection.addEventListener('change', (e) => handlePhotoSelection(e, 'reinspection'));


    // --- Collect Final Data for Backend ---
    function collectFinalData() {
        recalculateAll();

        const surveyData = {};
        const EXPECTED_SURVEY_KEYS = [
            "report_no", "report_date", "policy_no", "claim_no", "policy_validity", "insurer", "insured", "insured_contact_name", "insured_contact_no", "hypothecation", "idv", "policy_type_label", "vehicle_regn_no", "vehicle_regn_date", "vehicle_chassis_no", "vehicle_engine_no", "vehicle_make_model", "vehicle_type_body", "vehicle_cf_validity", "vehicle_seating", "vehicle_bhp_cc", "vehicle_pre_accident_condition", "vehicle_ulw", "vehicle_rlw", "vehicle_permit_no", "vehicle_permit_type", "vehicle_permit_validity", "vehicle_route_area", "vehicle_tax_token", "vehicle_tax_validity", "vehicle_odometer", "vehicle_colour", "class_of_vehicle", "regn_cert_no", "vehicle_cc", "dl_name", "dl_no", "dl_issue_date", "dl_validity", "dl_issuing_authority", "dl_endorsement", "dl_type", "dl_dob", "doc_regn_cert", "doc_dl", "doc_tax_token", "doc_permit_compared", "doc_fitness_certificate", "doc_load_challan", "load_nature_packing", "load_weight_goods", "load_origin_destination", "load_lr_invoice_no", "load_transport_name", "load_date", "accident_datetime", "accident_assign_received", "accident_survey_date", "accident_place", "accident_survey_place", "police_reported_to", "police_diary_case_no", "police_date_reported", "tp_details", "accident_cause", "damages_extent", "remark", "tp_injury_loss", "injury_driver_occupant", "damages_consistent"
        ];
        EXPECTED_SURVEY_KEYS.forEach(key => {
            const inputElement = document.getElementById(`input-${key}`);
            surveyData[key] = inputElement ? inputElement.value.trim() : '';
        });

        const collectedParts = [];
        partsDetailsTbody.querySelectorAll('tr').forEach(row => {
            const slNoInput = row.querySelector('.part-slno-input');
            const estSlNoInput = row.querySelector('.part-est-slno-input');
            const billSlNoInput = row.querySelector('.part-bill-slno-input');
            const nameInput = row.querySelector('.part-name-input');
            const typeSelect = row.querySelector('.part-type-select');
            const gstPcInput = row.querySelector('.part-gst-pc-input');
            const qtyInput = row.querySelector('.part-qty-input');
            const amtInput = row.querySelector('.part-amt-input');
            const deprInput = row.querySelector('.part-depr-input');
            const imtCheckbox = row.querySelector('.part-imt-checkbox');
            const salvageSelect = row.querySelector('.part-salvage-select');
            const remarksSelect = row.querySelector('.part-remarks-select');

            const originalSlNo = slNoInput ? slNoInput.dataset.slNo : null;
            const partDataFromStore = currentAssessmentData?.parts?.find(p => p.sl_no == originalSlNo);

            const slNo = parseInt(slNoInput?.value) || 0;
            const gstPc = parseFloat(gstPcInput?.value || 0);
            const gstApplicable = gstPc > 0;
            const finalDeprAmount = parseFormattedNumber(deprInput?.value || 0);
            const partType = typeSelect?.value || '';
            const hnsInput = row.querySelector('.part-hns-input');
            const estimateInput = row.querySelector('.part-estimate-input');
            const billInput = row.querySelector('.part-bill-input');

            collectedParts.push({
                sl_no: slNo,
                est_sl_no: estSlNoInput?.value.trim() || '',
                bill_sl_no: billSlNoInput?.value.trim() || '',
                part_name: nameInput?.value.trim() || '',
                hns_code: hnsInput?.value.trim() || '',
                estimate_amt: parseFormattedNumber(estimateInput?.value || 0),
                bill_amt: parseFormattedNumber(billInput?.value || 0),
                type_part: partType,
                gst_applicable: gstApplicable,
                original_gst_pc: gstPc,
                qty: parseFormattedNumber(qtyInput?.value || 0),
                part_amt: parseFormattedNumber(amtInput?.value || 0),
                depr: !isNaN(finalDeprAmount) ? finalDeprAmount : -1,
                imt_applied: imtCheckbox ? imtCheckbox.checked : false,
                imt_23_amt: parseFormattedNumber(partDataFromStore?.imt_23_amt || 0),
                salvage_produce: salvageSelect ? salvageSelect.value : 'YES',
                remarks: remarksSelect ? remarksSelect.value : 'REPLACED BY NEW',
                net_amt: parseFormattedNumber(partDataFromStore?.net_amt || 0),
                gross_amt: parseFormattedNumber(partDataFromStore?.gross_amt || 0),
                total_gst: parseFormattedNumber(partDataFromStore?.total_gst || 0),
                total_parts_amt: parseFormattedNumber(partDataFromStore?.total_parts_amt || 0),
            });
        });

        const page3FeeItems = [];
        if (page3FeeItemsTbody) {
            page3FeeItemsTbody.querySelectorAll('tr').forEach(row => {
                const nameInput = row.querySelector('input[name="page3_fee_name"]');
                const amountInput = row.querySelector('input[name="page3_fee_amount"]');
                page3FeeItems.push({
                    name: nameInput?.value.trim() || '',
                    amount: amountInput?.value.trim() || '0'
                });
            });
        }

        const includeInConsolidatedCheckbox = document.getElementById('page3-include-in-consolidated');
        const getVal = (id) => document.getElementById(id)?.value.trim() || '';

        const page3Data = {
            customer_gstin: page3CustomerGstinInput?.value.trim() || '',
            company_gstin: getVal('page3-company-gstin'),
            estimated_amount: document.getElementById('page3-estimated-amount')?.value.trim() || '0',
            photo_copies_count: page3PhotoCopiesCountInput?.value.trim() || '0',
            fee_items: page3FeeItems,
            include_in_consolidated: includeInConsolidatedCheckbox ? includeInConsolidatedCheckbox.checked : false,
            apply_gst: document.getElementById('page3-apply-gst') ? document.getElementById('page3-apply-gst').checked : true,
            surveyor_details: {
                gstin: getVal('surveyor-gstin'),
                pan: getVal('surveyor-pan'),
                bank_name: getVal('surveyor-bank-name'),
                account_no: getVal('surveyor-account-no'),
                micr: getVal('surveyor-micr'),
                ifsc: getVal('surveyor-ifsc'),
                state_code: getVal('surveyor-state-code'),
                surveyor_code: getVal('surveyor-code')
            }
        };

        const collectedUserLabourRows = [];
        labourDetailsTbody.querySelectorAll('tr').forEach(row => {
            const nameInput = row.querySelector('input[name="labour_part_name"]');
            const gstSelect = row.querySelector('select[name="labour_row_gst_pc"]');
            const removingInput = row.querySelector('input[name="labour_removing_refitting"]');
            const dentingInput = row.querySelector('input[name="labour_denting_repairing"]');
            const paintingInput = row.querySelector('input[name="labour_painting"]');
            const totalInput = row.querySelector('input[name="labour_total"]');

            collectedUserLabourRows.push({
                part_name: nameInput?.value.trim() || '',
                labour_row_gst_pc: gstSelect ? parseInt(gstSelect.value) : 0,
                removing_refitting: removingInput?.value.trim() || '0',
                denting_repairing: dentingInput?.value.trim() || '0',
                painting: paintingInput?.value.trim() || '0',
                total: totalInput?.value.trim() || '0'
            });
        });

        const imt23Checkbox = document.getElementById('assessment-labour-imt-23');
        const imposeExcessInput = document.getElementById('assessment-impose-excess');
        // Collect Estimate Overrides
        const estLabourOverride = document.getElementById('assessment-est-labour')?.value.trim();
        const estPaintOverride = document.getElementById('assessment-est-paint')?.value.trim();
        const estPartsOverride = document.getElementById('assessment-est-parts')?.value.trim();

        const assessmentDataForGeneration = {
            header_gst: assessmentHeaderGstInput.value.trim(),
            header_vehicle_year: assessmentHeaderVehicleYearInput.value.trim(),
            policy_type: assessmentPolicyTypeDropdown.value,
            report_type: assessmentReportTypeDropdown.value,
            claim_type: assessmentClaimTypeDropdown.value,
            labour_tax_type: assessmentLabourTaxTypeDropdown.value,
            labour_paint_depn: parseFormattedNumber(assessmentLabourPaintDepnInput.value || 0),
            labour_imt_applied: imt23Checkbox ? imt23Checkbox.checked : false,
            parts: collectedParts,
            deductibles: parseFormattedNumber(assessmentDeductiblesInput.value || 1000),
            impose_excess: parseFormattedNumber(imposeExcessInput?.value || 0),
            nd_deduction_pc: parseFloat(document.getElementById('assessment-nd-deduction-pc')?.value || 5),
            nd_deduction_amount: parseFormattedNumber(document.getElementById('assessment-nd-deduction-amt')?.value || 0),
            towing_charges: parseFormattedNumber(document.getElementById('assessment-towing-charges')?.value || 0),
            salvage: assessmentSalvageInput.value.trim() || '-',
            user_labour_rows: collectedUserLabourRows,
            note_text: document.getElementById('input-note_text')?.value.trim() || '',
            payment_to_text: document.getElementById('input-payment_to_text')?.value.trim() || '',
            reinspection_note: document.getElementById('input-reinspection_note')?.value.trim() || '',
            enclosures_text: document.getElementById('input-enclosures_text')?.value.trim() || '',
            parts_table_note: document.getElementById('input-parts_table_note')?.value.trim() || '',
            est_labour_override: estLabourOverride,
            est_paint_override: estPaintOverride,
            est_parts_override: estPartsOverride,
            spot_report_text: document.getElementById('input-spot_report_text').value.trim(),
            spot_report_enclosures: document.getElementById('input-spot_report_enclosures').value.trim(),
            page3_details: page3Data,
            net_liability: currentAssessmentData.net_liability
        };

        // Collect Photos Data
        const photosData = {
            first_inspection: {
                images: uploadedPhotos.first_inspection,
                per_page: document.getElementById('photos-layout-first')?.value || 4
            },
            dismantling: {
                images: uploadedPhotos.dismantling,
                per_page: document.getElementById('photos-layout-dismantling')?.value || 4
            },
            reinspection: {
                images: uploadedPhotos.reinspection,
                per_page: document.getElementById('photos-layout-reinspection')?.value || 4
            }
        };

        return {
            survey_report: surveyData,
            assessment: assessmentDataForGeneration,
            photos: photosData,
            claim_meta: currentClaimMeta,
            include_signature: document.getElementById('include-signature-checkbox') ? document.getElementById('include-signature-checkbox').checked : true
        };
    }

    function blobToBase64(blob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(blob);
            reader.onload = () => {
                const result = reader.result;
                resolve(result.split(',')[1]); // Remove data URL prefix
            };
            reader.onerror = error => reject(error);
        });
    }

    // --- Process PDF ---
    processButton.addEventListener('click', async () => {
        const file = pdfFileInput.files[0];
        if (!file) { showStatus('Please select a PDF file first.', 'error'); return; }

        showStatus('Uploading and processing PDF securely...', 'processing');
        processButton.disabled = true; processButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        uploadProgressContainer.classList.remove('hidden'); uploadProgress.style.width = `0%`;

        let progressValue = 0;
        const progressInterval = setInterval(() => {
            progressValue += Math.random() * 15; progressValue = Math.min(progressValue, 95);
            uploadProgress.style.width = `${progressValue}%`;
            if (progressValue >= 95) clearInterval(progressInterval);
        }, 300);

        let responseData = null;

        try {
            const formData = new FormData();
            formData.append('pdf_file', file);
            const response = await fetch('/process_pdf', { method: 'POST', body: formData });

            if (!response.ok) {
                let errorMsg = `Server error: ${response.status} ${response.statusText}`;
                try { const errorData = await response.json(); errorMsg = errorData.error || errorMsg; } catch (e) { }
                throw new Error(errorMsg);
            }
            const submitResult = await response.json();
            const taskId = submitResult.task_id;
            if (!taskId) throw new Error('No task_id received from server');

            // Poll for completion
            showStatus('AI is analyzing document... This may take a minute.', 'processing');
            while (true) {
                await new Promise(resolve => setTimeout(resolve, 3000)); // Poll every 3 seconds
                const statusRes = await fetch(`/process_pdf/status/${taskId}`);
                if (!statusRes.ok) throw new Error(`Status check failed: ${statusRes.status}`);
                const statusData = await statusRes.json();

                if (statusData.status === 'completed') {
                    responseData = statusData.result;
                    break;
                } else if (statusData.status === 'error') {
                    throw new Error(statusData.error || 'AI processing failed');
                }
                // else still processing, continue polling
            }

            clearInterval(progressInterval); uploadProgress.style.width = '100%';
            await new Promise(resolve => setTimeout(resolve, 300));
            uploadProgressContainer.classList.add('hidden');

            try {
                displayPreview(responseData);
            } catch (displayError) {
                console.error('Error occurred *inside* displayPreview:', displayError);
                showStatus(`Error displaying preview: ${displayError.message}. Check console.`, 'error');
                uploadSection.classList.remove('hidden'); previewSection.classList.add('hidden'); updateSteps('upload');
            }
        } catch (error) {
            console.error('Error processing PDF:', error);
            clearInterval(progressInterval); uploadProgressContainer.classList.add('hidden');
            showStatus(`Error processing PDF: ${error.message}. Check console.`, 'error');
            uploadSection.classList.remove('hidden'); previewSection.classList.add('hidden'); updateSteps('upload');
        } finally {
            processButton.disabled = false; processButton.innerHTML = '<i class="fas fa-cogs"></i> Process PDF';
            if (!pdfFileInput.files[0]) processButton.disabled = true;
        }
    });

    // --- Generate Files ---
    generateButton.addEventListener('click', async () => {
        showStatus('Confirming data and generating files...', 'processing');
        generateButton.disabled = true; generateButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
        saveProgressButton.disabled = true;

        const finalDataToSend = collectFinalData();

        try {
            const response = await fetch('/generate_files', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(finalDataToSend)
            });
            if (!response.ok) {
                let errorMsg = `Server error: ${response.status} ${response.statusText}`;
                try { const errorData = await response.json(); errorMsg = errorData.error || errorMsg; } catch (e) { }
                throw new Error(errorMsg);
            }
            const submitResult = await response.json();
            const taskId = submitResult.task_id;
            if (!taskId) throw new Error('No task_id received from server');

            // Poll for completion
            showStatus('Generating PDF report... This may take a moment.', 'processing');
            let result = null;
            while (true) {
                await new Promise(resolve => setTimeout(resolve, 3000));
                const statusRes = await fetch(`/generate_files/status/${taskId}`);
                if (!statusRes.ok) throw new Error(`Status check failed: ${statusRes.status}`);
                const statusData = await statusRes.json();

                if (statusData.status === 'completed') {
                    result = statusData.result;
                    break;
                } else if (statusData.status === 'error') {
                    throw new Error(statusData.error || 'File generation failed');
                }
            }

            const reportNo = finalDataToSend.survey_report['report_no'] || 'SurveyReport';
            displayDownloadLinks(result.request_id, reportNo, result.drive_link);
        } catch (error) {
            console.error('Generation error:', error);
            showStatus(`Error generating files: ${error.message}`, 'error');
        } finally {
            generateButton.disabled = false; generateButton.innerHTML = '<i class="fas fa-file-export"></i> Generate Files';
            saveProgressButton.disabled = false;
        }
    });

    // --- Save Progress ---
    saveProgressButton.addEventListener('click', async () => {
        const reportNoInput = document.getElementById('input-report_no');
        if (!reportNoInput || !reportNoInput.value.trim()) {
            showStatus('Please enter a Report Number before saving.', 'error', true);
            reportNoInput.focus();
            return;
        }

        // Debounce: Prevent double clicks
        if (saveProgressButton.disabled) return;

        showStatus('Saving report data...', 'processing', true);
        saveProgressButton.disabled = true; saveProgressButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        generateButton.disabled = true;

        const finalDataToSend = collectFinalData();
        // Attach the current DB UUID so the backend knows which row to UPDATE.
        // If null, the backend will INSERT a fresh row.
        if (currentDbReportId) {
            finalDataToSend._current_report_id = currentDbReportId;
        }

        try {
            const response = await fetch('/save_report', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(finalDataToSend)
            });
            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || `Server error: ${response.status}`);
            }
            // Update our local UUID with what the server confirmed/created.
            // This ensures that the very first save of a new report also correctly tracks the ID.
            if (result.report_id) {
                currentDbReportId = result.report_id;
            }
            showStatus(result.message || 'Report saved successfully!', 'success', true);
            fetchSavedReports();
        } catch (error) {
            console.error('Save error:', error);
            showStatus(`Error saving report: ${error.message}`, 'error', true);
        } finally {
            saveProgressButton.disabled = false; saveProgressButton.innerHTML = '<i class="fas fa-save"></i> Save Progress';
            generateButton.disabled = false;
        }
    });


    // --- Display Download Links ---
    function displayDownloadLinks(requestId, reportNoBase, driveLink) {
        downloadLinksDiv.innerHTML = '';

        const pdfLink = document.createElement('a');
        pdfLink.href = `/download/report_pdf/${requestId}`;
        pdfLink.className = `btn btn-primary`;
        pdfLink.innerHTML = `<i class="fas fa-file-pdf"></i> Download PDF Report`;
        pdfLink.target = '_blank';
        downloadLinksDiv.appendChild(pdfLink);

        // Drive auto-upload status — only show when link actually exists
        if (driveLink) {
            const driveStatus = document.createElement('span');
            driveStatus.style.marginLeft = '10px';
            driveStatus.style.display = 'inline-flex';
            driveStatus.style.alignItems = 'center';
            driveStatus.style.gap = '5px';
            driveStatus.innerHTML = `<i class="fas fa-check-circle" style="color: #22c55e;"></i> <a href="${driveLink}" target="_blank" style="color: #22c55e;">Saved to Drive</a>`;
            downloadLinksDiv.appendChild(driveStatus);
        }

        previewSection.classList.add('hidden');
        downloadSection.classList.remove('hidden');
        updateSteps('download');
        showStatus('Files generated successfully!', 'success');
    }

    // --- Navigation Buttons ---
    backToUploadButton.addEventListener('click', () => {
        previewSection.classList.add('hidden');
        uploadSection.classList.remove('hidden');
        updateSteps('upload');
        fetchSavedReports();
    });

    startNewButton.addEventListener('click', () => {
        previewForm.reset();

        uploadedPhotos.first_inspection = [];
        uploadedPhotos.dismantling = [];
        uploadedPhotos.reinspection = [];
        renderPhotos('first_inspection');
        renderPhotos('dismantling');
        renderPhotos('reinspection');

        pdfFileInput.value = '';
        selectedFileName.textContent = '';
        pdfDropzone.classList.remove('active');
        processButton.disabled = true;
        downloadSection.classList.add('hidden');
        uploadSection.classList.remove('hidden');
        updateSteps('upload');
        hideStatus();
        fetchSavedReports();
        currentReportId = null;
        currentDbReportId = null; // Clear UUID tracking - next save will INSERT a new row
    });

    // --- Saved Reports Functionality ---
    const reportSearchInput = document.getElementById('report-search-input');
    const reportSearchBtn = document.getElementById('report-search-btn');
    const reportSearchReset = document.getElementById('report-search-reset');

    if (reportSearchBtn) {
        reportSearchBtn.addEventListener('click', () => fetchSavedReports(reportSearchInput.value));
    }
    if (reportSearchReset) {
        reportSearchReset.addEventListener('click', () => {
            reportSearchInput.value = '';
            fetchSavedReports();
        });
    }

    async function fetchSavedReports(query = '') {
        savedReportsTbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 1rem;"><i class="fas fa-spinner fa-spin"></i> Loading...</td></tr>';
        loadingSpinner.classList.remove('hidden');
        try {
            const url = query ? `/get_saved_reports?q=${encodeURIComponent(query)}` : '/get_saved_reports';
            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to fetch reports');
            const reports = await response.json();
            renderSavedReports(reports);
        } catch (error) {
            console.error("Error fetching saved reports:", error);
            savedReportsTbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--danger); padding: 1rem;">Could not load saved reports.</td></tr>';
        } finally {
            loadingSpinner.classList.add('hidden');
        }
    }

    function renderSavedReports(reportsData) {
        const reports = Array.isArray(reportsData) ? reportsData : (reportsData && Array.isArray(reportsData.items) ? reportsData.items : []);
        savedReportsTbody.innerHTML = '';
        if (reports.length === 0) {
            savedReportsTbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 1rem; color: var(--text-muted);">No saved reports found.</td></tr>';
            return;
        }
        reports.forEach(report => {
            const row = savedReportsTbody.insertRow();
            [report.report_no, report.vehicle_no, report.insured_name, report.saved_at].forEach(value => {
                const cell = row.insertCell();
                cell.textContent = value || 'N/A';
            });
            const actionCell = row.insertCell();
            actionCell.className = 'action-cell';
            const createActionButton = (className, iconClass, label) => {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = className;
                button.dataset.reportId = String(report.id || '');
                const icon = document.createElement('i');
                icon.className = `fas ${iconClass}`;
                button.append(icon, document.createTextNode(` ${label}`));
                return button;
            };
            const loadButton = createActionButton('btn btn-primary btn-sm load-report-btn', 'fa-folder-open', 'Load');
            const deleteButton = createActionButton('btn btn-danger btn-sm delete-report-btn', 'fa-trash-alt', 'Delete');
            deleteButton.dataset.reportNo = String(report.report_no || '');
            actionCell.append(loadButton, deleteButton);
        });
        addSavedReportActionListeners();
    }

    function addSavedReportActionListeners() {
        savedReportsTbody.querySelectorAll('.load-report-btn').forEach(button => {
            button.addEventListener('click', handleLoadReport);
        });
        savedReportsTbody.querySelectorAll('.delete-report-btn').forEach(button => {
            button.addEventListener('click', handleDeleteReport);
        });
    }

    async function handleLoadReport(event) {
        const button = event.currentTarget;
        const reportId = button.dataset.reportId; // This IS the Postgres UUID
        showStatus('Loading report data...', 'processing');
        button.disabled = true; button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        try {
            const response = await fetch(`/load_report/${reportId}`);
            if (!response.ok) {
                let errorMsg = `Error ${response.status}`;
                try { const errData = await response.json(); errorMsg = errData.error || errorMsg; } catch (e) { }
                throw new Error(errorMsg);
            }
            const reportData = await response.json();
            // Pass reportId as BOTH the display ID and the DB UUID for safe updates
            displayPreview(reportData, reportId, reportId);
        } catch (error) {
            console.error("Error loading report:", error);
            showStatus(`Failed to load report: ${error.message}`, 'error', true);
            button.disabled = false; button.innerHTML = '<i class="fas fa-folder-open"></i> Load';
        }
    }

    async function handleDeleteReport(event) {
        const button = event.currentTarget;
        const reportId = button.dataset.reportId;
        const reportNo = button.dataset.reportNo || 'this report';

        // Secure Deletion: Prompt for password
        const password = prompt(`Enter your login password to delete report "${reportNo}":`);
        if (password === null) return; // User cancelled
        if (!password) {
            alert("Password is required to delete.");
            return;
        }

        showStatus('Deleting report...', 'processing', true);
        button.disabled = true; button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        const loadButton = button.closest('tr')?.querySelector('.load-report-btn');
        if (loadButton) loadButton.disabled = true;

        try {
            const response = await fetch(`/delete_report/${reportId}`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: password })
            });
            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || `Server error: ${response.status}`);
            }
            showStatus(result.message || 'Report deleted successfully.', 'success', true);
            button.closest('tr')?.remove();
            if (savedReportsTbody.rows.length === 0) {
                savedReportsTbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 1rem; color: var(--text-muted);">No saved reports found.</td></tr>';
            }

        } catch (error) {
            console.error("Error deleting report:", error);
            showStatus(`Failed to delete report: ${error.message}`, 'error', true);
            button.disabled = false; button.innerHTML = '<i class="fas fa-trash-alt"></i> Delete';
            if (loadButton) loadButton.disabled = false;
        }
    }

    async function handleConsolidatedCsvDownload() {
        const fromDate = consolidatedCsvDateFromInput.value;
        const toDate = consolidatedCsvDateToInput.value;

        if (!fromDate || !toDate) {
            showStatus('Please select both a "From" and "To" date.', 'error', true);
            return;
        }
        if (new Date(fromDate) > new Date(toDate)) {
            showStatus('"From" date cannot be after "To" date.', 'error', true);
            return;
        }

        showStatus('Generating consolidated CSV report...', 'processing', true);
        downloadConsolidatedCsvButton.disabled = true;
        downloadConsolidatedCsvButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';

        try {
            const response = await fetch(`/download_consolidated_csv?from_date=${fromDate}&to_date=${toDate}`);
            if (!response.ok) {
                let errorMsg = `Server error: ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMsg = errorData.error || errorMsg;
                } catch (e) {
                    const textError = await response.text();
                    errorMsg = textError || errorMsg;
                }
                throw new Error(errorMsg);
            }

            const blob = await response.blob();
            const contentDisposition = response.headers.get('content-disposition');
            let filename = "Consolidated_Reports.csv";
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
                if (filenameMatch && filenameMatch.length > 1) {
                    filename = filenameMatch[1];
                }
            }

            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(link.href);

            showStatus('Consolidated CSV downloaded successfully!', 'success', true);

        } catch (error) {
            console.error('Error downloading consolidated CSV:', error);
            showStatus(`Error downloading CSV: ${error.message}`, 'error', true);
        } finally {
            downloadConsolidatedCsvButton.disabled = false;
            downloadConsolidatedCsvButton.innerHTML = '<i class="fas fa-file-csv"></i> Download Consolidated CSV';
        }
    }

    // --- Motor Survey Management Workspace ---
    const workspaceState = { profile: null, claims: [], claimsPage: 1, claimsPageSize: 25, claimsTotal: 0 };
    const claimStatusLabels = {
        new_appointment: 'New appointment', inspection_pending: 'Inspection pending',
        documents_awaited: 'Documents awaited', report_under_preparation: 'Report under preparation',
        report_submitted: 'Report submitted', closed: 'Closed'
    };

    function escapeHtml(value) {
        return String(value ?? '').replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
    }

    function formatMoney(value) {
        return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(Number(value || 0));
    }

    function switchWorkspaceView(viewName) {
        const dashboardSec = document.getElementById('operations-workspace');
        const claimsSec = document.getElementById('claim-register-section');
        const feesSec = document.getElementById('fee-register-section');
        const activeNav = document.getElementById('workspace-active-nav');
        if (!dashboardSec || !claimsSec || !feesSec) return;

        // Hide all workspace detail cards first
        dashboardSec.classList.add('hidden');
        claimsSec.classList.add('hidden');
        feesSec.classList.add('hidden');

        // Unhide the top workspace active navigation bar
        activeNav?.classList.remove('hidden');

        // Update tab buttons state
        const tabDash = document.getElementById('tab-btn-dashboard');
        const tabClaims = document.getElementById('tab-btn-claims');
        const tabFees = document.getElementById('tab-btn-fees');

        tabDash?.classList.remove('active');
        tabClaims?.classList.remove('active');
        tabFees?.classList.remove('active');

        if (viewName === 'dashboard') {
            dashboardSec.classList.remove('hidden');
            tabDash?.classList.add('active');
        } else if (viewName === 'claims') {
            claimsSec.classList.remove('hidden');
            tabClaims?.classList.add('active');
        } else if (viewName === 'fees') {
            if (workspaceState.profile?.role === 'admin') {
                feesSec.classList.remove('hidden');
                tabFees?.classList.add('active');
            } else {
                claimsSec.classList.remove('hidden');
                tabClaims?.classList.add('active');
            }
        }

        // Scroll smoothly to top of workspace active navigation bar
        activeNav?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    async function initMotorSurveyWorkspace() {
        try {
            const res = await fetch('/get_user_profile');
            if (!res.ok) return;
            workspaceState.profile = await res.json();
            const workspaceId = workspaceState.profile.workspace_admin_id;
            if (!workspaceId) return;

            // Unhide the workspace navigation buttons card directly below upload section
            const navSection = document.getElementById('workspace-nav-section');
            if (navSection) navSection.classList.remove('hidden');

            const label = document.getElementById('workspace-role-label');
            if (label) label.textContent = workspaceState.profile.role === 'admin' ? 'Administrator workspace' : 'Shared operational workspace';
            const isAdmin = workspaceState.profile.role === 'admin';

            // Show admin-only navigation buttons if admin
            document.querySelectorAll('.admin-only-nav').forEach(el => {
                if (isAdmin) el.classList.remove('hidden');
                else el.classList.add('hidden');
            });

            if (isAdmin) {
                document.getElementById('financial-export-section')?.classList.remove('hidden');
                document.getElementById('page3-details-wrapper')?.classList.remove('hidden');
            } else {
                document.getElementById('financial-export-section')?.classList.add('hidden');
                document.getElementById('page3-details-wrapper')?.classList.add('hidden');
            }

            // Bind workspace navigation buttons below upload section
            document.getElementById('open-dashboard-btn')?.addEventListener('click', () => switchWorkspaceView('dashboard'));
            document.getElementById('open-claims-btn')?.addEventListener('click', () => switchWorkspaceView('claims'));
            document.getElementById('open-fees-btn')?.addEventListener('click', () => switchWorkspaceView('fees'));

            // Bind active workspace header tabs & back button
            document.getElementById('tab-btn-dashboard')?.addEventListener('click', () => switchWorkspaceView('dashboard'));
            document.getElementById('tab-btn-claims')?.addEventListener('click', () => switchWorkspaceView('claims'));
            document.getElementById('tab-btn-fees')?.addEventListener('click', () => switchWorkspaceView('fees'));

            document.getElementById('btn-back-to-upload')?.addEventListener('click', () => {
                document.getElementById('workspace-active-nav')?.classList.add('hidden');
                document.getElementById('operations-workspace')?.classList.add('hidden');
                document.getElementById('claim-register-section')?.classList.add('hidden');
                document.getElementById('fee-register-section')?.classList.add('hidden');
                document.getElementById('upload-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });

            await Promise.all([fetchDashboard(), fetchClaims(), initGmailControls(), workspaceState.profile.role === 'admin' ? fetchFees() : Promise.resolve()]);
            checkPending7DayAlerts();
        } catch (error) {
            console.error('Could not initialize motor survey workspace:', error);
        }
    }

    async function fetchDashboard() {
        const range = document.getElementById('dashboard-range-select')?.value || '1m';
        const res = await fetch(`/api/dashboard?range=${encodeURIComponent(range)}`);
        if (!res.ok) return;
        const data = await res.json();
        const operational = [
            ['Total claims', data.total_claims, ''],
            ['Pending claims', data.pending_claims, ''],
            ['Completed claims', data.completed_claims, 'report_submitted'],
            ['New appointment', data.new_appointment, 'new_appointment'],
            ['Inspection pending', data.inspection_pending, 'inspection_pending'],
            ['Documents awaited', data.documents_awaited, 'documents_awaited'],
            ['Report under preparation', data.report_under_preparation, 'report_under_preparation'],
            ['Submitted', data.report_submitted, 'report_submitted'],
            ['Closed', data.closed, 'closed']
        ];
        const cards = document.getElementById('dashboard-cards');
        if (cards) {
            cards.innerHTML = operational.map(([label, value, statusKey]) => 
                `<div class="metric-card clickable-metric" data-status-key="${escapeHtml(statusKey)}" style="cursor: pointer;" title="Click to view ${escapeHtml(label)} in Claim Register">
                    <span class="metric-label">${escapeHtml(label)}</span>
                    <span class="metric-value">${Number(value || 0)}</span>
                </div>`
            ).join('');

            cards.querySelectorAll('.clickable-metric').forEach(card => {
                card.addEventListener('click', () => {
                    const statusKey = card.getAttribute('data-status-key');
                    const tabBtn = document.getElementById('tab-btn-claims');
                    if (tabBtn) tabBtn.click();
                    const statusFilter = document.getElementById('claim-status-filter');
                    if (statusFilter) {
                        statusFilter.value = statusKey || '';
                        fetchClaims();
                    }
                });
            });
        }
        const financial = document.getElementById('financial-dashboard');
        if (financial && workspaceState.profile?.role === 'admin') {
            financial.classList.remove('hidden');
            financial.innerHTML = [
                ['Total invoiced', formatMoney(data.total_invoiced)], ['Cash received', formatMoney(data.amount_received)],
                ['Outstanding fees', formatMoney(data.outstanding_fees)], ['Overdue invoices', Number(data.overdue_count || 0)]
            ].map(([label, value]) => `<div class="metric-card financial"><span class="metric-label">${escapeHtml(label)}</span><span class="metric-value">${escapeHtml(value)}</span></div>`).join('');
        }
    }

    async function checkPending7DayAlerts() {
        try {
            const res = await fetch('/api/claims/pending_alerts');
            if (!res.ok) return;
            const data = await res.json();
            const count = data.pending_7day_count || 0;
            if (count > 0) {
                const countNum = document.getElementById('pending-7day-count-num');
                if (countNum) countNum.textContent = count;
                const modal = document.getElementById('pending-7day-alert-modal');
                if (modal) modal.classList.remove('hidden');
            }
        } catch (err) {
            console.error('Failed to check pending 7-day alerts:', err);
        }
    }

    function updateFeeCalculations() {
        const km = parseFloat(document.getElementById('fee-convenience-km')?.value || 0);
        const rate = parseFloat(document.getElementById('fee-convenience-rate')?.value || 0);
        const conveyanceInput = document.getElementById('fee-conveyance');
        if (conveyanceInput && !conveyanceInput.dataset.userEdited) {
            conveyanceInput.value = (km * rate).toFixed(2);
        }
    }

    document.getElementById('dashboard-range-select')?.addEventListener('change', () => {
        fetchDashboard();
    });


    let globalInsurerMasters = [];

    async function loadInsurerMasters() {
        try {
            const res = await fetch('/api/insurers');
            if (!res.ok) return;
            const data = await res.json();
            globalInsurerMasters = data.insurers || [];

            const feeSelect = document.getElementById('fee-insurer-master-select');
            const claimSelect = document.getElementById('claim-input-insurer-select');
            const optionsHtml = '<option value="">Select Insurer Master...</option>' +
                globalInsurerMasters.map(i => `<option value="${i.id}">${escapeHtml(i.insurer_name)} ${i.branch_name ? '(' + escapeHtml(i.branch_name) + ')' : ''}</option>`).join('');

            if (feeSelect) feeSelect.innerHTML = optionsHtml;
            if (claimSelect) claimSelect.innerHTML = optionsHtml;

            const tbody = document.getElementById('insurer-master-tbody');
            if (tbody) {
                if (!globalInsurerMasters.length) {
                    tbody.innerHTML = '<tr><td colspan="6">No Insurer Masters added yet.</td></tr>';
                } else {
                    tbody.innerHTML = globalInsurerMasters.map(i => `
                        <tr>
                            <td><strong>${escapeHtml(i.insurer_name)}</strong></td>
                            <td>${escapeHtml(i.branch_name || '—')}</td>
                            <td><code>${escapeHtml(i.invoice_prefix || '')}</code></td>
                            <td>${escapeHtml(i.gstin || '—')}</td>
                            <td>Rs. ${escapeHtml(i.default_conveyance_rate || 10)}/km</td>
                            <td>
                                <button type="button" class="btn btn-secondary btn-sm edit-im-btn" data-id="${i.id}">Edit</button>
                                <button type="button" class="btn btn-danger btn-sm delete-im-btn" data-id="${i.id}">Delete</button>
                            </td>
                        </tr>
                    `).join('');

                    tbody.querySelectorAll('.edit-im-btn').forEach(btn => btn.addEventListener('click', () => editInsurerMaster(btn.dataset.id)));
                    tbody.querySelectorAll('.delete-im-btn').forEach(btn => btn.addEventListener('click', () => deleteInsurerMaster(btn.dataset.id)));
                }
            }
        } catch (err) {
            console.error('Error loading insurer masters:', err);
        }
    }

    function editInsurerMaster(id) {
        const item = globalInsurerMasters.find(i => String(i.id) === String(id));
        if (!item) return;
        document.getElementById('insurer-master-id').value = item.id;
        document.getElementById('im-insurer-name').value = item.insurer_name || '';
        document.getElementById('im-branch-name').value = item.branch_name || '';
        document.getElementById('im-prefix').value = item.invoice_prefix || '';
        document.getElementById('im-gstin').value = item.gstin || '';
        document.getElementById('im-conveyance-rate').value = item.default_conveyance_rate || 10;
        document.getElementById('im-branch-address').value = item.branch_address || '';
    }

    async function deleteInsurerMaster(id) {
        if (!confirm('Are you sure you want to delete this Insurer Master entry?')) return;
        try {
            const res = await fetch(`/api/insurers/${id}`, { method: 'DELETE' });
            if (res.ok) {
                showStatus('Insurer Master deleted.', 'success', true);
                loadInsurerMasters();
            } else {
                showStatus('Could not delete Insurer Master.', 'error', true);
            }
        } catch (err) { showStatus(err.message, 'error', true); }
    }

    function updateDistanceConveyanceCalc() {
        const mode = document.getElementById('fee-conveyance-calc-mode')?.value || 'flat';
        const distBox = document.getElementById('fee-distance-inputs');
        const conveyanceInput = document.getElementById('fee-conveyance');
        const preview = document.getElementById('fee-dist-calc-preview');

        if (mode === 'distance') {
            if (distBox) distBox.style.display = 'block';
            const onewayKm = parseFloat(document.getElementById('fee-dist-oneway-km')?.value || 0);
            const ratePerKm = parseFloat(document.getElementById('fee-dist-rate-per-km')?.value || 10);
            const visits = parseInt(document.getElementById('fee-dist-visits')?.value || 1, 10);

            const totalConveyance = onewayKm * 2 * ratePerKm * visits;
            if (preview) preview.textContent = `Formula: ${onewayKm}km × 2 × Rs.${ratePerKm} × ${visits} visit(s) = Rs. ${totalConveyance.toFixed(2)}`;
            if (conveyanceInput) conveyanceInput.value = totalConveyance.toFixed(2);
        } else {
            if (distBox) distBox.style.display = 'none';
        }
    }

    function claimFilterQuery() {
        const pairs = new URLSearchParams();
        const mappings = [['q', 'claim-search-input'], ['status', 'claim-status-filter'], ['month', 'claim-month-filter'], ['insurer', 'claim-insurer-filter']];
        mappings.forEach(([key, id]) => {
            const value = document.getElementById(id)?.value.trim();
            if (value) pairs.set(key, value);
        });
        return pairs.toString();
    }

    async function fetchClaims() {
        const tbody = document.getElementById('claim-register-tbody');
        if (!tbody) return;
        tbody.innerHTML = '<tr><td colspan="7"><i class="fas fa-spinner fa-spin"></i> Loading claim register…</td></tr>';
        try {
            const query = new URLSearchParams(claimFilterQuery());
            query.set('page', String(workspaceState.claimsPage));
            query.set('page_size', String(workspaceState.claimsPageSize));
            const res = await fetch(`/api/claims?${query.toString()}`);
            if (!res.ok) throw new Error('Could not load claims');
            const data = await res.json();
            workspaceState.claims = data.items || [];
            workspaceState.claimsPage = Number(data.page || workspaceState.claimsPage);
            workspaceState.claimsPageSize = Number(data.page_size || workspaceState.claimsPageSize);
            workspaceState.claimsTotal = Number(data.total || 0);
            renderClaimRows(workspaceState.claims);
            populateFeeReportOptions();
            updateClaimPagination();
        } catch (error) {
            tbody.innerHTML = '<tr><td colspan="7">Could not load claim register.</td></tr>';
            console.error(error);
        }
    }

    function updateClaimPagination() {
        const totalPages = Math.max(1, Math.ceil(workspaceState.claimsTotal / workspaceState.claimsPageSize));
        const label = document.getElementById('claim-page-label');
        if (label) label.textContent = `Page ${workspaceState.claimsPage} of ${totalPages} (${workspaceState.claimsTotal} claims)`;
        const prev = document.getElementById('claim-page-prev');
        const next = document.getElementById('claim-page-next');
        if (prev) prev.disabled = workspaceState.claimsPage <= 1;
        if (next) next.disabled = workspaceState.claimsPage >= totalPages;
    }

    function renderClaimRows(claims) {
        const tbody = document.getElementById('claim-register-tbody');
        if (!tbody) return;
        if (!claims.length) {
            tbody.innerHTML = '<tr><td colspan="7">No claims found.</td></tr>';
            return;
        }
        tbody.innerHTML = claims.map(claim => {
            const current = claim.status || 'new_appointment';
            const options = Object.entries(claimStatusLabels).map(([value, label]) => `<option value="${value}" ${value === current ? 'selected' : ''}>${escapeHtml(label)}</option>`).join('');
            return `<tr><td>${escapeHtml(claim.claim_no || '—')}</td><td>${escapeHtml(claim.vehicle_no || '—')}</td><td>${escapeHtml(claim.insured_name || '—')}</td><td>${escapeHtml(claim.insurer || '')}</td><td><select class="claim-status-select" data-report-id="${escapeHtml(claim.id)}">${options}</select></td><td>${escapeHtml(claim.survey_type || 'final')}</td><td><button type="button" class="btn btn-primary btn-sm open-workspace-report" data-report-id="${escapeHtml(claim.id)}">Open</button> <button type="button" class="btn btn-secondary btn-sm open-pending-docs-modal" data-report-id="${escapeHtml(claim.id)}"><i class="fas fa-tasks"></i> Docs</button></td></tr>`;
        }).join('');
        tbody.querySelectorAll('.claim-status-select').forEach(select => select.addEventListener('change', async event => {
            const res = await fetch(`/api/claims/${encodeURIComponent(event.target.dataset.reportId)}`, {
                method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: event.target.value })
            });
            if (!res.ok) {
                showStatus('Could not update claim status.', 'error', true);
                fetchClaims();
            } else {
                fetchDashboard();
            }
        }));
        tbody.querySelectorAll('.open-workspace-report').forEach(button => button.addEventListener('click', () => loadWorkspaceReport(button.dataset.reportId)));
        tbody.querySelectorAll('.open-pending-docs-modal').forEach(button => button.addEventListener('click', () => openPendingDocsModal(button.dataset.reportId)));
    }

    function generateReminderTextClient(claim, pendingDocs, reminderCount) {
        const claimNo = claim.claim_no || '[Claim Number]';
        const policyNo = claim.policy_no || '[Policy Number]';
        const insured = claim.insured_name || '[Customer Name]';
        const vehicle = claim.vehicle_no || '[Vehicle Number]';
        const insurer = claim.insurer || '[Insurance Company Name]';

        const docsListStr = pendingDocs.length ? pendingDocs.map((d, i) => `${i + 1}. ${d}`).join('\n') : "1. Policy copy\n2. Duly completed and signed claim form\n3. Repairer's final tax invoice and payment receipt\n4. Clear bank details/cancelled cheque of the insured";

        let text = `Dear Sir/Madam,\n\nThis is regarding the motor insurance claim mentioned below:\n\n`;
        text += `Claim Number: ${claimNo}\n`;
        text += `Policy Number: ${policyNo}\n`;
        text += `Insured Name: ${insured}\n`;
        text += `Vehicle Registration Number: ${vehicle}\n`;
        text += `Insurance Company: ${insurer}\n\n`;
        text += `During the scrutiny of the claim documents, it has been observed that the following documents are still pending:\n\n`;
        text += `${docsListStr}\n\n`;
        text += `You are requested to submit clear and legible copies of the above documents at the earliest so that the survey report and claim assessment process can be completed without further delay.\n\n`;
        text += `Please mention the claim number and vehicle registration number while sending the documents.\n\n`;

        if (reminderCount === 2) {
            text += `Kindly note that this is the second time reminder, so please treat this with high priority; otherwise we assume you are not interested in taking the claim, and the insurance company may close the claim without further notice.\n\n`;
        } else if (reminderCount >= 3) {
            text += `Kindly note that this is the third time reminder, so please treat this with high priority; otherwise we assume you are not interested in taking the claim, and the insurance company may close the claim without further notice.\n\n`;
        } else {
            text += `Kindly note that any delay in submitting the required documents may delay the processing of your claim.\n\n`;
        }

        text += `Regards,\nSk Anowar Ali\nMotor Surveyor & Loss Assessor\nLicence No.: SLA-121784\nMobile: 8777370714`;
        return text;
    }

    let currentPendingDocs = [];

    async function openPendingDocsModal(reportId) {
        const report = workspaceState.claims.find(c => c.id === reportId) || {};
        document.getElementById('pending-docs-report-id').value = reportId;
        document.getElementById('pending-docs-claim-info').textContent = `Claim: ${report.claim_no || '—'} | Vehicle: ${report.vehicle_no || '—'} | Insured: ${report.insured_name || '—'}`;

        try {
            const res = await fetch(`/api/claims/${encodeURIComponent(reportId)}/pending_documents`);
            const data = await res.json();
            currentPendingDocs = data.pending_documents || [];
            const reminderInfo = data.reminder_info || {};
            
            const count = reminder_info.reminder_count || 0;
            const statusText = count > 0 ? `Reminders sent: ${count}/3. Last sent: ${reminderInfo.last_sent_at ? new Date(reminderInfo.last_sent_at).toLocaleDateString() : 'None'}` : 'No reminders sent yet. (Every 7 days, 3 times limit)';
            document.getElementById('pending-docs-reminder-status').textContent = statusText;

            if (reminder_info.claim_manager_email) document.getElementById('claim-manager-email-input').value = reminder_info.claim_manager_email;
            if (reminder_info.claim_manager_phone) document.getElementById('claim-manager-phone-input').value = reminder_info.claim_manager_phone;

            renderPendingDocsList();
            document.getElementById('pending-documents-modal').classList.remove('hidden');
        } catch (err) {
            showStatus('Failed to load pending documents checklist.', 'error', true);
        }
    }

    function renderPendingDocsList() {
        const container = document.getElementById('pending-docs-list-container');
        if (!container) return;
        if (!currentPendingDocs.length) {
            container.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.85rem;">No document items in list. Add custom items below.</p>';
            return;
        }
        container.innerHTML = currentPendingDocs.map((item, index) => {
            const name = typeof item === 'string' ? item : item.name;
            const received = typeof item === 'object' ? !!item.received : false;
            return `
                <div style="display: flex; align-items: center; justify-content: space-between; background: rgba(255,255,255,0.03); padding: 0.4rem 0.6rem; border-radius: 4px; border: 1px solid var(--border-color);">
                    <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer; font-size: 0.9rem;">
                        <input type="checkbox" class="doc-item-checkbox" data-index="${index}" ${received ? 'checked' : ''}>
                        <span style="${received ? 'text-decoration: line-through; opacity: 0.6;' : ''}">${escapeHtml(name)}</span>
                    </label>
                    <button type="button" class="remove-doc-item" data-index="${index}" style="color: var(--danger-color, #ef4444); background: none; border: none; font-size: 1.1rem; cursor: pointer;" title="Remove">&times;</button>
                </div>
            `;
        }).join('');

        container.querySelectorAll('.doc-item-checkbox').forEach(cb => cb.addEventListener('change', (e) => {
            const idx = Number(e.target.dataset.index);
            if (typeof currentPendingDocs[idx] === 'string') {
                currentPendingDocs[idx] = { name: currentPendingDocs[idx], received: e.target.checked };
            } else {
                currentPendingDocs[idx].received = e.target.checked;
            }
            renderPendingDocsList();
        }));

        container.querySelectorAll('.remove-doc-item').forEach(btn => btn.addEventListener('click', (e) => {
            const idx = Number(e.target.dataset.index);
            currentPendingDocs.splice(idx, 1);
            renderPendingDocsList();
        }));
    }

    async function savePendingDocsChecklist() {
        const reportId = document.getElementById('pending-docs-report-id')?.value;
        if (!reportId) return;
        try {
            const res = await fetch(`/api/claims/${encodeURIComponent(reportId)}/pending_documents`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pending_documents: currentPendingDocs })
            });
            if (!res.ok) throw new Error('Could not save checklist.');
            showStatus('Pending documents checklist saved.', 'success', true);
            document.getElementById('pending-documents-modal').classList.add('hidden');
        } catch (err) {
            showStatus(err.message, 'error', true);
        }
    }

    async function sendPendingNotification() {
        const reportId = document.getElementById('pending-docs-report-id')?.value;
        if (!reportId) return;
        const claimManagerEmail = document.getElementById('claim-manager-email-input')?.value.trim();
        const claimManagerPhone = document.getElementById('claim-manager-phone-input')?.value.trim();

        try {
            const res = await fetch(`/api/claims/${encodeURIComponent(reportId)}/send_reminder`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ claim_manager_email: claimManagerEmail, claim_manager_phone: claimManagerPhone })
            });
            const result = await res.json();
            if (!res.ok) throw new Error(result.error || 'Could not send notification.');
            
            showStatus(`Reminder #${result.reminder_count} sent successfully!`, 'success', true);
            
            // Format WhatsApp link if text returned
            if (result.message_text) {
                const encodedMsg = encodeURIComponent(result.message_text);
                const waBtn = document.getElementById('whatsapp-reminder-link');
                if (waBtn) {
                    const phone = claimManagerPhone || '';
                    waBtn.href = `https://api.whatsapp.com/send?text=${encodedMsg}${phone ? `&phone=${phone}` : ''}`;
                    waBtn.classList.remove('hidden');
                }
            }

            openPendingDocsModal(reportId);
        } catch (err) {
            showStatus(err.message, 'error', true);
        }
    }

    async function loadWorkspaceReport(reportId) {
        showStatus('Loading report workspace…', 'processing');
        try {
            const res = await fetch(`/load_report/${encodeURIComponent(reportId)}`);
            if (!res.ok) throw new Error('Report could not be loaded');
            displayPreview(await res.json(), reportId, reportId);
            document.getElementById('preview-section')?.scrollIntoView({ behavior: 'smooth' });
        } catch (error) {
            showStatus(error.message, 'error', true);
        }
    }

    function populateFeeReportOptions() {
        const select = document.getElementById('fee-report-id');
        if (!select) return;
        const selected = select.value;
        select.innerHTML = '<option value="">Linked report (optional)</option>' + workspaceState.claims.map(claim => `<option value="${escapeHtml(claim.id)}">${escapeHtml(claim.report_no || claim.claim_no || claim.id)} — ${escapeHtml(claim.claim_no || '')}</option>`).join('');
        select.value = selected;
    }

    async function createClaim(event) {
        event.preventDefault();
        const payload = {
            claim_no: document.getElementById('claim-input-no')?.value.trim(),
            insured_name: document.getElementById('claim-input-insured')?.value.trim(),
            vehicle_no: document.getElementById('claim-input-vehicle')?.value.trim(),
            policy_no: document.getElementById('claim-input-policy')?.value.trim(),
            insurer: document.getElementById('claim-input-insurer')?.value.trim(),
            date_of_loss: document.getElementById('claim-input-loss-date')?.value,
            survey_type: document.getElementById('claim-input-type')?.value,
            status: document.getElementById('claim-input-status')?.value
        };
        try {
            const res = await fetch('/api/claims', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const result = await res.json();
            if (!res.ok) throw new Error(result.error || 'Could not create claim');
            document.getElementById('new-claim-form')?.reset();
            document.getElementById('new-claim-form')?.classList.add('hidden');
            workspaceState.claimsPage = 1;
            showStatus(`Claim workspace ${result.report_no} created.`, 'success', true);
            await Promise.all([fetchClaims(), fetchDashboard()]);
        } catch (error) { showStatus(error.message, 'error', true); }
    }

    async function fetchFees() {
        const tbody = document.getElementById('fee-register-tbody');
        if (!tbody || workspaceState.profile?.role !== 'admin') return;
        try {
            const month = document.getElementById('fee-month-filter')?.value;
            const res = await fetch(`/api/fee_bills${month ? `?month=${encodeURIComponent(month)}` : ''}`);
            if (!res.ok) throw new Error('Could not load fees');
            const bills = await res.json();
            if (!bills.length) {
                tbody.innerHTML = '<tr><td colspan="12">No fee register rows found.</td></tr>';
                return;
            }
            tbody.innerHTML = bills.map(bill => {
                const insurerDisplay = bill.insurer_gst ? `${escapeHtml(bill.insurer_name || '')}<br><small style="color:#aaa;">GST: ${escapeHtml(bill.insurer_gst)}</small>` : escapeHtml(bill.insurer_name || '—');
                const convFee = bill.conveyance_fee ?? bill.convenience_fee ?? (Number(bill.convenience_km || 0) * Number(bill.convenience_rate || 0));
                const photoAmt = bill.photocopy_amount ?? bill.photocopy ?? 0;
                return `<tr><td>${escapeHtml(bill.invoice_no || '—')}</td><td>${escapeHtml(bill.claim_no || '—')}</td><td><span class="badge badge-outline">${escapeHtml(bill.survey_type || 'Survey Fee')}</span></td><td>${insurerDisplay}</td><td>${formatMoney(bill.professional_fee ?? 0)}</td><td>${formatMoney(convFee)}</td><td>${formatMoney(photoAmt)}</td><td>${formatMoney(bill.gst_amount ?? 0)}</td><td>${formatMoney(bill.gross_invoice_value ?? bill.total_amount ?? 0)}</td><td>${formatMoney(bill.amount_received ?? 0)}</td><td>${formatMoney(bill.outstanding_amount ?? 0)}</td><td>${escapeHtml(bill.payment_status || 'unpaid')}</td></tr>`;
            }).join('');
        } catch (error) { tbody.innerHTML = '<tr><td colspan="12">Could not load fee register.</td></tr>'; }
    }

    async function handleFeePdfUpload(file) {
        if (!file) return;
        const nameSpan = document.getElementById('fee-pdf-file-name');
        if (nameSpan) nameSpan.textContent = file.name;
        showStatus('Extracting billing details from PDF...', 'info', true);
        try {
            const formData = new FormData();
            formData.append('fee_pdf_file', file);
            const res = await fetch('/api/extract_fee_pdf', { method: 'POST', body: formData });
            const result = await res.json();
            if (!res.ok || !result.success) throw new Error(result.error || 'Failed to extract PDF');
            
            const ext = result.extracted || {};
            if (ext.insurer) document.getElementById('fee-insurer').value = ext.insurer;
            if (ext.insured) document.getElementById('fee-insured').value = ext.insured;
            if (ext.invoice_no || ext.report_no) document.getElementById('fee-invoice-no').value = ext.invoice_no || ext.report_no;
            if (ext.invoice_date) document.getElementById('fee-invoice-date').value = ext.invoice_date;
            
            showStatus('Extracted billing details successfully into form!', 'success', true);
        } catch (error) {
            showStatus(error.message || 'Error extracting PDF', 'error', true);
        }
    }

    async function saveFee(event) {
        event.preventDefault();
        const reportId = document.getElementById('fee-report-id')?.value;
        const report = workspaceState.claims.find(item => item.id === reportId) || {};
        const professional = Number(document.getElementById('fee-professional')?.value || 0);
        const convType = document.getElementById('fee-convenience-type')?.value || '1st Convenience';
        const convRoute = document.getElementById('fee-convenience-route')?.value.trim() || '';
        const convKm = Number(document.getElementById('fee-convenience-km')?.value || 0);
        const convRate = Number(document.getElementById('fee-convenience-rate')?.value || 0);
        const conveyanceFee = Number(document.getElementById('fee-conveyance')?.value || (convKm * convRate));
        const photocopyAmount = Number(document.getElementById('fee-photocopy')?.value || 0);
        const taxableAmount = professional + conveyanceFee + photocopyAmount;
        const gstPc = Number(document.getElementById('fee-gst-pc')?.value || 0);
        const gstAmount = taxableAmount * gstPc / 100;
        const grossValue = taxableAmount + gstAmount;

        const payload = {
            report_id: reportId || null,
            survey_type: document.getElementById('fee-survey-type')?.value || 'Survey Fee',
            insurer_name: document.getElementById('fee-insurer')?.value.trim(),
            insurer_gst: document.getElementById('fee-insurer-gst')?.value.trim() || '',
            insurer_state: document.getElementById('fee-insurer-state')?.value.trim() || '',
            insurer_address: document.getElementById('fee-insurer-address')?.value.trim() || '',
            insured_name: document.getElementById('fee-insured')?.value.trim(),
            invoice_no: document.getElementById('fee-invoice-no')?.value.trim(),
            invoice_date: document.getElementById('fee-invoice-date')?.value || new Date().toISOString().split('T')[0],
            professional_fee: professional,
            convenience_type: convType,
            convenience_route: convRoute,
            convenience_km: convKm,
            convenience_rate: convRate,
            conveyance_fee: conveyanceFee,
            photocopy_amount: photocopyAmount,
            taxable_amount: taxableAmount,
            gst_pc: gstPc,
            gst_amount: gstAmount,
            gross_invoice_value: grossValue,
            total_amount: grossValue,
            amount_received: Number(document.getElementById('fee-received')?.value || 0),
            outstanding_amount: Number(document.getElementById('fee-outstanding')?.value || 0),
            due_date: document.getElementById('fee-due-date')?.value || null,
            payment_status: document.getElementById('fee-payment-status')?.value,
            invoice_status: document.getElementById('fee-invoice-status')?.value,
            claim_no: report.claim_no || '',
            vehicle_no: report.vehicle_no || '',
            policy_no: report.policy_no || ''
        };
        try {
            const res = await fetch('/api/fee_bills', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const result = await res.json();
            if (!res.ok) throw new Error(result.error || 'Could not save fee');
            document.getElementById('fee-register-form')?.reset();
            const gstElem = document.getElementById('fee-gst-pc');
            if (gstElem) gstElem.value = '18';
            const invDateElem = document.getElementById('fee-invoice-date');
            if (invDateElem) invDateElem.value = new Date().toISOString().split('T')[0];
            const fileNameSpan = document.getElementById('fee-pdf-file-name');
            if (fileNameSpan) fileNameSpan.textContent = '';
            showStatus('Fee register saved.', 'success', true);
            await Promise.all([fetchFees(), fetchDashboard()]);
        } catch (error) { showStatus(error.message, 'error', true); }
    }


    async function initGmailControls() {
        const statusRes = await fetch('/auth/gmail/status');
        if (!statusRes.ok) return;
        const status = await statusRes.json();
        const toolbar = document.getElementById('gmail-sync-toolbar');
        if (toolbar && status.can_sync) {
            toolbar.classList.remove('hidden');
            fetchPendingGmailIntimations();
        }
        if (workspaceState.profile?.role === 'admin') await loadGmailDomains();
    }

    async function fetchPendingGmailIntimations() {
        const section = document.getElementById('gmail-import-section');
        const container = document.getElementById('gmail-import-cards-container');
        const countInfo = document.getElementById('gmail-import-count-info');
        if (!container) return;

        try {
            const res = await fetch('/api/gmail/intimations');
            if (!res.ok) return;
            const result = await res.json();
            const intimations = result.intimations || [];

            if (!intimations.length) {
                if (section) section.classList.add('hidden');
                return;
            }

            if (section) section.classList.remove('hidden');
            if (countInfo) countInfo.textContent = `${intimations.length} possible appointment email(s) found.`;

            container.innerHTML = intimations.map(item => {
                const parse = typeof item.parse_data_json === 'string' ? JSON.parse(item.parse_data_json || '{}') : (item.parse_data_json || {});
                return `
                    <div class="gmail-appointment-card" style="background: var(--bg-card, rgba(255,255,255,0.03)); border: 1px solid var(--border-color); border-radius: var(--border-radius); padding: 1.25rem;">
                        <h3 style="font-size: 1rem; margin-bottom: 0.25rem; font-weight: 600;">${escapeHtml(item.subject || 'Intimation Email')}</h3>
                        <small style="color: var(--text-secondary); font-family: monospace; display: block; margin-bottom: 0.75rem;">${escapeHtml(item.sender_email || '')}</small>

                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.5rem 1rem; margin-bottom: 1rem; font-size: 0.9rem;">
                            <div><strong>Claim No.</strong> ${escapeHtml(parse.claim_no || 'Not detected')}</div>
                            <div><strong>Policy No.</strong> ${escapeHtml(parse.policy_no || 'Not detected')}</div>
                            <div><strong>Insurer</strong> ${escapeHtml(parse.insurer || 'Not detected')}</div>
                            <div><strong>Insured</strong> ${escapeHtml(parse.insured_name || 'Not detected')}</div>
                            <div><strong>Contact</strong> ${escapeHtml(parse.contact || 'Not detected')}</div>
                            <div><strong>Vehicle</strong> ${escapeHtml(parse.vehicle_no || 'Not detected')}</div>
                        </div>

                        <div style="display: flex; gap: 0.75rem; align-items: center; margin-bottom: 0.75rem;">
                            <button type="button" class="btn btn-primary btn-sm add-gmail-intimation-btn" data-message-id="${escapeHtml(item.gmail_message_id)}">
                                <i class="fas fa-plus-circle"></i> Add to Claim Register
                            </button>
                            <button type="button" class="btn btn-secondary btn-sm cancel-gmail-intimation-btn" data-message-id="${escapeHtml(item.gmail_message_id)}">
                                Cancel
                            </button>
                        </div>

                        <div style="font-size: 0.85rem; color: var(--text-secondary); background: rgba(0,0,0,0.2); padding: 0.75rem; border-radius: 4px; max-height: 100px; overflow-y: auto; line-height: 1.4;">
                            ${escapeHtml(parse.snippet || parse.email_text || item.subject || '')}
                        </div>
                    </div>
                `;
            }).join('');

            container.querySelectorAll('.add-gmail-intimation-btn').forEach(btn => btn.addEventListener('click', () => addGmailIntimationToRegister(btn.dataset.messageId)));
            container.querySelectorAll('.cancel-gmail-intimation-btn').forEach(btn => btn.addEventListener('click', () => cancelGmailIntimation(btn.dataset.messageId)));
        } catch (err) {
            console.error('Error fetching pending Gmail intimations:', err);
        }
    }

    async function addGmailIntimationToRegister(messageId) {
        showStatus('Adding intimation to Claim Register...', 'processing');
        try {
            const res = await fetch(`/api/gmail/intimation/${encodeURIComponent(messageId)}/add`, { method: 'POST' });
            const result = await res.json();
            if (!res.ok) throw new Error(result.error || 'Failed to add claim');
            showStatus(`Claim ${result.claim_no || ''} added to Claim Register!`, 'success', true);
            await Promise.all([fetchPendingGmailIntimations(), fetchClaims(), fetchDashboard()]);
        } catch (err) {
            showStatus(err.message, 'error', true);
        }
    }

    async function cancelGmailIntimation(messageId) {
        try {
            const res = await fetch(`/api/gmail/intimation/${encodeURIComponent(messageId)}/cancel`, { method: 'POST' });
            const result = await res.json();
            if (!res.ok) throw new Error(result.error || 'Failed to cancel intimation');
            showStatus('Intimation dismissed.', 'info', true);
            await fetchPendingGmailIntimations();
        } catch (err) {
            showStatus(err.message, 'error', true);
        }
    }

    async function loadGmailDomains() {
        const res = await fetch('/api/admin/gmail-domains');
        if (!res.ok) return [];
        const domains = await res.json();
        const filter = document.getElementById('gmail-domain-filter');
        if (filter) filter.innerHTML = '<option value="">All approved senders</option>' + domains.map(item => `<option value="${escapeHtml(item.domain)}">${escapeHtml(item.domain)}</option>`).join('');
        const list = document.getElementById('gmail-domain-list');
        if (list) {
            list.innerHTML = domains.map(item => `<span class="chip">${escapeHtml(item.domain)} <button type="button" class="delete-gmail-domain" data-domain-id="${item.id}" aria-label="Delete ${escapeHtml(item.domain)}">×</button></span>`).join('') || '<span class="workspace-subtitle">No approved domains configured.</span>';
            list.querySelectorAll('.delete-gmail-domain').forEach(button => button.addEventListener('click', async () => {
                await fetch(`/api/admin/gmail-domains/${button.dataset.domainId}`, { method: 'DELETE' });
                loadGmailDomains();
            }));
        }
        return domains;
    }

    async function syncGmail() {
        const button = document.getElementById('sync-gmail-button');
        const importBtn = document.getElementById('sync-gmail-import-btn');
        const activeBtn = button || importBtn;
        if (activeBtn) { activeBtn.disabled = true; activeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Syncing…'; }
        try {
            const res = await fetch('/api/gmail/sync', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sender_domain: document.getElementById('gmail-domain-filter')?.value || '' }) });
            const result = await res.json();
            if (!res.ok) throw new Error(result.error || 'Gmail sync failed');
            showStatus(`Gmail sync complete. Found appointment emails.`, 'success', true);
            await Promise.all([fetchPendingGmailIntimations(), fetchDashboard(), fetchClaims(), fetchFees()]);
        } catch (error) { showStatus(error.message, 'error', true); }
        finally {
            if (button) { button.disabled = false; button.innerHTML = '<i class="fas fa-sync-alt"></i> Sync Gmail Intimations'; }
            if (importBtn) { importBtn.disabled = false; importBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Connect & Sync Gmail'; }
        }
    }

    async function loadAdminUsers() {
        const tbody = document.getElementById('employee-list-tbody');
        if (!tbody || workspaceState.profile?.role !== 'admin') return;
        const res = await fetch('/api/admin/users');
        if (!res.ok) { tbody.innerHTML = '<tr><td colspan="4">Could not load employees.</td></tr>'; return; }
        const users = await res.json();
        if (!users.length) { tbody.innerHTML = '<tr><td colspan="4">No employees yet.</td></tr>'; return; }
        tbody.innerHTML = users.map(user => `<tr><td>${escapeHtml(user.full_name || user.username)}<br><small>${escapeHtml(user.username)}</small></td><td>${user.is_locked ? 'Locked' : 'Active'}</td><td><input type="checkbox" class="employee-gmail-toggle" data-user-id="${user.id}" ${user.permissions?.gmail_sync ? 'checked' : ''}></td><td><button type="button" class="btn btn-secondary btn-sm employee-lock" data-user-id="${user.id}" data-locked="${user.is_locked}">${user.is_locked ? 'Unlock' : 'Lock'}</button> <button type="button" class="btn btn-secondary btn-sm employee-reset" data-user-id="${user.id}">Reset password</button></td></tr>`).join('');
        tbody.querySelectorAll('.employee-gmail-toggle').forEach(control => control.addEventListener('change', () => updateEmployeePermission(control.dataset.userId, control.checked)));
        tbody.querySelectorAll('.employee-lock').forEach(button => button.addEventListener('click', () => lockEmployee(button.dataset.userId, button.dataset.locked !== 'true')));
        tbody.querySelectorAll('.employee-reset').forEach(button => button.addEventListener('click', () => resetEmployeePassword(button.dataset.userId)));
    }

    async function updateEmployeePermission(userId, gmailSync) {
        await fetch(`/api/admin/users/${userId}/permissions`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ permissions: { gmail_sync: gmailSync } }) });
    }
    async function lockEmployee(userId, isLocked) {
        await fetch(`/api/admin/users/${userId}/lock`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ is_locked: isLocked }) });
        loadAdminUsers();
    }
    async function resetEmployeePassword(userId) {
        const password = prompt('Enter a new temporary password (8+ characters):');
        if (!password) return;
        const res = await fetch(`/api/admin/users/${userId}/reset-password`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ temporary_password: password }) });
        showStatus(res.ok ? 'Temporary password reset.' : 'Could not reset password.', res.ok ? 'success' : 'error', true);
    }

    async function refreshAdminSettings(profile) {
        const section = document.getElementById('admin-settings-section');
        if (!section) return;
        if (profile?.role !== 'admin') { section.classList.add('hidden'); return; }
        section.classList.remove('hidden');
        const gmail = await fetch('/auth/gmail/status').then(res => res.ok ? res.json() : null);
        const status = document.getElementById('gmail-connection-status');
        const connect = document.getElementById('gmail-connect-button');
        if (status && connect) {
            status.textContent = gmail?.connected ? `Connected: ${gmail.mailbox_email || 'shared mailbox'}` : 'No Gmail mailbox connected';
            connect.textContent = gmail?.connected ? 'Disconnect Gmail' : 'Connect Gmail';
            connect.onclick = async () => {
                if (gmail?.connected) { await fetch('/auth/gmail/disconnect', { method: 'POST' }); refreshAdminSettings(profile); }
                else window.location.href = '/auth/gmail';
            };
        }
        await Promise.all([loadGmailDomains(), loadAdminUsers()]);
    }

    function bindMotorWorkspaceEvents() {
        document.getElementById('toggle-new-claim')?.addEventListener('click', () => document.getElementById('new-claim-form')?.classList.toggle('hidden'));
        document.getElementById('new-claim-form')?.addEventListener('submit', createClaim);
        document.getElementById('claim-filter-button')?.addEventListener('click', () => { workspaceState.claimsPage = 1; fetchClaims(); });
        document.getElementById('claim-page-prev')?.addEventListener('click', () => {
            if (workspaceState.claimsPage > 1) { workspaceState.claimsPage -= 1; fetchClaims(); }
        });
        document.getElementById('claim-page-next')?.addEventListener('click', () => {
            const totalPages = Math.max(1, Math.ceil(workspaceState.claimsTotal / workspaceState.claimsPageSize));
            if (workspaceState.claimsPage < totalPages) { workspaceState.claimsPage += 1; fetchClaims(); }
        });
        document.getElementById('sync-gmail-button')?.addEventListener('click', syncGmail);
        document.getElementById('sync-gmail-import-btn')?.addEventListener('click', syncGmail);
        document.getElementById('pending-7day-proceed-btn')?.addEventListener('click', () => {
            document.getElementById('pending-7day-alert-modal')?.classList.add('hidden');
            document.getElementById('tab-btn-claims')?.click();
            const filter = document.getElementById('claim-status-filter');
            if (filter) { filter.value = 'documents_awaited'; fetchClaims(); }
        });
        document.getElementById('pending-7day-cancel-btn')?.addEventListener('click', () => {
            document.getElementById('pending-7day-alert-modal')?.classList.add('hidden');
        });
        document.getElementById('fee-convenience-km')?.addEventListener('input', updateFeeCalculations);
        document.getElementById('fee-convenience-rate')?.addEventListener('input', updateFeeCalculations);
        document.getElementById('fee-conveyance')?.addEventListener('input', (e) => {
            e.target.dataset.userEdited = "true";
        });
        document.getElementById('close-pending-docs-modal')?.addEventListener('click', () => {
            document.getElementById('pending-documents-modal')?.classList.add('hidden');
        });
        document.getElementById('add-custom-doc-btn')?.addEventListener('click', () => {
            const input = document.getElementById('add-custom-doc-input');
            const val = input?.value.trim();
            if (val) {
                currentPendingDocs.push({ name: val, received: false });
                input.value = '';
                renderPendingDocsList();
            }
        });
        document.getElementById('save-pending-docs-btn')?.addEventListener('click', savePendingDocsChecklist);
        document.getElementById('send-reminder-btn')?.addEventListener('click', sendPendingNotification);
        document.getElementById('copy-reminder-text-btn')?.addEventListener('click', () => {
            const reportId = document.getElementById('pending-docs-report-id')?.value;
            if (!reportId) return;
            const report = workspaceState.claims.find(c => c.id === reportId) || {};
            const pendingNames = currentPendingDocs.filter(d => typeof d === 'object' ? !d.received : true).map(d => typeof d === 'object' ? d.name : d);
            fetch(`/api/claims/${encodeURIComponent(reportId)}/pending_documents`)
                .then(r => r.json())
                .then(data => {
                    const count = (data.reminder_info?.reminder_count || 0) + 1;
                    const text = generateReminderTextClient(report, pendingNames, count);
                    navigator.clipboard.writeText(text);
                    showStatus('Reminder text copied to clipboard.', 'success', true);
                });
        });
        document.getElementById('download-admin-backup-btn')?.addEventListener('click', () => {
            window.location.href = '/api/admin/backup/download';
        });
        document.getElementById('add-gmail-domain')?.addEventListener('click', async () => {
            const input = document.getElementById('new-gmail-domain');
            const domain = input?.value.trim();
            if (!domain) return;
            const res = await fetch('/api/admin/gmail-domains', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ domain }) });
            if (res.ok) { input.value = ''; loadGmailDomains(); } else showStatus('Could not add sender domain.', 'error', true);
        });
        document.getElementById('create-employee-button')?.addEventListener('click', async () => {
            const payload = { username: document.getElementById('employee-username')?.value.trim(), full_name: document.getElementById('employee-name')?.value.trim(), email: document.getElementById('employee-email')?.value.trim(), temporary_password: document.getElementById('employee-password')?.value, permissions: { gmail_sync: document.getElementById('employee-gmail-permission')?.checked } };
            const res = await fetch('/api/admin/users', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            const result = await res.json();
            if (res.ok) { showStatus('Employee created.', 'success', true); ['employee-username','employee-name','employee-email','employee-password'].forEach(id => { const input = document.getElementById(id); if (input) input.value = ''; }); loadAdminUsers(); }
            else showStatus(result.error || 'Could not create employee.', 'error', true);
        });
        document.getElementById('change-password-button')?.addEventListener('click', async () => {
            const current_password = document.getElementById('current-password-input')?.value || '';
            const new_password = document.getElementById('new-password-input')?.value || '';
            const res = await fetch('/api/change-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ current_password, new_password }) });
            const result = await res.json();
            if (res.ok) { showStatus('Password updated.', 'success', true); document.getElementById('current-password-input').value = ''; document.getElementById('new-password-input').value = ''; }
            else showStatus(result.error || 'Could not update password.', 'error', true);
        });

        // Insurer Master Auto-Fill Listeners
        document.getElementById('fee-insurer-master-select')?.addEventListener('change', async (e) => {
            const id = e.target.value;
            if (!id) return;
            const item = globalInsurerMasters.find(i => String(i.id) === String(id));
            if (!item) return;
            const insurerInput = document.getElementById('fee-insurer');
            const gstinInput = document.getElementById('fee-insurer-gst');
            const addressInput = document.getElementById('fee-insurer-address');
            const rateInput = document.getElementById('fee-dist-rate-per-km');

            if (insurerInput) insurerInput.value = item.insurer_name || '';
            if (gstinInput) gstinInput.value = item.gstin || '';
            if (addressInput) addressInput.value = item.branch_address || '';
            if (rateInput) rateInput.value = item.default_conveyance_rate || 10;

            if (item.invoice_prefix) {
                try {
                    const res = await fetch(`/api/insurers/next-invoice-no?prefix=${encodeURIComponent(item.invoice_prefix)}`);
                    const data = await res.json();
                    if (data.success && data.next_invoice_no) {
                        const invInput = document.getElementById('fee-invoice-no');
                        if (invInput) invInput.value = data.next_invoice_no;
                    }
                } catch (err) { console.error('Error fetching next invoice number:', err); }
            }
            updateDistanceConveyanceCalc();
        });

        document.getElementById('claim-input-insurer-select')?.addEventListener('change', (e) => {
            const id = e.target.value;
            if (!id) return;
            const item = globalInsurerMasters.find(i => String(i.id) === String(id));
            if (!item) return;
            const insurerInput = document.getElementById('claim-input-insurer');
            const branchInput = document.getElementById('claim-input-branch');
            if (insurerInput) insurerInput.value = item.insurer_name || '';
            if (branchInput) branchInput.value = item.branch_name || '';
        });

        // Conveyance Distance Formula Listeners
        document.getElementById('fee-conveyance-calc-mode')?.addEventListener('change', updateDistanceConveyanceCalc);
        document.getElementById('fee-dist-oneway-km')?.addEventListener('input', updateDistanceConveyanceCalc);
        document.getElementById('fee-dist-rate-per-km')?.addEventListener('input', updateDistanceConveyanceCalc);
        document.getElementById('fee-dist-visits')?.addEventListener('change', updateDistanceConveyanceCalc);

        // Insurer Master Form Submit & Modal Controls
        document.getElementById('insurer-master-form')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                id: document.getElementById('insurer-master-id')?.value || null,
                insurer_name: document.getElementById('im-insurer-name')?.value.trim(),
                branch_name: document.getElementById('im-branch-name')?.value.trim(),
                invoice_prefix: document.getElementById('im-prefix')?.value.trim(),
                gstin: document.getElementById('im-gstin')?.value.trim(),
                state_code: document.getElementById('im-state-code')?.value.trim() || '19',
                default_conveyance_rate: document.getElementById('im-conveyance-rate')?.value,
                branch_address: document.getElementById('im-branch-address')?.value.trim()
            };
            try {
                const res = await fetch('/api/insurers', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                const result = await res.json();
                if (!res.ok) throw new Error(result.error || 'Failed to save Insurer Master');
                showStatus('Insurer Master saved.', 'success', true);
                document.getElementById('insurer-master-form')?.reset();
                document.getElementById('insurer-master-id').value = '';
                await loadInsurerMasters();
            } catch (err) { showStatus(err.message, 'error', true); }
        });

        document.getElementById('im-reset-btn')?.addEventListener('click', () => {
            document.getElementById('insurer-master-form')?.reset();
            document.getElementById('insurer-master-id').value = '';
        });

        document.getElementById('close-insurer-master-modal')?.addEventListener('click', () => {
            document.getElementById('insurer-master-modal')?.classList.add('hidden');
        });

        document.getElementById('close-gmail-staging-modal')?.addEventListener('click', () => {
            document.getElementById('gmail-staging-modal')?.classList.add('hidden');
        });
    }

    // --- Initial Load ---
    updateSteps('upload');
    fetchSavedReports();
    bindMotorWorkspaceEvents();
    initMotorSurveyWorkspace();
    loadInsurerMasters();

    if (downloadConsolidatedCsvButton) {
        downloadConsolidatedCsvButton.addEventListener('click', handleConsolidatedCsvDownload);
    }

    // --- Preview Functionality ---
    const previewButton = document.getElementById('preview-button');
    const previewModal = document.getElementById('preview-modal');
    const closePreviewModalBtn = document.getElementById('close-preview-modal');
    const previewIframe = document.getElementById('preview-iframe');

    if (previewButton) {
        previewButton.addEventListener('click', async () => {
            showStatus('Generating preview...', 'processing');
            previewButton.disabled = true; previewButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';

            const finalDataToSend = collectFinalData();

            try {
                const response = await fetch('/generate_files', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(finalDataToSend)
                });
                if (!response.ok) {
                    let errorMsg = `Server error: ${response.status}`;
                    try { const errorData = await response.json(); errorMsg = errorData.error || errorMsg; } catch (e) { }
                    throw new Error(errorMsg);
                }
                const submitResult = await response.json();
                const taskId = submitResult.task_id;
                if (!taskId) throw new Error('No task_id received from server');

                // Poll for completion
                showStatus('Generating PDF preview... This may take a moment.', 'processing');
                let result = null;
                while (true) {
                    await new Promise(resolve => setTimeout(resolve, 3000));
                    const statusRes = await fetch(`/generate_files/status/${taskId}`);
                    if (!statusRes.ok) throw new Error(`Status check failed: ${statusRes.status}`);
                    const statusData = await statusRes.json();

                    if (statusData.status === 'completed') {
                        result = statusData.result;
                        break;
                    } else if (statusData.status === 'error') {
                        throw new Error(statusData.error || 'Preview generation failed');
                    }
                }

                // Open Modal with PDF
                previewIframe.src = `/download/report_pdf/${result.request_id}?preview=true`;
                previewModal.classList.remove('hidden');
                showStatus('Preview generated.', 'success');

            } catch (error) {
                console.error('Preview error:', error);
                showStatus(`Error generating preview: ${error.message}`, 'error');
            } finally {
                previewButton.disabled = false; previewButton.innerHTML = '<i class="fas fa-eye"></i> Preview PDF';
            }
        });
    }

    if (closePreviewModalBtn) {
        closePreviewModalBtn.addEventListener('click', () => {
            previewModal.classList.add('hidden');
            previewIframe.src = ''; // Clear source
        });
    }

    // --- Profile Settings Logic ---
    const openProfileBtn = document.getElementById('open-profile-modal');
    const closeProfileBtn = document.getElementById('close-profile-modal');
    const profileModal = document.getElementById('profile-modal');
    const profileForm = document.getElementById('profile-form');

    if (openProfileBtn && profileModal) {
        openProfileBtn.addEventListener('click', async () => {
            // Fetch current profile
            try {
                const response = await fetch('/get_user_profile');
                if (response.ok) {
                    const data = await response.json();
                    // Populate form
                    for (const key in data) {
                        if (profileForm.elements[key]) {
                            profileForm.elements[key].value = data[key];
                        }
                    }
                    const storedKeyInput = document.getElementById('settings-gemini-key');
                    if (storedKeyInput) {
                        storedKeyInput.value = '';
                        storedKeyInput.placeholder = data.has_gemini_api_key
                            ? 'A key is stored securely; enter a replacement to change it'
                            : 'Optional: enter your Gemini key';
                    }
                    profileModal.classList.remove('hidden');
                    // Populate models dropdown
                    await loadAvailableModels(null, data.gemini_model);
                    await refreshAdminSettings(data);
                } else {
                    alert("Failed to load profile settings.");
                }
            } catch (e) {
                console.error(e);
                alert("Error loading profile settings.");
            }

            // Bind listener to validate custom API key dynamically on blur
            const geminiKeyInput = document.getElementById('settings-gemini-key');
            if (geminiKeyInput && !geminiKeyInput.dataset.listenerBound) {
                geminiKeyInput.dataset.listenerBound = "true";
                geminiKeyInput.addEventListener('blur', async () => {
                    const currentKey = geminiKeyInput.value.trim();
                    const modelSelect = document.getElementById('settings-gemini-model');
                    const savedValue = modelSelect ? modelSelect.value : '';
                    await loadAvailableModels(currentKey, savedValue);
                });
            }

            // Fetch Google Drive Status
            const driveBtn = document.getElementById('settings-drive-btn');
            const driveStatus = document.getElementById('settings-drive-status');
            const driveLabel = document.getElementById('settings-drive-label');

            if (driveBtn && driveStatus) {
                try {
                    const driveRes = await fetch('/auth/google/status');
                    const driveData = await driveRes.json();
                    
                    if (driveData.connected) {
                        driveStatus.innerHTML = `<i class="fas fa-check-circle" style="color: #22c55e;"></i> Connected to Drive`;
                        driveBtn.className = 'btn btn-danger btn-sm';
                        driveLabel.textContent = 'Disconnect';
                        driveBtn.onclick = async () => {
                            if(confirm("Disconnect Google Drive?")) {
                                await fetch('/auth/google/disconnect', { method: 'POST' });
                                driveBtn.click(); // reload status
                            }
                        };
                    } else {
                        driveStatus.innerHTML = `<i class="fas fa-info-circle"></i> Not connected`;
                        driveBtn.className = 'btn btn-secondary btn-sm';
                        driveLabel.textContent = 'Connect Drive';
                        driveBtn.onclick = () => {
                            window.location.href = '/auth/google';
                        };
                    }
                } catch (e) {
                    console.error("Error checking Drive status:", e);
                }
            }
        });

        closeProfileBtn.addEventListener('click', () => {
            profileModal.classList.add('hidden');
        });

        profileForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(profileForm);
            const data = Object.fromEntries(formData.entries());

            try {
                const response = await fetch('/update_user_profile', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                if (response.ok) {
                    alert("Profile updated successfully!");
                    profileModal.classList.add('hidden');
                } else {
                    alert("Error updating profile: " + result.error);
                }
                // Also update the header button if we disconnected from settings
                initHeaderDriveButton();
            } catch (e) {
                console.error(e);
                alert("Error updating profile.");
            }
        });
    }

    // --- Header Drive Button Logic ---
    async function initHeaderDriveButton() {
        const headerDriveBtn = document.getElementById('header-drive-btn');
        const headerDriveLabel = document.getElementById('header-drive-label');
        if (!headerDriveBtn || !headerDriveLabel) return;
        
        try {
            const res = await fetch('/auth/google/status');
            const data = await res.json();
            
            if (data.connected) {
                headerDriveBtn.classList.remove('btn-secondary');
                headerDriveBtn.classList.add('btn-success');
                headerDriveLabel.textContent = 'Drive Connected';
                headerDriveBtn.onclick = async () => {
                    if(confirm("Disconnect Google Drive?")) {
                        await fetch('/auth/google/disconnect', { method: 'POST' });
                        initHeaderDriveButton(); // Reload status
                        // Also click settings button to refresh if it's open
                        const settingsBtn = document.getElementById('settings-drive-btn');
                        if (settingsBtn && !document.getElementById('profile-modal').classList.contains('hidden')) {
                            document.getElementById('open-profile-modal').click();
                        }
                    }
                };
            } else {
                headerDriveBtn.classList.remove('btn-success');
                headerDriveBtn.classList.add('btn-secondary');
                headerDriveLabel.textContent = 'Connect Drive';
                headerDriveBtn.onclick = () => {
                    window.location.href = '/auth/google';
                };
            }
        } catch (e) {
            console.error("Failed to fetch header Drive status", e);
        }
    }
    
    async function loadAvailableModels(apiKey, savedModel) {
        const modelSelect = document.getElementById('settings-gemini-model');
        if (!modelSelect) return;
        
        // Save current selection to restore if it exists in new models list
        const currentSelection = savedModel || modelSelect.value;
        modelSelect.innerHTML = '<option value="">Auto Model Selection (Recommended)</option>';
        
        try {
            const response = await fetch('/api/available_models', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(apiKey ? { api_key: apiKey } : {})
            });
            if (response.ok) {
                const models = await response.json();
                models.forEach(model => {
                    const opt = document.createElement('option');
                    opt.value = model;
                    opt.textContent = model;
                    if (model === currentSelection) {
                        opt.selected = true;
                    }
                    modelSelect.appendChild(opt);
                });
            }
        } catch (e) {
            console.error("Error loading available models:", e);
        }
    }
    
    // --- Standalone Fee Bill & GST Export Event Handlers ---
    const btnOpenFeeBillModal = document.getElementById('btn-open-fee-bill-modal');
    const btnCloseFeeBillModal = document.getElementById('btn-close-fee-bill-modal');
    const feeBillModal = document.getElementById('fee-bill-modal');

    const fbInsurerName = document.getElementById('fb-insurer-name');
    const fbInvoiceNo = document.getElementById('fb-invoice-no');
    const fbInvoiceDate = document.getElementById('fb-invoice-date');
    const fbInsuredName = document.getElementById('fb-insured-name');
    const fbPolicyNo = document.getElementById('fb-policy-no');
    const fbClaimNo = document.getElementById('fb-claim-no');
    const fbVehicleNo = document.getElementById('fb-vehicle-no');
    const fbTaxableAmount = document.getElementById('fb-taxable-amount');
    const fbGstPc = document.getElementById('fb-gst-pc');
    const fbGstAmount = document.getElementById('fb-gst-amount');
    const fbTotalAmount = document.getElementById('fb-total-amount');
    const fbIncludeSig = document.getElementById('fb-include-signature');
    const btnSaveFeeBill = document.getElementById('btn-save-fee-bill');
    const btnGenerateFeePdf = document.getElementById('btn-generate-fee-pdf');

    const downloadGstExcelBtn = document.getElementById('download-gst-excel-button');
    const gstExcelDateFrom = document.getElementById('gst-excel-date-from');
    const gstExcelDateTo = document.getElementById('gst-excel-date-to');

    if (fbInvoiceDate) {
        fbInvoiceDate.value = new Date().toISOString().split('T')[0];
    }

    function calculateFeeBillAmounts() {
        if (!fbTaxableAmount || !fbGstPc || !fbGstAmount || !fbTotalAmount) return;
        const taxable = parseFloat(fbTaxableAmount.value) || 0;
        const gstPc = parseFloat(fbGstPc.value) || 0;
        const gstAmt = taxable * (gstPc / 100);
        const total = taxable + gstAmt;

        fbGstAmount.value = gstAmt.toFixed(2);
        fbTotalAmount.value = total.toFixed(2);
    }

    if (fbTaxableAmount) fbTaxableAmount.addEventListener('input', calculateFeeBillAmounts);
    if (fbGstPc) fbGstPc.addEventListener('input', calculateFeeBillAmounts);

    async function fetchNextInvoiceNumber() {
        if (!fbInsurerName || !fbInvoiceNo) return;
        const insurer = fbInsurerName.value.trim();
        const dateVal = fbInvoiceDate ? fbInvoiceDate.value : '';
        if (!insurer) return;

        try {
            const res = await fetch(`/api/next_invoice_no?insurer=${encodeURIComponent(insurer)}&date=${encodeURIComponent(dateVal)}`);
            if (res.ok) {
                const data = await res.json();
                if (data.invoice_no) {
                    fbInvoiceNo.value = data.invoice_no;
                }
            }
        } catch (e) {
            console.error("Error fetching auto invoice number:", e);
        }
    }

    if (fbInsurerName) fbInsurerName.addEventListener('change', fetchNextInvoiceNumber);
    if (fbInvoiceDate) fbInvoiceDate.addEventListener('change', fetchNextInvoiceNumber);

    if (btnOpenFeeBillModal && feeBillModal) {
        btnOpenFeeBillModal.addEventListener('click', () => {
            feeBillModal.classList.remove('hidden');
            fetchNextInvoiceNumber();
        });
    }

    if (btnCloseFeeBillModal && feeBillModal) {
        btnCloseFeeBillModal.addEventListener('click', () => {
            feeBillModal.classList.add('hidden');
        });
    }

    function collectFeeBillPayload() {
        calculateFeeBillAmounts();
        return {
            insurer_name: fbInsurerName?.value.trim() || '',
            invoice_no: fbInvoiceNo?.value.trim() || '',
            invoice_date: fbInvoiceDate?.value || '',
            insured_name: fbInsuredName?.value.trim() || '',
            policy_no: fbPolicyNo?.value.trim() || '',
            claim_no: fbClaimNo?.value.trim() || '',
            vehicle_no: fbVehicleNo?.value.trim() || '',
            taxable_amount: parseFloat(fbTaxableAmount?.value || 0),
            gst_pc: parseFloat(fbGstPc?.value || 18),
            gst_amount: parseFloat(fbGstAmount?.value || 0),
            total_amount: parseFloat(fbTotalAmount?.value || 0),
            include_signature: fbIncludeSig ? fbIncludeSig.checked : true
        };
    }

    if (btnSaveFeeBill) {
        btnSaveFeeBill.addEventListener('click', async () => {
            const payload = collectFeeBillPayload();
            if (!payload.insurer_name || !payload.insured_name) {
                showStatus("Please enter Insurance Company and Insured Name.", "error", true);
                return;
            }
            try {
                btnSaveFeeBill.disabled = true;
                const res = await fetch('/api/fee_bills', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    showStatus("Fee Bill saved successfully!", "success", true);
                } else {
                    showStatus("Failed to save fee bill.", "error", true);
                }
            } catch (e) {
                showStatus(`Error saving fee bill: ${e.message}`, "error", true);
            } finally {
                btnSaveFeeBill.disabled = false;
            }
        });
    }

    if (btnGenerateFeePdf) {
        btnGenerateFeePdf.addEventListener('click', async () => {
            const payload = collectFeeBillPayload();
            if (!payload.insurer_name || !payload.insured_name) {
                showStatus("Please enter Insurance Company and Insured Name.", "error", true);
                return;
            }
            try {
                btnGenerateFeePdf.disabled = true;
                btnGenerateFeePdf.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
                const res = await fetch('/generate_fee_pdf', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (!res.ok) throw new Error(`Server error ${res.status}`);
                const blob = await res.blob();
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = `${payload.invoice_no.replace(/[/\\?%*:|"<>]/g, '_') || 'FeeBill'}.pdf`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(link.href);
                showStatus("Fee Bill PDF downloaded!", "success", true);
            } catch (e) {
                showStatus(`Error generating Fee PDF: ${e.message}`, "error", true);
            } finally {
                btnGenerateFeePdf.disabled = false;
                btnGenerateFeePdf.innerHTML = '<i class="fas fa-file-pdf"></i> Download PDF';
            }
        });
    }

    if (downloadGstExcelBtn) {
        downloadGstExcelBtn.addEventListener('click', () => {
            const fromDate = gstExcelDateFrom ? gstExcelDateFrom.value : '';
            const toDate = gstExcelDateTo ? gstExcelDateTo.value : '';
            if (!fromDate || !toDate) {
                showStatus('Please select both From and To dates for GST report.', 'error', true);
                return;
            }
            if (new Date(fromDate) > new Date(toDate)) {
                showStatus('"From" date cannot be after "To" date.', 'error', true);
                return;
            }
            showStatus('Downloading GST 10-Column Excel report...', 'processing', true);
            window.location.href = `/download_gst_excel?from_date=${fromDate}&to_date=${toDate}`;
        });
    }

    function initSignatureUpload() {
        const sigBtn = document.getElementById('settings-signature-btn');
        const sigInput = document.getElementById('settings-signature-input');
        const sigStatus = document.getElementById('settings-signature-status');
        const sigPreviewContainer = document.getElementById('settings-signature-preview-container');
        const sigPreviewImg = document.getElementById('settings-signature-preview');

        async function checkSigStatus() {
            try {
                const res = await fetch('/signature_status');
                if (res.ok) {
                    const data = await res.json();
                    if (data.has_signature && data.url) {
                        if (sigStatus) {
                            sigStatus.textContent = 'Active signature file uploaded ✓';
                            sigStatus.style.color = '#10b981';
                        }
                        if (sigPreviewImg) sigPreviewImg.src = data.url;
                        if (sigPreviewContainer) sigPreviewContainer.style.display = 'block';
                    } else {
                        if (sigStatus) {
                            sigStatus.textContent = 'No image uploaded (PNG with transparent background recommended)';
                            sigStatus.style.color = 'var(--text-secondary)';
                        }
                        if (sigPreviewContainer) sigPreviewContainer.style.display = 'none';
                    }
                }
            } catch (e) {
                console.error("Error checking signature status:", e);
            }
        }

        if (sigBtn && sigInput) {
            sigBtn.addEventListener('click', () => sigInput.click());
            sigInput.addEventListener('change', async () => {
                if (!sigInput.files || sigInput.files.length === 0) return;
                const file = sigInput.files[0];
                const formData = new FormData();
                formData.append('signature', file);

                sigBtn.disabled = true;
                sigBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';

                try {
                    const res = await fetch('/upload_signature', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await res.json();
                    if (res.ok && data.success) {
                        if (sigStatus) {
                            sigStatus.textContent = 'Signature image updated successfully! ✓';
                            sigStatus.style.color = '#10b981';
                        }
                        if (sigPreviewImg) sigPreviewImg.src = data.url;
                        if (sigPreviewContainer) sigPreviewContainer.style.display = 'block';
                        showStatus('Digital Seal & Signature image updated!', 'success', true);
                    } else {
                        showStatus(data.error || 'Failed to upload signature image.', 'error', true);
                    }
                } catch (err) {
                    showStatus('Error uploading signature image: ' + err.message, 'error', true);
                } finally {
                    sigBtn.disabled = false;
                    sigBtn.innerHTML = '<i class="fas fa-upload"></i> Upload Signature Image';
                }
            });
        }

        checkSigStatus();
    }

    // Initialize on page load
    initHeaderDriveButton();
    initSignatureUpload();

});
