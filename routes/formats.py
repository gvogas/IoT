from datetime import datetime

from models.database import DATE_FORMAT


# "2026-11-06 15:03:43" -> "Nov 6, 2026"
def nice_date(text):
    moment = datetime.strptime(text, DATE_FORMAT)
    return f"{moment:%b} {moment.day}, {moment.year}"


# "2026-11-06 15:03:43" -> "Nov 6, 2026 at 3:03 PM"
def nice_datetime(text):
    moment = datetime.strptime(text, DATE_FORMAT)
    return f"{nice_date(text)} at {moment.hour % 12 or 12}:{moment.minute:02d} {'AM' if moment.hour < 12 else 'PM'}"


# 1314.5 -> "$1,314.50" and -16 -> "-$16.00"
def money(amount):
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):,.2f}"
