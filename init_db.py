import sqlite3

conn = sqlite3.connect('customer.db')
cursor = conn.cursor()

cursor.execute(''' 
CREATE TABLE Customer (
    customerID INTEGER PRIMARY KEY AUTOINCREMENT,
    customerName VARCHAR(100) NOT NULL,
    address VARCHAR(255) NOT NULL,
    phoneNumber VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE);
''')

conn.commit()
conn.close()
print("SQLite db initialized successfully!")