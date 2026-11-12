from flask import Blueprint, render_template, request

from models.checkout import PERIODS, period_start, profit_summary, top_products
from models.customer import all_customers
from models.product import all_products
from routes.guards import admin_page

admin_routes = Blueprint("admin_routes", __name__)


# The admin page: the money numbers for the chosen period, the best products, then a card for each dashboard
@admin_routes.route("/admin")
@admin_page
def admin():
    # The period buttons add ?period=today, month or all to the address. All time is the default
    period = request.args.get("period", "all")
    if period not in PERIODS:
        period = "all"
    since = period_start(period)
    return render_template("admin/home.html", customer_count=len(all_customers()), product_count=len(all_products()),
                           periods=PERIODS, period=period, money=profit_summary(since), top=top_products(since))
