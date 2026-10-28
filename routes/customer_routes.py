from flask import Blueprint, jsonify, redirect, render_template, request, session
import sqlite3

from models.customer import ROLES, Customer, all_customers, get_customer, set_role
from hardware.signals import send_success, send_error
from routes.auth_routes import is_admin, is_signed_in

# The customer pages (sign up and the list). app.py adds them with app.register_blueprint(customer_routes)
customer_routes = Blueprint("customer_routes", __name__)


# -------------------------
# Sign up page
# -------------------------

@customer_routes.route("/signup")
def signup():
    return render_template("signup.html")


# -------------------------
# My Account
# -------------------------

@customer_routes.route("/account")
def account():
    if not is_signed_in():
        return redirect("/signin")
    return show_account()


# The account page (the home page uses it too)
def show_account():
    try:
        customer = get_customer(session["id"])
    except sqlite3.Error as err:
        return f"Database error: {err}", 500

    if customer is None:
        session.clear()
        return redirect("/signin")
    return render_template("account.html", customer=customer)


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
# Change a customer's role
# -------------------------

@customer_routes.route("/api/customers/<int:customer_id>/role", methods=["POST"])
def change_role(customer_id):
    if not is_admin():
        return jsonify(error="Only admins can change roles."), 403

    role = request.form.get("role", "")
    if role not in ROLES:
        return jsonify(error=f"Role must be one of {', '.join(ROLES)}."), 400

    # An admin can't change their own role
    if customer_id == session["id"]:
        return jsonify(error="You can't change your own role. Ask another admin."), 400

    try:
        found = set_role(customer_id, role)
        customer = get_customer(customer_id) if found else None
    except sqlite3.Error as err:
        return jsonify(error=f"Database error: {err}"), 500

    if customer is None:
        return jsonify(error=f"Customer {customer_id} not found."), 404

    return jsonify(success=f"{customer['customerName']} is now {'an admin' if role == 'admin' else 'a customer'}.", role=role), 200


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

        membership_number = customer.save()

    except sqlite3.IntegrityError:
        # Just in case two people sign up with the same email at the exact same time
        send_error()
        return jsonify(error="This email or phone number is already registered."), 400

    except sqlite3.Error as err:
        send_error()
        return jsonify(error=f"Database error: {err}"), 400

    send_success()
    return jsonify(success=f"Account created! Your membership number is {membership_number}.\nYou can sign in now."), 200
