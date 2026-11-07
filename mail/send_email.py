import smtplib
from email.message import EmailMessage

from flask import render_template

from config import ALERT_EMAIL, ALERT_EMAIL_PASSWORD, ALERT_TO, SMTP_PORT, SMTP_SERVER


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


# Email a receipt to the customer. receipt is the dict from models.checkout.receipt()
# The templates are in templates/email/. This runs inside a web request, so they can be filled in here
def send_receipt_email(to_address, receipt):
    return send(
        to_address,
        f"Your Store receipt #{receipt['purchaseID']}: ${receipt['total']:.2f}",
        render_template("email/receipt.txt", receipt=receipt),
        render_template("email/receipt.html", receipt=receipt),
    )
