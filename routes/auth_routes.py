from flask import Blueprint, redirect, render_template, request, session

from models.customer import check_sign_in
from routes.guards import remember_sign_in

auth_routes = Blueprint("auth_routes", __name__)


@auth_routes.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "GET":
        return render_template("auth/signin.html")

    customer = check_sign_in(request.form.get("email", ""), request.form.get("password", ""))
    if customer is None:
        return render_template("auth/signin.html", error="Wrong email or password.")

    remember_sign_in(customer)
    # Admins go to the admin page, customers go to the checkout
    return redirect("/admin" if customer["role"] == "admin" else "/")


@auth_routes.route("/signout")
def signout():
    session.clear()
    return redirect("/")
