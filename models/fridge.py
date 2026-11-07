from models.database import execute, query, query_one


class Fridge:

    def __init__(self, fridge_id, name=None, threshold=None):
        self.id = fridge_id
        self.name = name
        self.threshold = threshold

        # MQTT topics, like "frig1/temperature"
        self.temp_topic = f"frig{fridge_id}/temperature"
        self.hum_topic = f"frig{fridge_id}/humidity"

    @staticmethod
    def from_row(row):
        return Fridge(row["fridgeID"], name=row["fridgeName"], threshold=row["temp_threshold"])

    @staticmethod
    def get_all():
        rows = query("SELECT fridgeID, fridgeName, temp_threshold FROM Fridge ORDER BY fridgeID")
        return [Fridge.from_row(row) for row in rows]

    # Gives back one Fridge, or None if the ID is not there
    @staticmethod
    def get_by_id(fridge_id):
        row = query_one("SELECT fridgeID, fridgeName, temp_threshold FROM Fridge WHERE fridgeID = ?", (fridge_id,))
        return Fridge.from_row(row) if row else None

    # Read every time, so a new threshold from the dashboard works right away
    def get_threshold(self):
        latest = Fridge.get_by_id(self.id)
        self.threshold = latest.threshold if latest else None
        return self.threshold

    # Gives back False if the fridge is not in the database
    def set_threshold(self, threshold):
        changed = execute("UPDATE Fridge SET temp_threshold = ? WHERE fridgeID = ?", (threshold, self.id))
        if changed == 0:
            return False
        self.threshold = threshold
        return True
