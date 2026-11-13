import calendar
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from models.database import DATE_FORMAT, execute, money_or_none, now_text, placeholders, query, query_one, transaction

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


# The period buttons on the Reports page
PERIODS = {"today": "Today", "month": "This month", "last_month": "Last month", "all": "All time"}

# Full dates on purpose: SQLite treats a short one like "9999" as a number
FIRST_DATE = "0000-01-01 00:00:00"
LAST_DATE = "9999-12-31 23:59:59"


# The same moment one month earlier. Mar 31 becomes Feb 28, because February has no 31st
def one_month_back(moment):
    year, month = (moment.year, moment.month - 1) if moment.month > 1 else (moment.year - 1, 12)
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


# Start and end of a period and the one before it. None means no limit
def period_dates(period):
    now = datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    first_of_month = midnight.replace(day=1)

    if period == "today":
        # Today so far, against yesterday up to the same time
        start, end = midnight, None
        before_start, before_end = midnight - timedelta(days=1), now - timedelta(days=1)
        label = "yesterday"
    elif period == "month":
        # This month so far, against last month up to the same day
        start, end = first_of_month, None
        before_start, before_end = one_month_back(first_of_month), one_month_back(now)
        label = "last month"
    elif period == "last_month":
        # The whole of last month, against the whole month before it
        start, end = one_month_back(first_of_month), first_of_month
        before_start, before_end = one_month_back(start), start
        label = "the month before"
    else:
        return {"start": None, "end": None, "before_start": None, "before_end": None, "compare_label": None}

    def as_text(moment):
        return moment.strftime(DATE_FORMAT) if moment else None

    return {"start": as_text(start), "end": as_text(end), "before_start": as_text(before_start),
            "before_end": as_text(before_end), "compare_label": label}


