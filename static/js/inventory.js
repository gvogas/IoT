// Search and filter for the inventory and products tables
const searchBox = document.querySelector("[data-search]");
const rows = [...document.querySelectorAll("[data-search-row]")];

if (searchBox && rows.length) {
    const chips = [...document.querySelectorAll("[data-status-filter]")];
    const count = document.querySelector("[data-count]");
    const empty = document.querySelector("[data-empty]");
    let status = "all";

    function applyFilters() {
        const words = searchBox.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
        let shown = 0;
        rows.forEach((row) => {
            const matchesText = words.every((word) => row.dataset.search.includes(word));
            const matchesStatus = status === "all" || row.dataset.status === status;
            row.hidden = !(matchesText && matchesStatus);
            if (!row.hidden) shown++;
        });
        if (count) count.textContent = `Showing ${shown} of ${rows.length}`;
        if (empty) empty.hidden = shown > 0;
    }

    searchBox.addEventListener("input", applyFilters);
    chips.forEach((chip) => {
        chip.addEventListener("click", () => {
            status = chip.dataset.statusFilter;
            chips.forEach((other) => other.classList.toggle("active", other === chip));
            applyFilters();
        });
    });
    applyFilters();
}

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
        scanButton.textContent = on ? "Stop scanning" : "Scan tags";
        scanButton.classList.toggle("btn-outline-primary", !on);
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

// Ask before anything that can't be undone
document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
        if (!confirm(form.dataset.confirm)) event.preventDefault();
    });
});

// Category and producer boxes: suggest the names already in the database as you type, closest matches first.
// The dropdown button shows them all
document.querySelectorAll("[data-combo]").forEach((combo) => {
    const input = combo.querySelector("input");
    const menu = combo.querySelector("[data-combo-menu]");
    const toggle = combo.querySelector("[data-combo-toggle]");
    const names = JSON.parse(input.dataset.options);
    const SHOW = 8;
    let shown = [];
    let active = -1;

    // Lower is better: exact, starts with, a word starts with, anywhere. -1 means no match
    function rank(name, query) {
        const lower = name.toLowerCase();
        if (lower === query) return 0;
        if (lower.startsWith(query)) return 1;
        if (lower.split(/\s+/).some((word) => word.startsWith(query))) return 2;
        if (lower.includes(query)) return 3;
        return -1;
    }

    function choose(name) {
        input.value = name;
        menu.hidden = true;
        input.setAttribute("aria-expanded", "false");
    }

    // showAll is true when the dropdown button was pressed: the whole list, not just the closest matches
    function render(showAll) {
        const query = input.value.trim().toLowerCase();
        let matches = names
            .map((name) => ({ name, score: query && !showAll ? rank(name.toLowerCase(), query) : 0 }))
            .filter((match) => match.score >= 0)
            .sort((a, b) => a.score - b.score || a.name.localeCompare(b.name));
        if (!showAll) matches = matches.slice(0, SHOW);
        shown = matches.map((match) => match.name);
        active = -1;
        menu.replaceChildren();

        shown.forEach((name) => {
            const item = document.createElement("button");
            item.type = "button";
            item.className = "dropdown-item";
            item.setAttribute("role", "option");
            item.textContent = name;
            // mousedown (not click) so the box doesn't lose focus before the choice is made
            item.addEventListener("mousedown", (event) => {
                event.preventDefault();
                choose(name);
            });
            menu.appendChild(item);
        });

        const typed = input.value.trim();
        const exact = names.some((name) => name.toLowerCase() === typed.toLowerCase());
        if (!showAll && typed && !exact) {
            const note = document.createElement("div");
            note.className = "dropdown-item-text small text-secondary";
            note.textContent = `New: "${typed}" will be added`;
            menu.appendChild(note);
        }

        menu.hidden = menu.children.length === 0;
        input.setAttribute("aria-expanded", String(!menu.hidden));
    }

    function highlight(index) {
        const items = menu.querySelectorAll("[role='option']");
        items.forEach((item, i) => item.classList.toggle("active", i === index));
        if (items[index]) items[index].scrollIntoView({ block: "nearest" });
        active = index;
    }

    // Keep the focus in the box when the button is pressed, so the list doesn't close first
    toggle.addEventListener("mousedown", (event) => event.preventDefault());
    toggle.addEventListener("click", () => {
        if (!menu.hidden) {
            menu.hidden = true;
            return;
        }
        input.focus();
        render(true);
    });

    input.addEventListener("input", () => render(false));
    input.addEventListener("focus", () => render(false));
    input.addEventListener("blur", () => { menu.hidden = true; });
    input.addEventListener("keydown", (event) => {
        if (menu.hidden) return;
        if (event.key === "ArrowDown") {
            event.preventDefault();
            highlight(Math.min(active + 1, shown.length - 1));
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            highlight(Math.max(active - 1, 0));
        } else if (event.key === "Enter" && active >= 0) {
            event.preventDefault();
            choose(shown[active]);
        } else if (event.key === "Escape") {
            menu.hidden = true;
        }
    });
});
