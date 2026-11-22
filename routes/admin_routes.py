from datetime import datetime, timedelta

from flask import Blueprint, render_template, request

from config import FRIDGES_ENABLED, MSP01_ENABLED
from models.fridge import Fridge
from models.report import (PERIODS, chart_by_month, most_and_least_sold, period_dates, product_quantities, profit_summary,
                           range_dates, sales_by_category, sales_chart, top_products)
from routes.fridge_routes import fridge_data
from routes.guards import admin_page

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

    bars = sales_chart(period, dates["start"], dates["end"])

    categories = sales_by_category(dates["start"], dates["end"])
    category_total = sum(category["sales"] for category in categories) or 1

    quantities = product_quantities(dates["start"], dates["end"])
    most_sold, least_sold = most_and_least_sold(quantities)

    return render_template("admin/reports.html", periods=PERIODS, period=period, money=money,
                           changes=changes, compare_label=dates["compare_label"],
                           bars=bars, by_month=chart_by_month(period, dates["start"], dates["end"]),
                           top=top_products(dates["start"], dates["end"], 8),
                           categories=categories, category_total=category_total,
                           quantities=quantities, most_sold=most_sold, least_sold=least_sold,
                           range_text=range_text(dates["start"], dates["end"]),
                           day_from=dates.get("from", ""), day_to=dates.get("to", ""), date_error=date_error,
                           product_categories=sorted({row["categoryName"] for row in quantities}, key=str.lower))