# Sales before tax, cost and profit. Units with no cost are counted in `missing`
def profit_summary(start=None, end=None):
    dates = (start or FIRST_DATE, end or LAST_DATE)
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
              WHERE pu.purchaseDate >= ? AND pu.purchaseDate < ?)
    """, dates)
    purchases = query_one("""
        SELECT COUNT(*) AS orders,
               ROUND(COALESCE(SUM(gstAmount), 0), 2) AS gst,
               ROUND(COALESCE(SUM(qstAmount), 0), 2) AS qst
        FROM Purchase WHERE purchaseDate >= ? AND purchaseDate < ?
    """, dates)

    summary = dict(items)
    summary.update(dict(purchases))
    summary["tax"] = round(summary["gst"] + summary["qst"], 2)
    # The margin only compares the profit with the sales that have a cost, so missing costs don't make it look smaller
    if summary["costedSales"] > 0:
        summary["margin"] = round(summary["profit"] * 100 / summary["costedSales"], 1)
    else:
        summary["margin"] = None
    if summary["orders"]:
        summary["average"] = round(summary["sales"] / summary["orders"], 2)
        summary["items_per_order"] = round(summary["units"] / summary["orders"], 1)
    else:
        summary["average"] = 0
        summary["items_per_order"] = 0
    return summary


# Most profitable products first. Products with no cost come last
def top_products(start=None, end=None, limit=5):
    rows = query("""
        SELECT productID, productName, imagePath,
               SUM(quantity) AS units,
               ROUND(SUM(quantity * unitPrice), 2) AS sales,
               ROUND(SUM(CASE WHEN cost IS NOT NULL THEN quantity * (unitPrice - cost) END), 2) AS profit,
               COALESCE(SUM(CASE WHEN cost IS NULL THEN quantity END), 0) AS missing
        FROM (SELECT p.productID, p.productName, p.imagePath, pi.quantity, pi.unitPrice, COALESCE(pi.unitCost, p.costPrice) AS cost
              FROM PurchaseItem pi
              JOIN Purchase pu ON pu.purchaseID = pi.purchaseID
              JOIN Product p ON p.productID = pi.productID
              WHERE pu.purchaseDate >= ? AND pu.purchaseDate < ?)
        GROUP BY productID
        ORDER BY profit IS NULL, profit DESC, sales DESC
        LIMIT ?
    """, (start or FIRST_DATE, end or LAST_DATE, limit))
    return [dict(row) for row in rows]


# Reports chart bars: one per day for a month, one per month for all time
def sales_chart(period, start=None):
    if period == "today":
        return []

    group = "%Y-%m" if period == "all" else "%Y-%m-%d"
    rows = query(f"""
        SELECT strftime('{group}', purchaseDate) AS slot, ROUND(SUM(subtotal), 2) AS sales
        FROM Purchase WHERE purchaseDate >= ?
        GROUP BY slot
    """, (start or FIRST_DATE,))
    sales_by_slot = {row["slot"]: row["sales"] for row in rows}

    bars = []
    if period == "all":
        first_sale = query_one("SELECT MIN(purchaseDate) AS first FROM Purchase")["first"]
        if first_sale is None:
            return []
        month = datetime.strptime(first_sale[:7], "%Y-%m")
        this_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        while month <= this_month:
            bars.append({"label": month.strftime("%b"), "title": month.strftime("%B %Y"),
                         "sales": sales_by_slot.get(month.strftime("%Y-%m"), 0)})
            # The 28th plus 4 days is always in the next month
            month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
    else:
        # Every day of the month. Only the 1st and every 5th day get a label, so they fit
        first_day = datetime.strptime(start[:10], "%Y-%m-%d")
        days_in_month = calendar.monthrange(first_day.year, first_day.month)[1]
        for number in range(days_in_month):
            day = first_day + timedelta(days=number)
            bars.append({"label": str(day.day) if day.day == 1 or day.day % 5 == 0 else "",
                         "title": day.strftime("%b %d"), "sales": sales_by_slot.get(day.strftime("%Y-%m-%d"), 0)})
    return bars


# Sales before tax for each of the last `days` days, oldest first. Days with no sales get 0
def daily_sales(days=7):
    today = datetime.now().date()
    first = today - timedelta(days=days - 1)
    rows = query("""
        SELECT DATE(purchaseDate) AS day, ROUND(SUM(subtotal), 2) AS sales
        FROM Purchase WHERE purchaseDate >= ?
        GROUP BY day
    """, (first.strftime(DATE_FORMAT),))
    sales_by_day = {row["day"]: row["sales"] for row in rows}

    result = []
    for number in range(days):
        day = first + timedelta(days=number)
        result.append({"label": day.strftime("%a"), "date": day.strftime("%b %d"),
                       "sales": sales_by_day.get(day.isoformat(), 0), "today": day == today})
    return result


# Sales before tax per category, biggest first
def sales_by_category(start=None, end=None):
    rows = query("""
        SELECT c.categoryName, ROUND(SUM(pi.quantity * pi.unitPrice), 2) AS sales, SUM(pi.quantity) AS units
        FROM PurchaseItem pi
        JOIN Purchase pu ON pu.purchaseID = pi.purchaseID
        JOIN Product p ON p.productID = pi.productID
        JOIN Category c ON c.categoryID = p.categoryID
        WHERE pu.purchaseDate >= ? AND pu.purchaseDate < ?
        GROUP BY c.categoryID
        ORDER BY sales DESC
    """, (start or FIRST_DATE, end or LAST_DATE))
    return [dict(row) for row in rows]


# The newest receipts from every customer
def recent_purchases(limit=6):
    rows = query("""
        SELECT pu.purchaseID, pu.purchaseDate, pu.total, pu.paymentMethod, c.customerName,
               (SELECT SUM(quantity) FROM PurchaseItem WHERE purchaseID = pu.purchaseID) AS units
        FROM Purchase pu
        LEFT JOIN Customer c ON c.customerID = pu.customerID
        ORDER BY pu.purchaseDate DESC
        LIMIT ?
    """, (limit,))
    return [dict(row) for row in rows]

