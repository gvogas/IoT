# Phase 3 Status

Checked against `Phase-3.pdf` on 2026-11-06. Found by reading the code, not by running the app. Tick a box when the item is finished and tested.

**Progress:** 31 of 36 items done. Of the 5 open items, 2 are bonus (French, responsive) and 3 are still to be checked or implemented.

## Product Management
- [x] Register a product (name, category, price, UPC, EPC, producer)
- [x] Edit a product
- [x] Delete a product
- [x] UPC max 13 characters, EPC max 24 characters (check the form validation)
- [x] Extra field: product image (`models/product_image.py`)
- [ ] Extra field: expiry date (the column exists, but no form or page uses it)

## Inventory
- [x] Receive stock multiple times per product (quantity and date, `Reception` table)
- [x] Total quantity in stock shown
- [x] Inventory dashboard (`/inventory`) and CSV export

Extra, not in the PDF: admins are emailed when a product becomes low or out of stock, and when a low or out of stock product is restocked (`templates/email/stock_alert.html`, `restocked.html`).
## Barcode and RFID
- [x] CF600 RFID reader over serial (`hardware/rfid.py`)
- [x] EPC read into the receive form (`/rfid/scan`)
- [x] Barcode scan for membership card sign-in (`/api/scan-login`)
- [ ] UPC read by barcode scanner on the product form (the form takes a scanned UPC without submitting early. Not tested with the real scanner yet)

## Self-Checkout
- [x] Scan all items at once with RFID (`/api/checkout/scan`)
- [x] Shopping list with items, tax and total
- [x] Remove unwanted items before paying (Remove button per product, plus Clear)
- [x] Payment simulation (`pay()`, tags marked as sold)
- [ ] Membership card step is optional (guest checkout is blocked now)
- [x] Points added to the customer's account (10 points for every complete $5 spent before tax; balance updated in the sale transaction)
- [x] Receipt generated after payment (window with lines, tax, total, date and points earned)
- [x] Receipt emailed automatically after payment when the customer has an email address; Send Email button remains available for retry and from purchase history.

## Customer Accounts
- [x] Create an account
- [x] Name, email, auto-generated membership number, total points
- [x] Sign in
- [x] Purchase history (list of past receipts)
- [x] Purchase history shows points earned per receipt

Extra, not in the PDF: customers can change their own email on My Account (`/account/email`).

## Receipt Contents
- [x] Product list (name, quantity, price)
- [x] Total amount
- [x] Points earned
- [x] Date and time

## Database
- [x] Schema with relations (Product, Reception, Customer, Purchase, PurchaseItem, ProductItem)
- [x] ER diagram (`docs/database.md`)

## Notifications and UI
- [x] Toast notifications exist (`static/js/common.js`)
- [ ] Toast shown after every action (add, edit, delete, receive, checkout). Not checked.
- [ ] Bilingual English/French interface (bonus)
- [ ] Responsive UI check on phone width (bonus)

## Suggested order
1. Points formula, saved inside `pay()`
2. Points earned on the receipt and in the purchase history
3. Send the receipt email automatically on payment
4. Make the membership card step optional
5. Expiry date on the product form
6. Test the UPC field with the real barcode scanner
7. Notification check, then French, then responsive
