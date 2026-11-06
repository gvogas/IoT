// The checkout page: the basket, paying, and signing in with the barcode scanner

const basketRows = document.getElementById("basket-rows");
const basketEmpty = document.getElementById("basket-empty");
const basketTotal = document.getElementById("basket-total");
const basketMessage = document.getElementById("basket-message");
const payButton = document.getElementById("pay-button");
const clearButton = document.getElementById("clear-basket");

let items = [];

// The basket is kept in this tab, so it is still there after signing in
try { items = JSON.parse(sessionStorage.getItem("basket") || "[]"); } catch (e) { items = []; }

function money(value) {
    return "$" + value.toFixed(2);
}

// Money is added up in whole cents so the page and the receipt always agree
function cents(value) {
    return Math.round(value * 100);
}

// Show a message in a box as a coloured alert, then hide it after a while.
// kind is "success", "warning" or "danger". Errors stay longest so they can be read
const SHOW_TIME = { success: 5000, warning: 6000, danger: 8000 };

function notify(element, text, kind) {
    if (!element) return;
    // The same message again (an item held near the reader): keep it, just show it for longer
    const same = element.textContent === text && element.dataset.kind === kind;
    if (!same) {
        element.className = `alert alert-${kind} py-2 px-3 mb-3`;
        element.textContent = text;
        element.dataset.kind = kind;
    }
    element.hidden = false;
    clearTimeout(element.hideTimer);
    element.hideTimer = setTimeout(() => {
        element.hidden = true;
        element.textContent = "";
        element.dataset.kind = "";
    }, SHOW_TIME[kind]);
}

function render() {
    const lines = new Map();
    items.forEach((item) => {
        const line = lines.get(item.productID) || { name: item.name, price: item.price, qty: 0 };
        line.qty++;
        lines.set(item.productID, line);
    });

    basketRows.innerHTML = "";
    lines.forEach((line, productID) => {
        const row = document.createElement("tr");
        [line.name, line.qty, money(line.price), money(line.price * line.qty)].forEach((text, i) => {
            const cell = document.createElement("td");
            cell.textContent = text;
            if (i > 0) cell.className = "text-end";
            row.appendChild(cell);
        });
        const actions = document.createElement("td");
        actions.className = "text-end";
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "btn btn-sm btn-outline-danger";
        remove.textContent = "Remove";
        remove.setAttribute("aria-label", `Remove ${line.name}`);
        remove.addEventListener("click", () => removeProduct(productID, line.name));
        actions.appendChild(remove);
        row.appendChild(actions);
        basketRows.appendChild(row);
    });

    const subtotalCents = items.reduce((sum, item) => sum + cents(item.price), 0);
    const taxCents = Math.floor((subtotalCents * window.taxBasisPoints + 5000) / 10000);   // rounded half up
    document.getElementById("basket-subtotal").textContent = money(subtotalCents / 100);
    document.getElementById("basket-tax").textContent = money(taxCents / 100);
    basketTotal.textContent = money((subtotalCents + taxCents) / 100);
    basketEmpty.hidden = items.length > 0;
    payButton.disabled = !window.signedIn || items.length === 0;
    clearButton.disabled = items.length === 0;
    try { sessionStorage.setItem("basket", JSON.stringify(items)); } catch (e) { /* storage blocked */ }
}

async function post(url, body) {
    const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || {})
    });
    return { ok: response.ok, data: await response.json() };
}

// The reader scans all the time. Each new tag in range is added to the basket
const SCAN_PAUSE = 300;
const RETRY_PAUSE = 3000;   // when the reader does not answer, try again after this long
let paused = false;         // true while paying
// The tags the reader saw on its last read, to tell an item held in range from one scanned again
let lastSeen = new Set();
// Tags the customer took out of the basket. They are ignored until they leave the reader's range,
// so an item still lying on the reader is not added straight back
let removedTags = new Set();

async function scanLoop() {
    while (true) {
        let pause = SCAN_PAUSE;
        if (!paused && !document.hidden) {
            try {
                const { ok, data } = await post("/api/checkout/scan");
                if (!ok) throw new Error(data.error || "The reader did not answer.");
                if (!paused) handleScan(data);
            } catch (err) {
                notify(basketMessage, `Can't read items: ${err.message} Trying again...`, "danger");
                pause = RETRY_PAUSE;
            }
        }
        await new Promise((resolve) => setTimeout(resolve, pause));
    }
}

function handleScan(data) {
    const inRange = new Set(data.items.map((item) => item.epc));
    removedTags.forEach((epc) => { if (!inRange.has(epc)) removedTags.delete(epc); });
    data = { ...data, items: data.items.filter((item) => !removedTags.has(item.epc)) };

    const have = new Set(items.map((item) => item.epc));
    const fresh = data.items.filter((item) => !have.has(item.epc));
    // A tag already in the basket that was out of range on the last read has been scanned again
    const again = data.items.filter((item) => have.has(item.epc) && !lastSeen.has(item.epc));
    lastSeen = new Set(data.items.map((item) => item.epc));

    if (fresh.length) {
        items = items.concat(fresh);
        render();
    }

    const names = (list) => [...new Set(list.map((item) => item.name))].join(", ");
    if (data.sold) {
        notify(basketMessage, "Item already sold", "danger");
    } else if (again.length) {
        notify(basketMessage, `Item already scanned: ${names(again)}`, "warning");
    } else if (data.unknown) {
        notify(basketMessage, `${data.unknown} ${data.unknown === 1 ? "item" : "items"} in range could not be recognised.`, "danger");
    } else if (fresh.length) {
        notify(basketMessage, `Added: ${names(fresh)}`, "success");
    }
}

