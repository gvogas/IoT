// Sign in with a membership card: the barcode scanner types the number, then Enter

const scanForm = document.getElementById("scan-form");
const scanInput = document.getElementById("scan-input");
const scanMessage = document.getElementById("scan-message");

function showError(text) {
    scanMessage.className = "alert alert-danger py-2 px-3 mt-3 mb-0";
    scanMessage.textContent = text;
    scanMessage.hidden = false;
    clearTimeout(scanMessage.hideTimer);
    scanMessage.hideTimer = setTimeout(() => { scanMessage.hidden = true; }, 8000);
}

async function signInWithCode(code) {
    if (!code) {
        showError("Scan your membership card, or type the number on it.");
        return;
    }
    try {
        const response = await fetch("/api/scan-login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code })
        });
        const result = await response.json();
        if (!response.ok) {
            showError(result.error);
            return;
        }
        // Admins go to the admin page, customers go to the checkout
        window.location.href = result.redirect || "/";
    } catch (error) {
        showError("Unable to sign in. Please try again.");
    }
}

scanForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const code = scanInput.value.trim();
    scanInput.value = "";
    signInWithCode(code);
});

// A scan while the cursor is not in any box also works: keys typed faster than a person types, ending in Enter
const MAX_KEY_GAP = 100;   // milliseconds
let buffer = "";
let lastKey = 0;

document.addEventListener("keydown", (event) => {
    const tag = (event.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea") return;

    const now = Date.now();
    if (now - lastKey > MAX_KEY_GAP) buffer = "";
    lastKey = now;

    if (event.key === "Enter") {
        const code = buffer.trim();
        buffer = "";
        if (code.length >= 4) signInWithCode(code);
    } else if (event.key.length === 1) {
        buffer += event.key;
    }
});
