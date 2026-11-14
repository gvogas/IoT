# Phase 4 status

Checked against `Phase-4.pdf` on 2026-11-13. Found by reading the code, not by running the app. Tick a box when the item is finished and tested.

**Progress:** 16 of 41 items done. The biggest gaps are the Customer Activity report, date-range filters on the Sales report, and the customer-side reports (period filter, item search, price history).

## 1. System Integration
- [x] Phase 2 (product tracking and inventory) working. See `phase3-status.md`
- [x] Phase 3 (sales, purchasing, customers) working. See `phase3-status.md`
- [ ] Full run-through of one demo workflow (receive stock, checkout, receipt, reports, MSP01) on the Pi, with the hardware plugged in

## 2.1 Inventory Report (Admin)
- [x] Available quantity for each product (`/inventory`, In stock column)
- [x] Last restocked date (Last received column)
- [x] Colour-coded levels (red = out, yellow = low, green = ok badges)
- [x] Low stock alert, customizable (per product, `lowStockThreshold`, plus the admin emails). The PDF says per category; ours is per product, which is finer. Mention this in the demo
- [ ] Real-time updates after a purchase. The page only changes when you reload it. Add a `setInterval` that fetches the stock numbers, like `fridges/dashboard.js` does

## 2.2 Sales Report (Admin)
`/reports` has fixed periods only: Today, This month, Last month, All time.
- [x] Sales chart per day (a month) or per month (all time)
- [x] Sales by category (table with share bars)
- [ ] Pick a specific day (date input)
- [ ] Pick a date range (from and to date inputs instead of, or as well as, the fixed buttons)
- [ ] Sold quantity for every product in the period. The Best products table only shows the top 8, sorted by profit
- [ ] Most sold items by quantity (ties shown together, like "2 items: Smart Plug, Smart Camera")
- [ ] Least sold items in the period (include products that sold 0?)
- [ ] Total sales for the chosen day or range shown with the dates, like "Total Sales (Feb 1 to Feb 28): $2,540.00". The Sales card has the number but not a custom range
- [ ] Category filter (show only one category's products)

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
- [x] Dashboard widgets on `/admin` (today's numbers, last 7 days, stock problems, fridges, MSP01)
- [ ] Light and dark mode. No dark theme in `theme.css` yet
- [ ] Export the Sales or Customer Activity report (CSV, or a Print button with `window.print()` for PDF)
- [ ] Responsive check on phone width (carried over from Phase 3)

## 5. MSP01 BLE Sensor
Not committed yet (`hardware/msp01.py`, `msp01/`, `models/room.py`, `routes/room_routes.py`, `static/js/admin/room.js` are new files).
- [x] Read the MSP01 over Bluetooth with reelyActive barnowl/advlib and publish to MQTT (`msp01/index.js`)
- [x] Temperature, humidity, light and motion widgets on `/admin`, updated every 5 seconds
- [x] Readings saved (`RoomReading`, `MotionEvent`) with 24 h min/max and motion per hour
- [ ] Commit the MSP01 work and add the setup steps (`npm install`, `npm run privileges`) to the README if they are not there yet

## 5b. Audit fixes (13 November 2026)
From the IoT Store Audit. Fixed: R1, R2, R3, R6, R7, R12, S3, S10, S11, C2, C3, U1, U6, U8, U12.
- [x] One bad MQTT message can't stop the readings, and the site starts without the broker (warning on the fridge pages)
- [x] Fridge list read from the `Fridge` table; limits must be −30 to 30 °C; new databases start at 5 °C
- [x] Receipt email sent in the background
- [x] YES replies only count from `ALERT_TO`, to an alert sent in the last hour, while the fridge is still warm. The `fan/command` topic is gone
- [x] Broker login settings for the app, ESP32 and MSP01 bridge (Mosquitto setup in [fridges.md](fridges.md#putting-a-password-on-the-broker))
- [x] Pinned `requirements.txt`; logging to `logs/app.log`
- [x] Interface: fan on/off button, readable reward text, right-to-left numbers, skip link, show password, remove one item, report bar amounts
- [ ] Still open from the audit: S1 (debug mode), S2 (card number opens admin), S4 (CSRF), S5 (password guesses), R4, R5, and the rest

## 6. Final Demo
- [ ] Demo script: inventory, purchase, live sync, admin reports, customer reports, extras
- [ ] Be ready to explain design decisions, technologies and the database (`architecture.md`, `database.md`)

## Suggested order
1. Commit the MSP01 work
2. Sales report: date inputs (day or range), quantity per product, most and least sold, category filter
3. Customer Activity report (new page or a tab on `/reports`)
4. My Account: period filter with total spent, item search with price history chart
5. Live inventory updates
6. Report export (CSV or Print)
7. Dark mode, phone width check
8. Demo run-through on the Pi
