const page = document.getElementById("fridge");
const fridgeId = page.dataset.id;
const message = document.getElementById("message");
const fanState = document.getElementById("fan-state");
const form = document.getElementById("threshold-form");

let latest = null;
let historyHours = 24;

function $(selector) {
    return page.querySelector(selector);
}

// -------------------------
// Gauges
// -------------------------

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

    // Numbers down the side
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

async function updateFan() {
    try {
        const response = await fetch("/api/fan", { cache: "no-store" });
        const result = await response.json();
        fanState.textContent = response.ok ? result.state : "UNKNOWN";
        fanState.className = result.state === "ON" ? "ok" : "";
    } catch (error) {
        fanState.textContent = "UNKNOWN";
    }
}

// -------------------------
// Change the limit
// -------------------------

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
        const response = await fetch(`/api/fridges/${fridgeId}/threshold`, { method: "POST", body: new FormData(form) });
        const result = await response.json();
        setMessage(message, result.error || result.success, result.error ? "danger" : "success");
        if (response.ok) {
            form.reset();
            update();
            updateHistory();
        }
    } catch (error) {
        setMessage(message, "Unable to save the limit. Please try again.");
    }
});

// -------------------------
// History chart
// -------------------------

const CHART_W = 1000, CHART_H = 240;

function parseTime(text) {
    return new Date(text.replace(" ", "T"));
}

// Line through the readings, with a break where the sensor was offline
function linePath(points, x, y) {
    let d = "", last = null;
    for (const point of points) {
        const jump = last === null || point.t - last > 5 * 60 * 1000;
        d += `${jump ? "M" : "L"}${x(point.t).toFixed(1)} ${y(point.v).toFixed(1)} `;
        last = point.t;
    }
    return d;
}

// Red boxes where the fridge was over the limit
function shadePath(points, limit, x) {
    let d = "", start = null, previous = null;
    for (const point of points) {
        if (point.v > limit && start === null) start = point.t;
        if (point.v <= limit && start !== null) {
            d += `M${x(start).toFixed(1)} 0 H${x(previous).toFixed(1)} V${CHART_H} H${x(start).toFixed(1)} Z `;
            start = null;
        }
        previous = point.t;
    }
    if (start !== null) d += `M${x(start).toFixed(1)} 0 H${x(previous).toFixed(1)} V${CHART_H} H${x(start).toFixed(1)} Z`;
    return d;
}

function timeLabel(date) {
    const time = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    if (historyHours <= 24) return time;
    return date.toLocaleDateString([], { weekday: "short" }) + " " + time;
}

function drawChart(rows) {
    const empty = rows.length === 0;
    $(".history-empty").hidden = !empty;
    $(".chart").style.opacity = empty ? 0.4 : 1;

    const end = Date.now(), start = end - historyHours * 3600 * 1000;
    const temps = rows.filter((r) => r.temperature !== null).map((r) => ({ t: parseTime(r.time).getTime(), v: r.temperature }));
    const hums = rows.filter((r) => r.humidity !== null).map((r) => ({ t: parseTime(r.time).getTime(), v: r.humidity }));
    const limit = latest ? latest.threshold : 0;
    const top = scaleTop(limit, ...temps.map((p) => p.v));

    const x = (t) => ((t - start) / (end - start)) * CHART_W;
    const yTemp = (v) => CHART_H - (Math.min(Math.max(v, 0), top) / top) * CHART_H;
    const yHum = (v) => CHART_H - (v / 100) * CHART_H;

    $(".chart-temp").setAttribute("d", linePath(temps, x, yTemp));
    $(".chart-hum").setAttribute("d", linePath(hums, x, yHum));
    $(".chart-shade").setAttribute("d", shadePath(temps, limit, x));
    $(".chart-limit").setAttribute("y1", yTemp(limit));
    $(".chart-limit").setAttribute("y2", yTemp(limit));

    $(".chart-y").replaceChildren(...[4, 3, 2, 1, 0].map((i) => {
        const span = document.createElement("span");
        span.textContent = `${Math.round(top * i / 4)}${i === 4 ? " °C" : ""}`;
        return span;
    }));
    $(".chart-x").replaceChildren(...[0, 1, 2, 3, 4].map((i) => {
        const span = document.createElement("span");
        span.textContent = i === 4 ? "now" : timeLabel(new Date(start + (end - start) * i / 4));
        return span;
    }));
}

async function updateHistory() {
    try {
        const response = await fetch(`/api/fridges/${fridgeId}/history?hours=${historyHours}`, { cache: "no-store" });
        const rows = await response.json();
        if (response.ok) drawChart(rows);
    } catch (error) {
        // keep showing the old chart if the server can't be reached
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
setInterval(update, 2000);         // newest reading every 2 seconds
setInterval(updateFan, 2000);
setInterval(updateHistory, 60000); // a new reading is saved every minute
