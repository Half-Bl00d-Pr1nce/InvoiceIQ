# InvoiceIQ — AI-Assisted Invoice Processing & Exception Investigation

## 1. Project Overview

InvoiceIQ is an AI-assisted invoice processing system designed to automate the extraction, verification and validation of supplier invoices.

In a typical organisation, finance teams receive invoices in different PDF formats, manually extract invoice details, compare them against purchase orders, verify vendor information and investigate discrepancies. This process can be time-consuming and prone to human error.

InvoiceIQ addresses this problem through an automated processing pipeline that combines local Large Language Model (LLM) extraction with deterministic business-rule validation.

The system extracts structured information from invoice PDFs, validates the extracted data against vendor and purchase order records, performs financial checks and assigns a final processing decision.

**The central design principle is that AI extracts and interprets invoice information, while deterministic Python logic performs financial calculations and makes the final decision.**

## 2. Key Features

- **PDF Invoice Ingestion:** Supports digital, scanned and mixed-content PDF documents.
- **OCR Processing:** Uses Tesseract OCR to extract text from scanned invoice pages.
- **LLM-Based Extraction:** Uses a locally hosted Qwen2.5 model to extract structured invoice information.
- **Structured Data Validation:** Uses Pydantic schemas to validate extracted invoice fields.
- **Vendor Verification:** Checks vendor identity and registration details against the approved vendor master.
- **Purchase Order Matching:** Supports explicit PO matching and suggests candidates when a PO reference is missing.
- **Item-Level Reconciliation:** Compares invoice descriptions, item codes, quantities and prices against purchase order details.
- **Financial Validation:** Checks subtotal calculations, tax amounts, invoice totals and PO-related tax expectations.
- **Duplicate Detection:** Identifies duplicate invoices using file hashes and invoice-related information.
- **Cumulative Billing Validation:** Tracks invoices billed against a purchase order to identify quantity and monetary limit violations.
- **Exception Handling:** Routes uncertain or inconsistent invoices for human review.
- **Audit Trail:** Stores processing information, validation results and invoice decisions in SQLite.
- **Interactive Dashboard:** Provides an overview of invoice processing activity and decision status.

## 3. System Architecture

InvoiceIQ follows a modular processing architecture.

```text
                 Invoice PDF Upload
                         |
                         v
                 Document Ingestion
                         |
                         v
              Document Type Detection
                         |
             +-----------+-----------+
             |                       |
             v                       v
       Digital Extraction       OCR Processing
          (PyMuPDF)             (Tesseract)
             |                       |
             +-----------+-----------+
                         |
                         v
                Extracted Text
                         |
                         v
               LLM-Based Extraction
                 (Ollama + Qwen)
                         |
                         v
              Structured Data Schema
                    (Pydantic)
                         |
                         v
                Validation Pipeline
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
     Duplicate       Vendor Check    PO Matching
     Detection                       & Matching
          |              |              |
          +--------------+--------------+
                         |
                         v
                Financial Validation
                         |
                         v
                Item Reconciliation
                         |
                         v
                 Decision Engine
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
          APPROVED    REJECTED   PENDING_REVIEW
             |           |           |
             +-----------+-----------+
                         |
                         v
                SQLite Audit Storage
                         |
                         v
                 Streamlit Dashboard
```

### Processing Workflow

1. The user uploads an invoice PDF through the Streamlit interface.
2. The document router identifies whether each page contains digital text or requires OCR.
3. PyMuPDF extracts digital text, while Tesseract processes scanned pages.
4. The extracted text is passed to the local Qwen2.5 model.
5. The LLM returns structured invoice information, which is validated using Pydantic.
6. The validation modules check duplicates, vendor details, PO references, item information and financial calculations.
7. The decision engine evaluates the validation results and assigns the final invoice status.
8. Processing information and validation results are stored in SQLite.
9. The dashboard displays invoice activity and processing decisions.

## 4. Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Programming Language | Python | Core application logic |
| Frontend | Streamlit | Interactive dashboard and invoice processing interface |
| PDF Processing | PyMuPDF | Digital PDF text extraction |
| OCR | Tesseract OCR | Scanned document text extraction |
| LLM | Qwen2.5 1.5B | Structured invoice information extraction |
| LLM Runtime | Ollama | Local model execution |
| Data Validation | Pydantic | Structured schema validation |
| Data Processing | Pandas | Reference data and tabular operations |
| Database | SQLite | Invoice records and audit information |
| Configuration | YAML | Business rules and processing thresholds |
| Testing | Pytest | Unit and regression testing |
| Visualization | Plotly | Dashboard visualizations |

