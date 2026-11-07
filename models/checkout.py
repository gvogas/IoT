from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from models.database import execute, placeholders, query, query_one, transaction

# The sales tax added to every purchase. Change it here and the checkout page and the receipts follow
TAX_RATE = Decimal("0.15")
# The same rate in basis points (15% = 1500), so the page can add it up in whole cents
TAX_BASIS_POINTS = int(TAX_RATE * 10000)


# The tax on a subtotal, rounded to the cent. Gives back a Decimal
def tax_for(subtotal):
    return (subtotal * TAX_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# Look up the scanned tags. Gives back (items, sold, unknown)
# items: one dict per tag that is a unit in stock, with its product name and price
# sold: how many tags were already sold
# unknown: how many tags are not in the system (or were removed from stock)
def basket_items(epcs):
    if not epcs:
        return [], 0, 0
    rows = query(f"""
        SELECT i.epc, i.status, p.productID, p.productName, p.price, p.imagePath
        FROM ProductItem i
        JOIN Product p ON p.productID = i.productID
        WHERE i.epc IN ({placeholders(epcs)})
        ORDER BY p.productName COLLATE NOCASE, i.epc
    """, list(epcs))
    items = [{"epc": r["epc"], "productID": r["productID"], "name": r["productName"], "price": r["price"], "image": r["imagePath"]}
             for r in rows if r["status"] == "in_stock"]
    sold = sum(1 for r in rows if r["status"] == "sold")
    return items, sold, len(set(epcs)) - len(rows) + sum(1 for r in rows if r["status"] == "removed")


# Save a paid basket: the receipt, one line per product, and mark each tag as sold
# Gives back (purchaseID, total), or raises ValueError if a tag is not in stock any more (nothing is saved then)
def pay(customer_id, epcs, payment_method="card"):
    epcs = list(dict.fromkeys(epcs))
    items, sold, unknown = basket_items(epcs)
    if sold:
        raise ValueError("Item already sold. Remove it and scan again.")
    if not items or unknown:
        raise ValueError("Some items are not available any more. Scan the basket again.")

    subtotal = sum((Decimal(str(item["price"])) for item in items), Decimal("0"))
    tax = tax_for(subtotal)
    total = subtotal + tax

    def work(conn):
        cursor = conn.execute(
            """INSERT INTO Purchase (customerID, purchaseDate, subtotal, taxAmount, total, pointsEarned, paymentMethod)
               VALUES (?, ?, ?, ?, ?, 0, ?)""",
            (customer_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str(subtotal), str(tax), str(total), payment_method),
        )
        purchase_id = cursor.lastrowid

        by_product = {}
        for item in items:
            by_product.setdefault(item["productID"], []).append(item)

        for product_id, units in by_product.items():
            line = conn.execute(
                "INSERT INTO PurchaseItem (purchaseID, productID, quantity, unitPrice) VALUES (?, ?, ?, ?)",
                (purchase_id, product_id, len(units), str(units[0]["price"])),
            )
            changed = conn.execute(
                f"UPDATE ProductItem SET status = 'sold', purchaseItemID = ? WHERE status = 'in_stock' AND epc IN ({placeholders(units)})",
                [line.lastrowid] + [unit["epc"] for unit in units],
            ).rowcount
            if changed != len(units):
                raise ValueError("Some items are not available any more. Scan the basket again.")
        return purchase_id

    return transaction(work), total


def _receipt_lines(purchase_id):
    return query("""
        SELECT p.productName, p.imagePath, pi.quantity, pi.unitPrice
        FROM PurchaseItem pi JOIN Product p ON p.productID = pi.productID
        WHERE pi.purchaseID = ? ORDER BY p.productName COLLATE NOCASE
    """, (purchase_id,))


# A customer's receipts, newest first, each with its lines. For the Purchase History on My Account
def purchase_history(customer_id):
    purchases = [dict(row) for row in query(
        "SELECT purchaseID, purchaseDate, subtotal, taxAmount, total, paymentMethod, emailSent FROM Purchase WHERE customerID = ? ORDER BY purchaseDate DESC, purchaseID DESC",
        (customer_id,))]
    for purchase in purchases:
        purchase["lines"] = _receipt_lines(purchase["purchaseID"])
        purchase["itemCount"] = sum(line["quantity"] for line in purchase["lines"])
    return purchases


# One receipt for the page that shows it right after paying: the date, the lines, and the amounts
def receipt(purchase_id):
    purchase = query_one(
        """SELECT p.purchaseID, p.purchaseDate, p.subtotal, p.taxAmount, p.total, p.paymentMethod, c.customerName, c.membershipNumber
           FROM Purchase p LEFT JOIN Customer c ON c.customerID = p.customerID WHERE p.purchaseID = ?""",
        (purchase_id,))
    if purchase is None:
        return None
    lines = _receipt_lines(purchase_id)
    return {
        "purchaseID": purchase["purchaseID"],
        "date": purchase["purchaseDate"],
        "customer": purchase["customerName"],
        "membershipNumber": purchase["membershipNumber"],
        "paymentMethod": purchase["paymentMethod"],
        "lines": [{"name": l["productName"], "quantity": l["quantity"], "unitPrice": float(l["unitPrice"]),
                   "lineTotal": float(Decimal(str(l["unitPrice"])) * l["quantity"])} for l in lines],
        "subtotal": float(purchase["subtotal"]),
        "tax": float(purchase["taxAmount"]),
        "total": float(purchase["total"]),
    }


# Is this receipt one of this customer's own?
def purchase_belongs_to(purchase_id, customer_id):
    return query_one("SELECT 1 FROM Purchase WHERE purchaseID = ? AND customerID = ?", (purchase_id, customer_id)) is not None


# The email address a receipt goes to, or None if there isn't one
def receipt_email_address(purchase_id):
    row = query_one("SELECT c.email FROM Purchase p JOIN Customer c ON c.customerID = p.customerID WHERE p.purchaseID = ?", (purchase_id,))
    return row["email"] if row else None


def mark_receipt_emailed(purchase_id):
    execute("UPDATE Purchase SET emailSent = 1 WHERE purchaseID = ?", (purchase_id,))
