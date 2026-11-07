from functools import wraps

from flask import jsonify, render_template, session

from models.customer import get_customer


# Gives back True if someone is signed in
def is_signed_in():
    return "id" in session


# Gives back True if the person on the website is signed in as an admin
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


# Remember who signed in (Flask saves this in a cookie in the browser)
def remember_sign_in(customer):
    session["id"] = customer["customerID"]
    session["name"] = customer["customerName"]
    session["role"] = customer["role"]


# Put @admin_page above a page only admins can see. Everyone else gets the sign in form
def admin_page(view):
    @wraps(view)
    def checked(*args, **kwargs):
        if not is_admin():
            return render_template("auth/signin.html", error="Only admins can see this page."), 403
        return view(*args, **kwargs)
    return checked


# Put @admin_api above an API endpoint only admins can use. Everyone else gets a 403
def admin_api(view):
    @wraps(view)
    def checked(*args, **kwargs):
        if not is_admin():
            return jsonify(error="Only admins can do this."), 403
        return view(*args, **kwargs)
    return checked
