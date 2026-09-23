#not yet configured

from flask import  Blueprint, Flask

customer_bp = Blueprint('customer_auth', __name__)

customer_bp.route('/customer')
def signUp():
    return "This is the cusotmer sign up page"

app = Flask(__name__)
app.register_blueprint(customer_bp, url_prefix="/pages")
