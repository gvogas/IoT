import sqlite3
import threading

from flask import Blueprint, current_app, jsonify, render_template, request, session, url_for

from hardware.rfid import scan_once
from mail.send_email import receipt_email, send, send_receipt_email, send_stock_alert
from models.checkout import (
    GST_PARTS, GST_PERCENT, POINTS_PER_STEP, POINTS_STEP, QST_PARTS, QST_PERCENT, basket_items, mark_receipt_emailed,
    pay, purchase_belongs_to, receipt, receipt_email_address, stock_alerts,
)
from models.customer import get_customer, get_customer_by_membership
from models.reception import read_epcs
from routes.guards import is_signed_in, remember_sign_in

checkout_routes = Blueprint("checkout_routes", __name__)


# Anyone can scan items, but paying needs someone signed in
@checkout_routes.route("/")
def checkout():
    customer = get_customer(session["id"]) if is_signed_in() else None
    return render_template("checkout/checkout.html", gst_parts=GST_PARTS, qst_parts=QST_PARTS,
                           gst_percent=GST_PERCENT, qst_percent=QST_PERCENT, customer=customer,
                           points_step=POINTS_STEP, points_per_step=POINTS_PER_STEP)


# The tags in the basket right now
@checkout_routes.route("/api/checkout/scan", methods=["POST"])
def scan_basket():
    items, sold, unknown = basket_items(scan_once())
    items = [{"epc": i["epc"], "productID": i["productID"], "name": i["name"], "price": float(i["price"]), "taxable": i["taxable"],
              "image": url_for("static", filename=i["image"]) if i["image"] else None} for i in items]
    return jsonify(items=items, sold=sold, unknown=unknown)


# Pay, email the receipt, and sign the customer out
@checkout_routes.route("/api/checkout/pay", methods=["POST"])
def pay_basket():
    if not is_signed_in():
        return jsonify(error="Scan your membership card or sign in to pay."), 401

    epcs = (request.get_json(silent=True) or {}).get("epcs")
    if not isinstance(epcs, list) or not all(isinstance(epc, str) for epc in epcs):
        return jsonify(error="The basket is empty. Scan your items first."), 400
    epcs, errors = read_epcs(" ".join(epcs))
    if errors:
        return jsonify(error=" ".join(errors)), 400
    if not epcs:
        return jsonify(error="The basket is empty. Scan your items first."), 400

    try:
        purchase_id, total = pay(session["id"], epcs)
    except ValueError as err:
        return jsonify(error=str(err)), 409

    # The payment is saved, so sign out now. The next person at the checkout starts signed out,
    # even if something below goes wrong
    name = session.get("name", "")
    session.clear()
    # So the customer can still email this receipt after being signed out
    session["last_purchase"] = purchase_id

    paid_receipt = receipt(purchase_id)

    # Email the receipt in the background, so the customer doesn't wait for Gmail.
    # If it fails, the Send email button on the receipt tries again
    address = receipt_email_address(purchase_id)
    if address:
        email_in_background(purchase_id, address, paid_receipt)

    # A failed stock alert should not look like a failed payment
    try:
        alerts = stock_alerts(purchase_id)
        if alerts:
            send_stock_alert(alerts)
    except Exception:
        current_app.logger.exception("Stock alert after purchase %s failed", purchase_id)

    email_message = (
        f"Your receipt is on its way to {address}." if address
        else "There is no email on this account, so no receipt was emailed."
    )
    return jsonify(
        success=f"Thank you, {name}! Paid ${total:.2f}.",
        purchaseID=purchase_id,
        receipt=paid_receipt,
        emailMessage=email_message,
    )


# Remember that the receipt went out
def record_emailed(purchase_id):
    try:
        mark_receipt_emailed(purchase_id)
    except sqlite3.Error:
        pass   # the email went out, only the record failed


# Send the receipt in a thread. The email is made here first, because templates need the web request
def email_in_background(purchase_id, address, paid_receipt):
    subject, text, html = receipt_email(paid_receipt)

    def send_and_record():
        if send(address, subject, text, html):
            record_emailed(purchase_id)

    threading.Thread(target=send_and_record, daemon=True).start()


# Gives back True if the email was sent
def email_and_record(purchase_id, address, paid_receipt):
    if not send_receipt_email(address, paid_receipt):
        return False
    record_emailed(purchase_id)
    return True


# Send a receipt to the customer's current email
def send_receipt(purchase_id):
    paid_receipt = receipt(purchase_id)
    if paid_receipt is None:
        return jsonify(error="That receipt was not found."), 404
    address = receipt_email_address(purchase_id)
    if not address:
        return jsonify(error="No email address on this account."), 400

    if not email_and_record(purchase_id, address, paid_receipt):
        return jsonify(error="The email could not be sent. Please try again."), 502
    return jsonify(success=f"Receipt sent to {address}.")


# The receipt that was just paid. The customer is signed out by now, so the session remembers which one
@checkout_routes.route("/api/checkout/receipt-email", methods=["POST"])
def email_receipt():
    purchase_id = session.get("last_purchase")
    if not purchase_id:
        return jsonify(error="No recent receipt to send."), 400
    return send_receipt(purchase_id)


# A past receipt from My Account. Only the customer's own receipts
@checkout_routes.route("/api/receipts/<int:purchase_id>/email", methods=["POST"])
def email_past_receipt(purchase_id):
    if not is_signed_in():
        return jsonify(error="Please sign in again."), 401
    if not purchase_belongs_to(purchase_id, session["id"]):
        return jsonify(error="That receipt was not found."), 404
    return send_receipt(purchase_id)


# Sign in by scanning a membership card. Admins have to use the sign in form
@checkout_routes.route("/api/scan-login", methods=["POST"])
def scan_login():
    code = (request.get_json(silent=True) or {}).get("code")
    customer = get_customer_by_membership(code) if isinstance(code, str) and code.strip() else None
    if customer is None:
        return jsonify(error="Barcode not recognised."), 404

    # Anyone holding the card could sign in with it, so admin accounts need the password
    if customer["role"] == "admin":
        return jsonify(error="Admins sign in with their email and password."), 403

    remember_sign_in(customer)
    return jsonify(success=True)
