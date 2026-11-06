import sqlite3

from flask import Blueprint, jsonify, render_template, request, session

from mail.send_email import send_receipt_email
from hardware.rfid import ReaderError, scan_once
from models.checkout import TAX_BASIS_POINTS, basket_items, pay, receipt
from models.customer import get_customer_by_membership
from models.database import execute, query_one
from models.reception import read_epcs
from routes.auth_routes import is_signed_in

# The checkout page (the main page), paying, and signing in with a barcode.
# app.py adds them with app.register_blueprint(checkout_routes)
checkout_routes = Blueprint("checkout_routes", __name__)


# The checkout page. Anyone can scan items, but paying needs someone signed in
@checkout_routes.route("/")
def checkout():
    return render_template("checkout.html", tax_basis_points=TAX_BASIS_POINTS)


# Ask the RFID reader which tags are in the basket right now
@checkout_routes.route("/api/checkout/scan", methods=["POST"])
def scan_basket():
    try:
        epcs = scan_once()
        items, sold, unknown = basket_items(epcs)
    except ReaderError as err:
        return jsonify(error=str(err)), 503
    except sqlite3.Error as err:
        return jsonify(error=f"Database error: {err}"), 500
    return jsonify(items=_json_items(items), sold=sold, unknown=unknown)


# Pay for the basket. The customer must be signed in
@checkout_routes.route("/api/checkout/pay", methods=["POST"])
def pay_basket():
    if not is_signed_in():
        return jsonify(error="Scan your membership card or sign in to pay."), 401

    epcs, errors = read_epcs(" ".join((request.get_json(silent=True) or {}).get("epcs", [])))
    if errors or not epcs:
        return jsonify(error="The basket is empty. Scan your items first."), 400

    try:
        purchase_id, total = pay(session["id"], epcs)
        paid_receipt = receipt(purchase_id)
    except ValueError as err:
        return jsonify(error=str(err)), 409
    except sqlite3.Error as err:
        return jsonify(error=f"Database error: {err}"), 500

    # The next person at the checkout starts signed out
    name = session.get("name", "")
    session.clear()
    # Remember this one receipt so the customer can still email it after being signed out
    session["last_purchase"] = purchase_id
    return jsonify(success=f"Thank you, {name}! Paid ${total:.2f}.", purchaseID=purchase_id, receipt=paid_receipt)


# Email the receipt that was just paid to the email the customer registered with
@checkout_routes.route("/api/checkout/receipt-email", methods=["POST"])
def email_receipt():
    purchase_id = session.get("last_purchase")
    if not purchase_id:
        return jsonify(error="No recent receipt to send."), 400

    try:
        row = query_one("SELECT c.email FROM Purchase p JOIN Customer c ON c.customerID = p.customerID WHERE p.purchaseID = ?", (purchase_id,))
        paid_receipt = receipt(purchase_id)
    except sqlite3.Error as err:
        return jsonify(error=f"Database error: {err}"), 500
    if row is None or not row["email"] or paid_receipt is None:
        return jsonify(error="No email address on this account."), 400

    if not send_receipt_email(row["email"], paid_receipt):
        return jsonify(error="The email could not be sent. Please try again."), 502
    try:
        execute("UPDATE Purchase SET emailSent = 1 WHERE purchaseID = ?", (purchase_id,))
    except sqlite3.Error:
        pass   # the email went out, only the record failed
    return jsonify(success=f"Receipt sent to {row['email']}.")


# Sign in by scanning the barcode on a membership card (the scanner types the number, then Enter)
# Admins are sent to the admin page. Customers stay on the checkout
@checkout_routes.route("/api/scan-login", methods=["POST"])
def scan_login():
    code = (request.get_json(silent=True) or {}).get("code", "")
    try:
        customer = get_customer_by_membership(code) if code.strip() else None
    except sqlite3.Error as err:
        return jsonify(error=f"Database error: {err}"), 500

    if customer is None:
        return jsonify(error="Barcode not recognised."), 404

    session["id"] = customer["customerID"]
    session["name"] = customer["customerName"]
    session["role"] = customer["role"]

    if customer["role"] == "admin":
        return jsonify(role="admin", redirect="/admin")
    return jsonify(role="customer", name=customer["customerName"])


def _json_items(items):
    return [{"epc": i["epc"], "productID": i["productID"], "name": i["name"], "price": float(i["price"])} for i in items]
