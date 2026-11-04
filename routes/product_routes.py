import csv
import io
import sqlite3
from datetime import date

from flask import Blueprint, Response, flash, jsonify, redirect, render_template, request

from models.product import (
    all_products, delete_product, get_product, inventory_rows, known_categories, known_producers,
    read_product_form, save_product, update_product,
)
from models.unit import find_units, known_epcs, units_for_product
from models.reception import (
    check_reception, read_epcs, reception_history, save_reception,
)
from hardware.rfid import ReaderError, scan_once
from routes.auth_routes import is_admin

# The inventory dashboard, the product pages and receiving stock. app.py adds them with app.register_blueprint(product_routes)
product_routes = Blueprint("product_routes", __name__)

# Every page here is for admins only. Put this at the top of each route:
#     if not is_admin():
#         return render_template("signin.html", error="Only admins can see this page."), 403


# -------------------------
# Inventory dashboard
# -------------------------

@product_routes.route("/inventory")
def inventory():
    if not is_admin():
        return render_template("signin.html", error="Only admins can see this page."), 403

    try:
        rows = inventory_rows()
    except sqlite3.Error as err:
        return f"Database error: {err}", 500

    units = sum(row["inStock"] for row in rows)
    low = sum(1 for row in rows if row["lowStock"])
    out = sum(1 for row in rows if row["inStock"] == 0)
    last = max((row["lastReceived"] for row in rows if row["lastReceived"]), default=None)
    # The EPC lookup box on the page. Empty means no search
    epc_query = request.args.get("epc", "").strip().upper()
    try:
        matches = find_units(epc_query) if epc_query else []
    except sqlite3.Error as err:
        return f"Database error: {err}", 500

    return render_template(
        "inventory.html", rows=rows, units=units, low=low, out=out, last=last,
        epc_query=epc_query, matches=matches,
    )


# Download the inventory as a spreadsheet file (CSV)
@product_routes.route("/inventory.csv")
def inventory_csv():
    if not is_admin():
        return render_template("signin.html", error="Only admins can see this page."), 403

    try:
        rows = inventory_rows()
    except sqlite3.Error as err:
        return f"Database error: {err}", 500

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Product", "Category", "Price", "In stock", "Sold", "Low stock alert at", "Last received"])
    for row in rows:
        writer.writerow([row["productName"], row["categoryName"], f"{row['price']:.2f}", row["inStock"],
                         row["totalSold"], row["lowStockThreshold"], row["lastReceived"] or ""])

    filename = f"inventory-{date.today().isoformat()}.csv"
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


# -------------------------
# Products list
# -------------------------

@product_routes.route("/products")
def products():
    if not is_admin():
        return render_template("signin.html", error="Only admins can see this page."), 403

    try:
        rows = all_products()
    except sqlite3.Error as err:
        return f"Database error: {err}", 500
    return render_template("products.html", products=rows)


# -------------------------
# Add a product
# -------------------------

@product_routes.route("/products/new", methods=["GET", "POST"])
def new_product():
    if not is_admin():
        return render_template("signin.html", error="Only admins can see this page."), 403

    if request.method == "GET":
        return render_product_form(None, {"active": True, "lowStockThreshold": 5})

    product, errors = read_product_form(request.form)
    if errors:
        flash(f"Product not added. {len(errors)} {'problem' if len(errors) == 1 else 'problems'} to fix.", "error")
        return render_product_form(None, request.form, errors), 400

    try:
        product_id = save_product(product)
    except sqlite3.Error as err:
        flash(f"Product not added. Database error: {err}", "error")
        return render_product_form(None, request.form), 500

    flash(f"Product \"{product['name']}\" added successfully.", "success")
    return redirect(f"/products/{product_id}")


# -------------------------
# One product: details, stock and receiving
# -------------------------

@product_routes.route("/products/<int:product_id>")
def product_detail(product_id):
    if not is_admin():
        return render_template("signin.html", error="Only admins can see this page."), 403

    try:
        product = get_product(product_id)
        if product is None:
            flash("That product was not found.", "error")
            return redirect("/products")
        history = reception_history(product_id)
    except sqlite3.Error as err:
        return f"Database error: {err}", 500

    stock = next((row for row in inventory_rows() if row["productID"] == product_id), None)
    units, unit_total = units_for_product(product_id)
    return render_template(
        "product_detail.html", product=product, history=history, stock=stock,
        units=units, unit_total=unit_total,
        today=date.today().isoformat(), epc_text="", receive_error=None,
    )


# -------------------------
# Edit a product
# -------------------------

