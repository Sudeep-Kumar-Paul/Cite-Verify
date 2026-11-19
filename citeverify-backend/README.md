# CiteVerify Backend

AI-powered scientific claim and citation verification platform for academic documents.

## Features
- **PDF Processing**: Upload academic PDFs and extract text using PyMuPDF
- **Claim Extraction**: AI-powered identification of scientific claims using Google Gemini
- **Citation Detection**: Regex + AI parsing of numbered, author-year, and narrative citations
- **Reference Matching**: Fuzzy matching of in-text citations to bibliography entries
- **Paper Discovery**: Semantic Scholar API + Crossref REST API integration
- **Evidence Retrieval**: Open-access PDF download and text extraction
- **Claim Verification**: Gemini-powered evidence comparison with strict accuracy safeguards
- **Verdict Classification**: SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, CONTRADICTORY, NEEDS_HUMAN_REVIEW, POSSIBLY_OUTDATED
- **PDF Reports**: Professional ReportLab-generated downloadable reports
- **REST API**: Full FastAPI backend with Swagger documentation
- **Verification History**: Document and verification history tracking

## Tech Stack

| Component | Technology |
|-----------|-----------|
| API Framework | FastAPI + Uvicorn |
| AI Engine | Google Gemini API (`google-genai` SDK) |
| PDF Processing | PyMuPDF (fitz) |
| Academic Search | Semantic Scholar API + Crossref REST API |
| Database | SQLite + SQLAlchemy 2.0 |
| Reports | ReportLab |
| Validation | Pydantic v2 |
| Testing | pytest + pytest-asyncio + pytest-mock |

## Project Structure

```
citeverify-backend/
├── app/
│   ├── main.py                          # FastAPI app entry point
│   ├── config.py                        # Settings (pydantic-settings)
│   ├── database.py                      # SQLAlchemy engine + session
│   ├── api/routes/
│   │   ├── documents.py                 # Upload, extract, list documents
│   │   ├── claims.py                    # Claim extraction and management
│   │   ├── citations.py                 # Citation extraction and matching
│   │   ├── verification.py              # Run and retrieve verifications
│   │   ├── reports.py                   # Generate and download reports
│   │   └── history.py                   # Verification history
│   ├── core/
│   │   ├── exceptions.py               # Custom exceptions + handlers
│   │   └── security.py                  # File validation + path safety
│   ├── models/                          # SQLAlchemy ORM models
│   │   ├── document.py
│   │   ├── claim.py
│   │   ├── citation.py
│   │   ├── source.py
│   │   └── verification.py
│   ├── schemas/                         # Pydantic request/response schemas
│   │   ├── document.py
│   │   ├── claim.py
│   │   ├── citation.py
│   │   ├── verification.py
│   │   └── report.py
│   ├── services/
│   │   ├── pdf_service.py              # File storage
│   │   ├── text_extraction_service.py  # PDF text extraction
│   │   ├── gemini_service.py           # Gemini AI integration
│   │   ├── claim_extraction_service.py # Claim identification
│   │   ├── citation_extraction_service.py  # Citation parsing
│   │   ├── reference_matching_service.py   # Bibliography matching
│   │   ├── paper_search_service.py     # Semantic Scholar
│   │   ├── crossref_service.py         # DOI verification
│   │   ├── evidence_retrieval_service.py   # Paper download + text
│   │   ├── verification_service.py     # Core verification engine
│   │   └── report_service.py          # PDF report generation
│   └── utils/
│       ├── text_cleaner.py             # Text processing utilities
│       ├── doi_utils.py                # DOI extraction and validation
│       └── confidence.py              # Confidence scoring
├── uploads/                            # Uploaded PDFs (auto-created)
├── reports/                            # Generated reports (auto-created)
├── tests/
│   └── test_citeverify.py              # Complete pytest test suite
├── .env.example                        # Environment variable template
├── requirements.txt                    # Python dependencies
└── README.md
```

## Windows Setup (PowerShell)

### 1. Prerequisites

```powershell
python --version   # Must be 3.10+
pip --version
```

### 2. Navigate to project

```powershell
Set-Location "c:\Users\YourName\Documents\CiteVerify\citeverify-backend"
```

### 3. Create virtual environment

```powershell
python -m venv venv
```

### 4. Activate virtual environment

```powershell
.\venv\Scripts\Activate.ps1

# If you get an execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\Activate.ps1
```

### 5. Install dependencies

```powershell
pip install -r requirements.txt
```

### 6. Configure environment

```powershell
Copy-Item .env.example .env
notepad .env
```

