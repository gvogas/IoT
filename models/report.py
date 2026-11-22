import calendar
from datetime import datetime, timedelta

from models.database import DATE_FORMAT, query, query_one

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


# Start and end of a date range picked on the Reports page, like "2026-02-01" to "2026-02-28".
# Both days are included. Leave day_to empty for a single day. Gives back None if a date is not valid
def range_dates(day_from, day_to):
    try:
        first = datetime.strptime(day_from or day_to, "%Y-%m-%d")
        last = datetime.strptime(day_to or day_from, "%Y-%m-%d")
    except ValueError:
        return None
    if first > last:
        first, last = last, first

    # The end is midnight after the last day, so the whole last day counts
    end = last + timedelta(days=1)
    day_count = (end - first).days
    # Compared with the same number of days just before
    before_start = first - timedelta(days=day_count)
    label = "the day before" if day_count == 1 else f"the {day_count} days before"

    return {"start": first.strftime(DATE_FORMAT), "end": end.strftime(DATE_FORMAT),
            "before_start": before_start.strftime(DATE_FORMAT), "before_end": first.strftime(DATE_FORMAT),
            "compare_label": label, "from": first.strftime("%Y-%m-%d"), "to": last.strftime("%Y-%m-%d")}


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
               ROUND(COALESCE(SUM(qstAmount), 0), 2) AS qst,
               ROUND(COALESCE(SUM(total), 0), 2) AS total
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


# How many units of each product were sold in the period, most first.
# Products still for sale that sold nothing are in the list too, with 0
def product_quantities(start=None, end=None):
    rows = query("""
        SELECT p.productID, p.productName, p.imagePath, c.categoryName,
               COALESCE(s.units, 0) AS units, COALESCE(s.sales, 0) AS sales
        FROM Product p
        JOIN Category c ON c.categoryID = p.categoryID
        LEFT JOIN (SELECT pi.productID, SUM(pi.quantity) AS units, ROUND(SUM(pi.quantity * pi.unitPrice), 2) AS sales
                   FROM PurchaseItem pi
                   JOIN Purchase pu ON pu.purchaseID = pi.purchaseID
                   WHERE pu.purchaseDate >= ? AND pu.purchaseDate < ?
                   GROUP BY pi.productID) s ON s.productID = p.productID
        WHERE p.isActive = 1 OR s.units > 0
        ORDER BY units DESC, p.productName COLLATE NOCASE
    """, (start or FIRST_DATE, end or LAST_DATE))
    return [dict(row) for row in rows]


# The most sold and least sold products from product_quantities(). Ties are all kept, so each one is a list.
# Gives back ([], []) when nothing was sold
def most_and_least_sold(products):
    if not products or products[0]["units"] == 0:
        return [], []
    most = max(product["units"] for product in products)
    least = min(product["units"] for product in products)
    most_sold = [product for product in products if product["units"] == most]
    least_sold = [product for product in products if product["units"] == least]
    return most_sold, least_sold


# Does the Reports chart have one bar per month? Yes for all time and for ranges longer than 62 days
def chart_by_month(period, start=None, end=None):
    if period == "custom":
        day_count = (datetime.strptime(end[:10], "%Y-%m-%d") - datetime.strptime(start[:10], "%Y-%m-%d")).days
        return day_count > 62
    return period == "all"


# Reports chart bars: one per day for a month or a short date range, one per month for all time or a long range.
# end is the day after the last one (like in period_dates). Today or a single day has no chart
def sales_chart(period, start=None, end=None):
    if period == "today":
        return []

    if period == "custom":
        first_day = datetime.strptime(start[:10], "%Y-%m-%d")
        day_count = (datetime.strptime(end[:10], "%Y-%m-%d") - first_day).days
        if day_count == 1:
            return []
    by_month = chart_by_month(period, start, end)

    group = "%Y-%m" if by_month else "%Y-%m-%d"
    rows = query(f"""
        SELECT strftime('{group}', purchaseDate) AS slot, ROUND(SUM(subtotal), 2) AS sales
        FROM Purchase WHERE purchaseDate >= ? AND purchaseDate < ?
        GROUP BY slot
    """, (start or FIRST_DATE, end or LAST_DATE))
    sales_by_slot = {row["slot"]: row["sales"] for row in rows}

    bars = []
    if by_month:
        if period == "all":
            first_sale = query_one("SELECT MIN(purchaseDate) AS first FROM Purchase")["first"]
            if first_sale is None:
                return []
            month = datetime.strptime(first_sale[:7], "%Y-%m")
            last_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            month = datetime.strptime(start[:7], "%Y-%m")
            last_day = datetime.strptime(end[:10], "%Y-%m-%d") - timedelta(days=1)
            last_month = last_day.replace(day=1)
        while month <= last_month:
            bars.append({"label": month.strftime("%b"), "title": month.strftime("%B %Y"),
                         "sales": sales_by_slot.get(month.strftime("%Y-%m"), 0)})
            # The 28th plus 4 days is always in the next month
            month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
    else:
        if period != "custom":
            # Every day of the month
            first_day = datetime.strptime(start[:10], "%Y-%m-%d")
            day_count = calendar.monthrange(first_day.year, first_day.month)[1]
        # Only the 1st and every 5th day get a label, so they fit
        for number in range(day_count):
            day = first_day + timedelta(days=number)
            bars.append({"label": str(day.day) if day.day == 1 or day.day % 5 == 0 else "",
                         "title": day.strftime("%b %d"), "sales": sales_by_slot.get(day.strftime("%Y-%m-%d"), 0)})
    return bars


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
