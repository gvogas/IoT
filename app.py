from flask import Flask, render_template, request
import sqlite3
# from Customer import customer_auth

app = Flask(__name__)

# app.register_blueprint(customer_auth)

def get_db_connection():
    conn = sqlite3.connect('customer.db')

    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    return render_template('customerDashboard.html')

@app.route('/submit', methods=['POST'])
def submit():
    customer_name = request.form.get("name")
    customer_address = request.form.get("address")
    customer_email = request.form.get("email")
    customer_phone_number = request.form.get("phoneNumber")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = "INSERT INTO Customer (customerName, address, email, phoneNumber) VALUES (?,?,?,?)"
        cursor.execute(query, (customer_name, customer_address, customer_email, customer_phone_number))

        conn.commit()
        return "Data successfully written"
    
    except sqlite3.Error as err:
        return f"An error occured: {err}"
    
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    app.run(debug=True)