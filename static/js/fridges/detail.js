const page = document.getElementById("fridge");
const fridgeId = page.dataset.id;
const message = document.getElementById("message");
const fanState = document.getElementById("fan-state");
const fanButton = document.getElementById("fan-button");
const brokerMessage = document.getElementById("broker-message");
const form = document.getElementById("threshold-form");

let latest = null;
let historyHours = 24;

function $(selector) {
    return page.querySelector(selector);
}

// Thermometer: 0 °C at y=150, top of the scale at y=20
function showThermometer(fridge, status) {
    const top = scaleTop(fridge.threshold, fridge.temperature);
    const y = (value) => 150 - (Math.min(Math.max(value, 0), top) / top) * 130;
    $(".thermo-reading").classList.toggle("hot", status === "hot");

    const fillY = fridge.temperature === null ? 150 : y(fridge.temperature);
    $(".thermo-fill").setAttribute("y", fillY);
    $(".thermo-fill").setAttribute("height", 162 - fillY);

    const limitY = y(fridge.threshold);
    $(".limit-line").setAttribute("y1", limitY);
    $(".limit-line").setAttribute("y2", limitY);
    $(".limit-text").setAttribute("y", limitY + 4);
    $(".scale-red").setAttribute("height", limitY - 20);
    $(".scale-green").setAttribute("y", limitY);
    $(".scale-green").setAttribute("height", 150 - limitY);

    page.querySelectorAll(".ticks text").forEach((text, i) => {
        text.textContent = `${Math.round(top * (4 - i) / 4)}°`;
    });

    $(".thermometer").setAttribute("aria-label", `Thermometer showing ${oneDecimal(fridge.temperature)} °C, limit ${oneDecimal(fridge.threshold)} °C`);
}

// Humidity dial
function showDial(humidity) {
    if (humidity === null) return;
    const angle = Math.PI * (1 - Math.min(Math.max(humidity, 0), 100) / 100);
    const x = 100 + 80 * Math.cos(angle), y = 105 - 80 * Math.sin(angle);
    $(".hum-arc").setAttribute("d", `M20 105 A80 80 0 0 1 ${x.toFixed(1)} ${y.toFixed(1)}`);
    $(".hum-needle").setAttribute("x2", (100 + 58 * Math.cos(angle)).toFixed(1));
    $(".hum-needle").setAttribute("y2", (105 - 58 * Math.sin(angle)).toFixed(1));
}

// The "Last 24 hours" doughnut: green for the time under the limit, red for the time over it.
// Grey when there are no saved readings yet. Colours come from static/js/charts.js
const rangeChart = new Chart(document.getElementById("range-chart"), {
    type: "doughnut",
    data: {
        labels: ["Under the limit", "Over the limit"],
        datasets: [{ data: [0, 0], backgroundColor: [SUCCESS, DANGER], borderColor: "#fff", borderWidth: 2 }]
    },
    options: {
        cutout: "70%",
        plugins: {
            legend: { position: "right", labels: { boxWidth: 12 } },
            tooltip: { callbacks: { label: (item) => ` ${item.label}: ${item.raw}%` } }
        }
    }
});

// inRange is the percent of the last 24 hours' readings that were under the limit, or null
function showRangeChart(inRange) {
    const numbers = inRange === null ? [0, 0] : [inRange, 100 - inRange];
    const bars = rangeChart.data.datasets[0];
    // Only redraw when the numbers change, so the doughnut doesn't flicker every 2 seconds
    if (bars.data[0] === numbers[0] && bars.data[1] === numbers[1]) return;
    bars.data = numbers;
    rangeChart.update();
    $(".range-text").textContent = inRange === null
        ? "No saved readings yet."
        : `${inRange}% of the readings were under the limit.`;
}

