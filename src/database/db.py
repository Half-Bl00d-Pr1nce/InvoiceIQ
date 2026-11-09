import sqlite3
from pathlib import Path

DB_PATH = Path("data/invoiceiq.db")


def get_connection():
    """Create and return a SQLite database connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database():
    """Create all InvoiceIQ database tables."""

    connection = get_connection()

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS vendors (
            vendor_id TEXT PRIMARY KEY,
            vendor_name TEXT NOT NULL,
            gstin TEXT,
            status TEXT NOT NULL CHECK (
                status IN ('ACTIVE', 'INACTIVE', 'BLOCKED')
            ),
            bank_ref TEXT
        );

        CREATE TABLE IF NOT EXISTS purchase_orders (
            po_id TEXT PRIMARY KEY,
            vendor_id TEXT NOT NULL,
            po_date TEXT NOT NULL,
            status TEXT NOT NULL,
            currency TEXT NOT NULL DEFAULT 'INR',
            FOREIGN KEY (vendor_id)
                REFERENCES vendors(vendor_id)
        );

        CREATE TABLE IF NOT EXISTS po_items (
            po_item_id TEXT PRIMARY KEY,
            po_id TEXT NOT NULL,
            item_code TEXT,
            description TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit_price_paise INTEGER NOT NULL,
            tax_rate REAL,
            FOREIGN KEY (po_id)
                REFERENCES purchase_orders(po_id)
        );

        CREATE TABLE IF NOT EXISTS invoices (
            invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id TEXT,
            invoice_number TEXT,
            invoice_date TEXT,
            po_id TEXT,
            subtotal_paise INTEGER,
            tax_amount_paise INTEGER,
            total_amount_paise INTEGER,
            currency TEXT DEFAULT 'INR',
            file_name TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            extraction_confidence REAL,
            status TEXT NOT NULL DEFAULT 'PROCESSING',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vendor_id)
                REFERENCES vendors(vendor_id)
        );

        CREATE TABLE IF NOT EXISTS invoice_items (
            invoice_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            item_code TEXT,
            description TEXT NOT NULL,
            quantity REAL,
            unit_price_paise INTEGER,
            tax_rate REAL,
            line_total_paise INTEGER,
            FOREIGN KEY (invoice_id)
                REFERENCES invoices(invoice_id)
        );

        CREATE TABLE IF NOT EXISTS validation_results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            check_name TEXT NOT NULL,
            status TEXT NOT NULL,
            expected_value TEXT,
            actual_value TEXT,
            explanation TEXT NOT NULL,
            FOREIGN KEY (invoice_id)
                REFERENCES invoices(invoice_id)
        );

        CREATE TABLE IF NOT EXISTS processing_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (invoice_id)
                REFERENCES invoices(invoice_id)
        );

        CREATE TABLE IF NOT EXISTS review_actions (
            action_id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            original_value TEXT,
            corrected_value TEXT,
            reviewer_note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (invoice_id)
                REFERENCES invoices(invoice_id)
        );

        CREATE INDEX IF NOT EXISTS idx_invoice_vendor_number
        ON invoices(vendor_id, invoice_number);

        CREATE INDEX IF NOT EXISTS idx_invoice_po
        ON invoices(po_id);

        CREATE INDEX IF NOT EXISTS idx_invoice_hash
        ON invoices(file_hash);
        """
    )

    connection.commit()
    connection.close()

def migrate_database():
    """Add new invoice fields without deleting existing records."""

    connection = get_connection()

    try:
        existing_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(invoices)"
            ).fetchall()
        }

        migrations = {
            "extracted_vendor_name": "TEXT",
            "shipping_amount": "TEXT",
            "discount_amount": "TEXT",
            "tax_treatment": "TEXT",

            # Currency-independent monetary values
            "subtotal_amount": "TEXT",
            "tax_amount": "TEXT",
            "total_amount": "TEXT",
        }

        for column, data_type in migrations.items():
            if column not in existing_columns:
                connection.execute(
                    f"ALTER TABLE invoices ADD COLUMN "
                    f"{column} {data_type}"
                )
        
        existing_item_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(invoice_items)"
            ).fetchall()
        }

        item_migrations = {
            "unit_price_amount": "TEXT",
            "line_total_amount": "TEXT",
        }

        for column, data_type in item_migrations.items():
            if column not in existing_item_columns:
                connection.execute(
                    f"ALTER TABLE invoice_items ADD COLUMN "
                    f"{column} {data_type}"
                )

        connection.commit()
        print("Database migration completed successfully.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

if __name__ == "__main__":
    initialize_database()
    print("InvoiceIQ database initialized successfully.")