import smtplib
from email.message import EmailMessage

# 1. Setup email configuration variables
SMTP_SERVER = "smtp.gmail.com"  # e.g., smtp.office365.com for Outlook
SMTP_PORT = 587                 # Standard port for TLS encryption
SENDER_EMAIL = ""
SENDER_PASSWORD = "" 
RECEIVER_EMAIL = ""

# 2. Construct the email message
msg = EmailMessage()
msg["Subject"] = ""
msg["From"] = SENDER_EMAIL
msg["To"] = RECEIVER_EMAIL
msg.set_content("")

# 3. Establish a secure connection and send the email
try:
    # Use smtplib.SMTP as a context manager to ensure proper connection closure
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()  # Secure the connection using TLS encryption
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        
    print("Email sent successfully!")

except Exception as e:
    print(f"An error occurred: {e}")