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
