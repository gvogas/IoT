# Dashboard and reports

Two admin pages show how the store is doing: the dashboard (`/admin`) for today, and Reports (`/reports`) for a longer period. The queries behind them are explained in [database.md](database.md#sales-and-profit).

## Contents
1. [The dashboard](#the-dashboard)
2. [Reports](#reports)
3. [How Reports is built](#how-reports-is-built)
4. [Where the code is](#where-the-code-is)

## The dashboard

Admins land on the dashboard when they sign in. It is about today:

| Part | Shows |
|---|---|
| Today's numbers | Sales, orders, average order and profit so far today. Under each one is how much it went up or down since yesterday at the same time of day, or "No sales yesterday to compare with" |
| Needs attention | One line per problem, most urgent first, each with a button that goes to the fix. When the list is empty it says everything is caught up |
| Latest orders | The latest 6 orders |
| Last 7 days | A bar for each day (today's is dark) with its amount, and the 4 best sellers of those 7 days |
| Fridge 3 (MSP01) | Temperature, humidity, light and motion cards. See [msp01.md](msp01.md#dashboard-widgets) |

### Needs attention order

1. Fridges with a problem
2. Out of stock products
3. Products priced below their cost
4. Low stock products
5. Products with no cost yet

A fridge that is over its threshold gets a red banner at the top of the page (with whether the alert email went out), and is not repeated in the list. A fridge shows up in the list when its sensor hasn't sent anything for 15 seconds, or when there has been no reading at all. The 15 seconds match `static/js/fridges/common.js`. With `FRIDGES_ENABLED` on, the page reloads every 30 seconds so a new problem appears by itself. With it off, no fridge lines are shown.

## Reports

Reports has buttons for Today, This month, Last month and All time, with All time as the default. Under them are From and To date boxes for any days you want (both days included). Leave To empty to see a single day. For the chosen period it shows:

| Part | Shows |
|---|---|
| Total sales line | The dates and the total, like "Total sales (Feb 1, 2026 to Feb 28, 2026): $2,540.00 before tax · $2,920.37 with tax" |
| Sales | Before tax (GST and QST go to the government), and the number of orders |
| Net profit | With the margin and the cost of the items sold |
| Average order | With the items per order |
| Tax owed | Split into GST and QST |
| Sales chart | Sales per day for a month or a range of up to 62 days, or per month for all time or a longer range. Today or a single day has no chart |
| Sold per product | Every product with the units sold and the sales, most sold first. Products still for sale that sold nothing are listed with 0. It has search, a category filter and sortable columns |
| Most and least sold | Above that table. Ties are all shown, like "2 items: Smart Plug, Smart Camera, 5 sold each". The least sold counts products that sold 0 |
| Best products | The 8 products that made the most profit, with the best seller's picture at the top. Each one's profit counts only its units with a cost |
| By category | Sales per category, with each category's share |

Each number except tax is compared with the period before:

| Period | Compared with |
|---|---|
| Today | Yesterday, up to the same time |
| This month | Last month, up to the same day |
| Last month | The month before |
| All time | Nothing to compare with |
| From and To | The same number of days just before, like the 28 days before Feb 1 to Feb 28 |

## How Reports is built

```mermaid
flowchart TD
    Button["Period button<br/>?period=month"] --> Dates["period_dates() or range_dates()<br/>start, end, and the period before"]
    Range["From and To boxes<br/>?from=...&to=..."] --> Dates
    Dates --> Now["profit_summary()<br/>for this period"]
    Dates --> Before["profit_summary()<br/>for the period before"]
    Now & Before --> Change["percent_change()<br/>up or down, in %"]
    Dates --> Chart["sales_chart()"]
    Dates --> Top["top_products()"]
    Dates --> Cat["sales_by_category()"]
    Dates --> Qty["product_quantities()<br/>most_and_least_sold()"]
    Now & Change & Chart & Top & Cat & Qty --> Page["admin/reports.html"]
```

## Where the code is

| Function | File | What it does |
|---|---|---|
| `period_dates()` | `models/checkout.py` | Turns a period into a start and end date, plus the dates of the period to compare with |
| `range_dates()` | `models/checkout.py` | The same for the From and To boxes. Gives back None for a bad date |
| `range_text()` | `routes/admin_routes.py` | The dates for the total sales line, like "Feb 1, 2026 to Feb 28, 2026" |
| `product_quantities()` | `models/checkout.py` | Units sold and sales for every product in the period, including 0 |
| `most_and_least_sold()` | `models/checkout.py` | The most and least sold products, with ties |
| `chart_by_month()` | `models/checkout.py` | Whether the chart has a bar per month or per day |
| `profit_summary()` | `models/checkout.py` | Sales, cost, profit, margin, tax and orders for a period |
| `top_products()` | `models/checkout.py` | Best products by profit |
| `sales_chart()`, `daily_sales()` | `models/checkout.py` | The bars of the charts |
| `sales_by_category()` | `models/checkout.py` | Sales per category |
| `recent_purchases()` | `models/checkout.py` | Latest orders for the dashboard |
| `products_below_cost()`, `products_without_cost()` | `models/product.py` | The pricing problems for Needs attention |
| `percent_change()` | `routes/admin_routes.py` | Up or down, in % |
| `money` filter | `routes/formats.py` | Shows amounts like `$1,314.50` or `-$16.00` |
