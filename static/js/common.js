// Helpers every page can use. base.html loads this before the page's own script

// Send JSON to the server. Gives back { ok, data }
async function postJson(url, body) {
    const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || {})
    });
    return { ok: response.ok, data: await response.json() };
}

// Show a message in a box as a coloured alert. kind is "success", "warning" or "danger". Empty text hides the box
// content can be text, or a list of text and elements (like a link)
function setMessage(element, content, kind = "danger") {
    if (!element) return;
    const parts = [].concat(content || []);
    element.replaceChildren(...parts);
    element.hidden = parts.length === 0;
    element.className = parts.length ? `alert alert-${kind} py-2 px-3 js-message` : "";
    element.dataset.kind = parts.length ? kind : "";
}

// The same, but the message goes away by itself. Errors stay longest so they can be read
const SHOW_TIME = { success: 5000, warning: 6000, danger: 8000 };

function notify(element, text, kind) {
    if (!element) return;
    // The same message again (an item held near the reader): keep it, just show it for longer
    if (element.textContent !== text || element.dataset.kind !== kind) setMessage(element, text, kind);
    clearTimeout(element.hideTimer);
    element.hideTimer = setTimeout(() => setMessage(element, ""), SHOW_TIME[kind]);
}

// Our own window for "are you sure?". Gives back a promise of true (confirmed) or false (cancelled, closed or Escape)
// options: title, text, button (the label on the confirm button) and danger (true makes that button red)
function askToConfirm({ title, text, button, danger = false }) {
    const element = document.getElementById("confirm-modal");
    const yes = document.getElementById("confirm-yes");
    const cancel = document.getElementById("confirm-cancel");

    document.getElementById("confirm-title").textContent = title;
    document.getElementById("confirm-text").textContent = text;
    element.querySelector(".confirm-icon").classList.toggle("danger", danger);
    yes.textContent = button;
    yes.className = `btn ${danger ? "btn-danger" : "btn-primary"}`;

    return new Promise((resolve) => {
        const modal = bootstrap.Modal.getOrCreateInstance(element);
        let confirmed = false;
        const onYes = () => {
            confirmed = true;
            modal.hide();
        };
        yes.addEventListener("click", onYes);
        // The cursor starts on Cancel, so pressing Enter by accident changes nothing
        element.addEventListener("shown.bs.modal", () => cancel.focus(), { once: true });
        element.addEventListener("hidden.bs.modal", () => {
            yes.removeEventListener("click", onYes);
            resolve(confirmed);
        }, { once: true });
        modal.show();
    });
}

// A form with data-confirm-title asks first. It also takes data-confirm-text, data-confirm-button and data-confirm-danger
document.querySelectorAll("form[data-confirm-title]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const { confirmTitle, confirmText, confirmButton, confirmDanger } = form.dataset;
        // If Bootstrap didn't load (no internet), still ask before doing it
        const confirmed = window.bootstrap
            ? await askToConfirm({ title: confirmTitle, text: confirmText, button: confirmButton, danger: confirmDanger !== undefined })
            : window.confirm(`${confirmTitle} ${confirmText}`);
        // submit() goes straight to the server without coming back through this handler
        if (confirmed) form.submit();
    });
});

// Show each notification from the server. Bootstrap's toast fades out by itself after its delay
document.querySelectorAll(".toast[data-delay]").forEach((element) => {
    new bootstrap.Toast(element, { delay: Number(element.dataset.delay) }).show();
});
