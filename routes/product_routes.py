import csv
import io
import sqlite3
from datetime import date

from flask import Blueprint, Response, flash, jsonify, redirect, render_template, request

from hardware.rfid import scan_once
from mail.send_email import send_restock_alert
from models.product import (
    all_products, delete_product, get_product, has_history, inventory_rows, known_categories, known_producers,
    product_stock, product_with_upc, read_product_form, save_product, update_product,
)
from models.product_image import MAX_UPLOAD_BYTES, delete_image, read_image, save_image
from models.reception import check_reception, read_epcs, reception_history, save_reception
from models.unit import clear_product_units, find_units, known_epcs, units_for_product
from routes.guards import admin_api, admin_page

product_routes = Blueprint("product_routes", __name__)


# "1 unit", "3 units"
def count_of(count, word):
    return f"{count} {word if count == 1 else word + 's'}"


# The uploaded image, checked and shrunk, or None. A bad file is added to errors
def read_uploaded_image(errors):
    data, error = read_image(request.files.get("image"))
    if error:
        errors["image"] = error
    return data


# Back to the products page with an error
def product_not_found():
    flash("That product was not found.", "error")
    return redirect("/products")


# Inventory

# Stock of every product, out of stock first
@product_routes.route("/inventory")
@admin_page
def inventory():
    rows = inventory_rows()
    low = [row for row in rows if row["lowStock"] and row["inStock"] > 0]
    out = [row for row in rows if row["inStock"] == 0]
    # What needs ordering comes first: out of stock, then low, then the rest
    rows = out + low + [row for row in rows if not row["lowStock"] and row["inStock"] > 0]
    # The EPC search box
    epc_query = request.args.get("epc", "").strip().upper()
    return render_template(
        "products/inventory.html",
        rows=rows,
        units=sum(row["inStock"] for row in rows),
        value=sum(row["inStock"] * row["price"] for row in rows),
        low=len(low),
        out=len(out),
        categories=sorted({row["categoryName"] for row in rows}, key=str.lower),
        last=max((row["lastReceived"] for row in rows if row["lastReceived"]), default=None),
        epc_query=epc_query,
        matches=find_units(epc_query) if epc_query else [],
    )


# Download the inventory as a CSV spreadsheet
@product_routes.route("/inventory.csv")
@admin_page
def inventory_csv():
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Product", "Category", "Price", "In stock", "Sold", "Low stock alert at", "Last received"])
    for row in inventory_rows():
        writer.writerow([row["productName"], row["categoryName"], f"{row['price']:.2f}", row["inStock"],
                         row["totalSold"], row["lowStockThreshold"], row["lastReceived"] or ""])

    filename = f"inventory-{date.today().isoformat()}.csv"
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


# Products: list, add, edit, delete

# Every product, active or hidden
@product_routes.route("/products")
@admin_page
def products():
    rows = all_products()
    return render_template("products/list.html", products=rows,
                           categories=sorted({row["categoryName"] for row in rows}, key=str.lower))


# values fills the boxes: the defaults, the saved product, or what was typed
def render_product_form(product_id, values, errors=None, image_path=None):
    return render_template(
        "products/form.html", product_id=product_id, values=values, errors=errors or {},
        categories=known_categories(), producers=known_producers(), image_path=image_path,
        max_upload_bytes=MAX_UPLOAD_BYTES,
        # A product with deliveries or sales can only be hidden
        can_delete=product_id is None or not has_history(product_id),
    )


# The saved product, keyed by the form field names
def product_to_form(product):
    return {
        "name": product["productName"], "category": product["categoryName"], "producer": product["producerName"],
        "price": f"{product['price']:.2f}", "upc": product["upc"],
        "costPrice": "" if product["costPrice"] is None else f"{product['costPrice']:.2f}",
        "description": product["description"] or "", "lowStockThreshold": product["lowStockThreshold"],
        "active": bool(product["isActive"]), "taxable": bool(product["isTaxable"]),
    }


# Add a product
@product_routes.route("/products/new", methods=["GET", "POST"])
@admin_page
def new_product():
    if request.method == "GET":
        return render_product_form(None, {"active": True, "taxable": True, "lowStockThreshold": 5})

    product, errors = read_product_form(request.form)
    image_data = read_uploaded_image(errors)
    if errors:
        flash(f"Product not added. {count_of(len(errors), 'problem')} to fix.", "error")
        return render_product_form(None, request.form, errors), 400

    product["image"] = None
    try:
        if image_data:
            product["image"] = save_image(image_data)
        product_id = save_product(product)
    except (sqlite3.Error, OSError) as err:
        delete_image(product["image"])
        flash(f"Product not added. Could not save it: {err}", "error")
        return render_product_form(None, request.form), 500

    flash(f"Product \"{product['name']}\" added successfully.", "success")
    # "Save and add another" comes back to an empty form
    if request.form.get("next") == "another":
        return redirect("/products/new")
    return redirect(f"/products/{product_id}")