// Take every item of one product out of the basket (the other products stay)
// The tags stay out of the basket until the item is held near the reader again
function removeProduct(productID, name) {
    items.filter((item) => item.productID === productID).forEach((item) => removedTags.add(item.epc));
    items = items.filter((item) => item.productID !== productID);
    render();
    notify(basketMessage, `Removed: ${name}`, "success");
}

clearButton.addEventListener("click", () => {
    items.forEach((item) => removedTags.add(item.epc));
    items = [];
    render();
});

payButton.addEventListener("click", async () => {
    payButton.disabled = true;
    paused = true;   // stop reading while paying, so the paid items are not looked at again
    try {
        const { ok, data } = await post("/api/checkout/pay", { epcs: items.map((item) => item.epc) });
        if (ok) {
            items = [];
            window.signedIn = false;   // the server signs the customer out after paying
            render();
            notify(basketMessage, data.success, "success");
            // The reader stays paused until the page reloads for the next customer
            showReceipt(data.receipt);
            return;
        }
        notify(basketMessage, data.error, "danger");
    } catch (e) {
        notify(basketMessage, "Payment failed. Please try again.", "danger");
    }
    paused = false;
    render();
});

// The receipt after paying: shown in a window until the customer taps Done (or leaves it for a while)
const RECEIPT_TIMEOUT = 60000;

function showReceipt(receipt) {
    if (!receipt) {
        setTimeout(() => window.location.reload(), SHOW_TIME.success);
        return;
    }
    const body = document.getElementById("receipt-body");
    body.innerHTML = "";
    const add = (tag, text, className) => {
        const element = document.createElement(tag);
        element.textContent = text;
        if (className) element.className = className;
        body.appendChild(element);
        return element;
    };
    add("p", `Receipt #${receipt.purchaseID} · ${receipt.date}`, "text-secondary mb-1");
    add("p", receipt.customer ? `${receipt.customer} (${receipt.membershipNumber})` : "", "mb-3");

    const table = document.createElement("table");
    table.className = "table table-sm";
    receipt.lines.forEach((line) => {
        const row = table.insertRow();
        [line.name, `${line.quantity} × ${money(line.unitPrice)}`, money(line.lineTotal)].forEach((text, i) => {
            const cell = row.insertCell();
            cell.textContent = text;
            if (i > 0) cell.className = "text-end";
        });
    });
    [["Subtotal", receipt.subtotal], ["Tax", receipt.tax], ["Total", receipt.total]].forEach(([label, value], i) => {
        const row = table.insertRow();
        if (i === 2) row.className = "fw-bold";
        row.insertCell().textContent = label;
        row.insertCell();
        const cell = row.insertCell();
        cell.className = "text-end";
        cell.textContent = money(value);
    });
    body.appendChild(table);
    add("p", `Paid by ${receipt.paymentMethod}. Thank you!`, "mb-0");

    const modalElement = document.getElementById("receipt-modal");
    const modal = new bootstrap.Modal(modalElement);
    const finish = () => window.location.reload();
    document.getElementById("receipt-done").addEventListener("click", finish);
    const emailButton = document.getElementById("receipt-email");
    emailButton.disabled = false;
    emailButton.addEventListener("click", async () => {
        emailButton.disabled = true;
        try {
            const { ok, data } = await post("/api/checkout/receipt-email");
            notify(document.getElementById("receipt-message"), ok ? data.success : data.error, ok ? "success" : "danger");
            if (!ok) emailButton.disabled = false;
        } catch (e) {
            notify(document.getElementById("receipt-message"), "The email could not be sent. Please try again.", "danger");
            emailButton.disabled = false;
        }
    });
    setTimeout(finish, RECEIPT_TIMEOUT);
    modal.show();
}


// -------------------------
// Barcode scanner login
// -------------------------
// A scanner types like a keyboard: the number very fast, then Enter.
// Keys that come faster than a person types, ending in Enter, count as a scan.

const scanMessage = document.getElementById("scan-message");
const scanForm = document.getElementById("scan-form");
const scanInput = document.getElementById("scan-input");

async function signInWithCode(code) {
    if (code.length < 4) return;
    try {
        const { ok, data } = await post("/api/scan-login", { code });
        if (!ok) {
            notify(scanMessage, data.error, "danger");
            return;
        }
        // Admins go to the admin page. Customers stay here, so reload to show they are signed in
        if (data.redirect) window.location.href = data.redirect;
        else window.location.reload();
    } catch (e) {
        notify(scanMessage, "Unable to sign in. Please try again.", "danger");
    }
}

if (scanForm) {
    scanForm.addEventListener("submit", (event) => {
        event.preventDefault();
        signInWithCode(scanInput.value.trim());
        scanInput.value = "";
    });
    scanInput.focus();
}

const MAX_KEY_GAP = 100;  // milliseconds between keys, a person types slower than this
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
        if (code.length >= 4 && !window.signedInBusy) signInWithCode(code);
    } else if (event.key.length === 1) {
        buffer += event.key;
    }
});

render();
scanLoop();
