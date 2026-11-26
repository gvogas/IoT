import sqlite3

from config import DB_PATH, MSP01_ENABLED, MSP01_FRIDGE_ID

# Create the tables, or update an older database
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
            membershipNumber VARCHAR(32) NOT NULL UNIQUE,
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

    # MSP01 sensor (in Fridge 3) readings, saved once a minute. light is in lux
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS RoomReading (
            readingID INTEGER PRIMARY KEY AUTOINCREMENT,
            temperature FLOAT,
            humidity FLOAT,
            light INTEGER,
            recordedAt DATETIME NOT NULL
        );''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_roomreading_time ON RoomReading(recordedAt)")

    # One row each time the MSP01 starts seeing someone move
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS MotionEvent (
            motionID INTEGER PRIMARY KEY AUTOINCREMENT,
            detectedAt DATETIME NOT NULL
        );''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_motion_time ON MotionEvent(detectedAt)")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Category (
            categoryID INTEGER PRIMARY KEY AUTOINCREMENT,
            categoryName VARCHAR(50) NOT NULL UNIQUE
        );''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Producer (
            producerID INTEGER PRIMARY KEY AUTOINCREMENT,
            producerName VARCHAR(100) NOT NULL UNIQUE
        );''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Product (
            productID INTEGER PRIMARY KEY AUTOINCREMENT,
            productName VARCHAR(100) NOT NULL,
            categoryID INTEGER NOT NULL REFERENCES Category(categoryID),
            producerID INTEGER NOT NULL REFERENCES Producer(producerID),
            price DECIMAL(10,2) NOT NULL CHECK (price >= 0),
            costPrice DECIMAL(10,2) CHECK (costPrice >= 0),
            upc VARCHAR(13) NOT NULL UNIQUE CHECK (length(upc) <= 13),
            imagePath VARCHAR(255),
            lowStockThreshold INTEGER NOT NULL DEFAULT 5 CHECK (lowStockThreshold >= 0),
            -- SQLite has no real true/false type: a BOOLEAN column saves True as 1 and False as 0
            isActive BOOLEAN NOT NULL DEFAULT 1 CHECK (isActive IN (0, 1)),
            isTaxable BOOLEAN NOT NULL DEFAULT 1 CHECK (isTaxable IN (0, 1)),
            createdAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            description VARCHAR(500)
        );''')

    # Databases made before these columns existed get them here (CREATE TABLE above skips old tables)
    existing = {row[1] for row in cursor.execute("PRAGMA table_info(Product)")}
    if "lowStockThreshold" not in existing:
        cursor.execute("ALTER TABLE Product ADD COLUMN lowStockThreshold INTEGER NOT NULL DEFAULT 5 CHECK (lowStockThreshold >= 0)")
    if "description" not in existing:
        cursor.execute("ALTER TABLE Product ADD COLUMN description VARCHAR(500)")
    # What the store pays for one unit. Empty until the admin fills it in on the product form
    if "costPrice" not in existing:
        cursor.execute("ALTER TABLE Product ADD COLUMN costPrice DECIMAL(10,2) CHECK (costPrice >= 0)")
    # Does the checkout charge GST and QST on this product? Products that were already there are taxable
    if "isTaxable" not in existing:
        cursor.execute("ALTER TABLE Product ADD COLUMN isTaxable BOOLEAN NOT NULL DEFAULT 1 CHECK (isTaxable IN (0, 1))")
    # A product has no EPC of its own. Each unit has one (ProductItem), so an EPC column from an earlier try is removed
    if "epc" in existing:
        cursor.execute("DROP INDEX IF EXISTS idx_product_epc")
        cursor.execute("ALTER TABLE Product DROP COLUMN epc")
    # Each unit's EPC is scanned or typed in when it is received, so the company prefix and item reference are removed
    if "companyPrefix" in existing or "itemReference" in existing:
        cursor.execute("DROP INDEX IF EXISTS idx_product_epc_prefix")
    for column in ("companyPrefix", "itemReference"):
        if column in existing:
            cursor.execute(f"ALTER TABLE Product DROP COLUMN {column}")

    # One row per delivery of a product
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Reception (
            receptionID INTEGER PRIMARY KEY AUTOINCREMENT,
            productID INTEGER NOT NULL REFERENCES Product(productID),
            quantityReceived INTEGER NOT NULL CHECK (quantityReceived > 0),
            dateReceived DATE NOT NULL
        );''')

    # Receipt header (customerID is NULL only for old demo data)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Purchase (
            purchaseID INTEGER PRIMARY KEY AUTOINCREMENT,
            customerID INTEGER REFERENCES Customer(customerID),
            purchaseDate DATETIME NOT NULL,
            subtotal DECIMAL(10,2) NOT NULL CHECK (subtotal >= 0),
            gstAmount DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (gstAmount >= 0),
            qstAmount DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (qstAmount >= 0),
            taxAmount DECIMAL(10,2) NOT NULL DEFAULT 0,
            total DECIMAL(10,2) NOT NULL CHECK (total >= 0),
            pointsEarned INTEGER NOT NULL DEFAULT 0,
            paymentMethod VARCHAR(20) NOT NULL DEFAULT 'card'
                CHECK (paymentMethod IN ('card', 'cash', 'mobile')),
            emailSent BOOLEAN NOT NULL DEFAULT 0 CHECK (emailSent IN (0, 1))
        );''')

    # Older databases: split the tax into GST (5%) and QST (the rest)
    existing = {row[1] for row in cursor.execute("PRAGMA table_info(Purchase)")}
    if "gstAmount" not in existing:
        cursor.execute("ALTER TABLE Purchase ADD COLUMN gstAmount DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (gstAmount >= 0)")
        cursor.execute("ALTER TABLE Purchase ADD COLUMN qstAmount DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (qstAmount >= 0)")
        cursor.execute("UPDATE Purchase SET gstAmount = ROUND(subtotal * 0.05, 2) WHERE taxAmount > 0")
        cursor.execute("UPDATE Purchase SET qstAmount = ROUND(taxAmount - gstAmount, 2) WHERE taxAmount > 0")
    # An earlier version of the step above gave untaxed purchases 5% GST and a negative QST. This puts them back to 0
    cursor.execute("UPDATE Purchase SET gstAmount = 0, qstAmount = 0 WHERE taxAmount = 0")

    # Receipt lines, one per product
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS PurchaseItem (
            purchaseItemID INTEGER PRIMARY KEY AUTOINCREMENT,
            purchaseID INTEGER NOT NULL REFERENCES Purchase(purchaseID) ON DELETE CASCADE,
            productID INTEGER NOT NULL REFERENCES Product(productID),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            unitPrice DECIMAL(10,2) NOT NULL CHECK (unitPrice >= 0),
            unitCost DECIMAL(10,2) CHECK (unitCost >= 0),
            isTaxable BOOLEAN NOT NULL DEFAULT 1 CHECK (isTaxable IN (0, 1)),
            UNIQUE (purchaseID, productID)
        );''')

    # Cost at the time of sale, so a later cost change doesn't change old profit
    existing = {row[1] for row in cursor.execute("PRAGMA table_info(PurchaseItem)")}
    if "unitCost" not in existing:
        cursor.execute("ALTER TABLE PurchaseItem ADD COLUMN unitCost DECIMAL(10,2) CHECK (unitCost >= 0)")
    # Was tax charged on this line? Older lines count as taxed unless the purchase paid none
    if "isTaxable" not in existing:
        cursor.execute("ALTER TABLE PurchaseItem ADD COLUMN isTaxable BOOLEAN NOT NULL DEFAULT 1 CHECK (isTaxable IN (0, 1))")
        cursor.execute("UPDATE PurchaseItem SET isTaxable = 0 WHERE purchaseID IN (SELECT purchaseID FROM Purchase WHERE taxAmount = 0)")

    # One row per physical RFID-tagged unit (sold <=> linked to a receipt line)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ProductItem (
            epc VARCHAR(24) PRIMARY KEY CHECK (length(epc) <= 24),
            productID INTEGER NOT NULL REFERENCES Product(productID),
            receptionID INTEGER NOT NULL REFERENCES Reception(receptionID),
            status VARCHAR(10) NOT NULL DEFAULT 'in_stock'
                CHECK (status IN ('in_stock', 'sold', 'removed')),
            purchaseItemID INTEGER REFERENCES PurchaseItem(purchaseItemID),
            expiryDate DATE,
            CHECK ((status = 'sold') = (purchaseItemID IS NOT NULL))
        );''')

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reception_product ON Reception(productID)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_product_status ON ProductItem(productID, status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_purchaseitem ON ProductItem(purchaseItemID)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_purchase_customer ON Purchase(customerID)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_purchaseitem_product ON PurchaseItem(productID)")

    # Stock in hand = number of unsold tags, for the inventory dashboard
    cursor.execute('''
        DROP VIEW IF EXISTS ProductStock;''')
    cursor.execute('''
        CREATE VIEW ProductStock AS
        SELECT p.productID,
               p.productName,
               c.categoryName,
               p.price,
               COUNT(i.epc) AS totalTagged,
               COALESCE(SUM(i.status = 'in_stock'), 0) AS inStock,
               COALESCE(SUM(i.status = 'sold'), 0) AS totalSold,
               p.lowStockThreshold,
               COALESCE(SUM(i.status = 'in_stock'), 0) <= p.lowStockThreshold AS lowStock,
               (SELECT MAX(r.dateReceived) FROM Reception r
                 WHERE r.productID = p.productID) AS lastReceived
        FROM Product p
        JOIN Category c ON c.categoryID = p.categoryID
        LEFT JOIN ProductItem i ON i.productID = p.productID
        WHERE p.isActive = 1
        GROUP BY p.productID;''')
 
    cursor.execute("SELECT COUNT(*) FROM Fridge")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO Fridge (fridgeName, temp_threshold)
            VALUES ('Fridge 1', 5.0), ('Fridge 2', 5.0);
        ''')

    # The fridge the MSP01 sensor is in, if it isn't there yet
    cursor.execute("SELECT COUNT(*) FROM Fridge WHERE fridgeID = ?", (MSP01_FRIDGE_ID,))
    if MSP01_ENABLED and cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO Fridge (fridgeID, fridgeName, temp_threshold) VALUES (?, ?, 5.0)",
            (MSP01_FRIDGE_ID, f"Fridge {MSP01_FRIDGE_ID}"),
        )
    conn.commit()
    conn.close()
    print("SQLite db initialized successfully:", DB_PATH)

if __name__ == "__main__":
    main()
