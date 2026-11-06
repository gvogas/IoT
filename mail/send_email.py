import smtplib
from email.message import EmailMessage

# The email settings are in config.py
from config import ALERT_EMAIL, ALERT_EMAIL_PASSWORD, ALERT_TO, SMTP_PORT, SMTP_SERVER


# Gives back True if the email was sent, False if not
def send_temperature_alert(fridge_id, temperature, threshold):
    if not (ALERT_EMAIL and ALERT_EMAIL_PASSWORD and ALERT_TO):
        print("Email alert not sent: set ALERT_EMAIL, ALERT_EMAIL_PASSWORD and ALERT_TO (see config.py)")
        return False

    # 1. Construct the email message
    msg = EmailMessage()
    msg["Subject"] = f"Temperature Alert - Frig{fridge_id}"
    msg["From"] = ALERT_EMAIL
    msg["To"] = ALERT_TO

    msg.set_content(
        f"The current temperature in Frig{fridge_id} is {temperature}°C.\n"
        f"The temperature threshold is {threshold}°C.\n\n"
        "Would you like to turn on the fan?\n"
        "Reply YES to turn on the fan, or NO to take no action."
    )

    # 2. Establish a secure connection and send the email
    try:
        # Use smtplib.SMTP as a context manager to ensure proper connection closure
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.starttls()  # Secure the connection using TLS encryption
            server.login(ALERT_EMAIL, ALERT_EMAIL_PASSWORD)
            server.send_message(msg)

        print(f"Email sent successfully for Frig{fridge_id}!")
        return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False


# Email a receipt to the customer. receipt is the dict from models.checkout.receipt()
# Gives back True if the email was sent, False if not
def send_receipt_email(to_address, receipt):
    if not (ALERT_EMAIL and ALERT_EMAIL_PASSWORD):
        print("Receipt not sent: set ALERT_EMAIL and ALERT_EMAIL_PASSWORD (see config.py)")
        return False

    lines = [f"{l['name']}: {l['quantity']} x ${l['unitPrice']:.2f} = ${l['lineTotal']:.2f}" for l in receipt["lines"]]
    msg = EmailMessage()
    msg["Subject"] = f"Your receipt #{receipt['purchaseID']}"
    msg["From"] = ALERT_EMAIL
    msg["To"] = to_address
    msg.set_content(
        f"Thank you for your purchase, {receipt['customer']}!\n\n"
        f"Receipt #{receipt['purchaseID']} - {receipt['date']}\n\n"
        + "\n".join(lines)
        + f"\n\nSubtotal: ${receipt['subtotal']:.2f}\n"
        f"Tax: ${receipt['tax']:.2f}\n"
        f"Total: ${receipt['total']:.2f}\n"
        f"Paid by {receipt['paymentMethod']}\n"
    )

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(ALERT_EMAIL, ALERT_EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Receipt email error: {e}")
        return False
