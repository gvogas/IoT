# Phase 3 Status

Checked against `Phase-3.pdf` on 2026-11-09. Found by reading the code, not by running the app. Tick a box when the item is finished and tested.

**Progress:** 33 of 35 items done. The 2 open items are both bonus (French, responsive).

## Product Management
- [x] Register a product (name, category, price, UPC, EPC, producer)
- [x] Edit a product
- [x] Delete a product
- [x] UPC max 13 characters, EPC max 24 characters (check the form validation)
- [x] Extra field: product image (`models/product_image.py`)

## Inventory
- [x] Receive stock multiple times per product (quantity and date, `Reception` table)
- [x] Total quantity in stock shown
- [x] Inventory dashboard (`/inventory`) and CSV export

Extra, not in the PDF: admins are emailed when a product becomes low or out of stock, and when a low or out of stock product is restocked (`templates/email/stock_alert.html`, `restocked.html`).
## Barcode and RFID
- [x] CF600 RFID reader over serial (`hardware/rfid.py`)
- [x] EPC read into the receive form (`/rfid/scan`)
- [x] Barcode scan for membership card sign-in (`/api/scan-login`)
- [x] UPC read by barcode scanner on the product form 

## Self-Checkout
- [x] Scan all items at once with RFID (`/api/checkout/scan`)
- [x] Shopping list with items, tax and total
- [x] Remove unwanted items before paying (Remove button per product, plus Clear)
- [x] Payment simulation (`pay()`, tags marked as sold)
- [x] Membership card step
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
- [x] Toast shown after every action. Server actions use `flash()` (product add, edit, delete, receive, clear, sign-up, email change). Button actions on the pages use `showToast()` in `common.js` (checkout remove, clear and pay, receipt email, fridge limit, fan off). Not toasts on purpose: form errors next to the field, and the reader status line, which repeats
- [ ] Bilingual English/French interface (bonus). Not started: no translation code, and every template is `lang="en"`
- [ ] Responsive UI check on phone width (bonus). The viewport tag and some phone-width CSS rules exist (`components.css`), but no page has been checked at phone width

## Suggested order
1. Responsive check on phone width, then French