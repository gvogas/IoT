const message = document.getElementById("message");

// Make admin / Make customer buttons
document.querySelectorAll(".role-button").forEach((button) => {
    button.addEventListener("click", async () => {
        const name = button.dataset.name;
        const role = button.dataset.role;
        if (role === "admin" && !confirm(`Make ${name} an admin? They will be able to see every customer and control the fridges.`)) {
            return;
        }

        button.disabled = true;
        message.textContent = "";
        try {
            const body = new FormData();
            body.append("role", role);
            const response = await fetch(`/api/customers/${button.dataset.id}/role`, { method: "POST", body });
            const result = await response.json();

            message.textContent = result.error || result.success;
            message.style.color = result.error ? "red" : "green";

            if (response.ok) {
                // Show the new role and change the button
                const cell = button.closest("tr").querySelector(".role");
                cell.textContent = result.role;
                cell.className = `role ${result.role}`;
                button.dataset.role = result.role === "admin" ? "customer" : "admin";
                button.textContent = result.role === "admin" ? "Make customer" : "Make admin";
            }
        } catch (error) {
            message.textContent = "Unable to reach the server. The role was not changed.";
            message.style.color = "red";
        } finally {
            button.disabled = false;
        }
    });
});


// Edit a membership number: type it or scan the customer's barcode, then press Enter or Save.
// Leaving it empty gives the customer a new generated number
document.querySelectorAll(".membership").forEach((cell) => {
    const numberText = cell.querySelector(".membership-number");
    const editButton = cell.querySelector(".membership-edit");

    editButton.addEventListener("click", () => {
        const form = document.createElement("form");
        form.style.display = "flex";
        form.style.gap = "6px";

        const input = document.createElement("input");
        input.type = "text";
        input.maxLength = 32;
        input.autocomplete = "off";
        input.placeholder = "Scan a barcode, or leave empty for a new number";
        input.style.minWidth = "260px";

        const save = document.createElement("button");
        save.type = "submit";
        save.className = "small";
        save.textContent = "Save";

        const cancel = document.createElement("button");
        cancel.type = "button";
        cancel.className = "small";
        cancel.textContent = "Cancel";

        form.append(input, save, cancel);
        numberText.hidden = true;
        editButton.hidden = true;
        cell.appendChild(form);
        input.focus();

        function close() {
            form.remove();
            numberText.hidden = false;
            editButton.hidden = false;
        }

        cancel.addEventListener("click", close);

        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            save.disabled = true;
            message.textContent = "";
            try {
                const body = new FormData();
                body.append("membershipNumber", input.value);
                const response = await fetch(`/api/customers/${cell.dataset.id}/membership`, { method: "POST", body });
                const result = await response.json();

                message.textContent = result.error || result.success;
                message.style.color = result.error ? "red" : "green";

                if (response.ok) {
                    numberText.textContent = result.membershipNumber;
                    close();
                    return;
                }
            } catch (error) {
                message.textContent = "Unable to reach the server. The membership number was not changed.";
                message.style.color = "red";
            }
            save.disabled = false;
        });
    });
});
