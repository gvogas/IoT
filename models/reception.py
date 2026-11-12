import re
from datetime import date, datetime

from models.database import placeholders, query, query_one, transaction

# Shown in the error message, so a long list of duplicates doesn't fill the screen
SHOW_LIMIT = 5

# An EPC is hexadecimal (0-9 and A-F), up to 24 characters, whether it was typed or scanned from a tag
SCANNED_EPC_REGEX = r"^[0-9A-F]+$"

# Turn the scanned text into a list of EPCs. Gives back (epcs, errors)
# The text can have one EPC per line, or be separated by spaces or commas (what a reader or a paste gives)
def read_epcs(text):
    epcs = []
    errors = []
    for token in re.split(r"[\s,;]+", text.strip()):
        if not token:
            continue
        epc = token.upper()
        if len(epc) > 24 or not re.match(SCANNED_EPC_REGEX, epc):
            errors.append(f"\"{token}\" is not a valid EPC. EPCs use the letters A to F and digits 0 to 9, up to 24 characters.")
        else:
            epcs.append(epc)

    repeated = sorted({epc for epc in epcs if epcs.count(epc) > 1})
    if repeated:
        errors.append(f"These EPCs are in the list more than once: {', '.join(repeated[:SHOW_LIMIT])}.")

    return epcs, errors


# Check a delivery before saving it. Gives back a list of problems (empty if it's fine)
def check_reception(product_id, epcs, date_text):
    errors = []

    product = query_one("SELECT isActive FROM Product WHERE productID = ?", (product_id,))
    if product is None:
        errors.append("That product does not exist.")
    elif not product["isActive"]:
        errors.append("This product is hidden. Show it in inventory before receiving stock.")

    try:
        if datetime.strptime(date_text, "%Y-%m-%d").date() > date.today():
            errors.append("The date received can't be in the future.")
    except ValueError:
        errors.append("Please enter the date received.")

    if not epcs:
        errors.append("Please enter the EPC of at least one unit.")
    else:
        taken = [row["epc"] for row in query(
            f"SELECT epc FROM ProductItem WHERE epc IN ({placeholders(epcs)}) ORDER BY epc", epcs)]
        if taken:
            errors.append(f"These EPCs are already in the system: {', '.join(taken[:SHOW_LIMIT])}"
                          + (" and more." if len(taken) > SHOW_LIMIT else "."))

    return errors


# Save one delivery and one unit (ProductItem) per EPC. Gives back the new reception ID
def save_reception(product_id, epcs, date_text):
    def work(conn):
        cursor = conn.execute(
            "INSERT INTO Reception (productID, quantityReceived, dateReceived) VALUES (?, ?, ?)",
            (product_id, len(epcs), date_text),
        )
        conn.executemany(
            "INSERT INTO ProductItem (epc, productID, receptionID, status) VALUES (?, ?, ?, 'in_stock')",
            [(epc, product_id, cursor.lastrowid) for epc in epcs],
        )
        return cursor.lastrowid
    return transaction(work)


# The deliveries of one product, newest first. stillInStock is how many of its units are still on the shelf
def reception_history(product_id):
    return query("""
        SELECT r.receptionID, r.dateReceived, r.quantityReceived,
               (SELECT COUNT(*) FROM ProductItem i WHERE i.receptionID = r.receptionID AND i.status = 'in_stock') AS stillInStock
        FROM Reception r
        WHERE r.productID = ?
        ORDER BY r.dateReceived DESC, r.receptionID DESC
    """, (product_id,))
