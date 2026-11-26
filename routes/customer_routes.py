import sqlite3
from datetime import date

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session

from models.checkout import purchase_history
from models.customer import (
    ROLES, TAKEN_MESSAGE, Customer, check_membership_number, check_new_email, check_sign_in, customers_with_spending, get_customer,
    get_customer_by_membership, set_email, set_membership_number, set_role,
)
from routes.guards import admin_api, admin_page, remember_sign_in, signed_in_customer

customer_routes = Blueprint("customer_routes", __name__)


# The sign up form
@customer_routes.route("/signup")
def signup():
    return render_template("auth/signup.html")


# Save a new customer from the sign up form and sign them in
@customer_routes.route("/submit", methods=["POST"])
def submit():
    customer = Customer(
        request.form.get("name", ""),
        request.form.get("address", ""),
        request.form.get("email", ""),
        request.form.get("phoneNumber", ""),
        request.form.get("password", ""),
        request.form.get("barcode", ""),
    )

    try:
        errors = customer.validate()
        if errors:
            return jsonify(error="\n".join(errors)), 400

        customer.save()
        remember_sign_in(get_customer_by_membership(customer.barcode))

    except sqlite3.IntegrityError:
        # Two people signing up with the same email at the same moment
        return jsonify(error=TAKEN_MESSAGE), 400

    except sqlite3.Error:
        current_app.logger.exception("Could not save the new customer")
        return jsonify(error="Your account could not be saved. Please try again."), 500

    flash(f"Welcome! Your membership number is {customer.barcode}.")
    return jsonify(success="Account created!", redirect="/"), 200


# My Account: the membership card and purchase history
@customer_routes.route("/account")
def account():
    customer = signed_in_customer()
    if customer is None:
        return redirect("/signin")
    purchases = purchase_history(customer["customerID"])
    return render_template(
        "customers/account.html", customer=customer, purchases=purchases,
        total_spent=sum(purchase["total"] for purchase in purchases),
        item_count=sum(purchase["itemCount"] for purchase in purchases),
    )


# A customer changes their own email. They need their password, because anyone with their card can sign in by scanning it
@customer_routes.route("/account/email", methods=["POST"])
def change_email():
    customer = signed_in_customer()
    if customer is None:
        return redirect("/signin")

    if check_sign_in(customer["email"], request.form.get("password", "")) is None:
        flash("Wrong password, so your email was not changed.", "error")
        return redirect("/account")

    email, error = check_new_email(request.form.get("email", ""), customer["customerID"])
    if error:
        flash(error, "error")
        return redirect("/account")

    try:
        set_email(customer["customerID"], email)
    except sqlite3.IntegrityError:
        flash("This email is already registered.", "error")
        return redirect("/account")

    flash(f"Your email is now {email}. Use it next time you sign in.", "success")
    return redirect("/account")


# The customers page for admins
@customer_routes.route("/customers")
@admin_page
def customers():
    rows = customers_with_spending()
    this_month = date.today().strftime("%Y-%m")
    return render_template(
        "customers/list.html", customers=rows,
        admin_count=sum(1 for row in rows if row["role"] == "admin"),
        new_this_month=sum(1 for row in rows if row["createdAt"].startswith(this_month)),
        total_spent=sum(row["spent"] for row in rows),
    )


# Make a customer an admin, or not. Not your own role
@customer_routes.route("/api/customers/<int:customer_id>/role", methods=["POST"])
@admin_api
def change_role(customer_id):
    role = request.form.get("role", "")
    if role not in ROLES:
        return jsonify(error=f"Role must be one of {', '.join(ROLES)}."), 400

    if customer_id == session["id"]:
        return jsonify(error="You can't change your own role. Ask another admin."), 400

    customer = get_customer(customer_id) if set_role(customer_id, role) else None
    if customer is None:
        return jsonify(error=f"Customer {customer_id} not found."), 404

    # The page reloads after this and shows the flash message
    message = f"{customer['customerName']} is now {'an admin' if role == 'admin' else 'a customer'}."
    flash(message, "success")
    return jsonify(success=message), 200


# Give a customer a new card number
@customer_routes.route("/api/customers/<int:customer_id>/membership", methods=["POST"])
@admin_api
def change_membership(customer_id):
    customer = get_customer(customer_id)
    if customer is None:
        return jsonify(error=f"Customer {customer_id} not found."), 404

    number, error = check_membership_number(request.form.get("membershipNumber", ""), customer_id)
    if error:
        return jsonify(error=error), 400

    try:
        set_membership_number(customer_id, number)
    except sqlite3.IntegrityError:
        return jsonify(error="This membership number is already used by another customer."), 400

    message = f"{customer['customerName']}'s membership number is now {number}."
    flash(message, "success")
    return jsonify(success=message), 200
