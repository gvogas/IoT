// The "Email me this receipt" button on each purchase
document.querySelectorAll("[data-email-receipt]").forEach((button) => {
    const purchase = button.closest(".purchase");
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

    // Get the two date inputs from account.html
    const dateFrom = document.querySelector("[data-date-from]");
    const dateTo = document.querySelector("[data-date-to]");

    // Get all purchase receipts
    const purchaseRows = document.querySelectorAll(".purchase[data-search-row]");

    // Get the existing search bar and result counter
    const purchaseSearch = document.querySelector("[data-search]");
    const purchaseCount = document.querySelector("[data-count]");
    const emptyMessage = document.querySelector("[data-empty]");

    // Filter receipts whenever the search or dates change
    function filterPurchases() {
        let visibleCount = 0;

        purchaseRows.forEach((purchase) => {
            // Get the purchase date stored in the HTML
            const purchaseDate = purchase.dataset.purchaseDate || "";

            // Check whether the purchase matches the search bar
            const searchText = (purchaseSearch?.value || "").toLowerCase().trim();
            const matchesSearch = (purchase.dataset.search || "").includes(searchText);

            // Check whether the purchase is inside the selected date range
            const matchesFrom = !dateFrom?.value || purchaseDate >= dateFrom.value;
            const matchesTo = !dateTo?.value || purchaseDate <= dateTo.value;

            // Only show receipts matching all filters
            const matches = matchesSearch && matchesFrom && matchesTo;
            purchase.hidden = !matches;

            if (matches) visibleCount++;
        });

        // Update the number of matching receipts
        if (purchaseCount) {
            purchaseCount.textContent = `${visibleCount} purchases`;
        }

        // Display a message when nothing matches
        if (emptyMessage) {
            emptyMessage.hidden = visibleCount !== 0;
        }
    }

    // Run the filter when a date is selected
    dateFrom?.addEventListener("change", filterPurchases);
    dateTo?.addEventListener("change", filterPurchases);

    // Keep the existing search bar working with the date filters
    purchaseSearch?.addEventListener("input", filterPurchases);

// Get the Total Spent card
const totalSpentDisplay = document.querySelector("[data-total-spent]");

// Calculate spending using the receipt dates and totals
function updateTotalSpent() {
    let total = 0;

    purchaseRows.forEach((purchase) => {
        const purchaseDate = purchase.dataset.purchaseDate || "";
        const purchaseTotal = Number(purchase.dataset.purchaseTotal || 0);

        // Check if the purchase is within the selected dates
        const matchesFrom = !dateFrom?.value || purchaseDate >= dateFrom.value;
        const matchesTo = !dateTo?.value || purchaseDate <= dateTo.value;

        // Add the receipt total if the date matches
        if (matchesFrom && matchesTo) {
            total += purchaseTotal;
        }
    });

    // Display the calculated amount with two decimal places
    if (totalSpentDisplay) {
        totalSpentDisplay.textContent = `$${total.toFixed(2)}`;
    }
}

// Update spending when either date changes
dateFrom?.addEventListener("change", updateTotalSpent);
dateTo?.addEventListener("change", updateTotalSpent);

// Display the initial receipt count
filterPurchases();
updateTotalSpent();

// Get the summary elements from account.html
const productSummary = document.querySelector("#product-summary");
const searchedProduct = document.querySelector("#searched-product");
const productCount = document.querySelector("#product-purchase-count");
const productDetails = document.querySelector("#product-purchase-details");

// Get all purchased products from the receipts
const purchasedProducts = document.querySelectorAll(".purchase-line[data-product-name]");

// Show purchase history for the searched product
function updateProductSummary() {
    const search = purchaseSearch.value.trim().toLowerCase();

    // Hide the summary if the search is empty
    if (!search) {
        productSummary.hidden = true;
        return;
    }

    let matches = [];
    let totalQuantity = 0;

    purchasedProducts.forEach((product) => {
        // Check whether the product name matches the search
        if (product.dataset.productName.includes(search)) {
            matches.push(product);
            totalQuantity += Number(product.dataset.productQuantity);
        }
    });

    // Hide the summary if no products match
    if (matches.length === 0) {
        productSummary.hidden = true;
        return;
    }

    // Display the searched product
    searchedProduct.textContent = search;

    // Count the number of purchase instances
    productCount.textContent = matches.length;

    // Clear previous results
    productDetails.innerHTML = "";

    // Display the date, quantity and price of each purchase
    matches.forEach((product) => {
        const row = document.createElement("div");
        row.className = "d-flex justify-content-between border-bottom py-2";

        const date = document.createElement("span");
        date.textContent = product.dataset.productDate;

        const price = document.createElement("span");
        price.textContent = `${product.dataset.productQuantity} × $${product.dataset.productPrice}`;

        row.append(date, price);
        productDetails.appendChild(row);
    });
}

// Update the summary when the customer searches
purchaseSearch?.addEventListener("input", updateProductSummary);

// Run once when the page loads
if (purchaseSearch && productSummary) {
    updateProductSummary();
}