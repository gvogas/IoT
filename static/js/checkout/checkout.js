// The checkout page: the basket and paying

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

function plural(count, word) {
    return `${count} ${word}${count === 1 ? "" : "s"}`;
}

// The first column of the basket: the product's picture and name
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
    const box = document.createElement("div");
    box.className = "product-cell";
    box.append(picture, name);
    const cell = document.createElement("td");
    cell.className = "cell-title";
    cell.append(box);
    return cell;
}

function render() {
    const lines = new Map();
    items.forEach((item) => {
        const line = lines.get(item.productID) || { name: item.name, price: item.price, image: item.image, qty: 0 };
        line.qty++;
        lines.set(item.productID, line);
    });

    basketRows.innerHTML = "";
    lines.forEach((line, productID) => {
        const row = document.createElement("tr");
        row.appendChild(productCell(line));
        // The labels are shown next to each value when the table is stacked on a phone
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
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "btn btn-outline-danger btn-sm btn-icon";
        remove.innerHTML = '<i class="bi bi-trash3" aria-hidden="true"></i>';
        remove.title = "Remove";
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
    const total = money((subtotalCents + taxCents) / 100);
    basketTotal.textContent = total;
    payLabel.textContent = items.length ? `Pay ${total}` : "Pay";
    itemCount.textContent = items.length;
    itemCount.hidden = items.length === 0;
    summaryCount.textContent = plural(items.length, "item");
    if (pointsPreview) {
        // The same rule as the server: points for every complete step spent before tax
        const earned = Math.floor(subtotalCents / (window.points.step * 100)) * window.points.perStep;
        pointsPreview.textContent = plural(earned, "point");
    }
    basketEmpty.hidden = items.length > 0;
    document.getElementById("basket-table").hidden = items.length === 0;
    payButton.disabled = !window.signedIn || items.length === 0;
    clearButton.disabled = items.length === 0;
    try { sessionStorage.setItem("basket", JSON.stringify(items)); } catch (e) { /* storage blocked */ }
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

// The little light at the top of the page: is the reader working?
function setReaderStatus(state, text) {
    readerStatus.dataset.state = state;
    readerStatusText.textContent = text;
}

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
    paused = true;   // stop reading while paying, so the paid items are not looked at again
    setReaderStatus("paused", "Paying...");
    try {
        const { ok, data } = await postJson("/api/checkout/pay", { epcs: items.map((item) => item.epc) });
        if (ok) {
            items = [];
            window.signedIn = false;   // the server signs the customer out after paying
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
    setReaderStatus("ok", "Reader ready");
    render();
});

// The receipt after paying: shown in a window until the customer taps Done (or leaves it for a while)
const RECEIPT_TIMEOUT = 60000;

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
    document.getElementById("receipt-meta").textContent = `Receipt #${receipt.purchaseID} · ${receipt.date}`;
    if (receipt.customer) add("p", `${receipt.customer} (${receipt.membershipNumber})`, "mb-3");

    const table = document.createElement("table");
    table.className = "table table-sm receipt-table";
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
        if (i === 2) row.className = "total-row";
        row.insertCell().textContent = label;
        row.insertCell();
        const cell = row.insertCell();
        cell.className = "text-end";
        cell.textContent = money(value);
    });
    body.appendChild(table);

    // Show the points earned on this purchase and the customer's updated balance.
    add("p", `Loyalty points earned: +${receipt.pointsEarned || 0}`, "receipt-points mb-1");
    if (receipt.customerPoints !== null && receipt.customerPoints !== undefined) {
        add("p", `Your points balance: ${receipt.customerPoints} points ($${Math.floor(receipt.customerPoints / 100)} in rewards)`, "small text-secondary mb-2");
    }
    add("p", `Paid by ${receipt.paymentMethod}. Thank you!`, "mb-0");
    if (emailMessage) {
        add("p", emailMessage, "small text-secondary mt-2 mb-0");
    }

    const modalElement = document.getElementById("receipt-modal");
    const modal = new bootstrap.Modal(modalElement);
    const finish = () => window.location.reload();
    document.getElementById("receipt-done").addEventListener("click", finish);
    const emailButton = document.getElementById("receipt-email");
    emailButton.disabled = false;
    emailButton.addEventListener("click", async () => {
        emailButton.disabled = true;
        try {
            const { ok, data } = await postJson("/api/checkout/receipt-email");
            showToast(ok ? data.success : data.error, ok ? "success" : "danger");
            if (!ok) emailButton.disabled = false;
        } catch (e) {
            showToast("The email could not be sent. Please try again.", "danger");
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
