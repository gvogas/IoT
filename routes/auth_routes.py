from flask import Blueprint, redirect, render_template, request, session

from models.customer import check_sign_in, get_customer

# The sign in and sign out pages. app.py adds them with app.register_blueprint(auth_routes)
auth_routes = Blueprint("auth_routes", __name__)


# Gives back True if the person on the website is signed in as an admin
# Put this at the top of any page that only admins can see:
#     if not is_admin():
#         return render_template("signin.html", error="Only admins can see this page."), 403
def is_admin():
    if "id" not in session:
        return False
    # Check the database so a role change works right away
    customer = get_customer(session["id"])
    if customer is None:
        session.clear()
        return False
    session["role"] = customer["role"]
    return customer["role"] == "admin"


# Gives back True if someone is signed in
def is_signed_in():
    return "id" in session


# -------------------------
# Sign in
# -------------------------

@auth_routes.route("/signin", methods=["GET", "POST"])
def signin():

    # Just opening the page: show the form
    if request.method == "GET":
        return render_template("signin.html")

    # The form was sent: check the email + password
    email = request.form.get("email", "")
    password = request.form.get("password", "")
    customer = check_sign_in(email, password)

    if customer is None:
        return render_template("signin.html", error="Wrong email or password.")

    # Remember who signed in (Flask saves this in a cookie, a small file in the browser)
    session["id"] = customer["customerID"]
    session["name"] = customer["customerName"]
    session["role"] = customer["role"]

    # Admins go to the admin page, customers go to the checkout
    return redirect("/admin" if customer["role"] == "admin" else "/")


# -------------------------
# Sign out
# -------------------------

@auth_routes.route("/signout")
def signout():
    session.clear()   # forget who was signed in
    return redirect("/")
