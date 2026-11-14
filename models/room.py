"""The Minew MSP01 sensor in Fridge 3: saved readings and motion."""

from datetime import datetime, timedelta

from models.database import DATE_FORMAT, connect, execute, now_text


# Save one reading with the current time. Any of them can be None
def save_room_reading(temperature, humidity, light):
    execute(
        "INSERT INTO RoomReading (temperature, humidity, light, recordedAt) VALUES (?, ?, ?, ?)",
        (temperature, humidity, light, now_text()),
    )


# Save the time someone started moving in front of the sensor
def save_motion():
    execute("INSERT INTO MotionEvent (detectedAt) VALUES (?)", (now_text(),))


# Lowest and highest of the last 24 hours, and the motion today, for the dashboard
def get_room_stats():
    now = datetime.now()
    day_ago = (now - timedelta(hours=24)).strftime(DATE_FORMAT)
    midnight = now.strftime("%Y-%m-%d 00:00:00")

    conn = connect()
    try:
        day = conn.execute(
            """SELECT MIN(temperature) AS minTemp, MAX(temperature) AS maxTemp,
                      MIN(humidity) AS minHum, MAX(humidity) AS maxHum,
                      MIN(light) AS minLight, MAX(light) AS maxLight
               FROM RoomReading WHERE recordedAt >= ?""",
            (day_ago,),
        ).fetchone()

        # How many times motion started in each hour of today. "14" -> 3
        rows = conn.execute(
            """SELECT strftime('%H', detectedAt) AS hour, COUNT(*) AS total
               FROM MotionEvent WHERE detectedAt >= ? GROUP BY hour""",
            (midnight,),
        ).fetchall()

        last = conn.execute("SELECT MAX(detectedAt) FROM MotionEvent").fetchone()[0]
    finally:
        conn.close()

    # One number per hour, 0 to 23. Hours with no motion stay 0
    by_hour = [0] * 24
    for row in rows:
        by_hour[int(row["hour"])] = row["total"]

    # Seconds since the last motion (even before today)
    last_motion_age = None
    if last:
        last_motion_age = round((now - datetime.strptime(last, DATE_FORMAT)).total_seconds())

    return {
        "minTemp": day["minTemp"],
        "maxTemp": day["maxTemp"],
        "minHum": day["minHum"],
        "maxHum": day["maxHum"],
        "minLight": day["minLight"],
        "maxLight": day["maxLight"],
        "motionToday": sum(by_hour),
        "motionByHour": by_hour,
        "lastMotionAge": last_motion_age,
    }
