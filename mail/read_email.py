import email
import imaplib
import logging
import time
from email.utils import parseaddr

from config import ALERT_EMAIL, ALERT_EMAIL_PASSWORD, ALERT_TO, IMAP_SERVER
from controllers.fan_controller import fan_controller
from controllers.mqtt_controller import mqtt_controller
from mail.send_email import sent_alerts

log = logging.getLogger(__name__)

# How often to check the inbox (seconds)
CHECK_EVERY = 30

# A reply only counts if the alert was sent this recently (seconds)
REPLY_WITHIN = 60 * 60


# The text of an email, skipping attachments that happen to be plain text
def body_text(msg):
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.get_content_type() == "text/plain" and part.get_content_disposition() != "attachment":
            payload = part.get_payload(decode=True)
            if payload:
                return payload.decode(errors="replace")
    return ""


# Like "YES"
def first_word(text):
    words = text.split(maxsplit=1)
    return words[0].strip(".,!?").upper() if words else ""


# The fridge whose alert this email replies to, or None if it isn't a reply to a recent alert we sent
def replied_fridge(msg):
    # Every email program puts the ID of the email it replies to in In-Reply-To or References
    replied_to = f"{msg.get('In-Reply-To', '')} {msg.get('References', '')}"
    # list() makes a copy, because the MQTT thread can add an alert while we look
    for message_id, (fridge_id, sent_at) in list(sent_alerts.items()):
        if message_id in replied_to and time.time() - sent_at < REPLY_WITHIN:
            return fridge_id
    return None


# Gives back True if the email was a YES or NO reply to an alert
def handle_reply(msg):
    # Only the address the alerts go to can answer them
    sender = parseaddr(msg.get("From", ""))[1].lower()
    allowed = [parseaddr(address)[1].lower() for address in ALERT_TO.split(",")]
    if sender not in allowed:
        return False

    fridge_id = replied_fridge(msg)
    if fridge_id is None:
        return False

    answer = first_word(body_text(msg))
    log.info("Reply about Frig%s from %s: %s", fridge_id, sender, answer)

    if answer == "YES":
        # Only if the fridge is still too warm, so an old YES can't turn the fan on later
        if mqtt_controller.is_too_warm(fridge_id):
            fan_controller.turn_on()
            log.info("YES received. Fan turned on.")
        else:
            log.info("YES received, but Frig%s is back under its limit. Fan left alone.", fridge_id)
        return True
    if answer == "NO":
        log.info("NO received. No action taken.")
        return True

    log.info("Reply ignored. Please reply YES or NO.")
    return False


# Act on the unread replies to temperature alerts in the inbox
def check_email_replies():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    try:
        mail.login(ALERT_EMAIL, ALERT_EMAIL_PASSWORD)
        mail.select("inbox")

        # Only unread alert replies, so other emails in the inbox are left alone
        status, response = mail.search(None, 'UNSEEN SUBJECT "Temperature Alert"')
        if status != "OK":
            return

        for email_id in response[0].split():
            # BODY.PEEK reads the email without marking it as read
            status, msg_data = mail.fetch(email_id, "(BODY.PEEK[])")
            if status != "OK":
                continue
            for part in msg_data:
                if isinstance(part, tuple) and handle_reply(email.message_from_bytes(part[1])):
                    mail.store(email_id, "+FLAGS", "\\Seen")
    finally:
        mail.logout()


# app.py runs this in a background thread
def check_forever():
    while True:
        try:
            check_email_replies()
        except Exception as err:
            log.error("Could not check the inbox: %s", err)
        time.sleep(CHECK_EVERY)
