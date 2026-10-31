import re
import secrets
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash

from models.database import execute, query, query_one

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

# Membership numbers look like VM12345678
MEMBERSHIP_PREFIX = "VM"


# Make a membership number that no one has yet
def new_membership_number():
    while True:
        number = f"{MEMBERSHIP_PREFIX}{secrets.randbelow(10**8):08d}"
        taken = query_one("SELECT 1 FROM Customer WHERE membershipNumber = ?", (number,))
        if taken is None:
            return number


# Get every customer from the database, for the customers page
def all_customers():
    return query("SELECT customerID, customerName, address, email, phoneNumber, role, membershipNumber, totalPoints, createdAt FROM Customer ORDER BY customerID")


# Get one customer, or None if that ID is not there
def get_customer(customer_id):
    return query_one("SELECT customerID, customerName, address, email, phoneNumber, role, membershipNumber, totalPoints, createdAt FROM Customer WHERE customerID = ?", (customer_id,))


# For sign in: gives back the customer if the email and password are right, or None if not
def check_sign_in(email, password):
    row = query_one("SELECT customerID, customerName, role, passwordHash FROM Customer WHERE email = ?", (email.strip().lower(),))
    if row and check_password_hash(row["passwordHash"], password):
        return row
    return None


# Make a customer an admin, or a normal customer again. Gives back False if that ID is not there
def set_role(customer_id, role):
    if role not in ROLES:
        raise ValueError(f"Role must be one of {ROLES}")
    return execute("UPDATE Customer SET role = ? WHERE customerID = ?", (role, customer_id)) > 0


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
        return query_one("SELECT 1 FROM Customer WHERE LOWER(email) = ?", (customer.email,)) is not None

    def phone_taken(customer):
        return query_one("SELECT 1 FROM Customer WHERE phoneNumber = ?", (customer.phone_number,)) is not None

    # Add the customer to the database and give back their new membership number
    # If the email or phone number is already used, this gives an IntegrityError
    def save(customer):
        customer.membership_number = new_membership_number()
        execute(
            # New people always start as "customer". Use tools/set_role.py to make someone an admin
            "INSERT INTO Customer (customerName, address, email, phoneNumber, passwordHash, membershipNumber, createdAt) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (customer.name, customer.address, customer.email, customer.phone_number, generate_password_hash(customer.password),
             customer.membership_number, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        return customer.membership_number
