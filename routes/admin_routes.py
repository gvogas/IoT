from datetime import datetime, timedelta

from flask import Blueprint, render_template, request

from config import FRIDGES_ENABLED, MSP01_ENABLED, MSP01_FRIDGE_ID
from models.checkout import (PERIODS, chart_by_month, daily_sales, most_and_least_sold, period_dates, product_quantities,
                             profit_summary, range_dates, recent_purchases, sales_by_category, sales_chart, top_products)
from models.fridge import Fridge
from models.product import inventory_rows, products_below_cost, products_without_cost
from routes.fridge_routes import fridge_data
from routes.guards import admin_page

admin_routes = Blueprint("admin_routes", __name__)

# Seconds with no reading before a sensor counts as offline (same as static/js/fridges/common.js)
OFFLINE_AFTER = 15


# Fridges that are too warm or whose sensor stopped sending
def fridge_problems():
    if not FRIDGES_ENABLED:
        return []
    problems = []
    for fridge in Fridge.get_all():
        data = fridge_data(fridge)
        if data["age"] is None:
            problems.append({"id": fridge.id, "name": fridge.name, "hot": False,
                             "text": "No reading from the sensor yet"})
        elif data["age"] > OFFLINE_AFTER:
            ago = f"{data['age']} s" if data["age"] < 60 else f"{data['age'] // 60} min"
            problems.append({"id": fridge.id, "name": fridge.name, "hot": False,
                             "text": f"The sensor stopped sending {ago} ago. Check the {data['sensor']}"})
        elif data["temperature"] is not None and data["temperature"] > fridge.threshold:
            alert = data["alert"]
            if alert is None:
                alert_text = "The alert email is being sent"
            elif alert["status"] == "sent":
                alert_text = f"Alert emailed at {alert['time']}"
            else:
                alert_text = f"The alert email failed at {alert['time']}"
            problems.append({"id": fridge.id, "name": fridge.name, "hot": True,
                             "temperature": data["temperature"], "threshold": fridge.threshold,
                             "alert_text": alert_text, "alert_failed": alert is not None and alert["status"] == "failed",
                             "text": f"{data['temperature']:.1f} °C, over the {fridge.threshold:.1f} °C limit. {alert_text}"})
    return problems


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


# The admin dashboard
@admin_routes.route("/admin")
@admin_page
def admin():
    dates = period_dates("today")
    today = profit_summary(dates["start"])
    yesterday = profit_summary(dates["before_start"], dates["before_end"])
    changes = {}
    for name in ("sales", "orders", "average", "profit"):
        changes[name] = percent_change(today[name], yesterday[name])

    stock = inventory_rows()
    out_of_stock = [row for row in stock if row["inStock"] == 0]
    low_stock = [row for row in stock if row["lowStock"] and row["inStock"] > 0]

    # "or 1" stops a divide by zero when nothing was sold
    days = daily_sales(7)
    best_day = max(day["sales"] for day in days) or 1
    week_total = round(sum(day["sales"] for day in days), 2)
    week_start = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d 00:00:00")

    # The fridge the MSP01 is in, for the title of its cards
    msp01_fridge = Fridge.get_by_id(MSP01_FRIDGE_ID) if MSP01_ENABLED else None

    return render_template("admin/home.html", greeting=greeting(), today_text=datetime.now().strftime("%A, %B %d"),
                           today=today, changes=changes, compare_label="yesterday",
                           fridges=fridge_problems(), out_of_stock=out_of_stock, low_stock=low_stock,
                           below_cost=products_below_cost(), no_cost=products_without_cost(),
                           recent=recent_purchases(6), days=days, best_day=best_day, week_total=week_total,
                           week_top=top_products(week_start, None, 4), fridges_enabled=FRIDGES_ENABLED,
                           msp01_enabled=MSP01_ENABLED, msp01_fridge=msp01_fridge)


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


# The Reports page for the chosen period, or for the days picked in the From and To boxes
@admin_routes.route("/reports")
@admin_page
def reports():
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
    money = profit_summary(dates["start"], dates["end"])

    changes = {}
    if dates["compare_label"]:
        before = profit_summary(dates["before_start"], dates["before_end"])
        for name in ("sales", "profit", "average", "orders"):
            changes[name] = percent_change(money[name], before[name])

    # "or 1" stops a divide by zero when nothing was sold
    bars = sales_chart(period, dates["start"], dates["end"])
    best_bar = max([bar["sales"] for bar in bars] or [0]) or 1

    categories = sales_by_category(dates["start"], dates["end"])
    category_total = sum(category["sales"] for category in categories) or 1

    quantities = product_quantities(dates["start"], dates["end"])
    most_sold, least_sold = most_and_least_sold(quantities)

    return render_template("admin/reports.html", periods=PERIODS, period=period, money=money,
                           changes=changes, compare_label=dates["compare_label"],
                           bars=bars, best_bar=best_bar, by_month=chart_by_month(period, dates["start"], dates["end"]),
                           top=top_products(dates["start"], dates["end"], 8),
                           categories=categories, category_total=category_total,
                           quantities=quantities, most_sold=most_sold, least_sold=least_sold,
                           range_text=range_text(dates["start"], dates["end"]),
                           day_from=dates.get("from", ""), day_to=dates.get("to", ""), date_error=date_error,
                           product_categories=sorted({row["categoryName"] for row in quantities}, key=str.lower))
