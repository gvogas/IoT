import email
import imaplib
import time

import paho.mqtt.client as mqtt

from config import ALERT_EMAIL, ALERT_EMAIL_PASSWORD, FAN_COMMAND_TOPIC, IMAP_SERVER, MQTT_BROKER, MQTT_PORT

# Only replies to these alerts count
ALERT_SUBJECTS = ("temperature alert - frig1", "temperature alert - frig2")

# How often to check the inbox (seconds)
CHECK_EVERY = 8


# The text of an email, skipping attachments that happen to be plain text
def body_text(msg):
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.get_content_type() == "text/plain" and part.get_content_disposition() != "attachment":
            payload = part.get_payload(decode=True)
            if payload:
                return payload.decode(errors="replace")
    return ""


# The first word of the reply in capitals, like "YES"
def first_word(text):
    words = text.split(maxsplit=1)
    return words[0].strip(".,!?").upper() if words else ""


# Act on one email. Gives back True if it was a YES or NO reply to an alert
def handle_reply(msg, client):
    subject = msg.get("Subject", "").lower()
    if not any(alert in subject for alert in ALERT_SUBJECTS):
        return False

    answer = first_word(body_text(msg))
    print(f"Reply to \"{msg.get('Subject', '')}\": {answer}")

    if answer == "YES":
        # The app listens on this topic and turns the fan on (see controllers/mqtt_controller.py)
        client.publish(FAN_COMMAND_TOPIC, "ON", qos=1)
        print("YES received. Fan ON command sent.")
        return True
    if answer == "NO":
        print("NO received. No action taken.")
        return True

    print("Reply ignored. Please reply YES or NO.")
    return False


def check_email_replies():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    try:
        mail.login(ALERT_EMAIL, ALERT_EMAIL_PASSWORD)
        mail.select("inbox")

        status, response = mail.search(None, "UNSEEN")
        if status != "OK":
            return

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        try:
            for email_id in response[0].split():
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                if status != "OK":
                    continue
                for part in msg_data:
                    if isinstance(part, tuple) and handle_reply(email.message_from_bytes(part[1]), client):
                        mail.store(email_id, "+FLAGS", "\\Seen")
        finally:
            client.loop_stop()
            client.disconnect()
    finally:
        mail.logout()


# Check for replies forever. app.py runs this in the background
def check_forever():
    while True:
        try:
            check_email_replies()
        except Exception as err:
            print(f"Could not check the inbox: {err}")
        time.sleep(CHECK_EVERY)
