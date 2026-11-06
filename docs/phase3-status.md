# Phase 3 Status

Checked against `Phase-3.pdf` on 2026-11-06. Found by reading the code, not by running the app. Tick a box when the item is finished and tested.

**Progress:** 27 of 35 items done. Of the 8 open items, 2 are bonus (French, responsive) and 3 are "not checked yet" (UPC scanner field, optional membership, toast coverage).

## Product Management
- [x] Register a product (name, category, price, UPC, EPC, producer)
- [x] Edit a product
- [x] Delete a product
- [x] UPC max 13 characters, EPC max 24 characters (check the form validation)
- [x] Extra fields: image path, expiry date

## Inventory
- [x] Receive stock multiple times per product (quantity and date, `Reception` table)
- [x] Total quantity in stock shown
- [x] Inventory dashboard (`/inventory`) and CSV export

## Barcode and RFID
- [x] CF600 RFID reader over serial (`hardware/rfid.py`)
- [x] EPC read into the product and receive forms (`/rfid/scan`)
- [x] Barcode scan for membership card sign-in (`/api/scan-login`)
- [ ] UPC read by barcode scanner on the product form (check `product_form.html`)

## Self-Checkout
- [x] Scan all items at once with RFID (`/api/checkout/scan`)
- [x] Shopping list with items, tax and total
- [x] Remove unwanted items before paying (Remove button per product, plus Clear)
- [x] Payment simulation (`pay()`, tags marked as sold)
- [ ] Membership card step is optional (guest checkout is blocked now)
- [ ] **Points added to the customer's account** (`pay()` saves `pointsEarned = 0` and never updates `totalPoints`)
- [x] Receipt generated after payment (window with lines, tax, total, date; no points yet)
- [x] Receipt emailed to the customer (Send Email button, tested and working). Not automatic yet: the PDF says to send it on payment.

## Customer Accounts
- [x] Create an account
- [x] Name, email, auto-generated membership number, total points
- [x] Sign in
- [x] Purchase history (list of past receipts)
- [ ] Purchase history shows points earned per receipt

## Receipt Contents
- [x] Product list (name, quantity, price)
- [x] Total amount
- [ ] Points earned
- [x] Date and time

## Database
- [x] Schema with relations (Product, Reception, Customer, Purchase, PurchaseItem, ProductItem)
- [x] ER diagram (`docs/database.md`)

## Notifications and UI
- [x] Toast notifications exist (`static/js/toast.js`)
- [ ] Toast shown after every action (add, edit, delete, receive, checkout). Not checked.
- [ ] Bilingual English/French interface (bonus)
- [ ] Responsive UI check on phone width (bonus)

## Suggested order
1. Points formula, saved inside `pay()`
2. Receipt page with points earned
3. Email the receipt
4. Remove-item and optional-membership checks
5. Notification check, then French, then responsive