@product_routes.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
def edit_product(product_id):
    if not is_admin():
        return render_template("signin.html", error="Only admins can see this page."), 403

    try:
        product = get_product(product_id)
    except sqlite3.Error as err:
        return f"Database error: {err}", 500
    if product is None:
        flash("That product was not found.", "error")
        return redirect("/products")

    if request.method == "GET":
        return render_product_form(product_id, product_to_form(product))

    values, errors = read_product_form(request.form, product_id)
    if errors:
        flash(f"Changes not saved. {len(errors)} {'problem' if len(errors) == 1 else 'problems'} to fix.", "error")
        return render_product_form(product_id, request.form, errors), 400

    try:
        update_product(product_id, values)
    except sqlite3.Error as err:
        flash(f"Changes not saved. Database error: {err}", "error")
        return render_product_form(product_id, request.form), 500

    flash(f"Changes to \"{values['name']}\" saved.", "success")
    return redirect(f"/products/{product_id}")


# -------------------------
# Delete a product
# -------------------------

@product_routes.route("/products/<int:product_id>/delete", methods=["POST"])
def remove_product(product_id):
    if not is_admin():
        return render_template("signin.html", error="Only admins can see this page."), 403

    try:
        product = get_product(product_id)
        result = delete_product(product_id)
    except sqlite3.Error as err:
        flash(f"Product not deleted. Database error: {err}", "error")
        return redirect(f"/products/{product_id}")

    if result is None:
        flash("That product was not found.", "error")
        return redirect("/products")
    if result == "hidden":
        flash(f"\"{product['productName']}\" has deliveries or sales, so it was hidden instead of deleted.", "success")
    else:
        flash(f"\"{product['productName']}\" deleted.", "success")
    return redirect("/products")


# -------------------------
# Receive stock
# -------------------------

@product_routes.route("/products/<int:product_id>/receive", methods=["POST"])
def receive_stock(product_id):
    if not is_admin():
        return render_template("signin.html", error="Only admins can see this page."), 403

    date_text = request.form.get("dateReceived", "").strip()
    epc_text = request.form.get("epcs", "")

    epcs, errors = read_epcs(epc_text)
    if not errors:
        errors = check_reception(product_id, epcs, date_text)
    count = len(epcs)

    try:
        product = get_product(product_id)
        if product is None:
            flash("That product was not found.", "error")
            return redirect("/products")
        if errors:
            flash(f"Stock not received. {len(errors)} {'problem' if len(errors) == 1 else 'problems'} to fix.", "error")
            return render_product_detail_with_errors(product_id, epc_text, date_text, errors)
        save_reception(product_id, epcs, date_text)
    except sqlite3.Error as err:
        flash(f"Stock not received. Database error: {err}", "error")
        return redirect(f"/products/{product_id}")

    flash(f"{count} {'unit' if count == 1 else 'units'} of \"{product['productName']}\" received on {date_text}.", "success")
    return redirect(f"/products/{product_id}")


# The RFID reader, for the "Scan tags" button on the receive form. One call asks the reader once and gives back the new EPCs it saw, and the ones already in the system
@product_routes.route("/rfid/scan", methods=["POST"])
def rfid_scan():
    if not is_admin():
        return jsonify(error="Only admins can scan tags."), 403

    try:
        seen = scan_once()
        known = known_epcs(seen)
    except ReaderError as err:
        return jsonify(error=str(err)), 503
    except sqlite3.Error as err:
        return jsonify(error=f"Database error: {err}"), 500
    return jsonify(epcs=[epc for epc in seen if epc not in known], known=sorted(known))


def render_product_detail_with_errors(product_id, epc_text, date_text, errors):
    product = get_product(product_id)
    history = reception_history(product_id)
    stock = next((row for row in inventory_rows() if row["productID"] == product_id), None)
    units, unit_total = units_for_product(product_id)
    return render_template(
        "product_detail.html", product=product, history=history, stock=stock,
        units=units, unit_total=unit_total,
        today=date.today().isoformat(), epc_text=epc_text, date_text=date_text,
        receive_error=errors,
    ), 400


# The saved product, with the same names the form fields use
def product_to_form(product):
    return {
        "name": product["productName"], "category": product["categoryName"], "producer": product["producerName"],
        "price": f"{product['price']:.2f}", "upc": product["upc"],
        "description": product["description"] or "", "lowStockThreshold": product["lowStockThreshold"],
        "active": product["isActive"],
    }


# Show the product form. For a new product, values is the form (or defaults). For an edit, it's the saved product
def render_product_form(product_id, values, errors=None):
    try:
        categories = known_categories()
        producers = known_producers()
    except sqlite3.Error as err:
        return f"Database error: {err}", 500
    return render_template(
        "product_form.html", product_id=product_id, values=values, errors=errors or [],
        categories=categories, producers=producers,
    )
