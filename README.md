# InvoiceIQ — AI-Assisted Invoice Processing & Exception Investigation

InvoiceIQ is an end-to-end invoice verification application built for **Problem Statement 1 (PS-1)**. It automates the initial accounts-payable checks performed when supplier invoices are received: document extraction, vendor verification, purchase-order matching, financial validation, duplicate detection and exception identification.

The core design principle is simple: **AI understands the invoice; deterministic Python rules validate it and determine the outcome.** The LLM does not approve invoices or make financial decisions.

## 1. Problem and Solution

Supplier invoices arrive in different layouts and formats. They may be digitally generated, scanned or contain a mixture of both. Important information can appear in different places, line items may be bundled or itemised, tax may be included in prices or shown separately, and PO references may be explicit or missing.

InvoiceIQ addresses this workflow through a modular processing pipeline. It extracts invoice information from PDF documents, validates the extracted fields against vendor and purchase-order reference data, checks financial and item-level consistency, and produces one of three outcomes:

| Outcome | Meaning |
|---|---|
| `APPROVED` | Required validation checks pass. |
| `REJECTED` | A blocking issue, such as an unregistered vendor or confirmed duplicate, is identified. |
| `PENDING_REVIEW` | An ambiguity, discrepancy or incomplete validation needs human investigation. |

A potential duplicate or uncertain match is treated as an exception to investigate, not automatically as proof of fraud or duplication.

## 2. Key Features

- **PDF invoice intake:** Accepts digital, scanned and mixed-content PDF invoices.
- **Document routing:** Uses PyMuPDF for digital text extraction and Tesseract OCR for scanned pages.
- **LLM-assisted extraction:** Uses Qwen2.5 through Ollama when available, with Groq as a fallback backend.
- **Structured extraction:** Uses Pydantic to validate the extracted invoice fields and line items. Evidence can retain flexible source structures returned by the model.
- **Vendor verification:** Checks supplier identity and registration information against the vendor master.
- **PO matching:** Validates explicit PO references and identifies possible candidates when a reference is absent or unclear.
- **Item reconciliation:** Compares invoice item descriptions/codes, quantities and unit prices with PO line items.
- **Financial validation:** Checks line arithmetic, subtotal, tax, invoice total and configured tolerances.
- **Duplicate detection:** Uses file-level and invoice-level signals to identify exact or potential duplicates.
- **Cumulative billing checks:** Considers previously processed invoices against PO quantity and value limits, helping identify split-invoice overbilling.
- **Human-in-the-loop handling:** Sends uncertain or inconsistent cases to `PENDING_REVIEW` instead of guessing.
- **Reference-data management:** Provides a Manage Database page for uploading, previewing, validating and importing vendor and PO CSV data.
- **Audit history and dashboard:** Uses SQLite to store processing records and validation information for application history and dashboard views.
- **Resilient Groq requests:** Retries selected transient failures, including Groq JSON-generation validation failures, up to three attempts when that retry logic is enabled in `llm_client.py`.
- **Automated tests:** Includes a pytest suite for core modules and regression checks.

## 3. Application Pages

### Dashboard

Provides a summary of invoice processing activity, decision statuses and recent processing history.

### Process Invoice

Accepts a PDF invoice and runs the extraction and validation pipeline. The results are organised into:

- **Overview:** Invoice summary and final decision.
- **Extracted Fields:** Structured invoice and vendor information returned by extraction.
- **Validation Details:** Individual checks and their outcomes.
- **Decision Explanation:** Reasons supporting the final status.

### Manage Database

Allows the user to manage the reference data used during verification. Vendor and purchase-order CSV uploads are validated and previewed before the user explicitly confirms an import. The page also displays the currently loaded reference records.

## 4. System Architecture

```text
                         PDF Invoice Upload
                                  |
                                  v
                          Document Router
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
             Digital PDF Text                Scanned Page
               (PyMuPDF)                   (Tesseract OCR)
                    |                           |
                    +-------------+-------------+
                                  |
                                  v
                           Extracted Text
                                  |
                                  v
                         LLM Extraction Layer
                                  |
                      +-----------+-----------+
                      |                       |
                      v                       v
                 Ollama / Qwen             Groq API
                 (primary)                (fallback)
                      |                       |
                      +-----------+-----------+
                                  |
                                  v
                         Structured JSON
                                  |
                                  v
                         Pydantic Validation
                                  |
                                  v
                      Deterministic Validation
                                  |
          +-----------------------+-----------------------+
          |            |           |          |           |
          v            v           v          v           v
       Vendor       PO Match    Duplicate  Financial    Item-level
       Checks                   Checks     Checks    Reconciliation
          |            |           |          |           |
          +------------+-----------+----------+-----------+
                                  |
                                  v
                            Decision Engine
                                  |
                 +----------------+----------------+
                 |                |                |
                 v                v                v
              APPROVED          REJECTED      PENDING_REVIEW
                 |                |                |
                 +----------------+----------------+
                                  |
                                  v
                         SQLite Audit Storage
                                  |
                                  v
                        Streamlit Dashboard
```

