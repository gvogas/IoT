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
MAX_MEMBERSHIP = 32   # the size of the membershipNumber column (a barcode can be 16 digits or more)
# A scanned barcode can have letters and digits
BARCODE_REGEX = r"^[A-Z0-9]+$"

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


# For the barcode scanner: find a customer by the membership number on their card, or None
def get_customer_by_membership(number):
    return query_one("SELECT customerID, customerName, role FROM Customer WHERE membershipNumber = ?", (number.strip().upper(),))


# Check a membership number typed or scanned by an admin. Gives back (number, error)
# An empty number gives a new generated one. Pass the customer's ID so their own number doesn't count as taken
def check_membership_number(text, customer_id=None):
    number = "".join(text.split()).upper()
    if not number:
        return new_membership_number(), None
    if len(number) > MAX_MEMBERSHIP:
        return None, f"The membership number must be {MAX_MEMBERSHIP} characters or less."
    if not re.match(BARCODE_REGEX, number):
        return None, "The membership number can only have letters and digits."
    if query_one("SELECT 1 FROM Customer WHERE membershipNumber = ? AND customerID IS NOT ?", (number, customer_id)):
        return None, "This membership number is already used by another customer."
    return number, None


# Give a customer a new membership number. Gives back False if that ID is not there
def set_membership_number(customer_id, number):
    return execute("UPDATE Customer SET membershipNumber = ? WHERE customerID = ?", (number, customer_id)) > 0


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

    # barcode is optional: the number scanned from the customer's card. Leave it empty to get a new number
    def __init__(customer, name, address, email, phone_number, password, barcode=""):
        customer.name = " ".join(name.split())          # take out extra spaces
        customer.address = " ".join(address.split())
        customer.email = email.strip().lower()           # Ann@X.com and ann@x.com count as the same email
        customer.phone_number = re.sub(r"[\s().-]", "", phone_number)   # "(514) 555-1234" -> "5145551234"
        customer.barcode = "".join(barcode.split()).upper()   # saved in capitals, like the sign in expects
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

        if customer.barcode:
            if len(customer.barcode) > MAX_MEMBERSHIP:
                errors.append(f"The barcode must be {MAX_MEMBERSHIP} characters or less.")
            elif not re.match(BARCODE_REGEX, customer.barcode):
                errors.append("The barcode can only have letters and digits.")
            elif customer.barcode_taken():
                errors.append("This barcode is already registered to another customer.")

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

    def barcode_taken(customer):
        return query_one("SELECT 1 FROM Customer WHERE membershipNumber = ?", (customer.barcode,)) is not None

    def phone_taken(customer):
        return query_one("SELECT 1 FROM Customer WHERE phoneNumber = ?", (customer.phone_number,)) is not None

    # Add the customer to the database and give back their new membership number
    # If the email or phone number is already used, this gives an IntegrityError
    def save(customer):
        # The scanned barcode is the membership number. Without one, make a new number
        customer.membership_number = customer.barcode or new_membership_number()
        execute(
            # New people always start as "customer". Use tools/set_role.py to make someone an admin
            "INSERT INTO Customer (customerName, address, email, phoneNumber, passwordHash, membershipNumber, createdAt) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (customer.name, customer.address, customer.email, customer.phone_number, generate_password_hash(customer.password),
             customer.membership_number, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        return customer.membership_number
