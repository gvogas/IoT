// Keeps the Inventory page up to date. Every 2 seconds it asks /api/inventory for the stock numbers
// and changes the cards and the table, so a sale at the checkout shows up without reloading

const liveStatus = document.getElementById("live-status");

// The badge for each status, the same as in products/inventory.html
const BADGES = {
    out: ["text-bg-danger", "Out of stock"],
    low: ["text-bg-warning", "Low stock"],
    ok: ["text-bg-success", "In stock"],
    hidden: ["text-bg-secondary", "Hidden"]
};
// For sorting the Status column: out first, hidden last
const STATUS_ORDER = { out: 0, low: 1, ok: 2, hidden: 3 };

// Change one product's row
function updateRow(row, product) {
    row.querySelector("[data-in-stock]").textContent = product.inStock;
    row.querySelector("[data-in-stock]").closest("td").dataset.sortValue = product.inStock;
    row.querySelector("[data-sold]").textContent = product.totalSold;
    row.querySelector("[data-last-received]").textContent = product.lastReceived || "Never";

    // The bar under the number. It is full at twice the alert level
    const meter = row.querySelector("[data-meter]");
    if (meter) {
        meter.className = `stock-meter ${product.status}`;
        meter.firstElementChild.style.width = `${Math.min(product.inStock * 100 / Number(meter.dataset.full), 100)}%`;
    }

    const cell = row.querySelector("[data-status-cell]");
    const [badgeClass, badgeText] = BADGES[product.status];
    const badge = document.createElement("span");
    badge.className = `badge ${badgeClass}`;
    badge.textContent = badgeText;
    cell.replaceChildren(badge);
    cell.dataset.sortValue = STATUS_ORDER[product.status];
    row.dataset.status = product.status;
}

// The numbers on the In stock / Low / Out buttons
function updateFilterCounts() {
    const rows = [...document.querySelectorAll("[data-product-id]")];
    document.querySelectorAll("[data-status-filter]").forEach((chip) => {
        const value = chip.dataset.statusFilter;
        const number = chip.querySelector(".chip-count");
        if (number) number.textContent = value === "all" ? rows.length : rows.filter((row) => row.dataset.status === value).length;
    });
    // Run the search again, so a product that just ran out leaves the "In stock" list
    const searchBox = document.querySelector("[data-search]");
    if (searchBox) searchBox.dispatchEvent(new Event("input"));
}

// A card number, red when it is more than 0
function setCard(id, value, redWhenAbove0) {
    const element = document.getElementById(id);
    if (!element) return;
    element.textContent = value;
    if (redWhenAbove0) element.classList.toggle("alert-value", value > 0);
}

async function updateInventory() {
    try {
        const response = await fetch("/api/inventory", { cache: "no-store" });
        if (response.status === 403) {
            liveStatus.textContent = "Signed out. Sign in again to see live numbers.";
            return;
        }
        const data = await response.json();

        for (const product of data.products) {
            const row = document.querySelector(`[data-product-id="${product.productID}"]`);
            if (row) updateRow(row, product);
        }
        setCard("units", data.units, false);
        setCard("value", `$${data.value.toFixed(2)}`, false);
        setCard("low", data.low, true);
        setCard("out", data.out, true);
        setCard("last", data.last || "None yet", false);
        updateFilterCounts();

        liveStatus.textContent = `Last checked ${new Date().toLocaleTimeString()}.`;
    } catch (error) {
        liveStatus.textContent = "Cannot reach the server.";
    }
}

setInterval(updateInventory, 2000);
