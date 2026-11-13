from models.database import placeholders, query, query_one, transaction

UNIT_LIMIT = 500


# Units of one product, newest delivery first. Gives back (units, total), since units stops at UNIT_LIMIT
def units_for_product(product_id):
    total = query_one("SELECT COUNT(*) AS n FROM ProductItem WHERE productID = ?", (product_id,))["n"]
    units = query("""
        SELECT i.epc, i.status, i.receptionID, r.dateReceived
        FROM ProductItem i
        JOIN Reception r ON r.receptionID = i.receptionID
        WHERE i.productID = ?
        ORDER BY r.dateReceived DESC, i.epc
        LIMIT ?
    """, (product_id, UNIT_LIMIT))
    return units, total


# Units whose EPC contains the text, across all products
def find_units(text):
    return query("""
        SELECT i.epc, i.status, i.productID, p.productName, r.dateReceived
        FROM ProductItem i
        JOIN Product p ON p.productID = i.productID
        JOIN Reception r ON r.receptionID = i.receptionID
        WHERE i.epc LIKE ?
        ORDER BY i.epc
        LIMIT 50
    """, (f"%{text}%",))


# The EPCs from this list that are already in the database
def known_epcs(epcs):
    if not epcs:
        return set()
    rows = query(f"SELECT epc FROM ProductItem WHERE epc IN ({placeholders(epcs)})", list(epcs))
    return {row["epc"] for row in rows}


# For testing: delete a product's units and deliveries so its tags can be received again
def clear_product_units(product_id):
    def work(conn):
        count = conn.execute("DELETE FROM ProductItem WHERE productID = ?", (product_id,)).rowcount
        conn.execute("DELETE FROM Reception WHERE productID = ?", (product_id,))
        return count
    return transaction(work)
