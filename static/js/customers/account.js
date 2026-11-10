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
