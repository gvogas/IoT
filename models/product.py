import re
from decimal import Decimal, InvalidOperation

from models.database import execute, money_or_none, now_text, query, query_one, transaction

# These match the column sizes in tools/init_database.py
MAX_NAME = 100
MAX_CATEGORY = 50
MAX_PRODUCER = 100
MAX_DESCRIPTION = 500
MAX_UPC = 13
MAX_PRICE = Decimal("99999999.99")
MAX_THRESHOLD = 100000

UPC_REGEX = r"^[0-9]+$"


# A money amount typed in the form, like "2.5" -> Decimal("2.50"). Gives back (amount, error).
# name and example are only for the error message, like "price" and "2.50"
def read_money(text, name, example):
    try:
        amount = Decimal(text.strip()).quantize(Decimal("0.01"))
        # Inside the try, because comparing "NaN" with a number raises InvalidOperation
        if amount < 0 or amount > MAX_PRICE:
            return None, f"{name.capitalize()} must be between 0 and {MAX_PRICE}."
    except (InvalidOperation, ValueError):
        return None, f"Please enter the {name} as a number, like {example}."
    return amount, None


# Gives back (product, errors). Pass product_id when editing, so its own UPC doesn't count as taken
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

    price, error = read_money(form.get("price", ""), "price", "2.50")
    if error:
        errors["price"] = error

    # Optional. Sales of a product with no cost don't count in the profit
    cost = None
    raw_cost = form.get("costPrice", "").strip()
    if raw_cost:
        cost, error = read_money(raw_cost, "cost", "1.20")
        if error:
            errors["costPrice"] = error

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

    if upc_ok and upc_taken(upc, product_id):
        errors["upc"] = "This UPC is already used by another product."

    return product, errors


# The other product that already uses this UPC, or None
def product_with_upc(upc, product_id=None):
    return query_one("SELECT productID, productName FROM Product WHERE upc = ? AND productID IS NOT ?", (upc, product_id))


# Is the UPC used by another product?
def upc_taken(upc, product_id=None):
    return product_with_upc(upc, product_id) is not None


# For the suggestions on the product form
def known_categories():
    return [row["categoryName"] for row in query("SELECT categoryName FROM Category ORDER BY categoryName")]


# For the suggestions on the product form
def known_producers():
    return [row["producerName"] for row in query("SELECT producerName FROM Producer ORDER BY producerName")]


# One product with its category and producer, or None
def get_product(product_id):
    return query_one("""
        SELECT p.productID, p.productName, p.price, p.costPrice, p.upc, p.description, p.imagePath,
               p.lowStockThreshold, p.isActive, p.isTaxable, p.createdAt, c.categoryName, pr.producerName
        FROM Product p
        JOIN Category c ON c.categoryID = p.categoryID
        JOIN Producer pr ON pr.producerID = p.producerID
        WHERE p.productID = ?
    """, (product_id,))


# Gives back the ID of the category or producer, adding it if it's new
def _find_or_add(conn, table, id_column, name_column, name):
    row = conn.execute(f"SELECT {id_column} FROM {table} WHERE {name_column} = ? COLLATE NOCASE", (name,)).fetchone()
    if row is None:
        cursor = conn.execute(f"INSERT INTO {table} ({name_column}) VALUES (?)", (name,))
        return cursor.lastrowid
    return row[0]


# Add a product. Gives back its ID
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
             product["threshold"], product["active"], product["taxable"], now_text()),
        )
        return cursor.lastrowid
    return transaction(work)


# False if that ID is not there
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


# Does the product have deliveries or sales?
def has_history(product_id):
    row = query_one("""
        SELECT (SELECT COUNT(*) FROM Reception WHERE productID = ?)
             + (SELECT COUNT(*) FROM PurchaseItem WHERE productID = ?) AS n
    """, (product_id, product_id))
    return row["n"] > 0


# A product with deliveries or sales is hidden instead, so old records still make sense
def delete_product(product_id):
    if get_product(product_id) is None:
        return None
    if has_history(product_id):
        execute("UPDATE Product SET isActive = 0 WHERE productID = ?", (product_id,))
        return "hidden"
    execute("DELETE FROM Product WHERE productID = ?", (product_id,))
    return "deleted"


# Stock of every active product
def inventory_rows():
    return query("""
        SELECT s.productID, s.productName, s.categoryName, s.price, s.inStock, s.totalSold,
               s.lowStockThreshold, s.lowStock, s.lastReceived, p.imagePath, p.isActive
        FROM ProductStock s
        JOIN Product p ON p.productID = s.productID
        ORDER BY s.productName COLLATE NOCASE
    """)


# Hidden products, with the same columns as inventory_rows (ProductStock only has the active ones)
def hidden_inventory_rows():
    return query("""
        SELECT p.productID, p.productName, c.categoryName, p.price,
               COALESCE(SUM(i.status = 'in_stock'), 0) AS inStock,
               COALESCE(SUM(i.status = 'sold'), 0) AS totalSold,
               p.lowStockThreshold, 0 AS lowStock,
               (SELECT MAX(r.dateReceived) FROM Reception r WHERE r.productID = p.productID) AS lastReceived,
               p.imagePath, p.isActive
        FROM Product p
        JOIN Category c ON c.categoryID = p.categoryID
        LEFT JOIN ProductItem i ON i.productID = p.productID
        WHERE p.isActive = 0
        GROUP BY p.productID
        ORDER BY p.productName COLLATE NOCASE
    """)


# Not from ProductStock, so it works for hidden products too
def product_stock(product_id):
    return query_one("""
        SELECT COALESCE(SUM(status = 'in_stock'), 0) AS inStock, COALESCE(SUM(status = 'sold'), 0) AS totalSold
        FROM ProductItem WHERE productID = ?
    """, (product_id,))
