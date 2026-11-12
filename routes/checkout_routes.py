import sqlite3

from flask import Blueprint, jsonify, render_template, request, session, url_for

from hardware.rfid import scan_once
from mail.send_email import send_receipt_email, send_stock_alert
from models.checkout import (
    GST_PARTS, GST_PERCENT, POINTS_PER_STEP, POINTS_STEP, QST_PARTS, QST_PERCENT, basket_items, mark_receipt_emailed, pay, purchase_belongs_to, receipt, receipt_email_address,
    stock_alerts,
)
from models.customer import get_customer, get_customer_by_membership
from models.reception import read_epcs
from routes.guards import is_signed_in, remember_sign_in

checkout_routes = Blueprint("checkout_routes", __name__)


# The main page. Anyone can scan items, but paying needs someone signed in
@checkout_routes.route("/")
def checkout():
    # The signed-in customer, for the membership card in the summary (None for a guest)
    customer = get_customer(session["id"]) if is_signed_in() else None
    return render_template("checkout/checkout.html", gst_parts=GST_PARTS, qst_parts=QST_PARTS,
                           gst_percent=GST_PERCENT, qst_percent=QST_PERCENT, customer=customer,
                           points_step=POINTS_STEP, points_per_step=POINTS_PER_STEP)


# Ask the RFID reader which tags are in the basket right now
@checkout_routes.route("/api/checkout/scan", methods=["POST"])
def scan_basket():
    items, sold, unknown = basket_items(scan_once())
    items = [{"epc": i["epc"], "productID": i["productID"], "name": i["name"], "price": float(i["price"]), "taxable": i["taxable"],
              "image": url_for("static", filename=i["image"]) if i["image"] else None} for i in items]
    return jsonify(items=items, sold=sold, unknown=unknown)


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
    except ValueError as err:
        return jsonify(error=str(err)), 409
    paid_receipt = receipt(purchase_id)

    # Email the receipt straight away. If it fails, the Send email button on the receipt tries again
    address = receipt_email_address(purchase_id)
    email_sent = bool(address) and email_and_record(purchase_id, address, paid_receipt)

    # Tell the admin if this sale made anything low or out of stock
    alerts = stock_alerts(purchase_id)
    if alerts:
        send_stock_alert(alerts)

    # The next person at the checkout starts signed out
    name = session.get("name", "")
    session.clear()
    # Remember this one receipt so the customer can still email it after being signed out
    session["last_purchase"] = purchase_id
    email_message = (
        f"Receipt emailed to {address}." if email_sent
        else "Receipt email could not be sent automatically. You can try again below."
    )
    return jsonify(
        success=f"Thank you, {name}! Paid ${total:.2f}.",
        purchaseID=purchase_id,
        receipt=paid_receipt,
        emailSent=email_sent,
        emailMessage=email_message,
    )


# Email a receipt and remember that it went out. Gives back True if it was sent
def email_and_record(purchase_id, address, paid_receipt):
    if not send_receipt_email(address, paid_receipt):
        return False
    try:
        mark_receipt_emailed(purchase_id)
    except sqlite3.Error:
        pass   # the email went out, only the record failed
    return True


# Send one receipt to the customer's current email. Gives back the answer for the page
def send_receipt(purchase_id):
    address = receipt_email_address(purchase_id)
    paid_receipt = receipt(purchase_id)
    if not address or paid_receipt is None:
        return jsonify(error="No email address on this account."), 400

    if not email_and_record(purchase_id, address, paid_receipt):
        return jsonify(error="The email could not be sent. Please try again."), 502
    return jsonify(success=f"Receipt sent to {address}.")


# Email the receipt that was just paid. The customer is signed out by now, so the session remembers which one
@checkout_routes.route("/api/checkout/receipt-email", methods=["POST"])
def email_receipt():
    purchase_id = session.get("last_purchase")
    if not purchase_id:
        return jsonify(error="No recent receipt to send."), 400
    return send_receipt(purchase_id)


# Email a past receipt, from the purchase history on My Account. Only the customer's own receipts
@checkout_routes.route("/api/receipts/<int:purchase_id>/email", methods=["POST"])
def email_past_receipt(purchase_id):
    if not is_signed_in():
        return jsonify(error="Please sign in again."), 401
    if not purchase_belongs_to(purchase_id, session["id"]):
        return jsonify(error="That receipt was not found."), 404
    return send_receipt(purchase_id)


# Sign in by scanning the barcode on a membership card (the scanner types the number, then Enter)
# Admins are sent to the admin page. Customers stay on the checkout
@checkout_routes.route("/api/scan-login", methods=["POST"])
def scan_login():
    code = (request.get_json(silent=True) or {}).get("code", "")
    customer = get_customer_by_membership(code) if code.strip() else None
    if customer is None:
        return jsonify(error="Barcode not recognised."), 404

    remember_sign_in(customer)
    if customer["role"] == "admin":
        return jsonify(role="admin", redirect="/admin")
    return jsonify(role="customer", name=customer["customerName"])
