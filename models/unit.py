from models.database import placeholders, query, transaction

UNIT_LIMIT = 500


# Every unit of one product, newest delivery first. Gives back (units, total) so the page can say how many there are
def units_for_product(product_id):
    total = query("SELECT COUNT(*) AS n FROM ProductItem WHERE productID = ?", (product_id,))[0]["n"]
    units = query("""
        SELECT i.epc, i.status, i.receptionID, r.dateReceived
        FROM ProductItem i
        JOIN Reception r ON r.receptionID = i.receptionID
        WHERE i.productID = ?
        ORDER BY r.dateReceived DESC, i.epc
        LIMIT ?
    """, (product_id, UNIT_LIMIT))
    return units, total


# Find units whose EPC contains the text, across all products. Gives back at most 50 matches
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


# Which of these EPCs are already units in the database? Gives back a set
def known_epcs(epcs):
    if not epcs:
        return set()
    rows = query(f"SELECT epc FROM ProductItem WHERE epc IN ({placeholders(epcs)})", list(epcs))
    return {row["epc"] for row in rows}


# For testing: delete every unit (EPC) and delivery of one product, so its tags can be received again.
# The product and customer receipts are kept. Gives back how many units were deleted
def clear_product_units(product_id):
    def work(conn):
        count = conn.execute("DELETE FROM ProductItem WHERE productID = ?", (product_id,)).rowcount
        conn.execute("DELETE FROM Reception WHERE productID = ?", (product_id,))
        return count
    return transaction(work)
