import re
from werkzeug.security import check_password_hash, generate_password_hash

from models.database import connect

EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
PHONE_REGEX = r"^\+?[1-9]\d{7,14}$"
# A name can have letters (also letters like é), and words can be joined by a space, - or '
NAME_REGEX = r"^[^\W\d_]+([ '-][^\W\d_]+)*$"

# The longest each one can be. These match the sizes in tools/init_database.py
MAX_NAME = 100
MAX_ADDRESS = 255
MAX_EMAIL = 255
MIN_PASSWORD = 8

ROLES = ("customer", "admin")


# Get every customer from the database, for the customers page
def all_customers():
    conn = connect()
    try:
        rows = conn.execute("SELECT customerID, customerName, address, email, phoneNumber, role FROM Customer ORDER BY customerID").fetchall()
    finally:
        conn.close()
    return rows


# For sign in: gives back the customer if the email and password are right, or None if not
def check_sign_in(email, password):
    conn = connect()
    try:
        row = conn.execute("SELECT customerID, customerName, role, passwordHash FROM Customer WHERE email = ?", (email.strip().lower(),)).fetchone()
    finally:
        conn.close()
    if row and check_password_hash(row["passwordHash"], password):
        return row
    return None


# Make a customer an admin, or a normal customer again. Gives back False if that ID is not there
def set_role(customer_id, role):
    if role not in ROLES:
        raise ValueError(f"Role must be one of {ROLES}")
    conn = connect()
    try:
        cursor = conn.execute("UPDATE Customer SET role = ? WHERE customerID = ?", (role, customer_id))
        conn.commit()
    finally:
        conn.close()
    return cursor.rowcount > 0


class Customer:

    def __init__(customer, name, address, email, phone_number, password):
        customer.name = " ".join(name.split())          # take out extra spaces
        customer.address = " ".join(address.split())
        customer.email = email.strip().lower()           # Ann@X.com and ann@x.com count as the same email
        customer.phone_number = re.sub(r"[\s().-]", "", phone_number)   # "(514) 555-1234" -> "5145551234"
        customer.password = password       # we never save the real password, only a scrambled version (a hash)

    # Gives back a list of every problem. If the list is empty, everything is good
    def validate(customer):
        errors = []

        if not customer.name:
            errors.append("Please enter your name.")
        elif len(customer.name) > MAX_NAME:
            errors.append(f"Name must be {MAX_NAME} characters or less.")
        elif not re.match(NAME_REGEX, customer.name):
            errors.append("Name can only have letters, spaces, - and '.")

        if not customer.address:
            errors.append("Please enter your address.")
        elif len(customer.address) > MAX_ADDRESS:
            errors.append(f"Address must be {MAX_ADDRESS} characters or less.")
        elif len(customer.address) < 5:
            errors.append("Please enter your full address.")

        email_ok = False
        if not customer.email:
            errors.append("Please enter your email.")
        elif len(customer.email) > MAX_EMAIL:
            errors.append(f"Email must be {MAX_EMAIL} characters or less.")
        elif not re.match(EMAIL_REGEX, customer.email):
            errors.append("Please enter a valid email address.")
        else:
            email_ok = True

        phone_ok = False
        if not customer.phone_number:
            errors.append("Please enter your phone number.")
        elif not re.match(PHONE_REGEX, customer.phone_number):
            errors.append("Please enter a valid phone number.")
        else:
            phone_ok = True

        if len(customer.password) < MIN_PASSWORD:
            errors.append(f"Password must be at least {MIN_PASSWORD} characters.")

        # Only check the database if the email and phone look right
        if email_ok and customer.email_taken():
            errors.append("This email is already registered.")
        if phone_ok and customer.phone_taken():
            errors.append("This phone number is already registered.")

        return errors

    def email_taken(customer):
        conn = connect()
        try:
            row = conn.execute("SELECT 1 FROM Customer WHERE LOWER(email) = ?", (customer.email,)).fetchone()
        finally:
            conn.close()
        return row is not None

    def phone_taken(customer):
        conn = connect()
        try:
            row = conn.execute("SELECT 1 FROM Customer WHERE phoneNumber = ?", (customer.phone_number,)).fetchone()
        finally:
            conn.close()
        return row is not None

    # Add the customer to the database
    # If the email or phone number is already used, this gives an IntegrityError
    def save(customer):
        conn = connect()
        try:
            conn.execute(
                # New people always start as "customer". Use tools/set_role.py to make someone an admin
                "INSERT INTO Customer (customerName, address, email, phoneNumber, passwordHash) VALUES (?, ?, ?, ?, ?)",
                (customer.name, customer.address, customer.email, customer.phone_number, generate_password_hash(customer.password)),
            )
            conn.commit()
        finally:
            conn.close()
