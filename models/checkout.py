from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from models.database import execute, money_or_none, placeholders, query, query_one, transaction

# The two sales taxes in Quebec. Both are worked out on the subtotal of the taxable items (QST is not charged on top of GST).
# Change them here and the checkout page and the receipts follow
GST_RATE = Decimal("0.05")      # federal Goods and Services Tax
QST_RATE = Decimal("0.09975")   # Quebec Sales Tax
# The same rates out of 100,000 (5% = 5000, 9.975% = 9975), so the page can add them up in whole cents
GST_PARTS = int(GST_RATE * 100000)
QST_PARTS = int(QST_RATE * 100000)
# The rates as text for the labels on the checkout page, like "5" and "9.975"
GST_PERCENT = f"{float(GST_RATE * 100):g}"
QST_PERCENT = f"{float(QST_RATE * 100):g}"
# Loyalty points: every complete POINTS_STEP dollars spent before tax earns POINTS_PER_STEP points.
# The checkout page shows the same numbers before paying
POINTS_STEP = 5
POINTS_PER_STEP = 10


# One tax on a subtotal, rounded to the cent. Gives back a Decimal
def tax_for(subtotal, rate):
    return (subtotal * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# Look up the scanned tags. Gives back (items, sold, unknown)
# items: one dict per tag that is a unit in stock, with its product name and price
# sold: how many tags were already sold
# unknown: how many tags are not in the system (or were removed from stock)
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
    # GST and QST are only charged on the taxable items
    taxable_subtotal = sum((Decimal(str(item["price"])) for item in items if item["taxable"]), Decimal("0"))
    gst = tax_for(taxable_subtotal, GST_RATE)
    qst = tax_for(taxable_subtotal, QST_RATE)
    tax = gst + qst
    total = subtotal + tax

    # Every complete $5 spent before tax earns 10 loyalty points.
    # Decimal keeps the calculation accurate for money values.
    points_earned = int(subtotal // Decimal(POINTS_STEP)) * POINTS_PER_STEP

    def work(conn):
        cursor = conn.execute(
            """INSERT INTO Purchase (customerID, purchaseDate, subtotal, gstAmount, qstAmount, taxAmount, total, pointsEarned, paymentMethod)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (customer_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str(subtotal), str(gst), str(qst), str(tax), str(total),
             points_earned, payment_method),
        )
        # Update the customer's running point balance in the same transaction as the purchase.
        # If saving the purchase fails, the points update is rolled back too.
        if customer_id is not None and points_earned > 0:
            conn.execute(
                "UPDATE Customer SET totalPoints = totalPoints + ? WHERE customerID = ?",
                (points_earned, customer_id),
            )
        purchase_id = cursor.lastrowid

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


# Which products from this purchase just became low or out of stock. For the email to the admin
# Only counts the sale that crossed the line, so the admin gets one email and not one for every sale after it
# Hidden products are skipped because they are not being restocked
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


def _receipt_lines(purchase_id):
    return query("""
        SELECT p.productName, p.imagePath, pi.quantity, pi.unitPrice, pi.isTaxable
        FROM PurchaseItem pi JOIN Product p ON p.productID = pi.productID
        WHERE pi.purchaseID = ? ORDER BY p.productName COLLATE NOCASE
    """, (purchase_id,))


# A customer's receipts, newest first, each with its lines. For the Purchase History on My Account
def purchase_history(customer_id):
    purchases = [dict(row) for row in query(
        "SELECT purchaseID, purchaseDate, subtotal, gstAmount, qstAmount, taxAmount, total, pointsEarned, paymentMethod, emailSent FROM Purchase WHERE customerID = ? ORDER BY purchaseDate DESC, purchaseID DESC",
        (customer_id,))]
    for purchase in purchases:
        purchase["lines"] = _receipt_lines(purchase["purchaseID"])
        purchase["itemCount"] = sum(line["quantity"] for line in purchase["lines"])
    return purchases


# One receipt for the page that shows it right after paying: the date, the lines, and the amounts
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
        "lines": [{"name": l["productName"], "quantity": l["quantity"], "unitPrice": float(l["unitPrice"]),
                   "lineTotal": float(Decimal(str(l["unitPrice"])) * l["quantity"]),
                   "taxable": bool(l["isTaxable"])} for l in lines],
        "subtotal": float(purchase["subtotal"]),
        "gst": float(purchase["gstAmount"]),
        "qst": float(purchase["qstAmount"]),
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


# The time periods on the admin page: the button text for each one
PERIODS = {"today": "Today", "month": "This month", "all": "All time"}


# The first moment of a period, as text like "2026-11-01 00:00:00", or None for all time.
# Sale dates are saved as text in this same format, so they can be compared with >=
def period_start(period):
    now = datetime.now()
    if period == "today":
        return now.strftime("%Y-%m-%d 00:00:00")
    if period == "month":
        return now.strftime("%Y-%m-01 00:00:00")
    return None


# The money numbers for the admin page, for the sales since `since` (None means every sale):
# sales: what customers paid before GST and QST (the taxes go to the government, so they are not the store's money)
# cost: what the store paid for the items sold
# profit: sales minus cost, for the items that have a cost
# margin: profit as a percent of the sales it came from, or None when nothing with a cost was sold
# missing: how many units sold have no cost yet. They are left out of the cost and the profit
# orders, units: how many purchases, and how many items in them
# gst, qst: the tax collected, which the store owes the government
# Each line uses the cost saved at the time of the sale. Older sales, from before costs were saved, use the product's cost now
def profit_summary(since=None):
    since = since or "0000"   # every date is after "0000", so this means all time
    items = query_one("""
        SELECT ROUND(COALESCE(SUM(quantity * unitPrice), 0), 2) AS sales,
               ROUND(COALESCE(SUM(CASE WHEN cost IS NOT NULL THEN quantity * unitPrice END), 0), 2) AS costedSales,
               ROUND(COALESCE(SUM(CASE WHEN cost IS NOT NULL THEN quantity * cost END), 0), 2) AS cost,
               ROUND(COALESCE(SUM(CASE WHEN cost IS NOT NULL THEN quantity * (unitPrice - cost) END), 0), 2) AS profit,
               COALESCE(SUM(CASE WHEN cost IS NULL THEN quantity END), 0) AS missing,
               COALESCE(SUM(quantity), 0) AS units
        FROM (SELECT pi.quantity, pi.unitPrice, COALESCE(pi.unitCost, p.costPrice) AS cost
              FROM PurchaseItem pi
              JOIN Purchase pu ON pu.purchaseID = pi.purchaseID
              JOIN Product p ON p.productID = pi.productID
              WHERE pu.purchaseDate >= ?)
    """, (since,))
    purchases = query_one("""
        SELECT COUNT(*) AS orders,
               ROUND(COALESCE(SUM(gstAmount), 0), 2) AS gst,
               ROUND(COALESCE(SUM(qstAmount), 0), 2) AS qst
        FROM Purchase WHERE purchaseDate >= ?
    """, (since,))

    summary = dict(items)
    summary.update(dict(purchases))
    summary["tax"] = round(summary["gst"] + summary["qst"], 2)
    # The margin only compares the profit with the sales that have a cost, so missing costs don't make it look smaller
    if summary["costedSales"] > 0:
        summary["margin"] = round(summary["profit"] * 100 / summary["costedSales"], 1)
    else:
        summary["margin"] = None
    return summary


# The products that made the most profit since `since` (None means every sale), best first.
# Like profit_summary, the profit only counts the units that have a cost, and `missing` says how many don't.
# Products with no cost at all are listed after the others, with profit None
def top_products(since=None, limit=5):
    since = since or "0000"
    rows = query("""
        SELECT productID, productName,
               SUM(quantity) AS units,
               ROUND(SUM(quantity * unitPrice), 2) AS sales,
               ROUND(SUM(CASE WHEN cost IS NOT NULL THEN quantity * (unitPrice - cost) END), 2) AS profit,
               COALESCE(SUM(CASE WHEN cost IS NULL THEN quantity END), 0) AS missing
        FROM (SELECT p.productID, p.productName, pi.quantity, pi.unitPrice, COALESCE(pi.unitCost, p.costPrice) AS cost
              FROM PurchaseItem pi
              JOIN Purchase pu ON pu.purchaseID = pi.purchaseID
              JOIN Product p ON p.productID = pi.productID
              WHERE pu.purchaseDate >= ?)
        GROUP BY productID
        ORDER BY profit IS NULL, profit DESC, sales DESC
        LIMIT ?
    """, (since, limit))
    return [dict(row) for row in rows]
