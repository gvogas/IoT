const fridgesDiv = document.getElementById("fridges");
const message = document.getElementById("message");
const summary = document.getElementById("summary");
const fanState = document.getElementById("fan-state");
const fanMessage = document.getElementById("fan-message");
const fanOff = document.getElementById("fan-off");
const fanIcon = document.getElementById("fan-icon");

const tiles = {};
let latestFridges = [];

// Show the fan state. The icon spins while the fan is on
function setFanState(state) {
    fanState.textContent = state;
    fanState.className = state === "ON" ? "ok" : "";

    fanIcon.classList.toggle("on", state === "ON");
    showSummary();
}

// Get the fan state from the server
async function updateFan() {
    if (fanOff.disabled) return;
    try {
        const response = await fetch("/api/fan", { cache: "no-store" });
        const result = await response.json();
        if (fanOff.disabled) return;
        if (response.status === 403) {
            showSignedOut(message);
            setFanState("UNKNOWN");
            return;
        }
        setFanState(response.ok ? result.state : "UNKNOWN");
    } catch (error) {
        if (!fanOff.disabled) {
            setFanState("UNKNOWN");
            setMessage(fanMessage, "Cannot reach the server.");
        }
    }
}

fanOff.addEventListener("click", async () => {
    fanOff.disabled = true;
    try {
        const response = await fetch("/api/fan/off", { method: "POST" });
        const result = await response.json();
        if (response.status === 403) showSignedOut(message);
        setFanState(response.ok ? result.state : "UNKNOWN");
        showToast(result.error || result.success, result.error ? "danger" : "success");
    } catch (error) {
        setFanState("UNKNOWN");
        showToast("Unable to reach the server. Fan off is not confirmed.", "danger");
    } finally {
        fanOff.disabled = false;
    }
});

// The line at the top of the page
function showSummary() {
    if (!latestFridges.length) return;
    const counts = { ok: 0, hot: 0, offline: 0, waiting: 0 };
    for (const fridge of latestFridges) counts[fridgeStatus(fridge)]++;

    const parts = [];
    if (counts.ok) parts.push(`${counts.ok} OK`);
    if (counts.hot) parts.push(`${counts.hot} too warm`);
    if (counts.offline) parts.push(`${counts.offline} offline`);
    if (counts.waiting) parts.push(`${counts.waiting} waiting for data`);

    summary.textContent = `${latestFridges.length} fridges: ${parts.join(", ")}. Fan is ${fanState.textContent}.`;
    summary.className = `fridge-summary ${counts.hot ? "hot" : ""}`;
}

// Make a fridge's tile the first time it shows up
function makeTile(fridge) {
    const template = document.getElementById("tile-template");
    const tile = template.content.firstElementChild.cloneNode(true);
    tile.href = `/fridges/${fridge.id}`;
    tile.querySelector(".fridge-name").textContent = fridge.name;
    fridgesDiv.appendChild(tile);
    tiles[fridge.id] = tile;
}

// Put one fridge's newest data on its tile
function showTile(fridge) {
    const tile = tiles[fridge.id];
    const status = fridgeStatus(fridge);

    setStatus(tile.querySelector(".fridge-status"), status);
    tile.classList.toggle("hot", status === "hot");
    tile.classList.toggle("stale", status === "offline" || status === "waiting");
    tile.setAttribute("aria-label", `${fridge.name}: ${STATUS_TEXT[status]}, ${oneDecimal(fridge.temperature)} °C. View details`);

    const temp = tile.querySelector(".temp");
    temp.textContent = oneDecimal(fridge.temperature);
    tile.querySelector(".temp-value").className = `temp-value ${status === "hot" ? "hot" : ""}`;
    setTrend(tile.querySelector(".trend"), fridge.stats);

    // Where the temperature and the limit sit on the scale
    const top = scaleTop(fridge.threshold, fridge.temperature);
    const percent = (value) => `${(Math.min(Math.max(value, 0), top) / top) * 100}%`;
    tile.querySelector(".limit-safe").style.width = percent(fridge.threshold);
    tile.querySelector(".limit-mark").style.left = percent(fridge.threshold);
    const now = tile.querySelector(".limit-now");
    now.hidden = fridge.temperature === null;
    if (fridge.temperature !== null) now.style.left = percent(fridge.temperature);
    const label = tile.querySelector(".limit-label");
    label.textContent = `limit ${oneDecimal(fridge.threshold)} °C`;
    label.style.left = percent(fridge.threshold);
    tile.querySelector(".scale-top").textContent = `${top} °C`;

    tile.querySelector(".tile-sentence").textContent = fridgeSentence(fridge, fanState.textContent);
    tile.querySelector(".hum").textContent = fridge.humidity === null ? "--" : Math.round(fridge.humidity);
    tile.querySelector(".last-reading").textContent = fridge.age === null ? "No reading yet" : `Last reading ${timeAgo(fridge.age)}`;
}

// Get the newest readings and show them, too warm fridges first
async function update() {
    try {
        const response = await fetch("/api/fridges", { cache: "no-store" });
        const fridges = await response.json();
        if (response.status === 403) {
            showSignedOut(message);
            return;
        }
        if (!response.ok) {
            setMessage(message, fridges.error);
            return;
        }
        setMessage(message, "");

        // Too warm fridges first
        const order = { hot: 0, offline: 1, waiting: 2, ok: 3 };
        fridges.sort((a, b) => order[fridgeStatus(a)] - order[fridgeStatus(b)] || a.id - b.id);

        latestFridges = fridges;
        for (const fridge of fridges) {
            if (!tiles[fridge.id]) makeTile(fridge);
            showTile(fridge);
            fridgesDiv.appendChild(tiles[fridge.id]);
        }
        showSummary();
    } catch (error) {
        setMessage(message, "Cannot reach the server.");
    }
}

update();
updateFan();
setInterval(updateFan, 2000);
setInterval(update, 2000);
