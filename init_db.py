import sqlite3

conn = sqlite3.connect('customer.db')
cursor = conn.cursor()

cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS Customer (
        customerID INTEGER PRIMARY KEY AUTOINCREMENT,
        customerName VARCHAR(100) NOT NULL,
        address VARCHAR(255) NOT NULL,
        phoneNumber VARCHAR(20) NOT NULL UNIQUE,
        email VARCHAR(255) NOT NULL UNIQUE);
    ''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Fridge (
        fridgeID INTEGER PRIMARY KEY AUTOINCREMENT,
        fridgeName VARCHAR(100) NOT NULL,
        temp_threshold FLOAT NOT NULL
    );''')

# Only seed the fridges the first time
cursor.execute("SELECT COUNT(*) FROM Fridge")
if cursor.fetchone()[0] == 0:
    cursor.execute('''
        INSERT INTO Fridge (fridgeName, temp_threshold)
        VALUES ('Fridge 1', 50.0), ('Fridge 2', 50.0);
    ''')
conn.commit()
conn.close()
print("SQLite db initialized successfully!")