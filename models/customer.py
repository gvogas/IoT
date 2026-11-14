import re

from werkzeug.security import check_password_hash, generate_password_hash

from models.database import execute, now_text, query, query_one

EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
PHONE_REGEX = r"^\+?[1-9]\d{7,14}$"
# Letters (including é), with words joined by a space, - or '
NAME_REGEX = r"^[^\W\d_]+([ '-][^\W\d_]+)*$"

# These match the column sizes in tools/init_database.py
MAX_NAME = 100
MAX_ADDRESS = 255
MAX_EMAIL = 255
MIN_PASSWORD = 8
MAX_MEMBERSHIP = 32

# Sign-up says this when the email, phone or card is already used, without saying which
TAKEN_MESSAGE = "This email, phone number or membership card is already used by an account. If it's yours, sign in instead."
BARCODE_REGEX = r"^[A-Z0-9]+$"

ROLES = ("customer", "admin")

# Everything but the password hash
CUSTOMER_COLUMNS = "customerID, customerName, address, email, phoneNumber, role, membershipNumber, totalPoints, createdAt"


# Every customer, for tools/set_role.py
def all_customers():
    return query(f"SELECT {CUSTOMER_COLUMNS} FROM Customer ORDER BY customerID")


# Every customer with their purchase count and total spent
def customers_with_spending():
    return query(f"""
        SELECT {CUSTOMER_COLUMNS},
               (SELECT COUNT(*) FROM Purchase p WHERE p.customerID = Customer.customerID) AS purchases,
               (SELECT COALESCE(SUM(p.total), 0) FROM Purchase p WHERE p.customerID = Customer.customerID) AS spent
        FROM Customer
        ORDER BY customerName COLLATE NOCASE
    """)


# One customer, or None
def get_customer(customer_id):
    return query_one(f"SELECT {CUSTOMER_COLUMNS} FROM Customer WHERE customerID = ?", (customer_id,))


# Find a customer by their card number, or None
def get_customer_by_membership(number):
    return query_one("SELECT customerID, customerName, role FROM Customer WHERE membershipNumber = ?", (number.strip().upper(),))


# Pass customer_id so their own number doesn't count as taken
def check_membership_number(text, customer_id=None):
    number = "".join(text.split()).upper()
    if not number:
        return None, "Please scan the card or type the membership number."
    if len(number) > MAX_MEMBERSHIP:
        return None, f"The membership number must be {MAX_MEMBERSHIP} characters or less."
    if not re.match(BARCODE_REGEX, number):
        return None, "The membership number can only have letters and digits."
    if query_one("SELECT 1 FROM Customer WHERE membershipNumber = ? AND customerID IS NOT ?", (number, customer_id)):
        return None, "This membership number is already used by another customer."
    return number, None


# False if that ID is not there
def set_membership_number(customer_id, number):
    return execute("UPDATE Customer SET membershipNumber = ? WHERE customerID = ?", (number, customer_id)) > 0


# Gives back (email, error)
def check_new_email(text, customer_id):
    email = text.strip().lower()
    if not email:
        return None, "Please enter your new email."
    if len(email) > MAX_EMAIL:
        return None, f"Email must be {MAX_EMAIL} characters or less."
    if not re.match(EMAIL_REGEX, email):
        return None, "Please enter a valid email address."
    if query_one("SELECT 1 FROM Customer WHERE LOWER(email) = ? AND customerID != ?", (email, customer_id)):
        return None, "This email is already registered."
    return email, None


# Who gets the stock emails
def admin_emails():
    return [row["email"] for row in query("SELECT email FROM Customer WHERE role = 'admin' ORDER BY customerID")]


# Change a customer's email
def set_email(customer_id, email):
    execute("UPDATE Customer SET email = ? WHERE customerID = ?", (email, customer_id))


