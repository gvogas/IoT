import sqlite3

from flask import flash, jsonify, redirect, render_template, request

from hardware.rfid import ReaderError
from models.product_image import MAX_UPLOAD_BYTES
from routes.admin_routes import admin_routes
from routes.auth_routes import auth_routes
from routes.checkout_routes import checkout_routes
from routes.customer_routes import customer_routes
from routes.fan_routes import fan_routes
from routes.formats import money, nice_date, nice_datetime
from routes.fridge_routes import fridge_routes
from routes.product_routes import product_routes
from routes.room_routes import room_routes


# API errors are sent as JSON
def is_api_request():
    return request.path.startswith(("/api/", "/rfid/"))


# Add every page, filter and error handler to the app
def register_routes(app):
    for blueprint in (admin_routes, auth_routes, checkout_routes, customer_routes,
                      fan_routes, fridge_routes, product_routes, room_routes):
        app.register_blueprint(blueprint)

    app.add_template_filter(nice_date)
    app.add_template_filter(nice_datetime)
    app.add_template_filter(money)

    # Database errors no route handles, like "no such table" if init_database wasn't run
    @app.errorhandler(sqlite3.Error)
    def database_error(err):
        text = f"Database error: {err}"
        if is_api_request():
            return jsonify(error=text), 500
        return render_template("error.html", title="Something went wrong", text=text), 500

    # The product form checks the size first, so this only happens if that check didn't run
    @app.errorhandler(413)
    def upload_too_big(err):
        flash(f"That image is too big. The limit is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.", "error")
        return redirect(request.path)

    # The RFID reader is unplugged or not answering
    @app.errorhandler(ReaderError)
    def reader_error(err):
        return jsonify(error=str(err)), 503
