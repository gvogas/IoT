// The My Account page: the receipt filters, the totals, the spending chart and the product summary.
// Chart.js, the colours and dollars() come from static/js/charts.js

// The "Email me this receipt" button on each purchase
document.querySelectorAll("[data-email-receipt]").forEach((button) => {
    const label = button.querySelector("[data-email-label]");

    button.addEventListener("click", async () => {
        button.disabled = true;
        label.dataset.before = label.textContent;
        label.textContent = "Sending...";
        try {
            const { ok, data } = await postJson(`/api/receipts/${button.dataset.emailReceipt}/email`);
            showToast(ok ? data.success : data.error, ok ? "success" : "danger");
            label.textContent = ok ? "Email this receipt again" : label.dataset.before;
        } catch (error) {
            showToast("The email could not be sent. Please try again.", "danger");
            label.textContent = label.dataset.before;
        }
        button.disabled = false;
    });
});


// ---------- Filters and totals ----------

const searchBox = document.querySelector("[data-search]");
const dateFrom = document.querySelector("[data-date-from]");
const dateTo = document.querySelector("[data-date-to]");
const dateClear = document.querySelector("[data-date-clear]");
const purchaseCountText = document.querySelector("[data-count]");
const emptyMessage = document.querySelector("[data-empty]");

// The three cards at the top
const totalSpentCard = document.querySelector("[data-total-spent]");
const purchaseCountCard = document.querySelector("[data-purchase-count]");
const itemCountCard = document.querySelector("[data-item-count]");

// Every receipt. Each one has data-purchase-date like "2026-11-21"
const purchases = [...document.querySelectorAll(".purchase[data-search-row]")];

// Is this receipt inside the From and To days? An empty box means no limit
function inDateRange(purchase) {
    const day = purchase.dataset.purchaseDate;
    const afterFrom = !dateFrom.value || day >= dateFrom.value;
    const beforeTo = !dateTo.value || day <= dateTo.value;
    return afterFrom && beforeTo;
}

// Show the receipts that match the search and the dates, and update the cards for the chosen days
function filterPurchases() {
    const words = searchBox.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    let shown = 0;
    let total = 0;
    let receipts = 0;
    let items = 0;

    purchases.forEach((purchase) => {
        const inRange = inDateRange(purchase);
        const matchesSearch = words.every((word) => purchase.dataset.search.includes(word));
        purchase.hidden = !(inRange && matchesSearch);
        if (!purchase.hidden) shown++;

        // The cards count every receipt in the chosen days, whatever the search
        if (inRange) {
            total += Number(purchase.dataset.purchaseTotal);
            receipts++;
            items += Number(purchase.dataset.itemCount);
        }
    });

    purchaseCountText.textContent = shown === 1 ? "1 purchase" : `${shown} purchases`;
    emptyMessage.hidden = shown !== 0;
    totalSpentCard.textContent = dollars(total, true);
    purchaseCountCard.textContent = receipts;
    itemCountCard.textContent = items;
}


// ---------- Spending chart ----------

const spendingCanvas = document.getElementById("spending-chart");
let spendingChart = null;

// The money spent in the chosen days, per month. When every receipt is in the same month, per day instead
function drawSpendingChart() {
    // Oldest first. The receipts on the page are newest first
    const inRange = purchases.filter(inDateRange).reverse();
    const months = new Set(inRange.map((purchase) => purchase.dataset.purchaseDate.slice(0, 7)));
    const perDay = months.size <= 1;

    // Add up the totals for each month ("2026-11") or day ("2026-11-21")
    const totals = new Map();
    inRange.forEach((purchase) => {
        const key = perDay ? purchase.dataset.purchaseDate : purchase.dataset.purchaseDate.slice(0, 7);
        totals.set(key, (totals.get(key) || 0) + Number(purchase.dataset.purchaseTotal));
    });

    // "2026-11" -> "Nov 2026" and "2026-11-21" -> "Nov 21"
    const labels = [...totals.keys()].map((key) => {
        const date = new Date(key.length === 7 ? `${key}-01T00:00` : `${key}T00:00`);
        return perDay
            ? date.toLocaleDateString("en-US", { month: "short", day: "numeric" })
            : date.toLocaleDateString("en-US", { month: "short", year: "numeric" });
    });
    const amounts = [...totals.values()].map((amount) => Math.round(amount * 100) / 100);

    // Draw it again from scratch each time the dates change
    if (spendingChart) spendingChart.destroy();
    spendingChart = new Chart(spendingCanvas, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{ label: "Spent", data: amounts, backgroundColor: BLUE, borderRadius: 4, maxBarThickness: 56 }]
        },
        options: {
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: (item) => dollars(item.raw, true) } }
            },
            scales: {
                x: { grid: { display: false } },
                y: { beginAtZero: true, ticks: { callback: (value) => dollars(value, false) } }
            }
        }
    });
}


// ---------- Product summary and price history ----------

const productSummary = document.getElementById("product-summary");
const productChoices = document.getElementById("product-choices");
const choiceButtons = document.getElementById("product-choice-buttons");
const productDetails = document.getElementById("product-details");
const productName = document.getElementById("searched-product");
const productCount = document.getElementById("product-purchase-count");
const priceChange = document.getElementById("product-price-change");
const priceChartBox = document.getElementById("price-chart-box");
const purchaseList = document.getElementById("product-purchase-details");
const priceCanvas = document.getElementById("price-chart");
let priceChart = null;