## 5. Project Structure

```text
InvoiceIQ/
│
├── app.py
├── setup_database.py
├── requirements.txt
├── README.md
│
├── config/
│   └── rules.yaml
│
├── data/
│   ├── invoices/
│   ├── vendors.csv
│   ├── purchase_orders.csv
│   └── invoiceiq.db
│
├── src/
│   ├── ingestion/
│   │   ├── pdf_reader.py
│   │   ├── ocr_engine.py
│   │   └── document_router.py
│   │
│   ├── extraction/
│   │   ├── llm_extractor.py
│   │   ├── prompts.py
│   │   └── schemas.py
│   │
│   ├── matching/
│   │   ├── po_matcher.py
│   │   ├── semantic_matcher.py
│   │   └── item_reconciler.py
│   │
│   ├── validation/
│   │   ├── financial_checks.py
│   │   ├── duplicate_detector.py
│   │   ├── vendor_checks.py
│   │   └── anomaly_detector.py
│   │
│   ├── decision/
│   │   ├── rules_engine.py
│   │   └── explanation.py
│   │
│   └── database/
│       ├── db.py
│       └── repository.py
│
├── tests/
│
└── sample_invoices/
```

*Note: The structure above describes the main project modules. Additional scripts and test files may be present.*

## 6. Installation and Setup

### Prerequisites

Install the following before running InvoiceIQ:

- Python 3.10 or later
- Ollama
- Tesseract OCR
- Git (optional, for cloning the repository)

