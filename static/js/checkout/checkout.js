const basketRows = document.getElementById("basket-rows");
const basketEmpty = document.getElementById("basket-empty");
const basketTotal = document.getElementById("basket-total");
const basketMessage = document.getElementById("basket-message");
const payButton = document.getElementById("pay-button");
const clearButton = document.getElementById("clear-basket");
const payLabel = document.getElementById("pay-label");
const itemCount = document.getElementById("item-count");
const summaryCount = document.getElementById("summary-count");
const pointsPreview = document.getElementById("points-preview");
const readerStatus = document.getElementById("reader-status");
const readerStatusText = document.getElementById("reader-status-text");
const payHint = document.getElementById("pay-hint");
const paySpinner = document.getElementById("pay-spinner");

let items = [];
// Products scanned in since the last draw. Their rows are highlighted for a moment so the customer sees what was added
let justAdded = new Set();

// The basket is kept in this tab, so it is still there after signing in
try { items = JSON.parse(sessionStorage.getItem("basket") || "[]"); } catch (e) { items = []; }

// 12.5 -> "$12.50"
function money(value) {
    return "$" + value.toFixed(2);
}

// Money is added up in whole cents so the page and the receipt always agree
function cents(value) {
    return Math.round(value * 100);
}

// Items saved in the basket before the taxable setting existed count as taxable
function isTaxable(item) {
    return item.taxable !== false;
}

// "1 item", "3 items"
function plural(count, word) {
    return `${count} ${word}${count === 1 ? "" : "s"}`;
}

// The basket's first column: picture and name
function productCell(line) {
    const picture = document.createElement(line.image ? "img" : "span");
    picture.className = `product-image sm ${line.image ? "" : "no-image"}`;
    if (line.image) {
        picture.src = line.image;
        picture.alt = "";
    } else {
        picture.innerHTML = '<i class="bi bi-image" aria-hidden="true"></i>';
    }
    const name = document.createElement("span");
    name.className = "product-name";
    name.textContent = line.name;
    if (!line.taxable) {
        const note = document.createElement("small");
        note.className = "d-block text-secondary fw-normal";
        note.textContent = "No tax";
        name.append(note);
    }
    const box = document.createElement("div");
    box.className = "product-cell";
    box.append(picture, name);
    const cell = document.createElement("td");
    cell.className = "cell-title";
    cell.append(box);
    return cell;
}

// Draw the basket and the totals
function render() {
    const lines = new Map();
    items.forEach((item) => {
        const line = lines.get(item.productID) || { name: item.name, price: item.price, image: item.image, taxable: isTaxable(item), qty: 0 };
        line.qty++;
        lines.set(item.productID, line);
    });

    basketRows.innerHTML = "";
    lines.forEach((line, productID) => {
        const row = document.createElement("tr");
        if (justAdded.has(productID)) row.className = "just-added";
        row.appendChild(productCell(line));
        // data-label shows next to each value when the table is stacked on a phone
        [["Qty", line.qty], ["Price", money(line.price)], ["Total", money(line.price * line.qty)]].forEach(([label, text], i) => {
            const cell = document.createElement("td");
            cell.textContent = text;
            cell.dataset.label = label;
            cell.className = i === 2 ? "text-end num fw-semibold" : "text-end num";
            row.appendChild(cell);
        });
        const actions = document.createElement("td");
        actions.className = "text-end cell-actions";
        actions.dataset.label = "";
        // With two or more of a product, a minus button takes off just one
        if (line.qty > 1) {
            const minus = document.createElement("button");
            minus.type = "button";
            minus.className = "btn btn-outline-secondary btn-sm btn-icon me-1";
            minus.innerHTML = '<i class="bi bi-dash-lg" aria-hidden="true"></i>';
            minus.title = "Remove one";
            minus.setAttribute("aria-label", `Remove one ${line.name}`);
            minus.addEventListener("click", () => removeOne(productID, line.name));
            actions.appendChild(minus);
        }
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "btn btn-outline-danger btn-sm btn-icon";
        remove.innerHTML = '<i class="bi bi-trash3" aria-hidden="true"></i>';
        remove.title = line.qty > 1 ? "Remove all" : "Remove";
        remove.setAttribute("aria-label", line.qty > 1 ? `Remove all ${line.name}` : `Remove ${line.name}`);
        remove.addEventListener("click", () => removeProduct(productID, line.name));
        actions.appendChild(remove);
        row.appendChild(actions);
        basketRows.appendChild(row);
    });

    const subtotalCents = items.reduce((sum, item) => sum + cents(item.price), 0);
    // Same as the server: GST and QST on the taxable items only, rounded half up to the cent
    const taxableCents = items.filter(isTaxable).reduce((sum, item) => sum + cents(item.price), 0);
    const gstCents = Math.floor((taxableCents * window.taxParts.gst + 50000) / 100000);
    const qstCents = Math.floor((taxableCents * window.taxParts.qst + 50000) / 100000);
    document.getElementById("basket-subtotal").textContent = money(subtotalCents / 100);
    document.getElementById("basket-gst").textContent = money(gstCents / 100);
    document.getElementById("basket-qst").textContent = money(qstCents / 100);
    const total = money((subtotalCents + gstCents + qstCents) / 100);
    basketTotal.textContent = total;
    payLabel.textContent = items.length ? `Pay ${total}` : "Pay";
    itemCount.textContent = items.length;
    itemCount.hidden = items.length === 0;
    summaryCount.textContent = plural(items.length, "item");
    if (pointsPreview) {
        const earned = Math.floor(subtotalCents / (window.points.step * 100)) * window.points.perStep;
        pointsPreview.textContent = plural(earned, "point");
    }
    basketEmpty.hidden = items.length > 0;
    document.getElementById("basket-table").hidden = items.length === 0;
    payButton.disabled = !window.signedIn || items.length === 0;
    clearButton.disabled = items.length === 0;
    showSteps();
    justAdded = new Set();
    try { sessionStorage.setItem("basket", JSON.stringify(items)); } catch (e) { /* storage blocked */ }
}

