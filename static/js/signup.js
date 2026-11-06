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
            // Signed in already: go to the home page
            window.location.href = result.redirect || "/";
        }
    } catch (error) {
        message.textContent = "Unable to submit the form. Please try again.";
        message.style.color = "red";
    }
});

// Format the phone number as it is typed: (514) 555-1234. A number starting with + is kept as international.
const phone = document.getElementById("number_input");

phone.addEventListener("input", () => {
    const text = phone.value;
    if (text.trim().startsWith("+")) {
        phone.value = "+" + text.replace(/\D/g, "").slice(0, 15);
        return;
    }
    const d = text.replace(/\D/g, "").slice(0, 10);
    let out = d;
    if (d.length > 6) out = `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}`;
    else if (d.length > 3) out = `(${d.slice(0, 3)}) ${d.slice(3)}`;
    else if (d.length > 0) out = `(${d}`;
    phone.value = out;
});

// A barcode scanner types the number and then presses Enter. Don't let that Enter send the form
document.getElementById("barcode_input").addEventListener("keydown", (event) => {
    if (event.key === "Enter") event.preventDefault();
});
