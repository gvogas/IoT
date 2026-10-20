const form = document.getElementById("customer-form");
const message = document.getElementById("message");

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    message.textContent = "";
    message.style.color = "";

    try {
        const response = await fetch(form.action, {
            method: "POST",
            body: new FormData(form)
        });
        const result = await response.json();

        message.textContent = result.error || result.success;
        message.style.color = result.error ? "red" : "green";

        if (response.ok) {
            form.reset();
        }
    } catch (error) {
        message.textContent = "Unable to submit the form. Please try again.";
        message.style.color = "red";
    }
});
