from datetime import datetime, timedelta

from models.database import connect, execute, query

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# Turns "23.5" into 23.5, or None if it isn't a number
def to_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# Save one reading
def save_reading(fridge_id, temperature, humidity):
    execute(
        "INSERT INTO Reading (fridgeID, temperature, humidity, recordedAt) VALUES (?, ?, ?, ?)",
        (fridge_id, temperature, humidity, datetime.now().strftime(TIME_FORMAT)),
    )


# Readings from the last few hours, for the history chart
def get_history(fridge_id, hours):
    since = (datetime.now() - timedelta(hours=hours)).strftime(TIME_FORMAT)
    rows = query(
        "SELECT recordedAt, temperature, humidity FROM Reading WHERE fridgeID = ? AND recordedAt >= ? ORDER BY recordedAt",
        (fridge_id, since),
    )
    return [{"time": row["recordedAt"], "temperature": row["temperature"], "humidity": row["humidity"]} for row in rows]


# Lowest, highest, in range and trend for one fridge
def get_stats(fridge_id, threshold):
    now = datetime.now()
    day_ago = (now - timedelta(hours=24)).strftime(TIME_FORMAT)
    hour_ago = (now - timedelta(hours=1)).strftime(TIME_FORMAT)
    midnight = now.strftime("%Y-%m-%d 00:00:00")

    conn = connect()
    try:
        day = conn.execute(
            """SELECT MIN(temperature) AS minTemp, MAX(temperature) AS maxTemp,
                      MIN(humidity) AS minHum, MAX(humidity) AS maxHum,
                      COUNT(temperature) AS total, SUM(temperature > ?) AS overCount
               FROM Reading WHERE fridgeID = ? AND recordedAt >= ?""",
            (threshold, fridge_id, day_ago),
        ).fetchone()

        # Minutes over the limit today (one reading a minute)
        over_today = conn.execute(
            "SELECT COUNT(*) FROM Reading WHERE fridgeID = ? AND recordedAt >= ? AND temperature > ?",
            (fridge_id, midnight, threshold),
        ).fetchone()[0]

        # First and last reading of the last hour, for the trend
        first = conn.execute(
            "SELECT temperature, recordedAt FROM Reading WHERE fridgeID = ? AND recordedAt >= ? AND temperature IS NOT NULL ORDER BY recordedAt LIMIT 1",
            (fridge_id, hour_ago),
        ).fetchone()
        last = conn.execute(
            "SELECT temperature, recordedAt FROM Reading WHERE fridgeID = ? AND temperature IS NOT NULL ORDER BY recordedAt DESC LIMIT 1",
            (fridge_id,),
        ).fetchone()

        # When it went over the limit
        last_ok = conn.execute(
            "SELECT MAX(recordedAt) FROM Reading WHERE fridgeID = ? AND temperature <= ?",
            (fridge_id, threshold),
        ).fetchone()[0]
        over_since = conn.execute(
            "SELECT MIN(recordedAt) FROM Reading WHERE fridgeID = ? AND temperature > ? AND recordedAt > ?",
            (fridge_id, threshold, last_ok or ""),
        ).fetchone()[0]
    finally:
        conn.close()

    # °C per hour (needs at least 10 minutes of readings)
    trend = None
    if first and last and first["recordedAt"] != last["recordedAt"]:
        hours = (datetime.strptime(last["recordedAt"], TIME_FORMAT) - datetime.strptime(first["recordedAt"], TIME_FORMAT)).total_seconds() / 3600
        if hours >= 10 / 60:
            trend = round((last["temperature"] - first["temperature"]) / hours, 1)

    since = None
    if over_since:
        since_time = datetime.strptime(over_since, TIME_FORMAT)
        since = {"time": since_time.strftime("%H:%M"), "minutes": int((now - since_time).total_seconds() // 60)}

    total = day["total"]
    return {
        "minTemp": day["minTemp"],
        "maxTemp": day["maxTemp"],
        "minHum": day["minHum"],
        "maxHum": day["maxHum"],
        "inRange": round(100 * (total - day["overCount"]) / total) if total else None,
        "overTodayMinutes": over_today,
        "trend": trend,
        "overSince": since,
    }
