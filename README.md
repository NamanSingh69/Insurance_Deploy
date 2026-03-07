# Insurance Survey Report Generator (Private Freelance Project)

> ⚠️ **This is a private, proprietary freelance project. Source code is not publicly available.**

## Portfolio Summary

**Client**: Insurance industry (India)  
**Role**: Full-stack developer  
**Status**: ✅ Production (deployed on Render)

## What I Built

An AI-powered insurance survey report generator that automates the extraction of data from motor insurance claim documents (PDFs) and generates professionally formatted survey reports and repair assessment summaries.

### Key Features
- 📄 **AI-Powered PDF Extraction** — Gemini AI extracts 50+ structured fields from insurance claim documents
- 🔧 **Dual Processing Modes** — Full document processing + invoice-only parts extraction
- 📊 **Assessment Calculator** — Automated depreciation, GST (CGST/SGST/IGST), and net liability calculations
- 🖨️ **Professional PDF Generation** — Multi-page survey reports with Indian format number-to-words conversion
- 🔐 **Multi-User Auth** — Flask-Login with bcrypt password hashing
- 📋 **Google Sheets Database** — Production data stored in Google Sheets (replacing SQLite)
- ☁️ **Google Drive Integration** — OAuth2 file upload with resumable chunked uploads
- 📊 **Consolidated Reports** — Multi-report CSV export and XLSX generation

### Technology Stack
| Layer | Technology |
|-------|-----------|
| Backend | Flask, Python 3.10 |
| AI | Google Generative AI (Gemini 3 Flash Preview, Gemini 2.5 Pro) |
| PDF Engine | FPDF2, ReportLab |
| Database | Google Sheets (via gspread) |
| Auth | Flask-Login + Flask-Bcrypt |
| Cloud | Google Drive API (OAuth2), Render |
| Frontend | Jinja2 Templates, Server-rendered HTML |

### Architecture
```
[User] → [Flask Web App (Render)]
              ├─→ [Gemini AI] (PDF extraction)
              ├─→ [Google Sheets] (persistent storage)
              ├─→ [Google Drive] (file uploads via OAuth2)
              └─→ [FPDF2] (PDF report generation)
```

## 🔑 API Configuration
- **Gemini API Key**: Via [Google AI Studio](https://aistudio.google.com/app/apikey) (free tier)
- **Model Fallback**: Primary `gemini-3-flash-preview` → Fallback `gemini-2.5-pro`
- **Google OAuth2**: For Drive file upload integration
