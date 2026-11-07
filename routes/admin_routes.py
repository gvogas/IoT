from flask import Blueprint, render_template

from models.customer import all_customers
from models.product import all_products
from routes.guards import admin_page

admin_routes = Blueprint("admin_routes", __name__)


# The admin page, with a card for each dashboard
@admin_routes.route("/admin")
@admin_page
def admin():
    return render_template("admin/home.html", customer_count=len(all_customers()), product_count=len(all_products()))
