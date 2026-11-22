const fridgesDiv = document.getElementById("fridges");
const message = document.getElementById("message");
const summary = document.getElementById("summary");
const fanState = document.getElementById("fan-state");
const fanMessage = document.getElementById("fan-message");
const fanButton = document.getElementById("fan-button");
const brokerMessage = document.getElementById("broker-message");
const fanIcon = document.getElementById("fan-icon");

const tiles = {};
let latestFridges = [];

// Show the fan state. The icon spins while the fan is on
function setFanState(state) {
    fanState.textContent = state;
    fanState.className = state === "ON" ? "ok" : "";

    fanIcon.classList.toggle("on", state === "ON");
    showFanButton(fanButton, state);
    showSummary();
}

// Get the fan state, and whether the broker is reachable, from the server
async function updateFan() {
    if (fanButton.disabled) return;
    const fan = await fetchFan();
    // The button was pressed while we waited, so this answer is old
    if (fanButton.disabled) return;
    setFanState(fan.state);
    if (fan.signedOut) showSignedOut(message);
    if (fan.broker !== null) showBroker(brokerMessage, fan.broker);
    setMessage(fanMessage, fan.offline ? "Cannot reach the server." : "");
}

fanButton.addEventListener("click", async () => {
    setFanState(await pressFanButton(fanButton));
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

    // A limit near one end of the bar would sit on top of the "0 °C" or top label.
    // Then that end label is hidden and the limit label lines up with the edge instead
    const limitPercent = (fridge.threshold / top) * 100;
    const nearStart = limitPercent < 25;
    const nearEnd = limitPercent > 75;
    tile.querySelector(".scale-zero").style.visibility = nearStart ? "hidden" : "visible";
    tile.querySelector(".scale-top").style.visibility = nearEnd ? "hidden" : "visible";
    label.classList.toggle("near-start", nearStart);
    label.classList.toggle("near-end", nearEnd);

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

// "All fridges, last 24 hours": one line per fridge, made once. Colours come from static/js/charts.js

// Each fridge gets its own colour and line style (solid, dashed, dotted),
// so two fridges at the same temperature can still be told apart
const FRIDGE_LINES = [
    { colour: BLUE, dash: [] },
    { colour: WARNING, dash: [8, 4] },
    { colour: NAVY, dash: [2, 3] },
    { colour: SUCCESS, dash: [12, 4, 2, 4] }
];
const fridgesChart = new Chart(document.getElementById("fridges-chart"), {
    type: "line",
    data: { datasets: [] },
    options: {
        // animation, parsing and no dots, from FAST_LINE_CHART in static/js/fridges/common.js
        ...FAST_LINE_CHART,
        // The tooltip shows every fridge at the time closest to the mouse
        interaction: { mode: "nearest", axis: "x", intersect: false },
        plugins: {
            // The legend shows each line's style too. Click a fridge in it to hide or show its line
            legend: { position: "bottom", labels: { boxWidth: 30, boxHeight: 0, useBorderRadius: false } },
            tooltip: {
                callbacks: {
                    title: (items) => timeLabel(new Date(items[0].parsed.x), 24),
                    label: (item) => ` ${item.dataset.label}: ${item.parsed.y.toFixed(1)} °C`
                }
            }
        },
        scales: {
            // Time in milliseconds, shown as "14:05"
            x: { type: "linear", ticks: { maxTicksLimit: 6, callback: (value) => timeLabel(new Date(value), 24) } },
            // Zoomed in on the temperatures, with 1 °C of room above and below, so close lines are spread out
            y: { grace: 1, ticks: { callback: (value) => `${value} °C` } }
        }
    }
});

// Get the last 24 hours of every fridge and draw them
async function updateFridgesChart() {
    if (!latestFridges.length) return;
    // By ID, so each fridge keeps its colour
    const fridges = [...latestFridges].sort((a, b) => a.id - b.id);
    const datasets = [];
    try {
        for (const [i, fridge] of fridges.entries()) {
            const response = await fetch(`/api/fridges/${fridge.id}/history?hours=24`, { cache: "no-store" });
            if (!response.ok) return;
            const rows = await response.json();
            const line = FRIDGE_LINES[i % FRIDGE_LINES.length];
            datasets.push({ label: fridge.name, data: chartPoints(rows, "temperature"),
                            borderColor: line.colour, backgroundColor: line.colour,
                            borderDash: line.dash, borderWidth: 2.5 });
        }
    } catch (error) {
        return;   // Keep showing the old chart if the server can't be reached
    }

    const end = Date.now();
    fridgesChart.data.datasets = datasets;
    fridgesChart.options.scales.x.min = end - 24 * 3600 * 1000;
    fridgesChart.options.scales.x.max = end;
    fridgesChart.update();
}

update().then(updateFridgesChart);
updateFan();
setInterval(updateFan, 2000);
setInterval(update, 2000);
setInterval(updateFridgesChart, 60000); // a reading is saved once a minute