### Processing Workflow

1. The user uploads a PDF through the Streamlit interface.
2. The document router determines whether pages contain extractable digital text or need OCR.
3. PyMuPDF extracts digital text; Tesseract OCR processes scanned pages.
4. The extracted text is sent to the LLM extraction layer. The application attempts Ollama first and falls back to Groq if the primary backend is unavailable or fails.
5. The model returns structured invoice data. Pydantic validates the result against the invoice schema.
6. Python validation modules check vendor details, PO matching, duplicates, financial values and item-level reconciliation.
7. The decision engine applies the configured business rules and assigns the final status.
8. Processing details and validation outcomes are written to SQLite.
9. The dashboard displays the resulting activity and decision information.

## 5. Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Programming language | Python | Core application and business logic |
| Frontend | Streamlit | Dashboard, invoice processing and reference-data interface |
| PDF processing | PyMuPDF | Digital PDF text extraction |
| OCR | Tesseract OCR | Text extraction from scanned pages |
| Primary LLM runtime | Ollama | Local model execution |
| Primary local model | Qwen2.5 1.5B | Structured invoice information extraction |
| Fallback LLM | Groq API | Hosted extraction when Ollama is unavailable or fails |
| Fallback model | Configurable; default `openai/gpt-oss-20b` | Structured invoice extraction through Groq |
| Data validation | Pydantic | Invoice schema and field validation |
| Data processing | Pandas | Reference-data and tabular operations |
| Database | SQLite | Invoice processing records, reference data and audit information |
| Configuration | YAML | Business rules and processing thresholds |
| Visualization | Plotly | Dashboard charts |
| Testing | Pytest | Unit and regression tests |

## 6. Project Structure

The main modules are organised as follows. Individual repositories may contain additional helper files or tests.

```text
InvoiceIQ/
├── app.py
├── setup_database.py
├── requirements.txt
├── README.md
├── config/
│   └── rules.yaml
├── data/
│   ├── invoices/
│   ├── vendors.csv
│   ├── purchase_orders.csv
│   └── invoiceiq.db
├── src/
│   ├── ingestion/
│   │   ├── pdf_reader.py
│   │   ├── ocr_engine.py
│   │   └── document_router.py
│   ├── extraction/
│   │   ├── llm_client.py
│   │   ├── llm_extractor.py
│   │   ├── prompts.py
│   │   └── schemas.py
│   ├── matching/
│   │   ├── po_matcher.py
│   │   ├── semantic_matcher.py
│   │   └── item_reconciler.py
│   ├── validation/
│   │   ├── financial_checks.py
│   │   ├── duplicate_detector.py
│   │   ├── vendor_checks.py
│   │   └── anomaly_detector.py
│   ├── decision/
│   │   ├── rules_engine.py
│   │   └── explanation.py
│   └── database/
│       ├── db.py
│       └── repository.py
├── tests/
└── sample_invoices/
```

## 7. Local Installation and Setup

### Prerequisites

- Python 3.10 or later
- Tesseract OCR installed and available to the application
- Ollama installed, if using the local primary extraction backend
- A Groq API key, if using the fallback backend
- Git (optional, for cloning the repository)

### 1. Clone the repository

```bash
git clone https://github.com/Half-Bl00d-Pr1nce/InvoiceIQ.git
cd InvoiceIQ
```

### 2. Create and activate a virtual environment

**Windows**

```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Tesseract OCR

Install Tesseract OCR for your operating system and make sure its executable is available in the system PATH. On Windows, configure the executable path in the OCR configuration/module if it is not detected automatically.

### 5. Configure Ollama

Install Ollama from [ollama.com](https://ollama.com/) and download the configured local model:

```bash
ollama pull qwen2.5:1.5b
```

Make sure the Ollama service is running before processing invoices locally.

### 6. Configure the Groq fallback

Set the following environment variables in a local `.env` file or your environment. Keep credentials out of source control.

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-20b
```