// Mark the steps at the top done or current, and say under Pay what is still missing
function showSteps() {
    const scanned = items.length > 0;
    setStep("step-scan", scanned ? "done" : "current");
    if (!window.signedIn) setStep("step-card", scanned ? "current" : "");
    setStep("step-pay", scanned && window.signedIn ? "current" : "");

    if (!scanned) payHint.textContent = "Scan an item to start.";
    else if (!window.signedIn) payHint.textContent = "Scan your membership card above to pay.";
    else payHint.textContent = window.hasEmail ? "The receipt is emailed to you after paying." : "";
}

// state is "done", "current" or "" (not reached yet). A done step shows a tick instead of its number
function setStep(id, state) {
    const step = document.getElementById(id);
    if (!step) return;
    step.className = state;
    const mark = step.querySelector(".step-mark");
    if (state === "done") mark.innerHTML = '<i class="bi bi-check-lg"></i>';
    else mark.textContent = step.dataset.number;
    if (state === "current") step.setAttribute("aria-current", "step");
    else step.removeAttribute("aria-current");
}

// Show "Paying..." with a spinner on the Pay button while the payment is sent
function setPaying(paying) {
    paySpinner.hidden = !paying;
    if (paying) payLabel.textContent = "Paying...";
}

// The reader scans all the time, and each new tag in range is added to the basket
const SCAN_PAUSE = 300;
const RETRY_PAUSE = 3000;   // after the reader fails to answer
let paused = false;         // true while paying
// The tags the reader saw on its last read, to tell an item held in range from one scanned again
let lastSeen = new Set();
// Removed tags, ignored until they leave the reader's range
let removedTags = new Set();

// The light next to the page title
function setReaderStatus(state, text) {
    readerStatus.dataset.state = state;
    readerStatusText.textContent = text;
}

// Ask the reader for tags again and again
async function scanLoop() {
    while (true) {
        let pause = SCAN_PAUSE;
        if (!paused && !document.hidden) {
            try {
                const { ok, data } = await postJson("/api/checkout/scan");
                if (!ok) throw new Error(data.error || "The reader did not answer.");
                if (!paused) handleScan(data);
                setReaderStatus("ok", "Reader ready");
            } catch (err) {
                setReaderStatus("error", "Reader not answering");
                // Customers get a plain message. Staff can find the reason in the browser console
                console.error("Reader error:", err.message);
                notify(basketMessage, "The item reader is not working right now. Please ask a member of staff for help.", "danger");
                pause = RETRY_PAUSE;
            }
        }
        await new Promise((resolve) => setTimeout(resolve, pause));
    }
}

// Add the new tags to the basket and say what happened
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
        justAdded = new Set(fresh.map((item) => item.productID));
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

// Take one item of a product out of the basket
function removeOne(productID, name) {
    const item = items.find((i) => i.productID === productID);
    removedTags.add(item.epc);
    items = items.filter((i) => i !== item);
    render();
    showToast(`Removed one: ${name}`);
}

