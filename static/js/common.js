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

// kind is "success", "warning" or "danger". content is text or a list of text and elements. Empty hides the box
function setMessage(element, content, kind = "danger") {
    if (!element) return;
    const parts = [].concat(content || []);
    element.replaceChildren(...parts);
    element.hidden = parts.length === 0;
    // Remember the box's own classes from the HTML (like its spacing) so they are kept
    if (element.dataset.baseClass === undefined) element.dataset.baseClass = element.className;
    const alertClass = parts.length ? ` alert alert-${kind} py-2 px-3 js-message` : "";
    element.className = (element.dataset.baseClass + alertClass).trim();
    element.dataset.kind = parts.length ? kind : "";
}

// How long a message stays. Errors stay longest so they can be read
const SHOW_TIME = { success: 5000, warning: 6000, danger: 8000 };

// Like setMessage, but it goes away by itself
function notify(element, text, kind) {
    if (!element) return;
    // The same message again (an item held near the reader) just stays longer
    if (element.textContent !== text || element.dataset.kind !== kind) setMessage(element, text, kind);
    clearTimeout(element.hideTimer);
    element.hideTimer = setTimeout(() => setMessage(element, ""), SHOW_TIME[kind]);
}

// A notification at the bottom right, for something the person just did
function showToast(text, kind = "success") {
    const container = document.getElementById("toast-container");
    if (!container || !text) return;

    const element = document.createElement("div");
    element.className = `toast align-items-center border-0 text-bg-${kind}`;
    element.setAttribute("role", "status");

    const row = document.createElement("div");
    row.className = "d-flex";
    const body = document.createElement("div");
    body.className = "toast-body";
    body.textContent = text;
    const close = document.createElement("button");
    close.type = "button";
    close.className = "btn-close btn-close-white me-2 m-auto";
    close.setAttribute("data-bs-dismiss", "toast");
    close.setAttribute("aria-label", "Close");
    row.append(body, close);
    element.appendChild(row);
    container.appendChild(element);

    element.addEventListener("hidden.bs.toast", () => element.remove());
    new bootstrap.Toast(element, { delay: SHOW_TIME[kind] }).show();
}

// Our own "are you sure?" window. Resolves to true if confirmed. danger makes the button red
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

// Notifications from flash() on the server
document.querySelectorAll(".toast[data-delay]").forEach((element) => {
    new bootstrap.Toast(element, { delay: Number(element.dataset.delay) }).show();
});


// The moon / sun button in the top bar switches between light and dark mode, and the browser remembers it.
// base.html sets the mode when the page opens
const themeButton = document.getElementById("theme-button");
function showThemeButton() {
    const dark = document.documentElement.dataset.bsTheme === "dark";
    themeButton.querySelector("i").className = dark ? "bi bi-sun" : "bi bi-moon";
    themeButton.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
}
if (themeButton) {
    showThemeButton();
    themeButton.addEventListener("click", () => {
        const dark = document.documentElement.dataset.bsTheme === "dark";
        document.documentElement.dataset.bsTheme = dark ? "light" : "dark";
        localStorage.setItem("theme", dark ? "light" : "dark");
        showThemeButton();
        // Charts read their colours once, so a page with charts reloads to draw them in the new colours
        if (typeof Chart !== "undefined") location.reload();
    });
}