// Put the newest data on the page
function showFridge(fridge) {
    const status = fridgeStatus(fridge);
    const stats = fridge.stats || {};

    setStatus($(".fridge-status"), status);
    $(".last-reading").textContent = fridge.age === null ? "No reading yet" : `Last reading ${timeAgo(fridge.age)}`;
    $(".detail-card").classList.toggle("hot", status === "hot");
    $(".detail-card").classList.toggle("stale", status === "offline" || status === "waiting");

    $(".temp").textContent = oneDecimal(fridge.temperature);
    $(".temp-value").className = `temp-value ${status === "hot" ? "hot" : ""}`;
    setTrend($(".trend"), stats);
    showThermometer(fridge, status);

    $(".hum").textContent = fridge.humidity === null ? "--" : Math.round(fridge.humidity);
    $(".hum-range").textContent = stats.minHum === null || stats.minHum === undefined
        ? "24 h: --"
        : `24 h: ${Math.round(stats.minHum)} to ${Math.round(stats.maxHum)} %`;
    showDial(fridge.humidity);

    $(".detail-sentence").textContent = fridgeSentence(fridge, fanState.textContent);
    $(".detail-sentence").className = `detail-sentence ${status}`;

    $(".stat-min").textContent = stats.minTemp === null ? "--" : `${oneDecimal(stats.minTemp)} °C`;
    $(".stat-max").textContent = stats.maxTemp === null ? "--" : `${oneDecimal(stats.maxTemp)} °C`;
    $(".stat-range").textContent = stats.inRange === null ? "--" : `${stats.inRange}%`;
    showRangeChart(stats.inRange);
    $(".stat-over").textContent = stats.overTodayMinutes ? duration(stats.overTodayMinutes) : "none";
    $(".stat-over").className = `stat-over ${stats.overTodayMinutes ? "hot" : "ok"}`;

    $(".threshold").textContent = oneDecimal(fridge.threshold);
    form.querySelector("input").placeholder = fridge.threshold ?? "";

    const alertInfo = $(".alert-info");
    if (fridge.alert) {
        alertInfo.textContent = fridge.alert.status === "sent"
            ? `Alert emailed to ${fridge.alert.email} at ${fridge.alert.time}.`
            : `Alert email to ${fridge.alert.email} failed at ${fridge.alert.time}.`;
        alertInfo.className = `alert-info ${fridge.alert.status === "sent" ? "" : "hot"}`;
    } else {
        alertInfo.textContent = "No alert sent.";
        alertInfo.className = "alert-info text-secondary";
    }
}

// Get the newest reading from the server
async function update() {
    try {
        const response = await fetch(`/api/fridges/${fridgeId}`, { cache: "no-store" });
        const fridge = await response.json();
        if (response.status === 403) {
            showSignedOut(message);
            return;
        }
        if (!response.ok) {
            setMessage(message, fridge.error);
            return;
        }
        latest = fridge;
        showFridge(fridge);
    } catch (error) {
        setMessage(message, "Cannot reach the server.");
    }
}

// Show the fan state and the button that changes it
function setFanState(state) {
    fanState.textContent = state;
    fanState.className = state === "ON" ? "ok" : "";
    showFanButton(fanButton, state);
}

// Get the fan state, and whether the broker is reachable, from the server
async function updateFan() {
    if (fanButton.disabled) return;
    const fan = await fetchFan();
    // The button was pressed while we waited, so this answer is old
    if (fanButton.disabled) return;
    setFanState(fan.state);
    if (fan.broker !== null) showBroker(brokerMessage, fan.broker);
}

fanButton.addEventListener("click", async () => {
    setFanState(await pressFanButton(fanButton));
});

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
        const response = await fetch(`/api/fridges/${fridgeId}/threshold`, { method: "POST", body: new FormData(form) });
        const result = await response.json();
        showToast(result.error || result.success, result.error ? "danger" : "success");
        if (response.ok) {
            form.reset();
            update();
            updateHistory();
        }
    } catch (error) {
        showToast("Unable to save the limit. Please try again.", "danger");
    }
});

// History chart, drawn with Chart.js. Colours come from static/js/charts.js

