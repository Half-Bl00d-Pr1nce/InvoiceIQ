from src.database.db import get_connection

connection = get_connection()

print("\nVENDORS:")
for row in connection.execute("SELECT * FROM vendors"):
    print(dict(row))

print("\nPURCHASE ORDERS:")
for row in connection.execute("SELECT * FROM purchase_orders"):
    print(dict(row))

print("\nPO ITEMS:")
for row in connection.execute("SELECT * FROM po_items"):
    print(dict(row))

connection.close()