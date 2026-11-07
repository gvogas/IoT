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

# Everything but the password hash
CUSTOMER_COLUMNS = "customerID, customerName, address, email, phoneNumber, role, membershipNumber, totalPoints, createdAt"

# Membership numbers look like VM12345678
MEMBERSHIP_PREFIX = "VM"


# Make a membership number that no one has yet
def new_membership_number():
    while True:
        number = f"{MEMBERSHIP_PREFIX}{secrets.randbelow(10**8):08d}"
        taken = query_one("SELECT 1 FROM Customer WHERE membershipNumber = ?", (number,))
        if taken is None:
            return number


# Get every customer from the database, for tools/set_role.py
def all_customers():
    return query(f"SELECT {CUSTOMER_COLUMNS} FROM Customer ORDER BY customerID")


# Every customer with how many purchases they made and what they spent, for the customers page
def customers_with_spending():
    return query(f"""
        SELECT {CUSTOMER_COLUMNS},
               (SELECT COUNT(*) FROM Purchase p WHERE p.customerID = Customer.customerID) AS purchases,
               (SELECT COALESCE(SUM(p.total), 0) FROM Purchase p WHERE p.customerID = Customer.customerID) AS spent
        FROM Customer
        ORDER BY customerName COLLATE NOCASE
    """)


# Get one customer, or None if that ID is not there
def get_customer(customer_id):
    return query_one(f"SELECT {CUSTOMER_COLUMNS} FROM Customer WHERE customerID = ?", (customer_id,))


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


# Check a new email for a customer. Gives back (email, error)
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


# The email of every admin account, for the stock emails
def admin_emails():
    return [row["email"] for row in query("SELECT email FROM Customer WHERE role = 'admin' ORDER BY customerID")]


# Give a customer a new email
def set_email(customer_id, email):
    execute("UPDATE Customer SET email = ? WHERE customerID = ?", (email, customer_id))


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
    def __init__(self, name, address, email, phone_number, password, barcode=""):
        self.name = " ".join(name.split())          # take out extra spaces
        self.address = " ".join(address.split())
        self.email = email.strip().lower()           # Ann@X.com and ann@x.com count as the same email
        self.phone_number = re.sub(r"[\s().-]", "", phone_number)   # "(514) 555-1234" -> "5145551234"
        self.barcode = "".join(barcode.split()).upper()   # saved in capitals, like the sign in expects
        self.password = password       # we never save the real password, only a scrambled version (a hash)

    # Gives back a list of every problem. If the list is empty, everything is good
    def validate(self):
        errors = []

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

        if self.barcode:
            if len(self.barcode) > MAX_MEMBERSHIP:
                errors.append(f"The barcode must be {MAX_MEMBERSHIP} characters or less.")
            elif not re.match(BARCODE_REGEX, self.barcode):
                errors.append("The barcode can only have letters and digits.")
            elif self.barcode_taken():
                errors.append("This barcode is already registered to another customer.")

        if len(self.password) < MIN_PASSWORD:
            errors.append(f"Password must be at least {MIN_PASSWORD} characters.")

        # Only check the database if the email and phone look right
        if email_ok and self.email_taken():
            errors.append("This email is already registered.")
        if phone_ok and self.phone_taken():
            errors.append("This phone number is already registered.")

        return errors

    def email_taken(self):
        return query_one("SELECT 1 FROM Customer WHERE LOWER(email) = ?", (self.email,)) is not None

    def barcode_taken(self):
        return query_one("SELECT 1 FROM Customer WHERE membershipNumber = ?", (self.barcode,)) is not None

    def phone_taken(self):
        return query_one("SELECT 1 FROM Customer WHERE phoneNumber = ?", (self.phone_number,)) is not None

    # Add the customer to the database and give back their new membership number
    # If the email or phone number is already used, this gives an IntegrityError
    def save(self):
        # The scanned barcode is the membership number. Without one, make a new number
        self.membership_number = self.barcode or new_membership_number()
        execute(
            # New people always start as "customer". Use tools/set_role.py to make someone an admin
            "INSERT INTO Customer (customerName, address, email, phoneNumber, passwordHash, membershipNumber, createdAt) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.name, self.address, self.email, self.phone_number, generate_password_hash(self.password),
             self.membership_number, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        return self.membership_number
