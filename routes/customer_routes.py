import sqlite3
from datetime import date

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session

from hardware.signals import send_error, send_success
from models.checkout import purchase_history
from models.customer import (
    ROLES, Customer, check_membership_number, check_new_email, check_sign_in, customers_with_spending, get_customer,
    set_email, set_membership_number, set_role,
)
from routes.guards import admin_api, admin_page, is_signed_in, remember_sign_in

customer_routes = Blueprint("customer_routes", __name__)


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
        # Show every problem at once, each on its own line
        errors = customer.validate()
        if errors:
            send_error()
            return jsonify(error="\n".join(errors)), 400

        membership_number = customer.save()
        remember_sign_in(check_sign_in(customer.email, customer.password))

    except sqlite3.IntegrityError:
        # Just in case two people sign up with the same email at the exact same time
        send_error()
        return jsonify(error="This email or phone number is already registered."), 400

    except sqlite3.Error as err:
        send_error()
        return jsonify(error=f"Database error: {err}"), 400

    send_success()
    flash(f"Welcome! Your membership number is {membership_number}.")
    return jsonify(success="Account created!", redirect="/"), 200


@customer_routes.route("/account")
def account():
    if not is_signed_in():
        return redirect("/signin")

    customer = get_customer(session["id"])
    if customer is None:
        session.clear()
        return redirect("/signin")
    purchases = purchase_history(session["id"])
    return render_template(
        "customers/account.html", customer=customer, purchases=purchases,
        total_spent=sum(purchase["total"] for purchase in purchases),
        item_count=sum(purchase["itemCount"] for purchase in purchases),
    )


# A customer changes their own email. They need their password, because anyone with their card can sign in by scanning it
@customer_routes.route("/account/email", methods=["POST"])
def change_email():
    if not is_signed_in():
        return redirect("/signin")

    customer = get_customer(session["id"])
    if customer is None:
        session.clear()
        return redirect("/signin")

    if check_sign_in(customer["email"], request.form.get("password", "")) is None:
        flash("Your password is not right, so your email was not changed.", "error")
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


@customer_routes.route("/api/customers/<int:customer_id>/role", methods=["POST"])
@admin_api
def change_role(customer_id):
    role = request.form.get("role", "")
    if role not in ROLES:
        return jsonify(error=f"Role must be one of {', '.join(ROLES)}."), 400

    # An admin can't change their own role
    if customer_id == session["id"]:
        return jsonify(error="You can't change your own role. Ask another admin."), 400

    customer = get_customer(customer_id) if set_role(customer_id, role) else None
    if customer is None:
        return jsonify(error=f"Customer {customer_id} not found."), 404

    # The page reloads after this, and the notification says what happened
    message = f"{customer['customerName']} is now {'an admin' if role == 'admin' else 'a customer'}."
    flash(message, "success")
    return jsonify(success=message, role=role), 200


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
    return jsonify(success=message, membershipNumber=number), 200
