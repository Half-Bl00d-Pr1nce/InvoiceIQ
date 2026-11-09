import sqlite3

conn = sqlite3.connect("data/invoiceiq.db")

rows = conn.execute("""
    SELECT po_id, item_code, description, quantity, unit_price_paise
    FROM po_items
    WHERE po_id = 'PO-1004'
""").fetchall()

print("PO-1004 items:")
for row in rows:
    print(row)

conn.close()