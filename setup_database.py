from src.database.db import initialize_database, get_connection
from src.database.repository import load_reference_data


def main():
    initialize_database()
    print("1. Database initialized.")

    load_reference_data()
    print("2. Reference data loaded.")

    connection = get_connection()

    vendors = connection.execute(
        "SELECT * FROM vendors"
    ).fetchall()

    orders = connection.execute(
        """
        SELECT
            po.po_id,
            v.vendor_name,
            po_item.description,
            po_item.quantity,
            po_item.unit_price_paise
        FROM purchase_orders po
        JOIN vendors v ON po.vendor_id = v.vendor_id
        JOIN po_items po_item ON po.po_id = po_item.po_id
        """
    ).fetchall()

    print("\nVENDORS")
    for vendor in vendors:
        print(dict(vendor))

    print("\nPURCHASE ORDERS")
    for order in orders:
        print(dict(order))

    connection.close()


if __name__ == "__main__":
    main()