# The form asks this as soon as a UPC is scanned, so a duplicate shows before saving
@product_routes.route("/products/upc-check")
@admin_api
def upc_check():
    upc = request.args.get("upc", "").strip()
    product_id = request.args.get("productID", type=int)  # When editing, the product itself doesn't count
    other = product_with_upc(upc, product_id) if upc else None
    if other is None:
        return jsonify(taken=False)
    return jsonify(taken=True, productID=other["productID"], name=other["productName"])


# Change a product and its image
@product_routes.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_page
def edit_product(product_id):
    product = get_product(product_id)
    if product is None:
        return product_not_found()

    if request.method == "GET":
        return render_product_form(product_id, product_to_form(product), image_path=product["imagePath"])

    old_image = product["imagePath"]
    values, errors = read_product_form(request.form, product_id)
    image_data = read_uploaded_image(errors)
    if errors:
        flash(f"Changes not saved. {count_of(len(errors), 'problem')} to fix.", "error")
        return render_product_form(product_id, request.form, errors, old_image), 400

    # A new image replaces the old one. Otherwise it stays, unless "Remove this image" was ticked
    values["image"] = None if request.form.get("removeImage") else old_image
    try:
        if image_data:
            values["image"] = save_image(image_data)
        update_product(product_id, values)
    except (sqlite3.Error, OSError) as err:
        if values["image"] != old_image:
            delete_image(values["image"])
        flash(f"Changes not saved. Could not save them: {err}", "error")
        return render_product_form(product_id, request.form, image_path=old_image), 500

    # Only delete the old file once the database no longer points at it
    if values["image"] != old_image:
        delete_image(old_image)

    flash(f"Changes to \"{values['name']}\" saved.", "success")
    return redirect(f"/products/{product_id}")


# Delete a product, or hide it if it has history
@product_routes.route("/products/<int:product_id>/delete", methods=["POST"])
@admin_page
def remove_product(product_id):
    try:
        product = get_product(product_id)
        result = delete_product(product_id)
    except sqlite3.Error as err:
        flash(f"Product not deleted. Database error: {err}", "error")
        return redirect(f"/products/{product_id}")

    if result is None:
        return product_not_found()
    if result == "hidden":
        flash(f"\"{product['productName']}\" is now hidden. Turn on \"Show in inventory\" to bring it back.", "success")
    else:
        delete_image(product["imagePath"])
        flash(f"\"{product['productName']}\" deleted.", "success")
    return redirect("/products")


# One product: details, stock and receiving

# The receive form keeps what was typed if there are errors
def render_product_detail(product, epc_text="", date_text=None, errors=None):
    product_id = product["productID"]
    units, unit_total = units_for_product(product_id)
    today = date.today().isoformat()
    return render_template(
        "products/detail.html", product=product, history=reception_history(product_id),
        stock=product_stock(product_id), units=units, unit_total=unit_total, today=today,
        epc_text=epc_text, date_text=today if date_text is None else date_text, receive_error=errors,
    )


# One product with its stock and deliveries
@product_routes.route("/products/<int:product_id>")
@admin_page
def product_detail(product_id):
    product = get_product(product_id)
    if product is None:
        return product_not_found()
    return render_product_detail(product)


# Save a delivery, one unit per EPC
@product_routes.route("/products/<int:product_id>/receive", methods=["POST"])
@admin_page
def receive_stock(product_id):
    date_text = request.form.get("dateReceived", "").strip()
    epc_text = request.form.get("epcs", "")

    try:
        epcs, errors = read_epcs(epc_text)
        if not errors:
            errors = check_reception(product_id, epcs, date_text)

        product = get_product(product_id)
        if product is None:
            return product_not_found()
        if errors:
            flash(f"Stock not received. {count_of(len(errors), 'problem')} to fix.", "error")
            return render_product_detail(product, epc_text, date_text, errors), 400
        stock_before = product_stock(product_id)["inStock"]
        save_reception(product_id, epcs, date_text)
    except sqlite3.Error as err:
        flash(f"Stock not received. Database error: {err}", "error")
        return redirect(f"/products/{product_id}")

    if stock_before <= product["lowStockThreshold"]:
        send_restock_alert(product["productName"], len(epcs), stock_before + len(epcs), product["lowStockThreshold"])

    flash(f"{count_of(len(epcs), 'unit')} of \"{product['productName']}\" received on {date_text}.", "success")
    return redirect(f"/products/{product_id}")


# Delete every EPC and delivery of one product, so its tags can be received again while testing
@product_routes.route("/products/<int:product_id>/clear-epcs", methods=["POST"])
@admin_page
def clear_epcs(product_id):
    try:
        product = get_product(product_id)
        if product is None:
            return product_not_found()
        count = clear_product_units(product_id)
    except sqlite3.Error as err:
        flash(f"Database error: {err}", "error")
        return redirect(f"/products/{product_id}")

    flash(f"Cleared {count_of(count, 'unit')} of \"{product['productName']}\". The tags can be received again.", "success")
    return redirect(f"/products/{product_id}")


# The "Scan tags" button on the receive form: the new EPCs the reader sees, and the ones already in the system
@product_routes.route("/rfid/scan", methods=["POST"])
@admin_api
def rfid_scan():
    seen = scan_once()
    known = known_epcs(seen)
    return jsonify(epcs=[epc for epc in seen if epc not in known], known=sorted(known))
