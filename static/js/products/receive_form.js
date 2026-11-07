// The receive form: the button says how many units it will receive, from the EPCs typed or scanned
const epcBox = document.querySelector("[data-epc-input]");
const receiveButton = document.querySelector("[data-receive-button]");

function unitsLabel(count) {
    return `${count} ${count === 1 ? "unit" : "units"}`;
}

function updateReceiveForm() {
    if (!epcBox || !receiveButton) return;

    const hint = document.querySelector("[data-epc-count]");
    const tokens = epcBox.value.split(/[\s,;]+/).filter(Boolean).map((token) => token.toUpperCase());
    const valid = tokens.filter((token) => /^[0-9A-F]{1,24}$/.test(token));
    const repeated = new Set(valid.filter((token, index) => valid.indexOf(token) !== index));
    const bad = tokens.length - valid.length;

    let text = valid.length === 0 ? "No EPCs entered" : `${unitsLabel(valid.length)} entered`;
    if (bad) text += ` · ${bad} not a valid EPC`;
    if (repeated.size) text += ` · ${repeated.size} repeated`;
    hint.textContent = text;
    hint.classList.toggle("text-danger", bad > 0 || repeated.size > 0);

    receiveButton.textContent = valid.length ? `Receive ${unitsLabel(valid.length)}` : "Receive stock";
}

if (epcBox) epcBox.addEventListener("input", updateReceiveForm);
updateReceiveForm();

// The "Scan tags" button: ask the RFID reader again and again, and add each new EPC to the box
const scanButton = document.querySelector("[data-scan-button]");
const scanError = document.querySelector("[data-scan-error]");
const scanKnown = document.querySelector("[data-scan-known]");

if (epcBox && scanButton) {
    const SCAN_PAUSE = 300;
    let scanning = false;
    // Every tag seen since scanning started, so a tag held near the reader is added once, even if it is deleted from the box
    let seen = new Set();

    function addEpcs(epcs) {
        const have = new Set(epcBox.value.split(/[\s,;]+/).filter(Boolean).map((token) => token.toUpperCase()));
        const fresh = epcs.filter((epc) => !have.has(epc) && !seen.has(epc));
        fresh.forEach((epc) => seen.add(epc));
        if (!fresh.length) return;
        const text = epcBox.value.trimEnd();
        epcBox.value = (text ? text + "\n" : "") + fresh.join("\n") + "\n";
        updateReceiveForm();
    }

    function setScanning(on) {
        scanning = on;
        scanButton.querySelector("[data-scan-label]").textContent = on ? "Stop scanning" : "Scan tags";
        scanButton.classList.toggle("btn-outline-secondary", !on);
        scanButton.classList.toggle("btn-primary", on);
        scanButton.setAttribute("aria-pressed", String(on));
        if (!on) scanKnown.hidden = true;
    }

    async function scanLoop() {
        while (scanning) {
            try {
                const response = await fetch("/rfid/scan", { method: "POST" });
                const result = await response.json();
                if (!response.ok) throw new Error(result.error || "The reader did not answer.");
                // Tags already in the system are not added, and this note follows the reader: it goes away when they do
                scanKnown.textContent = `Already in the system, not added: ${result.known.join(", ")}`;
                scanKnown.hidden = result.known.length === 0;
                addEpcs(result.epcs);
            } catch (err) {
                scanError.textContent = err.message;
                scanError.hidden = false;
                setScanning(false);
                return;
            }
            await new Promise((resolve) => setTimeout(resolve, SCAN_PAUSE));
        }
    }

    scanButton.addEventListener("click", () => {
        if (scanning) {
            setScanning(false);
        } else {
            scanError.hidden = true;
            scanKnown.hidden = true;
            seen = new Set();
            setScanning(true);
            scanLoop();
        }
    });
}

// The Receive button on the inventory page comes here ready to scan or type
// (after the page has loaded, because the browser's jump to #receive clears the focus)
window.addEventListener("load", () => {
    if (epcBox && !epcBox.matches(":disabled") && window.location.hash === "#receive") {
        requestAnimationFrame(() => epcBox.focus());
    }
});
