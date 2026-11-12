import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from models.database import execute, money_or_none, query, query_one, transaction

# The longest each one can be. These match the sizes in tools/init_database.py
MAX_NAME = 100
MAX_CATEGORY = 50
MAX_PRODUCER = 100
MAX_DESCRIPTION = 500
MAX_UPC = 13
MAX_PRICE = Decimal("99999999.99")
MAX_THRESHOLD = 100000

# A UPC is only digits
UPC_REGEX = r"^[0-9]+$"


# Clean up the form and check every field. Gives back (product, errors)
# product is a dict with clean values, and errors has the message for each field with a problem (empty if all is good)
# Pass the product's ID when editing, so its own UPC doesn't count as taken
def read_product_form(form, product_id=None):
    errors = {}

    name = " ".join(form.get("name", "").split())
    if not name:
        errors["name"] = "Please enter the product name."
    elif len(name) > MAX_NAME:
        errors["name"] = f"Product name must be {MAX_NAME} characters or less."

    category = " ".join(form.get("category", "").split())
    if not category:
        errors["category"] = "Please enter a category."
    elif len(category) > MAX_CATEGORY:
        errors["category"] = f"Category must be {MAX_CATEGORY} characters or less."

    producer = " ".join(form.get("producer", "").split())
    if not producer:
        errors["producer"] = "Please enter the producer company."
    elif len(producer) > MAX_PRODUCER:
        errors["producer"] = f"Producer company must be {MAX_PRODUCER} characters or less."

    price = None
    try:
        price = Decimal(form.get("price", "").strip()).quantize(Decimal("0.01"))
        if price < 0 or price > MAX_PRICE:
            errors["price"] = "Price must be between 0 and 99999999.99."
            price = None
    except (InvalidOperation, ValueError):
        errors["price"] = "Please enter the price as a number, like 2.50."

    # The cost is optional. Empty means not known yet, and the product's sales don't count in the profit until it is filled in
    cost = None
    raw_cost = form.get("costPrice", "").strip()
    if raw_cost:
        try:
            cost = Decimal(raw_cost).quantize(Decimal("0.01"))
            if cost < 0 or cost > MAX_PRICE:
                errors["costPrice"] = "Cost must be between 0 and 99999999.99."
                cost = None
        except (InvalidOperation, ValueError):
            errors["costPrice"] = "Please enter the cost as a number, like 1.20."

    upc = form.get("upc", "").strip()
    upc_ok = False
    if not upc:
        errors["upc"] = "Please enter the UPC (the barcode number)."
    elif len(upc) > MAX_UPC:
        errors["upc"] = f"UPC must be {MAX_UPC} digits or less."
    elif not re.match(UPC_REGEX, upc):
        errors["upc"] = "UPC can only have digits."
    else:
        upc_ok = True

    description = " ".join(form.get("description", "").split())
    if len(description) > MAX_DESCRIPTION:
        errors["description"] = f"Description must be {MAX_DESCRIPTION} characters or less."

    threshold = 5
    raw_threshold = form.get("lowStockThreshold", "").strip()
    if raw_threshold:
        if raw_threshold.isdigit() and int(raw_threshold) <= MAX_THRESHOLD:
            threshold = int(raw_threshold)
        else:
            errors["lowStockThreshold"] = f"Low stock alert must be a whole number from 0 to {MAX_THRESHOLD}."

    product = {
        "name": name, "category": category, "producer": producer, "price": price, "cost": cost,
        "upc": upc, "description": description or None,
        "threshold": threshold, "active": bool(form.get("active")),
        "taxable": bool(form.get("taxable")),
    }

    # Only check the database when the value itself is well formed
    if upc_ok and upc_taken(upc, product_id):
        errors["upc"] = "This UPC is already used by another product."

    return product, errors


# Is this UPC used by another product? Pass the product's own ID when editing so it doesn't match itself
def upc_taken(upc, product_id=None):
    return query_one("SELECT 1 FROM Product WHERE upc = ? AND productID IS NOT ?", (upc, product_id)) is not None


# Category and producer names that already exist, for the suggestions on the form
def known_categories():
    return [row["categoryName"] for row in query("SELECT categoryName FROM Category ORDER BY categoryName")]


def known_producers():
    return [row["producerName"] for row in query("SELECT producerName FROM Producer ORDER BY producerName")]