// Made once. drawChart() puts new readings in it
const historyChart = new Chart(document.getElementById("history-chart"), {
    type: "line",
    data: {
        datasets: [
            {
                label: "Temperature",
                data: [],
                borderColor: BLUE,
                borderWidth: 2.5,
                yAxisID: "temp",
                // Red under the line wherever it is above the limit. drawChart() sets the limit
                fill: { target: { value: 0 }, above: DANGER_TINT, below: "transparent" }
            },
            { label: "Humidity", data: [], borderColor: MIST, borderWidth: 1.5, yAxisID: "hum" },
            { label: "Limit", data: [], borderColor: DANGER, borderWidth: 1.5, borderDash: [6, 4], yAxisID: "temp" }
        ]
    },
    options: {
        // animation, parsing and no dots, from FAST_LINE_CHART in static/js/fridges/common.js
        ...FAST_LINE_CHART,
        // The tooltip shows the readings closest to the mouse, left to right
        interaction: { mode: "nearest", axis: "x", intersect: false },
        plugins: {
            // Paint the red "above the limit" area first, so the humidity line shows on top of it
            filler: { drawTime: "beforeDatasetsDraw" },
            // The legend is under the chart in the page, with the "Above the limit" colour too
            legend: { display: false },
            tooltip: {
                // The limit line is the same everywhere, so it is not in the tooltip
                filter: (item) => item.dataset.label !== "Limit",
                callbacks: {
                    title: (items) => timeLabel(new Date(items[0].parsed.x), historyHours),
                    label: (item) => item.dataset.label === "Humidity"
                        ? ` Humidity: ${Math.round(item.parsed.y)} %`
                        : ` Temperature: ${item.parsed.y.toFixed(1)} °C`
                }
            }
        },
        scales: {
            // Time in milliseconds, shown as "14:05" (or "Mon 14:05" for a week)
            x: { type: "linear", ticks: { maxTicksLimit: 6, callback: (value) => timeLabel(new Date(value), historyHours) } },
            temp: { position: "left", suggestedMin: 0, ticks: { callback: (value) => `${value} °C` } },
            hum: { position: "right", min: 0, max: 100, grid: { display: false }, ticks: { callback: (value) => `${value} %` } }
        }
    }
});

// Average, lowest, highest and the share over the limit, for the time range on the chart.
// Uses every reading, not the averaged chart points, so the highest isn't averaged away
function showSummary(rows, limit) {
    const temps = rows.map((row) => row.temperature).filter((t) => t !== null);
    if (!temps.length) {
        page.querySelectorAll(".history-summary b").forEach((b) => { b.textContent = "--"; });
        return;
    }
    const average = temps.reduce((sum, t) => sum + t, 0) / temps.length;
    const overPercent = Math.round(temps.filter((t) => t > limit).length * 100 / temps.length);

    $(".sum-average").textContent = `${oneDecimal(average)} °C`;
    $(".sum-low").textContent = `${oneDecimal(Math.min(...temps))} °C`;
    $(".sum-high").textContent = `${oneDecimal(Math.max(...temps))} °C`;
    $(".sum-over").textContent = `${overPercent}%`;
    $(".sum-over").className = `sum-over ${overPercent > 0 ? "hot" : "ok"}`;
}

// Put the readings in the chart. rows come from /api/fridges/<id>/history.
function drawChart(rows) {
    const empty = rows.length === 0;
    $(".history-empty").hidden = !empty;
    $(".history-chart").style.opacity = empty ? 0.4 : 1;

    const end = Date.now(), start = end - historyHours * 3600 * 1000;
    const limit = latest ? latest.threshold : 0;
    const [temperature, humidity, limitLine] = historyChart.data.datasets;

    temperature.data = chartPoints(rows, "temperature");
    temperature.fill.target.value = limit;
    humidity.data = chartPoints(rows, "humidity");
    limitLine.data = [{ x: start, y: limit }, { x: end, y: limit }];

    // Always show the whole time range, even before the first reading. Leave room above the limit
    historyChart.options.scales.x.min = start;
    historyChart.options.scales.x.max = end;
    historyChart.options.scales.temp.suggestedMax = scaleTop(limit, ...temperature.data.map((point) => point.y));
    historyChart.update();
    showSummary(rows, limit);
}

// Get the saved readings for the chart
async function updateHistory() {
    try {
        const response = await fetch(`/api/fridges/${fridgeId}/history?hours=${historyHours}`, { cache: "no-store" });
        const rows = await response.json();
        if (response.ok) drawChart(rows);
    } catch (error) {
        // Keep showing the old chart if the server can't be reached
    }
}

page.querySelectorAll(".range-buttons button").forEach((button) => {
    button.addEventListener("click", () => {
        historyHours = Number(button.dataset.hours);
        page.querySelectorAll(".range-buttons button").forEach((b) => b.classList.toggle("active", b === button));
        updateHistory();
    });
});

update().then(updateHistory);
updateFan();
setInterval(update, 2000);
setInterval(updateFan, 2000);
setInterval(updateHistory, 60000); // a reading is saved once a minute