// Take every item of one product out of the basket
function removeProduct(productID, name) {
    items.filter((item) => item.productID === productID).forEach((item) => removedTags.add(item.epc));
    items = items.filter((item) => item.productID !== productID);
    render();
    showToast(`Removed: ${name}`);
}

clearButton.addEventListener("click", () => {
    items.forEach((item) => removedTags.add(item.epc));
    items = [];
    render();
    showToast("Basket cleared.");
});

payButton.addEventListener("click", async () => {
    payButton.disabled = true;
    paused = true;   // so the paid items are not scanned again
    setPaying(true);
    setReaderStatus("paused", "Paying...");
    try {
        const { ok, data } = await postJson("/api/checkout/pay", { epcs: items.map((item) => item.epc) });
        if (ok) {
            items = [];
            window.signedIn = false;   // the server signs the customer out after paying
            setPaying(false);
            render();
            setReaderStatus("paused", "Paid");
            showToast(data.success);
            // The reader stays paused until the page reloads for the next customer
            showReceipt(data.receipt, data.emailMessage);
            return;
        }
        showToast(data.error, "danger");
    } catch (e) {
        showToast("Payment failed. Please try again.", "danger");
    }
    paused = false;
    setPaying(false);
    setReaderStatus("ok", "Reader ready");
    render();
});

// The receipt stays up until the customer taps Done, or for RECEIPT_TIMEOUT
const RECEIPT_TIMEOUT = 60000;

// The receipt window after paying
function showReceipt(receipt, emailMessage) {
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
    document.getElementById("receipt-meta").textContent = `Receipt #${receipt.purchaseID}, ${receipt.date}`;
    if (receipt.customer) add("p", `${receipt.customer} (${receipt.membershipNumber})`, "mb-3");

    const table = document.createElement("table");
    table.className = "table table-sm receipt-table";
    receipt.lines.forEach((line) => {
        const row = table.insertRow();
        const name = line.taxable === false ? `${line.name} (No tax)` : line.name;
        [name, `${line.quantity} × ${money(line.unitPrice)}`, money(line.lineTotal)].forEach((text, i) => {
            const cell = row.insertCell();
            cell.textContent = text;
            if (i > 0) cell.className = "text-end";
        });
    });
    const sums = [
        ["Subtotal", receipt.subtotal],
        ["GST", receipt.gst],
        ["QST", receipt.qst],
        ["Total", receipt.total],
    ];
    sums.forEach(([label, value], i) => {
        const row = table.insertRow();
        if (i === sums.length - 1) row.className = "total-row";
        row.insertCell().textContent = label;
        row.insertCell();
        const cell = row.insertCell();
        cell.className = "text-end";
        cell.textContent = money(value);
    });
    body.appendChild(table);

    // The points earned get their own box: it is the part of paying the customer cares about most
    const points = document.createElement("div");
    points.className = "receipt-points";
    const earned = document.createElement("b");
    earned.textContent = `+${receipt.pointsEarned || 0} points`;
    points.appendChild(earned);
    if (receipt.customerPoints !== null && receipt.customerPoints !== undefined) {
        const balance = document.createElement("span");
        balance.textContent = `Balance ${receipt.customerPoints} points ($${Math.floor(receipt.customerPoints / 100)} in rewards)`;
        points.appendChild(balance);
    }
    body.appendChild(points);
    add("p", `Paid by ${receipt.paymentMethod}. Thank you!`, "mb-0 mt-3");
    if (emailMessage) {
        add("p", emailMessage, "small text-secondary mt-2 mb-0");
    }

    const modalElement = document.getElementById("receipt-modal");
    const modal = new bootstrap.Modal(modalElement);
    const finish = () => window.location.reload();
    document.getElementById("receipt-done").addEventListener("click", finish);
    const emailButton = document.getElementById("receipt-email");
    emailButton.disabled = false;
    const emailLabel = emailButton.querySelector("span");
    emailButton.addEventListener("click", async () => {
        emailButton.disabled = true;
        emailLabel.textContent = "Sending...";
        try {
            const { ok, data } = await postJson("/api/checkout/receipt-email");
            showToast(ok ? data.success : data.error, ok ? "success" : "danger");
            emailLabel.textContent = ok ? "Email sent" : "Send email";
            if (!ok) emailButton.disabled = false;
        } catch (e) {
            showToast("The email could not be sent. Please try again.", "danger");
            emailLabel.textContent = "Send email";
            emailButton.disabled = false;
        }
    });
    setTimeout(finish, RECEIPT_TIMEOUT);
    modal.show();
}

// Customers stay here, so reload to show they are signed in
setupBarcodeLogin(() => window.location.reload());

render();
scanLoop();