# The customer if the email and password are right, or None
def check_sign_in(email, password):
    row = query_one("SELECT customerID, customerName, role, passwordHash FROM Customer WHERE email = ?", (email.strip().lower(),))
    if row and check_password_hash(row["passwordHash"], password):
        return row
    return None


# False if that ID is not there
def set_role(customer_id, role):
    if role not in ROLES:
        raise ValueError(f"Role must be one of {ROLES}")
    return execute("UPDATE Customer SET role = ? WHERE customerID = ?", (role, customer_id)) > 0


# A new customer from the sign up form
class Customer:

    def __init__(self, name, address, email, phone_number, password, barcode=""):
        self.name = " ".join(name.split())
        self.address = " ".join(address.split())
        self.email = email.strip().lower()
        self.phone_number = re.sub(r"[\s().-]", "", phone_number)   # "(514) 555-1234" -> "5145551234"
        self.barcode = "".join(barcode.split()).upper()
        self.password = password   # only its hash is saved

    # Every problem with the form, empty if all is good
    def validate(self):
        errors = []
        taken = False

        if not self.name:
            errors.append("Please enter your name.")
        elif len(self.name) > MAX_NAME:
            errors.append(f"Name must be {MAX_NAME} characters or less.")
        elif not re.match(NAME_REGEX, self.name):
            errors.append("Name can only have letters, spaces, - and '.")

        if not self.address:
            errors.append("Please enter your address.")
        elif len(self.address) > MAX_ADDRESS:
            errors.append(f"Address must be {MAX_ADDRESS} characters or less.")
        elif len(self.address) < 5:
            errors.append("Please enter your full address.")

        email_ok = False
        if not self.email:
            errors.append("Please enter your email.")
        elif len(self.email) > MAX_EMAIL:
            errors.append(f"Email must be {MAX_EMAIL} characters or less.")
        elif not re.match(EMAIL_REGEX, self.email):
            errors.append("Please enter a valid email address.")
        else:
            email_ok = True

        phone_ok = False
        if not self.phone_number:
            errors.append("Please enter your phone number.")
        elif not re.match(PHONE_REGEX, self.phone_number):
            errors.append("Please enter a valid phone number.")
        else:
            phone_ok = True

        if not self.barcode:
            errors.append("Please scan your membership card.")
        elif len(self.barcode) > MAX_MEMBERSHIP:
            errors.append(f"The barcode must be {MAX_MEMBERSHIP} characters or less.")
        elif not re.match(BARCODE_REGEX, self.barcode):
            errors.append("The barcode can only have letters and digits.")
        elif self.barcode_taken():
            taken = True

        if len(self.password) < MIN_PASSWORD:
            errors.append(f"Password must be at least {MIN_PASSWORD} characters.")

        if email_ok and self.email_taken():
            taken = True
        if phone_ok and self.phone_taken():
            taken = True
        # One message that doesn't say which one is taken, so the form can't be used
        # to find out whose email, phone or card is in the store's records
        if taken:
            errors.append(TAKEN_MESSAGE)

        return errors

    # Is the email used by someone else?
    def email_taken(self):
        return query_one("SELECT 1 FROM Customer WHERE LOWER(email) = ?", (self.email,)) is not None

    # Is the barcode used by someone else?
    def barcode_taken(self):
        return query_one("SELECT 1 FROM Customer WHERE membershipNumber = ?", (self.barcode,)) is not None

    # Is the phone number used by someone else?
    def phone_taken(self):
        return query_one("SELECT 1 FROM Customer WHERE phoneNumber = ?", (self.phone_number,)) is not None

    # Raises IntegrityError if the email or phone is already used
    def save(self):
        self.membership_number = self.barcode
        # New people start as "customer". tools/set_role.py makes someone an admin
        execute(
            "INSERT INTO Customer (customerName, address, email, phoneNumber, passwordHash, membershipNumber, createdAt) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.name, self.address, self.email, self.phone_number, generate_password_hash(self.password),
             self.membership_number, now_text()),
        )
        return self.membership_number
