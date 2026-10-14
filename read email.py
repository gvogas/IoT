import email
import imaplib

# Replace with your details
username = ""
password = ""
imap_server = "imap.gmail.com"

# Connect to server
mail = imaplib.IMAP4_SSL(imap_server)
mail.login(username, password)

# Select the inbox folder
mail.select("inbox")

# Search for all emails
status, response = mail.search(None, "ALL")
email_ids = response[0].split()


for e_id in email_ids[-5:]:  # Loop through the last 5 emails
  # Fetch the email data by ID
  res, msg_data = mail.fetch(e_id, "(RFC822)")
 
  for response_part in msg_data:
    if isinstance(response_part, tuple):
      # Parse bytes into an email message object
      msg = email.message_from_bytes(response_part[1])
 
      sender = msg["From"]
      print(f"From: {sender}")
 
      # Extract the body text
      if msg.is_multipart():
        for part in msg.walk():
          # Skip attachments that happen to be plain text
          if part.get_content_type() == "text/plain" and part.get_content_disposition() != "attachment":
            body = part.get_payload(decode=True).decode(errors="replace")
            print(f"Body: {body}\n")
            break  # only print the first text body
      else:
        body = msg.get_payload(decode=True).decode(errors="replace")
        print(f"Body: {body}\n")
 
      print("-----")
 
# Close the connection
mail.logout()