### Step 1: Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd InvoiceIQ
```

Alternatively, download the project and open its root directory in a terminal.

### Step 2: Create a Virtual Environment

For Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

For Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Install and Configure Tesseract OCR

Install Tesseract OCR and ensure it is available in your system PATH.

On Windows, if necessary, configure the executable location in the OCR module.

### Step 5: Install and Start Ollama

Install Ollama from:

https://ollama.com/

Pull the model:

```bash
ollama pull qwen2.5:1.5b
```

Ensure the Ollama service is running before starting invoice processing.

## 7. Database Setup

InvoiceIQ uses SQLite to store invoice records, validation results, processing logs and reference information.

The reference data is maintained in:

- `data/vendors.csv`
- `data/purchase_orders.csv`

Run the database setup script:

```bash
python setup_database.py
```

This initializes the database and loads the vendor and purchase order reference data.

## 8. Running the Application

After completing the installation and database setup, start the Streamlit application:

```bash
streamlit run app.py
```

Open the local URL displayed in the terminal, typically:

```text
http://localhost:8501
```

### Application Workflow

1. Open the Dashboard to view invoice processing statistics.
2. Navigate to Process Invoice.
3. Upload a supplier invoice PDF.
4. Start the processing workflow.
5. Review extracted invoice information and validation results.
6. Inspect the final decision and any exceptions identified.

## 9. Business Validation and Decision Logic

InvoiceIQ separates information extraction from business validation.

The LLM is responsible for interpreting invoice documents and extracting structured fields. Python validation modules independently verify the extracted information.

### Vendor Validation

- Checks vendor identifiers and GSTIN against the vendor master.
- Identifies unregistered vendors.
- Detects conflicts between vendor identifiers.
- Checks whether the vendor is active.

### Purchase Order Matching

- Validates explicitly supplied PO references.
- Checks PO ownership and status.
- Suggests possible PO candidates when the reference is missing.
- Routes ambiguous matches for human review rather than automatically selecting an uncertain PO.

### Financial Validation

- Verifies line-item arithmetic.
- Checks subtotal and invoice total calculations.
- Validates tax amounts and tax treatment.
- Compares expected PO tax against the invoice tax when sufficient information is available.
- Applies configurable amount tolerances.

### Item Reconciliation

- Matches invoice items against PO items.
- Compares quantities and unit prices.
- Tracks cumulative billing across multiple invoices.
- Identifies quantity and price mismatches.
- Avoids automatically allocating bundled invoice items across PO components when the allocation is uncertain.

### Duplicate Detection

Uses multiple checks:

- Exact file hash comparison.
- Vendor and invoice number comparison.
- Vendor, invoice date and amount comparison.

### Final Decision

The decision engine assigns one of three outcomes:

| Decision | Meaning |
|---|---|
| APPROVED | Required validations pass and the invoice is eligible for approval. |
| REJECTED | A blocking issue such as a duplicate or vendor mismatch is identified. |
| PENDING_REVIEW | A discrepancy, ambiguity or incomplete validation requires human investigation. |

The final decision is generated through deterministic business rules, not directly by the LLM.

## 10. Configurable Business Rules

InvoiceIQ uses `config/rules.yaml` to maintain configurable processing policies.

Examples include:

- Required invoice fields.
- PO matching thresholds.
- Amount tolerance percentage.
- Absolute amount tolerance.
- Duplicate detection settings.
- Decision outcomes for validation failures.

The demo configuration uses a 2% percentage tolerance with an absolute cap of ₹100, whichever is lower.

These are configurable demonstration assumptions and should not be interpreted as universal accounting standards.

## 11. Edge-Case Testing

The system was evaluated against seven controlled invoice scenarios.

| Test | Scenario | Expected/Observed Decision |
|---|---|---|
| EC1 | Split invoicing and cumulative PO quantity limit | First two invoices APPROVED; third PENDING_REVIEW |
| EC2 | Missing PO reference with multiple plausible matches | PENDING_REVIEW |
| EC3 | Invoice from an unregistered vendor | REJECTED |
| EC4 | Invoice unit price higher than the PO price | PENDING_REVIEW |
| EC5 | Partial invoice with an incorrect unit price | PENDING_REVIEW |
| EC6 | Incorrect GST amount | Initial implementation exposed a validation gap |
| EC7 | Incorrect GST rate/amount compared with PO tax expectations | PENDING_REVIEW |

The GST validation gap identified during EC6 testing was addressed through an additional PO tax validation check and verified using EC7.

The project also includes a regression test suite to check that changes do not break existing functionality.

Run the tests using:

```bash
pytest tests/ -v
```

## 12. Design Decisions

### Local LLM Instead of Cloud APIs

Ollama and Qwen2.5 are used to run extraction locally. This avoids dependence on paid external LLM APIs and allows the demonstration to run on a local machine.

### Deterministic Financial Validation

Financial calculations are performed using Python rather than trusting LLM-generated arithmetic. This improves consistency and makes validation results easier to audit.

### Human-in-the-Loop Exception Handling

Invoices with ambiguous PO matches, uncertain extraction or financial discrepancies are routed for human review rather than being automatically approved.

### Modular Architecture

The application separates ingestion, extraction, matching, validation, decision-making and database operations. This makes individual components easier to test and maintain.

## 13. Limitations and Future Improvements

The current implementation is a local proof of concept intended to demonstrate an intelligent invoice-processing workflow.

Some limitations include:

- LLM extraction performance can vary depending on invoice layout, scan quality and document complexity.
- Local CPU inference may introduce processing delays.
- OCR accuracy depends on document quality and readability.
- Semantic matching uses a lexical similarity baseline and may not capture every contextual relationship.
- Vendor and PO verification depends on the accuracy of the supplied reference data.
- External ERP, banking and GST verification integrations are not included.
- Email mailbox integration is not included; PDF uploads simulate invoice intake.
- Human review is required for ambiguous or unsupported cases.

Potential future improvements include:

- Integration with ERP and accounting platforms.
- Email-based invoice intake.
- More advanced semantic item matching.
- Improved handling of bundled invoice items.
- Confidence calibration for extraction and matching.
- Role-based review workflows and approval tracking.
- Performance optimisation for larger invoice volumes.

## 14. Conclusion

InvoiceIQ demonstrates how local LLMs can be integrated with deterministic business logic to automate invoice processing while maintaining control over financial decisions.

By combining document extraction, vendor verification, purchase order reconciliation, financial validation and exception handling, the system provides a structured approach to reducing manual invoice verification effort.

Rather than relying entirely on AI-generated decisions, InvoiceIQ uses AI for document understanding and Python-based rules for validation and decision-making. This creates a more transparent and auditable workflow suitable for further development into an enterprise invoice-processing solution.

---

**Built as an AI-assisted invoice processing and exception investigation case study.**