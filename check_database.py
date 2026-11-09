from src.database.db import get_connection

connection = get_connection()

invoice_count = connection.execute(
    "SELECT COUNT(*) FROM invoices"
).fetchone()[0]

biohue_count = connection.execute(
    """
    SELECT COUNT(*)
    FROM invoices
    WHERE file_hash = ?
    """,
    (
        "bbf20764d6fd09ded170458a16b0a1acfa32241ce3d72b83c94125e29035865d",
    )
).fetchone()[0]

print("Total invoices:", invoice_count)
print("BioHue records:", biohue_count)

connection.close()