import sqlite3

from config import DB_PATH

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Customer (
            customerID INTEGER PRIMARY KEY AUTOINCREMENT,
            customerName VARCHAR(100) NOT NULL,
            address VARCHAR(255) NOT NULL,
            phoneNumber VARCHAR(20) NOT NULL UNIQUE,
            email VARCHAR(255) NOT NULL UNIQUE,
            passwordHash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'customer'
                CHECK (role IN ('customer', 'admin')),
            membershipNumber VARCHAR(12) NOT NULL UNIQUE,
            totalPoints INTEGER NOT NULL DEFAULT 0 CHECK (totalPoints >= 0),
            createdAt DATETIME NOT NULL);
        ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Fridge (
            fridgeID INTEGER PRIMARY KEY AUTOINCREMENT,
            fridgeName VARCHAR(100) NOT NULL,
            temp_threshold FLOAT NOT NULL
        );''')

    # Readings saved once a minute, for the history chart
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Reading (
            readingID INTEGER PRIMARY KEY AUTOINCREMENT,
            fridgeID INTEGER NOT NULL REFERENCES Fridge(fridgeID),
            temperature FLOAT,
            humidity FLOAT,
            recordedAt DATETIME NOT NULL
        );''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reading_fridge_time ON Reading(fridgeID, recordedAt)")

    # Add the 2 fridges only the first time
    # (after that, change the threshold on the Fridges page of the website)
    cursor.execute("SELECT COUNT(*) FROM Fridge")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO Fridge (fridgeName, temp_threshold)
            VALUES ('Fridge 1', 50.0), ('Fridge 2', 50.0);
        ''')
    conn.commit()
    conn.close()
    print("SQLite db initialized successfully:", DB_PATH)

if __name__ == "__main__":
    main()
