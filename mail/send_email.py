import smtplib
import threading
from datetime import datetime
from email.message import EmailMessage

from flask import render_template

from config import ALERT_EMAIL, ALERT_EMAIL_PASSWORD, ALERT_TO, SMTP_PORT, SMTP_SERVER
from models.customer import admin_emails


# Send one email from the store's Gmail account. Gives back True if it was sent, False if not
# html is optional. Email apps that can't show it, or block it, show the text instead
def send(to_address, subject, text, html=None):
    if not (ALERT_EMAIL and ALERT_EMAIL_PASSWORD and to_address):
        print(f"Email not sent ({subject}): set ALERT_EMAIL, ALERT_EMAIL_PASSWORD and ALERT_TO (see config.py)")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = ALERT_EMAIL
    msg["To"] = to_address
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(ALERT_EMAIL, ALERT_EMAIL_PASSWORD)
            server.send_message(msg)
    except Exception as err:
        print(f"Email not sent ({subject}): {err}")
        return False

    print(f"Email sent: {subject}")
    return True


# Tell the staff a fridge is too warm. read_email.py picks up the YES/NO reply
def send_temperature_alert(fridge_id, temperature, threshold):
    return send(
        ALERT_TO,
        f"Temperature Alert - Frig{fridge_id}",
        f"The current temperature in Frig{fridge_id} is {temperature}°C.\n"
        f"The temperature threshold is {threshold}°C.\n\n"
        "Would you like to turn on the fan?\n"
        "Reply YES to turn on the fan, or NO to take no action.",
    )


# Who gets the stock emails: every admin account, or ALERT_TO if there are no admins
def admin_address():
    return ", ".join(admin_emails()) or ALERT_TO


# Send an email to the admin in a thread, so the customer or the admin doesn't wait for it to send
def send_to_admin_in_background(subject, text, html):
    threading.Thread(target=send, args=(admin_address(), subject, text, html), daemon=True).start()


# Tell the admin which products are low or out of stock. alerts is the list from models.checkout.stock_alerts()
# The templates can only be filled in during a web request, so that happens here and not in the thread
def send_stock_alert(alerts):
    names = ", ".join(alert["name"] for alert in alerts)
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    send_to_admin_in_background(
        f"Stock Alert - {names}",
        render_template("email/stock_alert.txt", alerts=alerts, date=date),
        render_template("email/stock_alert.html", alerts=alerts, date=date),
    )


# Tell the admin a low or out of stock product just got a delivery
def send_restock_alert(name, received, in_stock, threshold):
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    send_to_admin_in_background(
        f"Restocked - {name}",
        render_template("email/restocked.txt", name=name, received=received, in_stock=in_stock, threshold=threshold, date=date),
        render_template("email/restocked.html", name=name, received=received, in_stock=in_stock, threshold=threshold, date=date),
    )


# Email a receipt to the customer. receipt is the dict from models.checkout.receipt()
# The templates are in templates/email/. This runs inside a web request, so they can be filled in here
def send_receipt_email(to_address, receipt):
    return send(
        to_address,
        f"Your Store receipt #{receipt['purchaseID']}: ${receipt['total']:.2f}",
        render_template("email/receipt.txt", receipt=receipt),
        render_template("email/receipt.html", receipt=receipt),
    )
