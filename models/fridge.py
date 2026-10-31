from models.database import execute, query, query_one


class Fridge:

    def __init__(fridge, fridge_id, name=None, threshold=None):
        fridge.id = fridge_id
        fridge.name = name
        fridge.threshold = threshold

        # MQTT topics, like "frig1/temperature"
        fridge.temp_topic = f"frig{fridge_id}/temperature"
        fridge.hum_topic = f"frig{fridge_id}/humidity"

    # Load all details in one query and return Fridge objects.
    @staticmethod
    def get_all():
        rows = query("SELECT fridgeID, fridgeName, temp_threshold FROM Fridge ORDER BY fridgeID")
        return [
            Fridge(row["fridgeID"], name=row["fridgeName"], threshold=row["temp_threshold"])
            for row in rows
        ]

    # Return one Fridge object, or None if the ID is not there.
    @staticmethod
    def get_by_id(fridge_id):
        row = query_one("SELECT fridgeID, fridgeName, temp_threshold FROM Fridge WHERE fridgeID = ?", (fridge_id,))
        if row is None:
            return None
        return Fridge(row["fridgeID"], name=row["fridgeName"], threshold=row["temp_threshold"])

    # We read it every time, so a new threshold from the dashboard works right away
    def get_threshold(fridge):
        latest = Fridge.get_by_id(fridge.id)
        fridge.threshold = latest.threshold if latest else None
        return fridge.threshold

    # Gives back False if the fridge is not in the database
    def set_threshold(fridge, threshold):
        changed = execute("UPDATE Fridge SET temp_threshold = ? WHERE fridgeID = ?", (threshold, fridge.id))
        if changed == 0:
            return False
        fridge.threshold = threshold
        return True
