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

    // Display the initial receipt count
    filterPurchases();
