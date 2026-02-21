document.addEventListener('DOMContentLoaded', () => {
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
    let currentReportId = null; // To track if we loaded a report
    let isGoogleDriveConnected = false; // Track Google Drive connection status

    // Google Drive button
    const googleDriveBtn = document.getElementById('google-drive-btn');
    const googleDriveStatus = document.getElementById('google-drive-status');

    // Step indicators
    const stepUpload = document.getElementById('step-upload');
    const stepReview = document.getElementById('step-review');
    const stepDownload = document.getElementById('step-download');

    // --- Check Google Drive Connection Status ---
    async function checkGoogleDriveStatus() {
        try {
            const response = await fetch('/auth/google/status');
            if (response.ok) {
                const data = await response.json();
                isGoogleDriveConnected = data.connected;
                updateGoogleDriveUI();
            }
        } catch (e) {
            console.log('Could not check Google Drive status');
        }
    }

    function updateGoogleDriveUI() {
        if (googleDriveBtn && googleDriveStatus) {
            if (isGoogleDriveConnected) {
                googleDriveStatus.textContent = 'Drive Connected';
                googleDriveBtn.classList.add('btn-success');
                googleDriveBtn.classList.remove('btn-secondary');
            } else {
                googleDriveStatus.textContent = 'Connect Drive';
                googleDriveBtn.classList.remove('btn-success');
                googleDriveBtn.classList.add('btn-secondary');
            }
        }
    }

    // Google Drive button click handler
    if (googleDriveBtn) {
        googleDriveBtn.addEventListener('click', async () => {
            if (isGoogleDriveConnected) {
                // Disconnect
                if (confirm('Disconnect from Google Drive?')) {
                    try {
                        await fetch('/auth/google/disconnect', { method: 'POST' });
                        isGoogleDriveConnected = false;
                        updateGoogleDriveUI();
                        showStatus('Disconnected from Google Drive', 'info', true);
                    } catch (e) {
                        showStatus('Failed to disconnect', 'error', true);
                    }
                }
            } else {
                // Connect - redirect to OAuth
                window.location.href = '/auth/google';
            }
        });
    }

    // Check status on page load
    checkGoogleDriveStatus();

    // --- Helper Functions ---
    function showStatus(message, type = 'processing', isFlash = false) {
        // Clear existing dynamic status
        statusDiv.classList.add('hidden');
        statusMessage.textContent = '';

        if (isFlash) {
            // Create a new flash message element
            const flashDiv = document.createElement('div');
            flashDiv.className = `status status-${type}`; // Use status class for styling
            flashDiv.innerHTML = `<i class="fas ${type === 'error' ? 'fa-exclamation-triangle' : type === 'success' ? 'fa-check-circle' : 'fa-info-circle'} status-icon"></i><span>${message}</span>`;
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
    function displayPreview(combinedData, loadedReportId = null) {
        previewForm.reset();
        labourDetailsTbody.innerHTML = '';
        partsDetailsTbody.innerHTML = '';
        if (page3FeeItemsTbody) page3FeeItemsTbody.innerHTML = '';
        currentReportId = loadedReportId;

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

        assessmentHeaderGstInput.value = currentAssessmentData.header_gst || '';
        assessmentHeaderVehicleYearInput.value = currentAssessmentData.header_vehicle_year || '';
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

        if (page3CustomerGstinInput) page3CustomerGstinInput.value = currentAssessmentData.page3_details.customer_gstin || '';
        const page3CompanyGstinInput = document.getElementById('page3-company-gstin');
        if (page3CompanyGstinInput) page3CompanyGstinInput.value = currentAssessmentData.page3_details.company_gstin || '';

        if (page3EstimatedAmountInput) page3EstimatedAmountInput.value = formatCurrency(currentAssessmentData.page3_details.estimated_amount || 0);
        if (page3PhotoCopiesCountInput) page3PhotoCopiesCountInput.value = currentAssessmentData.page3_details.photo_copies_count || '';

        const includeInConsolidatedCheckbox = document.getElementById('page3-include-in-consolidated');
        if (includeInConsolidatedCheckbox) {
            includeInConsolidatedCheckbox.checked = currentAssessmentData.page3_details.include_in_consolidated === true;
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
    }

    function updateDepreciationFieldStates() {
        const isNilDepn = assessmentPolicyTypeDropdown.value === 'NIL_DEPN';

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

        if (assessmentPolicyTypeDropdown.value === 'NIL_DEPN') {
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
        const isNilDepnPolicy = assessmentPolicyTypeDropdown.value === 'NIL_DEPN';

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

        currentAssessmentData.deductibles = lessExcess;
        currentAssessmentData.salvage = salvageValue;
        currentAssessmentData.impose_excess = imposeExcess;

        const netLiability = (addLabour + addPartsNet) - lessExcess - imposeExcess - salvageValue;

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

        const FILE_SIZE_LIMIT = 4 * 1024 * 1024; // 4 MB (Vercel serverless limit with overhead)
        const isLargeFile = file.size > FILE_SIZE_LIMIT;

        if (isLargeFile && !isGoogleDriveConnected) {
            const fileSizeMB = (file.size / (1024 * 1024)).toFixed(1);
            showInvoiceStatus(`File is too large (${fileSizeMB}MB). Connect Google Drive to upload files larger than 4MB.`, 'error');
            return;
        }

        showInvoiceStatus(isLargeFile ? 'Uploading to your Google Drive...' : 'Uploading and processing invoice...', 'processing');
        uploadInvoiceButton.disabled = true;
        uploadInvoiceButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing Invoice...';

        try {
            let response;

            if (isLargeFile && isGoogleDriveConnected) {
                // Upload to user's Drive
                const driveFileId = await uploadFileToUserDrive(file);
                response = await fetch('/process_invoice', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ drive_file_id: driveFileId })
                });
            } else {
                // Standard Upload
                const formData = new FormData(); formData.append('invoice_pdf_file', file);
                response = await fetch('/process_invoice', { method: 'POST', body: formData });
            }

            if (!response.ok) {
                let errorMsg = `Server error: ${response.status}`;
                try { const errorData = await response.json(); errorMsg = errorData.error || errorMsg; } catch (e) { }
                throw new Error(errorMsg);
            }

            const responseData = await response.json();

            if (!responseData || typeof responseData.parts === 'undefined') {
                throw new Error("Invalid response format received from invoice processing.");
            }

            if (page3CustomerGstinInput && typeof responseData.customer_gstin !== 'undefined') {
                page3CustomerGstinInput.value = responseData.customer_gstin;
                if (currentAssessmentData && currentAssessmentData.page3_details) {
                    currentAssessmentData.page3_details.customer_gstin = responseData.customer_gstin;
                }
            }

            mergeInvoiceParts(responseData.parts);
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

        if (selectedTaxType === 'IGST') {
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

        if (selectedTaxType === 'IGST') {
            p3Igst = totalBeforeGst * 0.18;
        } else {
            p3Cgst = totalBeforeGst * 0.09;
            p3Sgst = totalBeforeGst * 0.09;
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

    function compressImage(file, maxWidth = 1024, quality = 0.7) {
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
                    resolve(canvas.toDataURL('image/jpeg', quality));
                };
                img.onerror = error => reject(error);
            };
            reader.onerror = error => reject(error);
        });
    }

    function handlePhotoSelection(event, category) {
        const files = event.target.files;
        if (files.length > 0) {
            showStatus('Processing photos...', 'processing');

            const promises = Array.from(files).map(file => compressImage(file));

            Promise.all(promises).then(base64Images => {
                base64Images.forEach(base64Data => {
                    uploadedPhotos[category].push(base64Data);
                });
                renderPhotos(category);
                showStatus('Photos added!', 'success');
            }).catch(err => {
                console.error("Compression error:", err);
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
            photos: photosData
        };
    }

    // --- Direct Drive Upload Helper (Chunked via Backend Proxy) ---
    async function uploadFileDirectly(file) {
        const CHUNK_SIZE = 2 * 1024 * 1024; // 2 MB chunks
        const totalSize = file.size;
        const totalChunks = Math.ceil(totalSize / CHUNK_SIZE);

        // 1. Get Resumable Upload URL from Backend
        const getUrlResponse = await fetch('/get_upload_url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: file.name, mime_type: file.type, file_size: totalSize })
        });

        if (!getUrlResponse.ok) {
            throw new Error('Failed to get upload URL from server.');
        }

        const { url: uploadUrl, access_token: accessToken } = await getUrlResponse.json();

        // 2. Upload in chunks via backend proxy
        let fileId = null;

        for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
            const start = chunkIndex * CHUNK_SIZE;
            const end = Math.min(start + CHUNK_SIZE, totalSize);
            const chunk = file.slice(start, end);

            // Convert chunk to base64
            const chunkArrayBuffer = await chunk.arrayBuffer();
            const chunkBase64 = btoa(
                new Uint8Array(chunkArrayBuffer).reduce((data, byte) => data + String.fromCharCode(byte), '')
            );

            // Content-Range format: "bytes start-end/total"
            const contentRange = `bytes ${start}-${end - 1}/${totalSize}`;

            const proxyResponse = await fetch('/proxy_upload_chunk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    upload_url: uploadUrl,
                    chunk_data: chunkBase64,
                    content_range: contentRange,
                    content_type: file.type,
                    access_token: accessToken
                })
            });

            if (!proxyResponse.ok) {
                const errorData = await proxyResponse.json().catch(() => ({}));
                throw new Error(errorData.error || 'Chunk upload failed.');
            }

            const result = await proxyResponse.json();

            if (result.complete) {
                fileId = result.file_id;
                break;
            }
            // If not complete (308), continue to next chunk
        }

        if (!fileId) {
            throw new Error('Upload completed but no file ID received.');
        }

        return fileId;
    }

    // --- Upload to User's Drive (using their OAuth token) ---
    async function uploadFileToUserDrive(file) {
        const CHUNK_SIZE = 2 * 1024 * 1024; // 2 MB chunks
        const totalSize = file.size;
        const totalChunks = Math.ceil(totalSize / CHUNK_SIZE);

        // 1. Get Resumable Upload URL using user's token
        const getUrlResponse = await fetch('/get_user_upload_url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: file.name, mime_type: file.type })
        });

        if (!getUrlResponse.ok) {
            const errorData = await getUrlResponse.json().catch(() => ({}));
            if (getUrlResponse.status === 401) {
                isGoogleDriveConnected = false;
                updateGoogleDriveUI();
                throw new Error('Google Drive connection expired. Please reconnect.');
            }
            throw new Error(errorData.error || 'Failed to get upload URL.');
        }

        const { url: uploadUrl, access_token: accessToken } = await getUrlResponse.json();

        // 2. Upload in chunks via backend proxy
        let fileId = null;

        for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
            const start = chunkIndex * CHUNK_SIZE;
            const end = Math.min(start + CHUNK_SIZE, totalSize);
            const chunk = file.slice(start, end);

            // Convert chunk to base64
            const chunkArrayBuffer = await chunk.arrayBuffer();
            const chunkBase64 = btoa(
                new Uint8Array(chunkArrayBuffer).reduce((data, byte) => data + String.fromCharCode(byte), '')
            );

            const contentRange = `bytes ${start}-${end - 1}/${totalSize}`;

            const proxyResponse = await fetch('/proxy_upload_chunk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    upload_url: uploadUrl,
                    chunk_data: chunkBase64,
                    content_range: contentRange,
                    content_type: file.type,
                    access_token: accessToken
                })
            });

            if (!proxyResponse.ok) {
                const errorData = await proxyResponse.json().catch(() => ({}));
                throw new Error(errorData.error || 'Chunk upload failed.');
            }

            const result = await proxyResponse.json();

            if (result.complete) {
                fileId = result.file_id;
                break;
            }
        }

        if (!fileId) {
            throw new Error('Upload completed but no file ID received.');
        }

        return fileId;
    }

    // --- Process PDF ---
    processButton.addEventListener('click', async () => {
        const file = pdfFileInput.files[0];
        if (!file) { showStatus('Please select a PDF file first.', 'error'); return; }

        const FILE_SIZE_LIMIT = 4 * 1024 * 1024; // 4 MB (Vercel serverless limit with overhead)
        const isLargeFile = file.size > FILE_SIZE_LIMIT;

        if (isLargeFile && !isGoogleDriveConnected) {
            const fileSizeMB = (file.size / (1024 * 1024)).toFixed(1);
            showStatus(`File is too large (${fileSizeMB}MB). Connect Google Drive to upload files larger than 4MB, or compress the PDF.`, 'error');
            return;
        }

        showStatus(isLargeFile ? 'Large file detected. Uploading to your Google Drive...' : 'Uploading and processing PDF...', 'processing');
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
            let response;

            if (isLargeFile && isGoogleDriveConnected) {
                // Upload to user's Drive
                const driveFileId = await uploadFileToUserDrive(file);
                response = await fetch('/process_pdf', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ drive_file_id: driveFileId })
                });
            } else {
                // Standard Upload
                const formData = new FormData(); formData.append('pdf_file', file);
                response = await fetch('/process_pdf', { method: 'POST', body: formData });
            }

            clearInterval(progressInterval); uploadProgress.style.width = '100%';

            if (!response.ok) {
                let errorMsg = `Server error: ${response.status} ${response.statusText}`;
                try { const errorData = await response.json(); errorMsg = errorData.error || errorMsg; } catch (e) { }
                throw new Error(errorMsg);
            }
            responseData = await response.json();
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
            const result = await response.json();
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

        try {
            const response = await fetch('/save_report', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(finalDataToSend)
            });
            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || `Server error: ${response.status}`);
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

        // Drive auto-upload status
        const driveStatus = document.createElement('span');
        driveStatus.style.marginLeft = '10px';
        driveStatus.style.display = 'inline-flex';
        driveStatus.style.alignItems = 'center';
        driveStatus.style.gap = '5px';
        if (driveLink) {
            driveStatus.innerHTML = `<i class="fas fa-check-circle" style="color: #22c55e;"></i> <a href="${driveLink}" target="_blank" style="color: #22c55e;">Saved to Drive</a>`;
        } else {
            driveStatus.innerHTML = `<i class="fas fa-exclamation-circle" style="color: #f59e0b;"></i> <span style="color: #f59e0b; font-size: 0.85em;">Drive upload pending</span>`;
        }
        downloadLinksDiv.appendChild(driveStatus);

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

    function renderSavedReports(reports) {
        savedReportsTbody.innerHTML = '';
        if (reports.length === 0) {
            savedReportsTbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 1rem; color: var(--text-muted);">No saved reports found.</td></tr>';
            return;
        }
        reports.forEach(report => {
            const row = savedReportsTbody.insertRow();
            row.innerHTML = `
                <td>${report.report_no || 'N/A'}</td>
                <td>${report.vehicle_no || 'N/A'}</td>
                <td>${report.insured_name || 'N/A'}</td>
                <td>${report.saved_at || 'N/A'}</td>
                <td class="action-cell">
                    <button type="button" class="btn btn-primary btn-sm load-report-btn" data-report-id="${report.id}">
                        <i class="fas fa-folder-open"></i> Load
                    </button>
                    <button type="button" class="btn btn-danger btn-sm delete-report-btn" data-report-id="${report.id}" data-report-no="${report.report_no}">
                        <i class="fas fa-trash-alt"></i> Delete
                    </button>
                </td>
            `;
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
        const reportId = button.dataset.reportId;
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
            displayPreview(reportData, reportId);
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

    // --- Initial Load ---
    updateSteps('upload');
    fetchSavedReports();

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
                const result = await response.json();

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
                    profileModal.classList.remove('hidden');
                } else {
                    alert("Failed to load profile settings.");
                }
            } catch (e) {
                console.error(e);
                alert("Error loading profile settings.");
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
            } catch (e) {
                console.error(e);
                alert("Error updating profile.");
            }
        });
    }

});