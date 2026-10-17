from flask import Blueprint, jsonify, render_template, request
import sqlite3

from models.customer import Customer, all_customers
from hardware.signals import send_success, send_error
from routes.auth_routes import is_admin

# The customer pages (sign up and the list). app.py adds them with app.register_blueprint(customer_routes)
customer_routes = Blueprint("customer_routes", __name__)


# -------------------------
# Sign up page
# -------------------------

@customer_routes.route("/signup")
def signup():
    return render_template("signup.html")


# -------------------------
# All customers
# -------------------------

@customer_routes.route("/customers")
def customers():
    if not is_admin():
        return render_template("signin.html", error="Only admins can see this page."), 403

    try:
        rows = all_customers()
    except sqlite3.Error as err:
        return f"Database error: {err}", 500
    return render_template("customers.html", customers=rows)


# -------------------------
# Submit customer
# -------------------------

@customer_routes.route("/submit", methods=["POST"])
def submit():

    customer = Customer(
        request.form.get("name", ""),
        request.form.get("address", ""),
        request.form.get("email", ""),
        request.form.get("phoneNumber", ""),
        request.form.get("password", ""),
    )

    try:
        # Show every problem at once, each on its own line
        errors = customer.validate()
        if errors:
            send_error()
            return jsonify(error="\n".join(errors)), 400

        customer.save()

    except sqlite3.IntegrityError:
        # Just in case two people sign up with the same email at the exact same time
        send_error()
        return jsonify(error="This email or phone number is already registered."), 400

    except sqlite3.Error as err:
        send_error()
        return jsonify(error=f"Database error: {err}"), 400

    send_success()
    return jsonify(success="Customer information was added successfully."), 200
