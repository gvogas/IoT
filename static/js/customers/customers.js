// The windows for changing a membership number or a role.
// After a change the page reloads, and the server's notification says what happened

async function postForm(url, field, value) {
    const body = new FormData();
    body.append(field, value);
    const response = await fetch(url, { method: "POST", body });
    return { ok: response.ok, result: await response.json() };
}

// -------------------------
// Membership number
// -------------------------
const membershipElement = document.getElementById("membership-modal");
const membershipModal = new bootstrap.Modal(membershipElement);
const membershipForm = document.getElementById("membership-form");
const membershipInput = document.getElementById("membership-input");
const membershipMessage = document.getElementById("membership-message");
const membershipSave = document.getElementById("membership-save");
let membershipCustomer = null;

function updateSaveLabel() {
    membershipSave.textContent = membershipInput.value.trim() ? "Save number" : "Generate new number";
}

document.querySelectorAll("[data-edit-membership]").forEach((button) => {
    button.addEventListener("click", () => {
        membershipCustomer = button.dataset.id;
        membershipElement.querySelector("[data-customer-name]").textContent = button.dataset.name;
        membershipElement.querySelector("[data-current-number]").textContent = button.dataset.number;
        membershipInput.value = "";
        setMessage(membershipMessage, "");
        updateSaveLabel();
        membershipModal.show();
    });
});

// Ready for the scanner as soon as the window opens
membershipElement.addEventListener("shown.bs.modal", () => membershipInput.focus());
membershipInput.addEventListener("input", updateSaveLabel);

membershipForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    membershipSave.disabled = true;
    setMessage(membershipMessage, "");
    try {
        const { ok, result } = await postForm(`/api/customers/${membershipCustomer}/membership`, "membershipNumber", membershipInput.value);
        if (ok) {
            window.location.reload();
            return;
        }
        setMessage(membershipMessage, result.error);
    } catch (error) {
        setMessage(membershipMessage, "Unable to reach the server. The membership number was not changed.");
    }
    membershipSave.disabled = false;
    membershipInput.select();
});

// -------------------------
// Role
// -------------------------
const roleModal = new bootstrap.Modal(document.getElementById("role-modal"));
const roleMessage = document.getElementById("role-message");
const roleConfirm = document.getElementById("role-confirm");
let roleChange = null;

document.querySelectorAll("[data-change-role]").forEach((button) => {
    button.addEventListener("click", () => {
        const { id, name, role } = button.dataset;
        const toAdmin = role === "admin";
        roleChange = { id, role };
        document.getElementById("role-title").textContent = toAdmin ? `Make ${name} an admin?` : `Make ${name} a customer?`;
        document.getElementById("role-text").textContent = toAdmin
            ? "They will be able to see every customer, manage products and stock, and control the fridges."
            : "They will lose access to the admin pages straight away.";
        roleConfirm.textContent = toAdmin ? "Make admin" : "Make customer";
        setMessage(roleMessage, "");
        roleModal.show();
    });
});

roleConfirm.addEventListener("click", async () => {
    roleConfirm.disabled = true;
    setMessage(roleMessage, "");
    try {
        const { ok, result } = await postForm(`/api/customers/${roleChange.id}/role`, "role", roleChange.role);
        if (ok) {
            window.location.reload();
            return;
        }
        setMessage(roleMessage, result.error);
    } catch (error) {
        setMessage(roleMessage, "Unable to reach the server. The role was not changed.");
    }
    roleConfirm.disabled = false;
});
