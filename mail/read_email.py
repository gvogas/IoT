
import email
import imaplib
import time

import paho.mqtt.client as mqtt
from config import ALERT_EMAIL, ALERT_EMAIL_PASSWORD, FAN_COMMAND_TOPIC, IMAP_SERVER, MQTT_BROKER, MQTT_PORT

# Same Gmail account that sends the alerts (set in config.py)
username = ALERT_EMAIL
password = ALERT_EMAIL_PASSWORD
imap_server = IMAP_SERVER

# The app listens on this topic and turns the fan on (see controllers/mqtt_controller.py)
fan_topic = FAN_COMMAND_TOPIC


def check_email_replies():
    # Connect to server
    mail = imaplib.IMAP4_SSL(imap_server)

    try:
        mail.login(username, password)

        # Select the inbox folder
        mail.select("inbox")

        # Search for unread emails
        status, response = mail.search(None, "UNSEEN")

        if status != "OK":
            return

        email_ids = response[0].split()

        # Connect to the MQTT broker
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()

        try:
            for e_id in email_ids:
                # Fetch the email data by ID
                res, msg_data = mail.fetch(e_id, "(RFC822)")

                if res != "OK":
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        # Parse bytes into an email message object
                        msg = email.message_from_bytes(response_part[1])

                        subject = msg.get("Subject", "").lower()

                        # Only handle replies to refrigerator temperature alerts
                        if not (
                            "temperature alert - frig1" in subject
                            or "temperature alert - frig2" in subject
                        ):
                            continue

                        # Extract the body text
                        body = ""

                        if msg.is_multipart():
                            for part in msg.walk():
                                # Skip attachments that happen to be plain text
                                if (
                                    part.get_content_type() == "text/plain"
                                    and part.get_content_disposition() != "attachment"
                                ):
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        body = payload.decode(errors="replace")
                                        break  # only print the first text body
                        else:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                body = payload.decode(errors="replace")

                        # Check the first word of the reply
                        answer = body.strip().split(maxsplit=1)[0].strip(".,!?").upper() if body.strip() else ""

                        print(f"Subject: {msg.get('Subject', '')}")
                        print(f"Body: {body}")

                        if answer == "YES":
                            # Send an MQTT command to the Raspberry Pi's fan controller
                            client.publish(fan_topic, "ON", qos=1)
                            print("YES received. Fan ON command sent.")

                        elif answer == "NO":
                            # Do not send a command, so the fan state stays unchanged
                            print("NO received. No action taken.")

                        else:
                            # Ignore replies that do not start with YES or NO
                            print("Reply ignored. Please reply YES or NO.")

                            continue

                        # Mark the processed email as read
                        mail.store(e_id, "+FLAGS", "\\Seen")
                        print("-----")

        finally:
            client.loop_stop()
            client.disconnect()

    finally:
        # Close the connection
        mail.logout()


# Check for replies every 15 seconds. app.py runs this in the background
def check_forever():
    while True:
        try:
            check_email_replies()
        except Exception as e:
            print(f"An error occurred: {e}")

        time.sleep(15)


if __name__ == "__main__":
    check_forever()
