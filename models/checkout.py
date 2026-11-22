from decimal import ROUND_HALF_UP, Decimal

from models.database import execute, money_or_none, now_text, placeholders, query, query_one, transaction

# Quebec sales taxes. Both are charged on the taxable subtotal (QST is not charged on top of GST)
GST_RATE = Decimal("0.05")
QST_RATE = Decimal("0.09975")
# The same rates out of 100,000 (5% = 5000), so the checkout page can add them up in whole cents
GST_PARTS = int(GST_RATE * 100000)
QST_PARTS = int(QST_RATE * 100000)
# For the labels on the checkout page, like "5" and "9.975"
GST_PERCENT = f"{float(GST_RATE * 100):g}"
QST_PERCENT = f"{float(QST_RATE * 100):g}"
# Every complete POINTS_STEP dollars spent before tax earns POINTS_PER_STEP loyalty points
POINTS_STEP = 5
POINTS_PER_STEP = 10


# Rounded half up to the cent
def tax_for(subtotal, rate):
    return (subtotal * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# Gives back (items in stock, count already sold, count unknown or removed)
def basket_items(epcs):
    if not epcs:
        return [], 0, 0
    rows = query(f"""
        SELECT i.epc, i.status, p.productID, p.productName, p.price, p.costPrice, p.isTaxable, p.imagePath
        FROM ProductItem i
        JOIN Product p ON p.productID = i.productID
        WHERE i.epc IN ({placeholders(epcs)})
        ORDER BY p.productName COLLATE NOCASE, i.epc
    """, list(epcs))
    items = [{"epc": r["epc"], "productID": r["productID"], "name": r["productName"], "price": r["price"],
              "cost": r["costPrice"], "taxable": bool(r["isTaxable"]), "image": r["imagePath"]}
             for r in rows if r["status"] == "in_stock"]
    sold = sum(1 for r in rows if r["status"] == "sold")
    removed = sum(1 for r in rows if r["status"] == "removed")
    not_found = len(set(epcs)) - len(rows)
    return items, sold, not_found + removed


# Save a paid basket. Gives back (purchaseID, total), or raises ValueError and saves nothing
def pay(customer_id, epcs, payment_method="card"):
    epcs = list(dict.fromkeys(epcs))
    items, sold, unknown = basket_items(epcs)
    if sold:
        raise ValueError("Item already sold. Remove it and scan again.")
    if not items or unknown:
        raise ValueError("Some items are not available any more. Scan the basket again.")

    subtotal = sum((Decimal(str(item["price"])) for item in items), Decimal("0"))
    taxable_subtotal = sum((Decimal(str(item["price"])) for item in items if item["taxable"]), Decimal("0"))
    gst = tax_for(taxable_subtotal, GST_RATE)
    qst = tax_for(taxable_subtotal, QST_RATE)
    tax = gst + qst
    total = subtotal + tax
    points_earned = int(subtotal // Decimal(POINTS_STEP)) * POINTS_PER_STEP

    def work(conn):
        cursor = conn.execute(
            """INSERT INTO Purchase (customerID, purchaseDate, subtotal, gstAmount, qstAmount, taxAmount, total, pointsEarned, paymentMethod)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (customer_id, now_text(), str(subtotal), str(gst), str(qst), str(tax), str(total),
             points_earned, payment_method),
        )
        purchase_id = cursor.lastrowid
        if customer_id is not None and points_earned > 0:
            conn.execute(
                "UPDATE Customer SET totalPoints = totalPoints + ? WHERE customerID = ?",
                (points_earned, customer_id),
            )

        by_product = {}
        for item in items:
            by_product.setdefault(item["productID"], []).append(item)

        for product_id, units in by_product.items():
            line = conn.execute(
                "INSERT INTO PurchaseItem (purchaseID, productID, quantity, unitPrice, unitCost, isTaxable) VALUES (?, ?, ?, ?, ?, ?)",
                (purchase_id, product_id, len(units), str(units[0]["price"]), money_or_none(units[0]["cost"]), units[0]["taxable"]),
            )
            changed = conn.execute(
                f"UPDATE ProductItem SET status = 'sold', purchaseItemID = ? WHERE status = 'in_stock' AND epc IN ({placeholders(units)})",
                [line.lastrowid] + [unit["epc"] for unit in units],
            ).rowcount
            if changed != len(units):
                raise ValueError("Some items are not available any more. Scan the basket again.")
        return purchase_id

    return transaction(work), total


# Products this sale just made low or out of stock (hidden products skipped)
def stock_alerts(purchase_id):
    rows = query("""
        SELECT p.productName, p.lowStockThreshold, pi.quantity,
               (SELECT COUNT(*) FROM ProductItem i WHERE i.productID = p.productID AND i.status = 'in_stock') AS inStock
        FROM PurchaseItem pi JOIN Product p ON p.productID = pi.productID
        WHERE pi.purchaseID = ? AND p.isActive = 1
        ORDER BY p.productName COLLATE NOCASE
    """, (purchase_id,))

    alerts = []
    for row in rows:
        stock_before = row["inStock"] + row["quantity"]
        if row["inStock"] == 0:
            status = "out"
        elif row["inStock"] <= row["lowStockThreshold"] < stock_before:
            status = "low"
        else:
            continue
        alerts.append({"name": row["productName"], "status": status, "inStock": row["inStock"],
                       "threshold": row["lowStockThreshold"]})
    return alerts


# The lines of one receipt
def _receipt_lines(purchase_id):
    return query("""
        SELECT p.productName, p.imagePath, pi.quantity, pi.unitPrice, pi.isTaxable
        FROM PurchaseItem pi JOIN Product p ON p.productID = pi.productID
        WHERE pi.purchaseID = ? ORDER BY p.productName COLLATE NOCASE
    """, (purchase_id,))


# A customer's receipts, newest first, each with its lines
def purchase_history(customer_id):
    purchases = [dict(row) for row in query(
        "SELECT purchaseID, purchaseDate, subtotal, gstAmount, qstAmount, taxAmount, total, pointsEarned, paymentMethod, emailSent FROM Purchase WHERE customerID = ? ORDER BY purchaseDate DESC, purchaseID DESC",
        (customer_id,))]
    for purchase in purchases:
        purchase["lines"] = _receipt_lines(purchase["purchaseID"])
        purchase["itemCount"] = sum(line["quantity"] for line in purchase["lines"])
    return purchases


# One receipt with its lines and amounts
def receipt(purchase_id):
    purchase = query_one(
        """SELECT p.purchaseID, p.purchaseDate, p.subtotal, p.gstAmount, p.qstAmount, p.taxAmount, p.total, p.pointsEarned,
                  p.paymentMethod, c.customerName, c.membershipNumber, c.totalPoints
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
        "pointsEarned": purchase["pointsEarned"] or 0,
        "customerPoints": purchase["totalPoints"],
        "lines": [{"name": line["productName"], "quantity": line["quantity"], "unitPrice": float(line["unitPrice"]),
                   "lineTotal": float(Decimal(str(line["unitPrice"])) * line["quantity"]),
                   "taxable": bool(line["isTaxable"])} for line in lines],
        "subtotal": float(purchase["subtotal"]),
        "gst": float(purchase["gstAmount"]),
        "qst": float(purchase["qstAmount"]),
        "tax": float(purchase["taxAmount"]),
        "total": float(purchase["total"]),
    }


# Is this receipt the customer's own?
def purchase_belongs_to(purchase_id, customer_id):
    return query_one("SELECT 1 FROM Purchase WHERE purchaseID = ? AND customerID = ?", (purchase_id, customer_id)) is not None


# None if the purchase has no customer email
def receipt_email_address(purchase_id):
    row = query_one("SELECT c.email FROM Purchase p JOIN Customer c ON c.customerID = p.customerID WHERE p.purchaseID = ?", (purchase_id,))
    return row["email"] if row else None


# Remember that the receipt email went out
def mark_receipt_emailed(purchase_id):
    execute("UPDATE Purchase SET emailSent = 1 WHERE purchaseID = ?", (purchase_id,))