// Every line of every receipt. Each one has data-product-name, -date, -day, -price and -quantity
const lines = [...document.querySelectorAll(".purchase-line[data-product-name]")];

// Show how often one product was bought, at what price, and how its price changed
function showProduct(name, productLines) {
    // Oldest first, for the chart and the price change
    const oldestFirst = [...productLines].reverse();
    const units = productLines.reduce((sum, line) => sum + Number(line.dataset.productQuantity), 0);

    productName.textContent = name;
    productCount.textContent = `Bought ${plural(productLines.length, "time")}, ${plural(units, "unit")} in all`;

    // How the price changed from the first purchase to the last
    const firstPrice = Number(oldestFirst[0].dataset.productPrice);
    const lastPrice = Number(oldestFirst[oldestFirst.length - 1].dataset.productPrice);
    if (productLines.length === 1) {
        priceChange.textContent = `Price paid: ${dollars(lastPrice, true)}`;
    } else if (firstPrice === lastPrice) {
        priceChange.textContent = `The price stayed at ${dollars(lastPrice, true)}`;
    } else {
        const percent = Math.round((lastPrice - firstPrice) * 100 / firstPrice);
        const sign = percent > 0 ? "+" : "";
        priceChange.textContent = `The price went from ${dollars(firstPrice, true)} to ${dollars(lastPrice, true)} (${sign}${percent}%)`;
    }

    // The price history chart. Only worth drawing with two purchases or more
    if (priceChart) priceChart.destroy();
    priceChart = null;
    priceChartBox.hidden = productLines.length < 2;
    if (productLines.length >= 2) {
        priceChart = new Chart(priceCanvas, {
            type: "line",
            data: {
                labels: oldestFirst.map((line) => line.dataset.productDay),
                datasets: [{
                    label: "Price",
                    data: oldestFirst.map((line) => Number(line.dataset.productPrice)),
                    borderColor: BLUE,
                    backgroundColor: BLUE,
                    // Steps, because a price stays the same until it changes
                    stepped: true
                }]
            },
            options: {
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: (item) => dollars(item.raw, true) } }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: { ticks: { callback: (value) => dollars(value, true) } }
                }
            }
        });
    }

    // One row for each purchase, newest first: the date and time, then quantity × price
    purchaseList.innerHTML = "";
    productLines.forEach((line) => {
        const row = document.createElement("div");
        row.className = "d-flex justify-content-between border-bottom py-2";

        const date = document.createElement("span");
        date.textContent = line.dataset.productDate;

        const price = document.createElement("span");
        price.className = "num";
        price.textContent = `${line.dataset.productQuantity} × ${dollars(Number(line.dataset.productPrice), true)}`;

        row.append(date, price);
        purchaseList.appendChild(row);
    });
}

// Show the summary for the product typed in the search box. Only the receipts in the chosen days count
function updateProductSummary() {
    const search = searchBox.value.trim().toLowerCase();
    const matching = lines.filter((line) =>
        search && line.dataset.productName.toLowerCase().includes(search) && inDateRange(line.closest(".purchase")));

    if (matching.length === 0) {
        productSummary.hidden = true;
        return;
    }
    productSummary.hidden = false;

    // The different products the search matches. A name typed in full only matches that product
    let names = [...new Set(matching.map((line) => line.dataset.productName))];
    const exact = names.find((name) => name.toLowerCase() === search);
    if (exact) names = [exact];

    if (names.length === 1) {
        productChoices.hidden = true;
        productDetails.hidden = false;
        showProduct(names[0], matching.filter((line) => line.dataset.productName === names[0]));
        return;
    }

    // More than one product: a button for each. Pressing one puts its full name in the search box
    productChoices.hidden = false;
    productDetails.hidden = true;
    choiceButtons.innerHTML = "";
    names.sort().forEach((name) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "btn btn-outline-secondary btn-sm";
        button.textContent = name;
        button.addEventListener("click", () => {
            searchBox.value = name;
            updateAll();
        });
        choiceButtons.appendChild(button);
    });
}


// ---------- Date boxes ----------

// The To day can never be before the From day. The calendars grey out the days you cannot pick,
// and a day typed by hand that breaks the rule empties the other box
function checkDates(changedBox) {
    if (dateFrom.value && dateTo.value && dateTo.value < dateFrom.value) {
        if (changedBox === dateFrom) dateTo.value = "";
        else dateFrom.value = "";
    }
    dateTo.min = dateFrom.value;
    dateFrom.max = dateTo.value;
    dateClear.hidden = !dateFrom.value && !dateTo.value;
    updateAll();
}

function clearDates() {
    dateFrom.value = "";
    dateTo.value = "";
    checkDates();
}


// ---------- Run everything ----------

function updateAll() {
    filterPurchases();
    drawSpendingChart();
    updateProductSummary();
}

// The page has no receipts (and no search box) for a customer who has not bought anything yet
if (searchBox) {
    searchBox.addEventListener("input", () => {
        filterPurchases();
        updateProductSummary();
    });
    dateFrom.addEventListener("change", () => checkDates(dateFrom));
    dateTo.addEventListener("change", () => checkDates(dateTo));
    dateClear.addEventListener("click", clearDates);
    // The browser can keep the dates when the page is reloaded, so check them once at the start
    checkDates();
}
