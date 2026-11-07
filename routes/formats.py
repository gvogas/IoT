from datetime import datetime

# How the database stores dates and times
STORED_FORMAT = "%Y-%m-%d %H:%M:%S"


# "2026-11-06 15:03:43" -> "Nov 6, 2026"
def nice_date(text):
    moment = datetime.strptime(text, STORED_FORMAT)
    return f"{moment:%b} {moment.day}, {moment.year}"


# "2026-11-06 15:03:43" -> "Nov 6, 2026 at 3:03 PM"
def nice_datetime(text):
    moment = datetime.strptime(text, STORED_FORMAT)
    return f"{nice_date(text)} at {moment.hour % 12 or 12}:{moment.minute:02d} {'AM' if moment.hour < 12 else 'PM'}"
