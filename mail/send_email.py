import smtplib
import threading
from email.message import EmailMessage

from flask import render_template

from config import ALERT_EMAIL, ALERT_EMAIL_PASSWORD, ALERT_TO, SMTP_PORT, SMTP_SERVER
from mail.translations import receipt_text
from models.customer import admin_emails
from models.database import now_text


# Send from the store's Gmail account. Gives back True if it was sent
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


# In a thread, so the page doesn't wait for the email to send
def send_to_admin_in_background(subject, text, html):
    threading.Thread(target=send, args=(admin_address(), subject, text, html), daemon=True).start()


# Rendered here, not in the thread, because templates need the web request
def send_stock_alert(alerts):
    names = ", ".join(alert["name"] for alert in alerts)
    date = now_text()
    send_to_admin_in_background(
        f"Stock Alert - {names}",
        render_template("email/stock_alert.txt", alerts=alerts, date=date),
        render_template("email/stock_alert.html", alerts=alerts, date=date),
    )


# A low or out of stock product just got a delivery
def send_restock_alert(name, received, in_stock, threshold):
    date = now_text()
    send_to_admin_in_background(
        f"Restocked - {name}",
        render_template("email/restocked.txt", name=name, received=received, in_stock=in_stock, threshold=threshold, date=date),
        render_template("email/restocked.html", name=name, received=received, in_stock=in_stock, threshold=threshold, date=date),
    )


# receipt comes from models.checkout.receipt(). The email uses the language picked in the menu
def send_receipt_email(to_address, receipt):
    t = receipt_text()
    return send(
        to_address,
        f"{t['subject']} #{receipt['purchaseID']}: ${receipt['total']:.2f}",
        render_template("email/receipt.txt", receipt=receipt, t=t),
        render_template("email/receipt.html", receipt=receipt, t=t),
    )
