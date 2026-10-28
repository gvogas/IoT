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

function timeAgo(seconds) {
    if (seconds < 60) return `${seconds} s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
    return `${Math.floor(seconds / 3600)} h ago`;
}

function duration(minutes) {
    if (minutes < 60) return `${minutes} min`;
    return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}

// Top of the temperature scale
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
    if (status === "offline") return `The sensor stopped sending ${timeAgo(fridge.age)}. Check the ESP32.`;

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

// The server says 403 when nobody is signed in as admin (a restart of the app signs everyone out)
function showSignedOut(message) {
    const link = document.createElement("a");
    link.href = "/signin";
    link.textContent = "Sign in again";
    message.replaceChildren("You are signed out (the app may have restarted). ", link);
    message.style.color = "red";
}

// Show the status with its coloured dot
function setStatus(element, status) {
    element.className = `fridge-status ${status}`;
    element.querySelector(".status-text").textContent = STATUS_TEXT[status];
}

// Show the trend
function setTrend(element, stats) {
    const trend = trendInfo(stats);
    element.className = `trend ${trend.rising ? "hot" : "muted"}`;
    element.querySelector(".trend-arrow").style.transform = `rotate(${trend.angle}deg)`;
    element.querySelector(".trend-arrow").style.visibility = trend.known ? "visible" : "hidden";
    element.querySelector(".trend-text").textContent = trend.text;
}
