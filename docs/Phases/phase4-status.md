# Phase 4 status

Checked against `Phase-4.pdf` on 2026-11-13. Found by reading the code, not by running the app. Tick a box when the item is finished and tested.

**Progress:** 23 of 42 items done. The biggest gaps are the Customer Activity report and the customer-side reports (period filter, item search, price history).

## 1. System Integration
- [x] Phase 2 (product tracking and inventory) working. See `phase3-status.md`
- [x] Phase 3 (sales, purchasing, customers) working. See `phase3-status.md`
- [ ] Full run-through of one demo workflow (receive stock, checkout, receipt, reports, MSP01) on the Pi, with the hardware plugged in

## 2.1 Inventory Report (Admin)
- [x] Product name and product ID (ID column, also in the CSV and the search box)
- [x] Available quantity for each product (`/inventory`, In stock column)
- [x] Last restocked date (Last received column)
- [x] Colour-coded levels (red = out, yellow = low, green = ok badges)
- [x] Low stock alert, customizable (per product, `lowStockThreshold`, plus the admin emails). The PDF says per category; ours is per product, which is finer. Mention this in the demo
- [ ] Real-time updates after a purchase. Built: `static/js/products/inventory.js` asks `/api/inventory` every 5 s and updates the cards, stock, badges and filter counts. The API is tested; still to check in a browser with a real checkout

## 2.2 Sales Report (Admin)
`/reports` has Today, This month, Last month, All time, plus From and To date boxes (`?from=&to=`).
- [x] Sales chart per day (a month) or per month (all time)
- [x] Sales by category (table with share bars)
- [x] Pick a specific day (From only, To empty)
- [x] Pick a date range (From and To boxes, as well as the fixed buttons)
- [x] Sold quantity for every product in the period (Sold per product table, products with 0 included)
- [x] Most sold items by quantity (ties shown together, like "2 items: Smart Plug, Smart Camera")
- [x] Least sold items in the period (products that sold 0 count)
- [x] Total sales for the chosen day or range shown with the dates, like "Total sales (Feb 1, 2026 to Feb 28, 2026): $2,540.00 before tax" (with tax too)
- [ ] Category filter (show only one category's products). The Sold per product table has one; the cards, chart and Best products don't filter by category yet

## 2.3 Customer Activity Report (Admin)
Nothing for this yet. `/customers` lists customers and their spending, but has no date filter.
- [ ] Number of customers who bought something on a chosen day
- [ ] Number of customers who bought something in a date range
- [ ] New vs returning customers in the range (new = first purchase falls inside the range)
- [ ] Most crowded and least crowded day in the range (by number of purchases or customers)

## 3. Customer Reports (My Account)
### 3.1 Receipt history
- [x] List of receipts with date and time, items, prices and total (`/account`)
- [ ] Filter receipts by a day or a date range

### 3.2 Total purchase amount
- [x] Total spent (all time card)
- [ ] Total spent in the selected period
- [ ] Graph of spending over time (optional)

### 3.3 Search purchase history
The search box filters receipts by product name or date, but does not summarize the item.
- [ ] Choose an item and see how many times it was bought
- [ ] Date, time and price of each purchase of that item
- [ ] Price history chart ("inflation report") for that item

## 4. Extras (optional)
- [x] Notifications: toasts, low stock and restocked emails, receipt email, fridge temperature alert emails
- [x] Exportable report: inventory CSV (`/inventory.csv`)
- [x] Dashboard on `/admin`: today's profit (click it for today's report) and a live temperature card for each fridge
- [ ] Light and dark mode. No dark theme in `theme.css` yet
- [ ] Export the Sales or Customer Activity report (CSV, or a Print button with `window.print()` for PDF)
- [ ] Responsive check on phone width (carried over from Phase 3)

## 5. MSP01 BLE Sensor
- [x] Read the MSP01 over Bluetooth with reelyActive barnowl/advlib and publish to MQTT (`msp01/index.js`)
- [x] Light and motion cards and a motion-per-hour chart on Fridge 3's page (`/fridges/3`), updated every 2 seconds. Its temperature and humidity are on the same page and on the `/admin` fridge cards
- [x] Readings saved (`RoomReading`, `MotionEvent`) with 24 h min/max and motion per hour
- [x] MSP01 work committed, and the setup steps (`npm install`, `npm run privileges`) are in the README

## 5b. Audit fixes (13 November 2026)
From the IoT Store Audit. Fixed: R1, R2, R3, R6, R7, R12, S3, S10, S11, C2, C3, U1, U6, U8, U12.
- [x] One bad MQTT message can't stop the readings, and the site starts without the broker (warning on the fridge pages)
- [x] Fridge list read from the `Fridge` table; limits must be −30 to 30 °C; new databases start at 5 °C
- [x] Receipt email sent in the background
- [x] YES replies only count from `ALERT_TO`, to an alert sent in the last hour, while the fridge is still warm. The `fan/command` topic is gone
- [x] Broker login settings for the app, ESP32 and MSP01 bridge (Mosquitto setup in [fridges.md](fridges.md#putting-a-password-on-the-broker))
- [x] Pinned `requirements.txt`; logging to `logs/app.log`
- [x] Interface: fan on/off button, readable reward text, right-to-left numbers, skip link, show password, remove one item, report bar amounts


## 6. Final Demo
- [ ] Demo script: inventory, purchase, live sync, admin reports, customer reports, extras
- [ ] Be ready to explain design decisions, technologies and the database (`architecture.md`, `database.md`)

## Suggested order
1. ~~Commit the MSP01 work~~ (done)
2. ~~Sales report: date inputs (day or range), quantity per product, most and least sold~~ (done). Category filter for the whole page still open
3. Customer Activity report (new page or a tab on `/reports`)
4. My Account: period filter with total spent, item search with price history chart
5. Live inventory updates
6. Report export (CSV or Print)
7. Dark mode, phone width check
8. Demo run-through on the Pi