# Every product, active or hidden, for the products page
def all_products():
    return query("""
        SELECT p.productID, p.productName, p.price, p.upc, p.description, p.imagePath,
               p.lowStockThreshold, p.isActive, c.categoryName, pr.producerName,
               (SELECT COUNT(*) FROM ProductItem i WHERE i.productID = p.productID AND i.status = 'in_stock') AS inStock,
               (SELECT COUNT(*) FROM Reception r WHERE r.productID = p.productID) AS deliveries
        FROM Product p
        JOIN Category c ON c.categoryID = p.categoryID
        JOIN Producer pr ON pr.producerID = p.producerID
        ORDER BY p.productName COLLATE NOCASE
    """)


# One product with its category and producer names, or None if the ID is not there
def get_product(product_id):
    return query_one("""
        SELECT p.productID, p.productName, p.price, p.costPrice, p.upc, p.description, p.imagePath,
               p.lowStockThreshold, p.isActive, p.isTaxable, p.createdAt, c.categoryName, pr.producerName
        FROM Product p
        JOIN Category c ON c.categoryID = p.categoryID
        JOIN Producer pr ON pr.producerID = p.producerID
        WHERE p.productID = ?
    """, (product_id,))


# Find a category or producer by name (ignoring capitals), or add it if it's new. Gives back its ID
def _find_or_add(conn, table, id_column, name_column, name):
    row = conn.execute(f"SELECT {id_column} FROM {table} WHERE {name_column} = ? COLLATE NOCASE", (name,)).fetchone()
    if row is None:
        cursor = conn.execute(f"INSERT INTO {table} ({name_column}) VALUES (?)", (name,))
        return cursor.lastrowid
    return row[0]


# Add a new product. Gives back its ID
def save_product(product):
    def work(conn):
        category_id = _find_or_add(conn, "Category", "categoryID", "categoryName", product["category"])
        producer_id = _find_or_add(conn, "Producer", "producerID", "producerName", product["producer"])
        cursor = conn.execute(
            """INSERT INTO Product (productName, categoryID, producerID, price, costPrice, upc, description, imagePath,
                                    lowStockThreshold, isActive, isTaxable, createdAt)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (product["name"], category_id, producer_id, str(product["price"]), money_or_none(product["cost"]), product["upc"],
             product["description"], product["image"],
             product["threshold"], product["active"], product["taxable"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        return cursor.lastrowid
    return transaction(work)


# Change a product. Gives back False if that ID is not there
def update_product(product_id, product):
    def work(conn):
        category_id = _find_or_add(conn, "Category", "categoryID", "categoryName", product["category"])
        producer_id = _find_or_add(conn, "Producer", "producerID", "producerName", product["producer"])
        cursor = conn.execute(
            """UPDATE Product SET productName = ?, categoryID = ?, producerID = ?, price = ?, costPrice = ?, upc = ?,
                                  description = ?, imagePath = ?,
                                  lowStockThreshold = ?, isActive = ?, isTaxable = ?
               WHERE productID = ?""",
            (product["name"], category_id, producer_id, str(product["price"]), money_or_none(product["cost"]), product["upc"],
             product["description"], product["image"],
             product["threshold"], product["active"], product["taxable"], product_id),
        )
        return cursor.rowcount > 0
    return transaction(work)


# Does this product have any deliveries or sales? Then it can't be deleted, only hidden
def has_history(product_id):
    row = query_one("""
        SELECT (SELECT COUNT(*) FROM Reception WHERE productID = ?)
             + (SELECT COUNT(*) FROM PurchaseItem WHERE productID = ?) AS n
    """, (product_id, product_id))
    return row["n"] > 0


# Delete a product with no history. A product with history is hidden instead, so old records still make sense.
# Gives back "deleted", "hidden" or None (if the ID is not there)
def delete_product(product_id):
    if get_product(product_id) is None:
        return None
    if has_history(product_id):
        execute("UPDATE Product SET isActive = 0 WHERE productID = ?", (product_id,))
        return "hidden"
    execute("DELETE FROM Product WHERE productID = ?", (product_id,))
    return "deleted"


# Stock of every active product, for the inventory dashboard (from the ProductStock view)
def inventory_rows():
    return query("""
        SELECT s.productID, s.productName, s.categoryName, s.price, s.inStock, s.totalSold,
               s.lowStockThreshold, s.lowStock, s.lastReceived, p.imagePath
        FROM ProductStock s
        JOIN Product p ON p.productID = s.productID
        ORDER BY s.productName COLLATE NOCASE
    """)


# How many units of one product are on the shelf and sold. Counts the units, so it works for hidden products too
def product_stock(product_id):
    return query_one("""
        SELECT COALESCE(SUM(status = 'in_stock'), 0) AS inStock, COALESCE(SUM(status = 'sold'), 0) AS totalSold
        FROM ProductItem WHERE productID = ?
    """, (product_id,))
