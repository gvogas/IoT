// Membership card sign in. The scanner types the number very fast, then Enter

const MAX_KEY_GAP = 100;     // milliseconds between keys. A person types slower than this
const MIN_CODE_LENGTH = 4;

// onCustomer runs after a customer signs in. The server refuses admin cards, so admins use the sign in form
function setupBarcodeLogin(onCustomer) {
    const form = document.getElementById("scan-form");
    const input = document.getElementById("scan-input");
    const message = document.getElementById("scan-message");

    // Send the scanned number to the server
    async function signIn(code) {
        if (!code) {
            notify(message, "Scan your membership card, or type the number on it.", "danger");
            return;
        }
        try {
            const { ok, data } = await postJson("/api/scan-login", { code });
            if (!ok) notify(message, data.error, "danger");
            else onCustomer();
        } catch (error) {
            notify(message, "Unable to sign in. Please try again.", "danger");
        }
    }

    // There is no form when someone is already signed in
    if (form) {
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            signIn(input.value.trim());
            input.value = "";
        });
        input.focus();
    }

    let buffer = "";
    let lastKey = 0;

    document.addEventListener("keydown", (event) => {
        // Typing in a box is handled by that box
        const tag = (event.target.tagName || "").toLowerCase();
        if (tag === "input" || tag === "textarea") return;

        const now = Date.now();
        if (now - lastKey > MAX_KEY_GAP) buffer = "";
        lastKey = now;

        if (event.key === "Enter") {
            const code = buffer.trim();
            buffer = "";
            if (code.length >= MIN_CODE_LENGTH) {
                // The scanner's Enter should not also click the button that has focus
                event.preventDefault();
                signIn(code);
            }
        } else if (event.key.length === 1) {
            buffer += event.key;
        }
    });
}
