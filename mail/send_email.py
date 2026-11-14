import logging
import smtplib
import threading
import time
from email.message import EmailMessage
from email.utils import make_msgid

from flask import render_template

from config import ALERT_EMAIL, ALERT_EMAIL_PASSWORD, ALERT_TO, SMTP_PORT, SMTP_SERVER
from mail.translations import receipt_text
from models.customer import admin_emails
from models.database import now_text

log = logging.getLogger(__name__)

# The temperature alerts we sent: Message-ID -> (fridge id, time sent).
# read_email.py only accepts a YES that replies to one of these
sent_alerts = {}


# Send from the store's Gmail account. Gives back True if it was sent
def send(to_address, subject, text, html=None, message_id=None):
    if not (ALERT_EMAIL and ALERT_EMAIL_PASSWORD and to_address):
        log.warning("Email not sent (%s): set ALERT_EMAIL, ALERT_EMAIL_PASSWORD and ALERT_TO (see config.py)", subject)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = ALERT_EMAIL
    msg["To"] = to_address
    if message_id:
        msg["Message-ID"] = message_id
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(ALERT_EMAIL, ALERT_EMAIL_PASSWORD)
            server.send_message(msg)
    except Exception as err:
        log.error("Email not sent (%s): %s", subject, err)
        return False

    log.info("Email sent: %s", subject)
    return True


# Tell the staff a fridge is too warm. read_email.py picks up the YES/NO reply
def send_temperature_alert(fridge_id, temperature, threshold):
    # A unique ID, so we can tell a real reply to this email from any other email
    message_id = make_msgid()
    sent = send(
        ALERT_TO,
        f"Temperature Alert - Frig{fridge_id}",
        f"The current temperature in Frig{fridge_id} is {temperature}°C.\n"
        f"The temperature threshold is {threshold}°C.\n\n"
        "Would you like to turn on the fan?\n"
        "Reply YES to turn on the fan, or NO to take no action.",
        message_id=message_id,
    )
    if sent:
        sent_alerts[message_id] = (fridge_id, time.time())
    return sent


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


# The subject, text and HTML of a receipt email. receipt comes from models.checkout.receipt().
# The email uses the language picked in the menu
def receipt_email(receipt):
    t = receipt_text()
    subject = f"{t['subject']} #{receipt['purchaseID']}: ${receipt['total']:.2f}"
    text = render_template("email/receipt.txt", receipt=receipt, t=t)
    html = render_template("email/receipt.html", receipt=receipt, t=t)
    return subject, text, html


# Send a receipt now and wait for it. Gives back True if it was sent
def send_receipt_email(to_address, receipt):
    subject, text, html = receipt_email(receipt)
    return send(to_address, subject, text, html)
