// Seconds with no reading before a sensor counts as offline
const OFFLINE_AFTER = 15;

const STATUS_TEXT = { waiting: "Waiting", offline: "Offline", hot: "Too warm", ok: "OK" };

// Gives back "waiting", "offline", "hot" or "ok"
function fridgeStatus(fridge) {
    if (fridge.age === null) return "waiting";
    if (fridge.age > OFFLINE_AFTER) return "offline";
    if (fridge.temperature !== null && fridge.threshold !== null && fridge.temperature > fridge.threshold) return "hot";
    return "ok";
}

// One decimal, or "--" if there is no value
function oneDecimal(value) {
    return value === null || value === undefined ? "--" : value.toFixed(1);
}

// "5 s ago", "3 min ago", "2 h ago"
function timeAgo(seconds) {
    if (seconds < 60) return `${seconds} s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
    return `${Math.floor(seconds / 3600)} h ago`;
}

// "45 min" or "1 h 20 min"
function duration(minutes) {
    if (minutes < 60) return `${minutes} min`;
    return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}

// Top of the temperature scale: the first step that fits every value with 2 degrees to spare
function scaleTop(...values) {
    const highest = Math.max(...values.filter((v) => v !== null && v !== undefined));
    for (const top of [12, 20, 40, 60, 100]) {
        if (highest + 2 <= top) return top;
    }
    return 100;
}

// Text and arrow direction for the trend
function trendInfo(stats) {
    if (!stats || stats.trend === null) return { text: "trend after 10 min of readings", angle: 0, rising: false, known: false };
    if (Math.abs(stats.trend) < 1) return { text: "steady", angle: 0, rising: false, known: true };
    return {
        text: `${stats.trend > 0 ? "rising" : "falling"} ${Math.abs(stats.trend).toFixed(1)} °C / hour`,
        angle: stats.trend > 0 ? -45 : 45,
        rising: stats.trend > 0,
        known: true,
    };
}

// One sentence about the fridge
function fridgeSentence(fridge, fanState) {
    const status = fridgeStatus(fridge);
    if (status === "waiting") return "No reading from the sensor yet.";
    if (status === "offline") return `The sensor stopped sending ${timeAgo(fridge.age)}. Check the ${fridge.sensor}.`;

    const stats = fridge.stats || {};
    const diff = Math.abs(fridge.temperature - fridge.threshold).toFixed(1);
    const parts = [];

    if (status === "hot") {
        let text = `${diff} °C over the ${fridge.threshold.toFixed(1)} °C limit`;
        if (stats.overSince) text += ` since ${stats.overSince.time} (${duration(stats.overSince.minutes)})`;
        parts.push(text + ".");
        if (fridge.alert) {
            parts.push(fridge.alert.status === "sent"
                ? `Alert emailed at ${fridge.alert.time}.`
                : "The alert email failed to send.");
        }
        if (fanState === "ON") parts.push("Fan is on.");
    } else {
        parts.push(`${diff} °C under the ${fridge.threshold.toFixed(1)} °C limit.`);
        if (stats.overTodayMinutes) parts.push(`Was over the limit for ${duration(stats.overTodayMinutes)} today.`);
        else if (stats.inRange !== null && stats.inRange !== undefined) parts.push("In range all day.");
    }
    return parts.join(" ");
}

// For the history charts: a gap longer than this means the sensor was offline, so the line stops there (milliseconds)
const GAP = 5 * 60 * 1000;

// "2026-11-06 15:03:43" -> Date
function parseTime(text) {
    return new Date(text.replace(" ", "T"));
}

// A time on a chart, like "14:05". With more than 24 hours on the chart, the day too, like "Mon 14:05"
function timeLabel(date, hours) {
    const time = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    if (hours <= 24) return time;
    return date.toLocaleDateString([], { weekday: "short" }) + " " + time;
}

// Most points drawn on one chart line. A day has 1440 readings and a week 10080, which makes the chart
// slow on the Pi. This is still more points than the chart is wide, so the line looks the same
const MAX_POINTS = 400;

// The points of one chart line from /api/fridges/<id>/history rows, like [{ x: time in ms, y: 4.5 }, ...].
// name is "temperature" or "humidity". With more than MAX_POINTS readings, readings next to each other
// are averaged into one point. A point with y: null goes in each long gap, which makes Chart.js stop the line there
function chartPoints(rows, name) {
    const readings = rows
        .filter((row) => row[name] !== null)
        .map((row) => ({ x: parseTime(row.time).getTime(), y: row[name] }));
    // How many readings go into one point: 1 for an hour, 4 for a day, 26 for a week
    const groupSize = Math.ceil(readings.length / MAX_POINTS);

    const points = [];
    let group = [];
    for (let i = 0; i < readings.length; i++) {
        group.push(readings[i]);
        const next = readings[i + 1];
        const isLast = next === undefined;
        const gapAfter = !isLast && next.x - readings[i].x > GAP;

        // A group ends when it is full, at a gap, or at the last reading. A gap always ends a group,
        // so readings from before and after the sensor was offline are never averaged together
        if (group.length === groupSize || gapAfter || isLast) {
            const average = group.reduce((sum, reading) => sum + reading.y, 0) / group.length;
            points.push({ x: group[0].x, y: average });
            if (gapAfter) points.push({ x: readings[i].x + 1, y: null });
            group = [];
        }
    }
    return points;
}

// Settings for the history line charts that keep them quick on the Pi
const FAST_LINE_CHART = {
    // No animation: the chart is drawn again every minute
    animation: false,
    // The points are already { x, y } and sorted by time, so Chart.js can skip checking them
    parsing: false,
    normalized: true,
    // No dots on the lines, only the lines
    elements: { point: { radius: 0, hitRadius: 6 } }
};

// The server says 403 when nobody is signed in as admin (a restart of the app signs everyone out)
function showSignedOut(message) {
    const link = document.createElement("a");
    link.href = "/signin";
    link.className = "alert-link";
    link.textContent = "Sign in again";
    setMessage(message, ["You are signed out (the app may have restarted). ", link]);
}

// Show the status with its coloured dot. Other classes on the element, like ms-auto, stay
function setStatus(element, status) {
    element.classList.remove(...Object.keys(STATUS_TEXT));
    element.classList.add(status);
    element.querySelector(".status-text").textContent = STATUS_TEXT[status];
}

// Show the trend arrow and text
function setTrend(element, stats) {
    const trend = trendInfo(stats);
    element.className = `trend ${trend.rising ? "hot" : ""}`;
    element.querySelector(".trend-arrow").style.transform = `rotate(${trend.angle}deg)`;
    element.querySelector(".trend-arrow").style.visibility = trend.known ? "visible" : "hidden";
    element.querySelector(".trend-text").textContent = trend.text;
}

// The fan button only turns the fan off, so it only shows while the fan is on.
// Turning the fan on is done by replying YES to the alert email
function showFanButton(button, state) {
    button.hidden = state !== "ON";
}

// Ask the server for the fan state and whether the MQTT broker is reachable.
// Gives back { state, broker, signedOut, offline }. broker is null when we don't know
async function fetchFan() {
    try {
        const response = await fetch("/api/fan", { cache: "no-store" });
        const result = await response.json();
        if (response.status === 403) return { state: "UNKNOWN", broker: null, signedOut: true, offline: false };
        if (!response.ok) return { state: "UNKNOWN", broker: null, signedOut: false, offline: false };
        return { state: result.state, broker: result.broker, signedOut: false, offline: false };
    } catch (error) {
        return { state: "UNKNOWN", broker: null, signedOut: false, offline: true };
    }
}

// Turn the fan off. Gives back the new state
async function pressFanButton(button) {
    // Say what is happening while the request is on its way, so nobody presses twice
    const label = button.textContent;
    button.disabled = true;
    button.textContent = "Turning off...";
    try {
        const response = await fetch("/api/fan/off", { method: "POST" });
        const result = await response.json();
        showToast(result.error || result.success, result.error ? "danger" : "success");
        return response.ok ? result.state : "UNKNOWN";
    } catch (error) {
        showToast("Cannot reach the server. The fan may not have turned off.", "danger");
        return "UNKNOWN";
    } finally {
        button.disabled = false;
        button.textContent = label;
    }
}

// The warning shown when the app can't reach the MQTT broker
const BROKER_DOWN = "Can't reach the MQTT broker, so no new readings are coming in. Check that Mosquitto is running and MQTT_BROKER in config.py.";

// Show or hide the broker warning. Only changes the page when it changes, so screen readers don't repeat it
function showBroker(element, connected) {
    const text = connected ? "" : BROKER_DOWN;
    if (element.textContent !== text) setMessage(element, text, "warning");
}
