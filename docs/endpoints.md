# Pages and API endpoints

Every URL the app answers, grouped by area. "API" rows send back JSON and are called by the JavaScript in `static/js/`. Admin-only routes are guarded by `@admin_page` or `@admin_api` (see [accounts.md](accounts.md#sessions-and-admin-pages)).

## Checkout
| URL | Who can open it | File | What it does |
|---|---|---|---|
| `/` | everyone | routes/checkout_routes.py | The checkout: basket, summary and paying |
| `/api/checkout/scan` (POST) | everyone | routes/checkout_routes.py | Asks the RFID reader what is in the basket |
| `/api/checkout/pay` (POST) | signed in | routes/checkout_routes.py | Saves the receipt and marks the tags as sold |
| `/api/checkout/receipt-email` (POST) | after paying | routes/checkout_routes.py | Emails the receipt that was just paid |
| `/api/receipts/<id>/email` (POST) | signed in, own receipts | routes/checkout_routes.py | Emails a past receipt from the purchase history |
| `/api/scan-login` (POST) | everyone | routes/checkout_routes.py | Signs in with the barcode on a membership card |

## Accounts
| URL | Who can open it | File | What it does |
|---|---|---|---|
| `/signin`, `/signout` | everyone | routes/auth_routes.py | Checks email + password, stores `id`, `name`, `role` in the session cookie |
| `/signup` | everyone | routes/customer_routes.py | Sign up form (auth/signup.js sends it to `/submit`) |
| `/submit` (POST) | everyone | routes/customer_routes.py | Validates and saves a new customer, then signs them in |
| `/account` | signed in | routes/customer_routes.py | The customer's own details, membership number and purchases |
| `/account/email` (POST) | signed in | routes/customer_routes.py | Changes the customer's own email, after checking their password |
| `/customers` | admin | routes/customer_routes.py | List of every customer |
| `/api/customers/<id>/role` (POST) | admin | routes/customer_routes.py | Change someone's role (not your own) |
| `/api/customers/<id>/membership` (POST) | admin | routes/customer_routes.py | Change someone's membership number |

## Dashboard and Reports
| URL | Who can open it | File | What it does |
|---|---|---|---|
| `/admin` | admin | routes/admin_routes.py | The dashboard: today against yesterday, what needs attention, latest orders and the last 7 days |
| `/reports?period=today\|month\|last_month\|all` | admin | routes/admin_routes.py | Sales, profit, tax, a sales chart, units sold per product (with the most and least sold), the best products and sales per category for the period (all time if left out) |
| `/reports?from=YYYY-MM-DD&to=YYYY-MM-DD` | admin | routes/admin_routes.py | The same report for any days, both included. Leave `to` out for a single day |

## Products and stock
| URL | Who can open it | File | What it does |
|---|---|---|---|
| `/inventory`, `/inventory.csv` | admin | routes/product_routes.py | Stock of every product, EPC search and the CSV download |
| `/api/inventory` | admin | routes/product_routes.py | Stock numbers of every product and the totals for the cards (asked every 5 s by the Inventory page) |
| `/products/new` | admin | routes/product_routes.py | The form to add a product ("Save and add another" comes back to an empty form) |
| `/products/<id>` | admin | routes/product_routes.py | One product: stock, receiving, deliveries and units |
| `/products/<id>/edit`, `/delete`, `/receive`, `/clear-epcs` | admin | routes/product_routes.py | Change a product or its stock |
| `/products/upc-check` | admin | routes/product_routes.py | Says if another product already has a UPC, for the product form |
| `/rfid/scan` (POST) | admin | routes/product_routes.py | Asks the RFID reader for tags, for the receive form |

## Fridges and sensors
| URL | Who can open it | File | What it does |
|---|---|---|---|
| `/fridges` | admin | routes/fridge_routes.py | Dashboard with every fridge |
| `/fridges/<id>` | admin | routes/fridge_routes.py | One fridge: gauges, stats, history chart, threshold form |
| `/api/fridges` | admin | routes/fridge_routes.py | Live data for all fridges (asked every 2 s) |
| `/api/fridges/<id>` | admin | routes/fridge_routes.py | Live data for one fridge (asked every 2 s) |
| `/api/fridges/<id>/history?hours=1\|24\|168` | admin | routes/fridge_routes.py | Saved readings for the chart (asked every 60 s) |
| `/api/fridges/<id>/threshold` (POST) | admin | routes/fridge_routes.py | Change the fridge's temperature threshold |
| `/api/fan` | admin | routes/fan_routes.py | The fan's state, ON or OFF, and `broker`: whether the app can reach the MQTT broker (asked every 2 s) |
| `/api/fan/on` (POST) | admin | routes/fan_routes.py | Turn the fan on |
| `/api/fan/off` (POST) | admin | routes/fan_routes.py | Turn the fan off |
| `/api/room` | admin | routes/room_routes.py | The MSP01's live readings and stats (asked every 5 s). See [msp01.md](msp01.md#api) |

## Errors

`routes/__init__.py` adds every blueprint to the app, along with the template filters from `routes/formats.py` (`nice_date`, `nice_datetime` and `money`), and handles the errors they share:

| Error | Page | API (`/api/...`, `/rfid/...`) |
|---|---|---|
| Database error | Error page, 500 | JSON `error`, 500 |
| Image upload too big | Flash message, back to the form | Not used |
| RFID reader unplugged or not answering | Not used | JSON `error`, 503 |
