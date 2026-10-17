from models.db import connect


# Get every fridge from the database, like [Fridge 1, Fridge 2]
def all_fridges():
    conn = connect()
    try:
        ids = [row["fridgeID"] for row in conn.execute("SELECT fridgeID FROM Fridge")]
    finally:
        conn.close()
    return [Fridge(fridge_id) for fridge_id in ids]


class Fridge:

    def __init__(fridge, fridge_id, fan=None):
        fridge.id = fridge_id
        fridge.fan = fan    # a Fan, or None if this fridge has no fan yet

        # MQTT topics, like "frig1/temperature"
        fridge.temp_topic = f"frig{fridge_id}/temperature"
        fridge.hum_topic = f"frig{fridge_id}/humidity"
        fridge.fan_topic = f"frig{fridge_id}/fan"

    # Get the name and threshold from the database (None if the fridge is not there)
    def get_info(fridge):
        conn = connect()
        try:
            row = conn.execute("SELECT fridgeName, temp_threshold FROM Fridge WHERE fridgeID = ?", (fridge.id,)).fetchone()
        finally:
            conn.close()
        return row

    # We read it every time, so a new threshold from the dashboard works right away
    def get_threshold(fridge):
        row = fridge.get_info()
        return row["temp_threshold"] if row else None

    # Gives back False if the fridge is not in the database
    def set_threshold(fridge, threshold):
        conn = connect()
        try:
            cursor = conn.execute("UPDATE Fridge SET temp_threshold = ? WHERE fridgeID = ?", (threshold, fridge.id))
            conn.commit()
        finally:
            conn.close()
        return cursor.rowcount > 0

    # Turn the fan on if the temperature is higher than the threshold. Gives back "ON" or "OFF"
    def check_temperature(fridge, temperature):
        threshold = fridge.get_threshold()
        if threshold is None:
            return None
        state = "ON" if temperature > threshold else "OFF"

        if fridge.fan:
            if state == "ON":
                fridge.fan.on()
            else:
                fridge.fan.off()
        return state
