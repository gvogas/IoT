from flask import Flask, render_template
from Customer import customer_auth

app = Flask(__name__)

# app.register_blueprint(customer_auth)

@app.route("/")
def home():
    return render_template('customerDashboard.html')

if __name__ == '__main__':
    app.run(debug=True)