Add your Gemini API key:
```
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 7. Start the development server

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 8. Run tests

```powershell
pytest tests/ -v
```

> [!NOTE]
> Tests use mocked Gemini and external API responses — no API key required for testing.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/` | API info and links |
| POST | `/api/documents/` | Upload a PDF document |
| GET | `/api/documents/` | List all uploaded documents |
| GET | `/api/documents/{id}` | Get document details |
| POST | `/api/documents/{id}/extract` | Extract text from PDF |
| DELETE | `/api/documents/{id}` | Delete document |
| POST | `/api/documents/{id}/extract-claims` | Extract scientific claims |
| GET | `/api/documents/{id}/claims` | Get extracted claims |
| DELETE | `/api/documents/{id}/claims/{claim_id}` | Remove a claim |
| POST | `/api/documents/{id}/extract-citations` | Parse citations and bibliography |
| GET | `/api/documents/{id}/citations` | Get all citations |
| POST | `/api/documents/{id}/match-citations` | Match in-text citations to references |
| POST | `/api/verification/run` | Run AI verification |
| GET | `/api/verification/documents/{id}/results` | Get verification results |
| GET | `/api/reports/{id}` | Get report summary (JSON) |
| POST | `/api/reports/{id}/export` | Generate PDF report |
| GET | `/api/reports/{id}/download` | Download PDF report |
| GET | `/api/history/` | Verification history |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | ✅ Yes | — | Google Gemini API key |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Gemini model to use |
| `APP_ENV` | No | `development` | Environment name |
| `DEBUG` | No | `true` | Enable debug logging |
| `SECRET_KEY` | No | — | App secret key |
| `CORS_ORIGINS` | No | `localhost:3000,localhost:8501` | Comma-separated allowed origins |
| `MAX_UPLOAD_SIZE_MB` | No | `50` | Max PDF upload size in MB |
| `DATABASE_URL` | No | `sqlite:///./citeverify.db` | SQLAlchemy database URL |
| `SEMANTIC_SCHOLAR_API_KEY` | No | — | Optional; increases rate limits |
| `CROSSREF_EMAIL` | No | — | Polite pool access for Crossref |
| `EXTERNAL_API_TIMEOUT_SECONDS` | No | `30` | External API timeout |

## Verification Verdicts

| Verdict | Meaning |
|---------|---------|
| `SUPPORTED` | Evidence clearly and directly supports the claim |
| `PARTIALLY_SUPPORTED` | Evidence supports part of the claim or adds major caveats |
| `UNSUPPORTED` | Evidence does not support the claim (but doesn't contradict it) |
| `CONTRADICTORY` | Evidence directly conflicts with or disproves the claim |
| `NEEDS_HUMAN_REVIEW` | Insufficient evidence for automated determination |
| `POSSIBLY_OUTDATED` | Supported by source but findings may now be outdated |

## API Usage Examples

### Upload a document
```bash
curl -X POST http://127.0.0.1:8000/api/documents/ \
  -F "file=@my_paper.pdf"
```

### Extract text
```bash
curl -X POST http://127.0.0.1:8000/api/documents/{id}/extract
```

### Extract claims
```bash
curl -X POST http://127.0.0.1:8000/api/documents/{id}/extract-claims
```

### Run verification
```bash
curl -X POST http://127.0.0.1:8000/api/verification/run \
  -H "Content-Type: application/json" \
  -d '{"document_id": "{id}"}'
```

### Export report
```bash
curl -X POST http://127.0.0.1:8000/api/reports/{id}/export \
  -H "Content-Type: application/json" \
  -d '{"document_id": "{id}", "include_evidence_passages": true}'
```

## Troubleshooting (Windows)

**"Execution policy" error on venv activation**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**PyMuPDF import error**
```powershell
pip uninstall PyMuPDF -y
pip install PyMuPDF==1.24.3
```

**Port 8000 already in use**
```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

**Gemini API errors**
- Ensure `GEMINI_API_KEY` is set in your `.env` file
- Verify API key at https://aistudio.google.com/

**`fuzzywuzzy` warning about python-Levenshtein**
```powershell
pip install python-Levenshtein
```

## Limitations (MVP)

- Scanned PDFs are detected and flagged — OCR not included in v1
- Paywalled papers fall back to abstract-only evidence (reduces confidence)
- Citation style parsing uses regex heuristics; complex hybrid styles may need Gemini fallback
- Semantic Scholar and Crossref have rate limits; automatic exponential backoff is implemented
- English-language documents are the primary target