Optional settings are:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:1.5b
GROQ_API_URL=https://api.groq.com/openai/v1/chat/completions
```

The application reads Streamlit secrets when available and otherwise falls back to environment variables. Do not commit `.env` files or expose API keys in screenshots, logs or the repository.

## 8. Database Setup

InvoiceIQ uses SQLite as its lightweight relational database. It stores application data used for invoice processing, reference data and audit/history views.

The reference data includes vendor and purchase-order records. In a local setup, the repository may provide CSV files under `data/`. To initialise the database and load the default reference data, run:

```bash
python setup_database.py
```

The Manage Database page also supports uploading vendor and PO CSV files, validating them, previewing the data and explicitly confirming the import.

**Deployment note:** SQLite is file-based. On a local machine, the database file remains on disk unless it is removed. On hosted environments such as Streamlit Community Cloud, local application storage may be ephemeral and can reset after a restart or redeployment. Do not treat the deployed SQLite file as permanent production storage. For durable multi-user operation, use a managed persistent database.

## 9. Running the Application

Start the app from the project root:

```bash
streamlit run app.py
```

Open the local address printed by Streamlit, typically:

```text
http://localhost:8501
```

### Basic application workflow

1. Open Dashboard to inspect the current processing activity.
2. Open Manage Database and load the vendor and PO reference data required for the test invoice.
3. Open Process Invoice and upload a digital, scanned or mixed PDF invoice.
4. Start processing and allow document extraction and validation to complete.
5. Review the extracted fields, individual validation results and final decision explanation.

## 10. Streamlit Community Cloud Deployment

InvoiceIQ can be deployed as a Streamlit application. The hosted environment does not automatically have access to an Ollama server running on a developer's computer. In the current Ollama-first configuration, the extraction layer attempts Ollama and then uses Groq as the fallback when Ollama is unavailable.

For a hosted deployment:

1. Push the project to GitHub.
2. Create or open the app in Streamlit Community Cloud and point it to the repository and `app.py`.
3. Ensure the deployment environment has the required Python packages and Tesseract OCR binary available.
4. In the Streamlit app's **Secrets** settings, configure the credentials and model settings:

```toml
GROQ_API_KEY = "your_groq_api_key"
GROQ_MODEL = "openai/gpt-oss-20b"
```

5. Restart/redeploy the app after changing deployment settings.
6. Open Manage Database and import the vendor and PO data needed for the demonstration.
7. Test both a digital PDF and a scanned PDF before sharing the deployment link.

Never place the Groq API key directly in `app.py`, commit it to GitHub or include it in the README. The hosted SQLite file may reset, so re-import demo reference data when necessary and avoid relying on it for permanent records.

## 11. Business Validation and Decision Logic

InvoiceIQ separates document understanding from financial and procurement decisions. The LLM extracts the invoice fields; Python modules independently apply the business rules.

### Vendor validation

- Checks vendor identifiers and tax registration details against the vendor master.
- Identifies vendors that are not registered or are inactive.
- Detects conflicting vendor identifiers.

### Purchase-order matching

- Validates an explicitly supplied PO reference.
- Checks PO ownership and status.
- Can suggest possible PO candidates when the reference is missing.
- Routes ambiguous matches for human review rather than selecting an uncertain PO automatically.

### Financial validation

- Checks line-item arithmetic and subtotal calculations.
- Validates invoice totals and tax amounts.
- Compares expected PO tax information with invoice tax when sufficient reference data is available.
- Applies configurable amount tolerances.

### Item reconciliation and cumulative billing

- Matches invoice items against PO items using item identifiers and descriptions.
- Compares quantities and unit prices.
- Tracks billed quantity/value across invoices associated with the same PO.
- Identifies when cumulative billing exceeds the PO quantity or value.
- Avoids making uncertain allocations for bundled invoice items.

### Duplicate detection

Uses more than one signal, including:

- Exact file hash comparison.
- Vendor and invoice number comparison.
- Vendor, invoice date and amount comparison.

A similarity signal can result in a review flag; it is not necessarily proof that two invoices are the same.

### Decision engine

The decision engine evaluates the validation results and returns `APPROVED`, `REJECTED` or `PENDING_REVIEW`. The LLM does not select the final status.

## 12. Configurable Business Rules

Processing policies are maintained in `config/rules.yaml`. Configurable examples include:

- Required invoice fields.
- PO matching thresholds.
- Percentage and absolute amount tolerances.
- Duplicate detection settings.
- Decision outcomes for validation failures.

The demonstration configuration uses a **2% percentage tolerance with an absolute cap of ₹100, whichever is lower**. These are configurable case-study assumptions, not universal accounting or procurement standards.

## 13. Edge-Case Testing

The project was designed to evaluate several invoice scenarios beyond a straightforward successful invoice.

| Test case | Scenario | Intended handling / observed result |
|---|---|---|
| EC1 | Split invoices against one PO and cumulative quantity limit | Earlier invoice can pass; a subsequent invoice that takes cumulative billed quantity beyond the PO limit is sent for review. |
| EC2 | Missing PO reference with multiple plausible matches | `PENDING_REVIEW` rather than guessing the PO. |
| EC3 | Invoice from an unregistered vendor | `REJECTED`. |
| EC4 | Invoice unit price higher than the PO price | `PENDING_REVIEW`. |
| EC5 | Partial invoice with an incorrect unit price | `PENDING_REVIEW`. |
| EC6 | Incorrect GST amount | Exposed a validation gap in an earlier implementation. |
| EC7 | Incorrect GST rate/amount compared with PO tax expectations | `PENDING_REVIEW` after the additional PO tax validation check was introduced. |

The split-invoice scenario demonstrates why the system checks cumulative billed quantity/value across invoice history rather than validating each invoice in isolation.

Run the test suite with:

```bash
pytest tests/ -v
```

## 14. LLM Fallback and Error Handling

The extraction layer is designed to try the local Ollama backend first and fall back to Groq if the local backend is unavailable or fails. This makes the same extraction interface usable in a local development environment and in a hosted environment where a local Ollama service is not present.

The Groq client can retry selected transient failures, including JSON-generation validation failures, up to three attempts with short delays between attempts. Non-retryable API errors are surfaced without repeatedly sending the same request. The retry mechanism improves resilience but cannot guarantee that an external model API will always be available or return valid structured output.

At the UI level, an unsuccessful processing attempt should display a user-friendly message rather than exposing a full Python traceback. Technical error information can be inspected in the application logs during debugging.

## 15. Design Decisions

### AI for extraction, Python for decisions

LLMs are useful for interpreting varying invoice layouts and extracting semi-structured information. Financial calculations, reconciliation and final decisions remain deterministic Python operations so they can be tested and explained.

### Ollama-first with Groq fallback

Ollama supports local inference during development. Groq provides a hosted fallback for environments where a local Ollama service is unavailable. API credentials are stored in environment variables or Streamlit secrets, not source code.

### Human review for uncertain cases

Ambiguous PO matches, discrepancies, possible duplicates and incomplete data are routed to human review instead of being silently accepted.

### Cumulative checks

PO limits apply across invoices, not just to an individual invoice. Maintaining processing history enables the application to identify split billing that would be missed by invoice-by-invoice checks.

### Modular architecture

Ingestion, extraction, matching, validation, decision-making and database operations are separated into modules, making the system easier to test and maintain.

## 16. Limitations and Future Improvements

InvoiceIQ is a case-study implementation and proof of concept, not a complete production accounts-payable platform.

Current limitations include:

- LLM extraction quality can vary with scan quality, invoice layout, document complexity and model/API availability.
- OCR accuracy depends on image resolution, skew, contrast and legibility.
- Retrying selected API errors reduces intermittent failures but cannot eliminate external service failures.
- Local CPU inference may introduce processing delays.
- Semantic matching may not capture every contextual relationship between invoice and PO descriptions.
- Validation quality depends on accurate vendor and PO reference data.
- External ERP, banking and GST verification integrations are not included.
- Email mailbox intake is not included; PDF upload is used to simulate invoice intake.
- Human review remains necessary for ambiguous or unsupported cases.
- Hosted SQLite storage may be reset and is not intended as durable production storage.

Potential future improvements include:

- Persistent managed database integration for hosted deployments.
- ERP and accounting platform integration.
- Email-based invoice intake.
- More advanced semantic item matching and bundled-item allocation.
- Extraction confidence calibration and field-level review.
- Role-based exception review and approval workflows.
- Monitoring, structured logging and performance optimisation for higher invoice volumes.

## 17. Conclusion

InvoiceIQ demonstrates an AI-assisted approach to invoice processing that combines document extraction with deterministic procurement and financial validation. By supporting digital and scanned PDFs, vendor and PO verification, item reconciliation, cumulative billing checks, duplicate detection and human-in-the-loop exception handling, it provides an end-to-end workflow for the PS-1 case study.

The key principle remains that **AI assists with understanding the document, while explicit Python rules remain responsible for validation and decisions**. This separation makes the workflow more transparent, explainable and testable.

---

**Built as an AI-assisted invoice processing and exception investigation solution for Problem Statement 1 (PS-1).**
