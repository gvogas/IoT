import smtplib
from email.message import EmailMessage

# 1. Setup email configuration variables
SMTP_SERVER = "smtp.gmail.com"  # e.g., smtp.office365.com for Outlook
SMTP_PORT = 587                 # Standard port for TLS encryption
SENDER_EMAIL = ""
SENDER_PASSWORD = ""
RECEIVER_EMAIL = ""


def send_temperature_alert(fridge_id, temperature, threshold):
    # 2. Construct the email message
    msg = EmailMessage()
    msg["Subject"] = f"Temperature Alert - Frig{fridge_id}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL

    msg.set_content(
        f"The current temperature in Frig{fridge_id} is {temperature}°C.\n"
        f"The temperature threshold is {threshold}°C.\n\n"
        "Would you like to turn on the fan?\n"
        "Reply YES to turn on the fan, or NO to take no action."
    )

    # 3. Establish a secure connection and send the email
    try:
        # Use smtplib.SMTP as a context manager to ensure proper connection closure
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection using TLS encryption
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        print(f"Email sent successfully for Frig{fridge_id}!")

    except Exception as e:
        print(f"An error occurred: {e}")