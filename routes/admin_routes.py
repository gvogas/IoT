import csv
import io
from datetime import datetime, timedelta

from flask import Blueprint, Response, render_template, request

from config import FRIDGES_ENABLED, MSP01_ENABLED
from models.fridge import Fridge
from models.report import (PERIODS, category_names, chart_by_month, customer_activity, most_and_least_sold, period_dates,
                           product_quantities, profit_summary, range_dates, sales_by_category, sales_chart, top_products)
from routes.fridge_routes import fridge_data
from routes.guards import admin_page
from routes.product_routes import safe_cell

admin_routes = Blueprint("admin_routes", __name__)

# Seconds with no reading before a sensor counts as offline (same as static/js/fridges/common.js)
OFFLINE_AFTER = 15


# The words for each status on the fridge cards (the same as STATUS_TEXT in static/js/fridges/common.js)
STATUS_TEXT = {"waiting": "Waiting", "offline": "Offline", "hot": "Too warm", "ok": "OK"}


# Every fridge with its newest reading, for the dashboard cards. Each one gets a status:
# "waiting", "offline", "hot" or "ok", with the same rules as fridgeStatus() in static/js/fridges/common.js
def fridge_cards():
    if not (FRIDGES_ENABLED or MSP01_ENABLED):
        return []
    cards = []
    for fridge in Fridge.get_all():
        data = fridge_data(fridge)
        if data["age"] is None:
            data["status"] = "waiting"
        elif data["age"] > OFFLINE_AFTER:
            data["status"] = "offline"
        elif data["temperature"] is not None and data["temperature"] > fridge.threshold:
            data["status"] = "hot"
        else:
            data["status"] = "ok"
        cards.append(data)
    return cards


# Whole percent up or down. None when there is nothing to compare with
def percent_change(now, before):
    if not before:
        return None
    return round((now - before) * 100 / abs(before))


# "Good morning", "Good afternoon" or "Good evening"
def greeting():
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


# The admin dashboard: today's profit and the fridge temperatures
@admin_routes.route("/admin")
@admin_page
def admin():
    dates = period_dates("today")
    today = profit_summary(dates["start"])
    yesterday = profit_summary(dates["before_start"], dates["before_end"])
    return render_template("admin/home.html", greeting=greeting(), today_text=datetime.now().strftime("%A, %B %d"),
                           profit=today, change=percent_change(today["profit"], yesterday["profit"]),
                           fridges=fridge_cards(), status_text=STATUS_TEXT)


# A date like "Feb 1, 2026"
def day_text(moment):
    return f"{moment:%b} {moment.day}, {moment.year}"


# The dates a period covers, like "Feb 1, 2026 to Feb 28, 2026". The end is not included, so the
# last day is the second before it. No end means up to now
def range_text(start, end):
    if start is None:
        return "All time"
    first = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
    last = datetime.strptime(end, "%Y-%m-%d %H:%M:%S") - timedelta(seconds=1) if end else datetime.now()
    if first.date() == last.date():
        return day_text(first)
    return f"{day_text(first)} to {day_text(last)}"


# What the Reports page shows: the period (or the days in the From and To boxes) and the category.
# Gives back (period, dates, category, date_error). Used by the page and by its CSV download
def chosen_report():
    day_from = request.args.get("from", "").strip()
    day_to = request.args.get("to", "").strip()
    date_error = None
    dates = None
    if day_from or day_to:
        dates = range_dates(day_from, day_to)
        if dates is None:
            date_error = "That date is not valid. Pick the days again."

    if dates:
        period = "custom"
    else:
        period = request.args.get("period", "all")
        if period not in PERIODS:
            period = "all"
        dates = period_dates(period)

    # Only a category that exists, so a typo in the address shows every category
    category = request.args.get("category", "").strip()
    if category not in category_names():
        category = ""
    return period, dates, category, date_error


# The Reports page for the chosen period, or for the days picked in the From and To boxes
@admin_routes.route("/reports")
@admin_page
def reports():
    period, dates, category, date_error = chosen_report()
    money = profit_summary(dates["start"], dates["end"], category)

    changes = {}
    if dates["compare_label"]:
        before = profit_summary(dates["before_start"], dates["before_end"], category)
        for name in ("sales", "profit", "average", "orders"):
            changes[name] = percent_change(money[name], before[name])

    bars = sales_chart(period, dates["start"], dates["end"], category)

    categories = sales_by_category(dates["start"], dates["end"], category)
    category_total = sum(row["sales"] for row in categories) or 1

    quantities = product_quantities(dates["start"], dates["end"], category)
    most_sold, least_sold = most_and_least_sold(quantities)

    # The same address with .csv, so the download has the same period and category
    csv_link = "/reports.csv"
    if request.query_string:
        csv_link += "?" + request.query_string.decode()

    return render_template("admin/reports.html", periods=PERIODS, period=period, money=money,
                           changes=changes, compare_label=dates["compare_label"],
                           bars=bars, by_month=chart_by_month(period, dates["start"], dates["end"]),
                           top=top_products(dates["start"], dates["end"], 8, category),
                           categories=categories, category_total=category_total,
                           quantities=quantities, most_sold=most_sold, least_sold=least_sold,
                           activity=customer_activity(dates["start"], dates["end"], category),
                           range_text=range_text(dates["start"], dates["end"]),
                           day_from=dates.get("from", ""), day_to=dates.get("to", ""), date_error=date_error,
                           category=category, category_names=category_names(), csv_link=csv_link)


# The Reports page as a CSV file: the totals, the customer activity and the sold quantity of every product
@admin_routes.route("/reports.csv")
@admin_page
def reports_csv():
    period, dates, category, date_error = chosen_report()
    money = profit_summary(dates["start"], dates["end"], category)
    activity = customer_activity(dates["start"], dates["end"], category)

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Sales report", range_text(dates["start"], dates["end"])])
    writer.writerow(["Category", safe_cell(category) if category else "All categories"])
    writer.writerow([])
    writer.writerow(["Sales before tax", f"{money['sales']:.2f}"])
    writer.writerow(["GST", f"{money['gst']:.2f}"])
    writer.writerow(["QST", f"{money['qst']:.2f}"])
    writer.writerow(["Total with tax", f"{money['total']:.2f}"])
    writer.writerow(["Cost of items", f"{money['cost']:.2f}"])
    writer.writerow(["Net profit", f"{money['profit']:.2f}"])
    writer.writerow(["Orders", money["orders"]])
    writer.writerow([])
    writer.writerow(["Customer activity"])
    writer.writerow(["Customers", activity["customers"]])
    writer.writerow(["New customers", activity["new"]])
    writer.writerow(["Returning customers", activity["returning"]])
    writer.writerow(["Busiest day", ", ".join(f"{day['date']:%Y-%m-%d}" for day in activity["busiest"])])
    writer.writerow(["Quietest day", ", ".join(f"{day['date']:%Y-%m-%d}" for day in activity["quietest"])])
    writer.writerow([])
    writer.writerow(["Product ID", "Product", "Category", "Sold", "Sales before tax"])
    for product in product_quantities(dates["start"], dates["end"], category):
        writer.writerow([product["productID"], safe_cell(product["productName"]), safe_cell(product["categoryName"]),
                         product["units"], f"{product['sales']:.2f}"])

    filename = f"sales-report-{datetime.now():%Y-%m-%d}.csv"
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})
