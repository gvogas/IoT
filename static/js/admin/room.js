// The MSP01 sensor cards (the sensor is in Fridge 3) on the dashboard. Asks /api/room every 5 seconds

// Seconds with no message before the sensor counts as offline
const ROOM_OFFLINE_AFTER = 60;

// The light bar is full at this many lux (a bright shop is about 500)
const LIGHT_FULL = 1000;

const roomMessage = document.getElementById("room-message");
const hoursDiv = document.getElementById("room-hours");

function byId(id) {
    return document.getElementById(id);
}

// "5 s ago", "3 min ago", "2 h ago"
function roomTimeAgo(seconds) {
    if (seconds < 60) return `${seconds} s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
    return `${Math.floor(seconds / 3600)} h ago`;
}

// One decimal, or "--" if there is no value
function roomDecimal(value) {
    return value === null ? "--" : value.toFixed(1);
}

// "24 h: 19.5 to 23.1 °C", or "24 h: --" before the first saved reading
function rangeText(low, high, unit, decimals) {
    if (low === null || high === null) return "24 h: --";
    return `24 h: ${low.toFixed(decimals)} to ${high.toFixed(decimals)} ${unit}`;
}

// A word for the light level
function lightWord(lux) {
    if (lux < 50) return "Dark";
    if (lux < 300) return "Dim";
    return "Bright";
}

// Make the 24 bars of the hour chart once
function makeHourBars() {
    for (let hour = 0; hour < 24; hour++) {
        const bar = document.createElement("div");
        bar.className = "hour-bar";
        bar.innerHTML = '<div class="hour-fill"></div>';
        hoursDiv.appendChild(bar);
    }
}

// Waiting, Live or Offline, with its coloured dot
function showRoomStatus(age) {
    let status = "ok", text = "Live";
    if (age === null) {
        status = "waiting";
        text = "Waiting";
    } else if (age > ROOM_OFFLINE_AFTER) {
        status = "offline";
        text = "Offline";
    }
    byId("room-status").className = `fridge-status ${status}`;
    byId("room-status").querySelector(".status-text").textContent = text;
    byId("room-age").textContent = age === null ? "No reading yet" : `Last reading ${roomTimeAgo(age)}`;
}

// The light card. The sensor sends lux, or only light / dark on some versions
function showLight(room, stats) {
    const icon = byId("room-light-icon");
    if (room.light !== null) {
        byId("room-light").textContent = Math.round(room.light);
        byId("room-light-unit").textContent = `lux · ${lightWord(room.light)}`;
        byId("room-light-bar").style.width = `${Math.min(room.light, LIGHT_FULL) / LIGHT_FULL * 100}%`;
        icon.className = room.light < 50 ? "bi bi-moon" : "bi bi-brightness-high";
    } else if (room.bright !== null) {
        byId("room-light").textContent = room.bright ? "Light" : "Dark";
        byId("room-light-unit").textContent = "";
        byId("room-light-bar").style.width = room.bright ? "100%" : "0%";
        icon.className = room.bright ? "bi bi-brightness-high" : "bi bi-moon";
    }
    byId("room-light-range").textContent = rangeText(stats.minLight, stats.maxLight, "lux", 0);
}

// The motion card and the hour chart
function showMotion(room, stats) {
    byId("room-motion").textContent = room.motion ? "Motion now" : "No motion";
    byId("room-motion-card").classList.toggle("moving", room.motion);
    byId("room-motion-icon").className = `stat-icon ${room.motion ? "good" : ""}`;
    byId("room-last-motion").textContent = stats.lastMotionAge === null
        ? "No motion yet"
        : `Last motion ${roomTimeAgo(stats.lastMotionAge)}`;

    byId("room-visits").textContent = stats.motionToday;

    // Each bar's height is its count as a percent of the busiest hour. "|| 1" stops a divide by zero
    const busiest = Math.max(...stats.motionByHour) || 1;
    const thisHour = new Date().getHours();
    hoursDiv.querySelectorAll(".hour-bar").forEach((bar, hour) => {
        const count = stats.motionByHour[hour];
        bar.classList.toggle("now", hour === thisHour);
        bar.title = `${hour}:00 to ${hour}:59: ${count} ${count === 1 ? "time" : "times"}`;
        bar.querySelector(".hour-fill").style.height = `${count * 100 / busiest}%`;
    });
}

// Get the newest readings and show them
async function updateRoom() {
    try {
        const response = await fetch("/api/room", { cache: "no-store" });
        const room = await response.json();
        if (!response.ok) {
            setMessage(roomMessage, room.error);
            return;
        }
        setMessage(roomMessage, "");
        const stats = room.stats;

        showRoomStatus(room.age);
        byId("room-battery").textContent = room.battery === null ? "--" : Math.round(room.battery);
        byId("room-rssi").textContent = room.rssi === null ? "--" : Math.round(room.rssi);

        byId("room-temp").textContent = roomDecimal(room.temperature);
        byId("room-temp-range").textContent = rangeText(stats.minTemp, stats.maxTemp, "°C", 1);

        byId("room-hum").textContent = room.humidity === null ? "--" : Math.round(room.humidity);
        byId("room-hum-bar").style.width = `${room.humidity === null ? 0 : Math.min(room.humidity, 100)}%`;
        byId("room-hum-range").textContent = rangeText(stats.minHum, stats.maxHum, "%", 0);

        showLight(room, stats);
        showMotion(room, stats);
    } catch (error) {
        setMessage(roomMessage, "Cannot reach the server.");
    }
}

makeHourBars();
updateRoom();
setInterval(updateRoom, 5000);
