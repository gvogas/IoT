// The MSP01 sensor's light and motion cards, on the page of the fridge it is in (Fridge 3). Asks /api/room every 2 seconds.
// The fridge page already shows its temperature and humidity

// Seconds with no message before the sensor counts as offline
const ROOM_OFFLINE_AFTER = 60;

// The light bar is full at this many lux (a bright shop is about 500)
const LIGHT_FULL = 1000;

const roomMessage = document.getElementById("room-message");

function byId(id) {
    return document.getElementById(id);
}

// "5 s ago", "3 min ago", "2 h ago"
function roomTimeAgo(seconds) {
    if (seconds < 60) return `${seconds} s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
    return `${Math.floor(seconds / 3600)} h ago`;
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

// "12 am", "1 am" ... "11 pm"
function hourName(hour) {
    const suffix = hour < 12 ? "am" : "pm";
    return `${hour % 12 === 0 ? 12 : hour % 12} ${suffix}`;
}

// The "Motion today" chart: one bar per hour, made once with Chart.js and filled in by showMotion().
// Colours come from static/js/charts.js
const hourChart = new Chart(document.getElementById("room-hours"), {
    type: "bar",
    data: {
        // Only every 6th hour has a label under it, so they fit
        labels: Array.from({ length: 24 }, (_, hour) => (hour % 6 === 0 ? hourName(hour) : "")),
        datasets: [{ label: "Motion", data: new Array(24).fill(0), backgroundColor: BLUE, borderRadius: 3 }]
    },
    options: {
        // No animation, because the numbers are filled in again every 2 seconds
        animation: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                callbacks: {
                    // "2 pm to 3 pm" and "3 times"
                    title: (items) => `${hourName(items[0].dataIndex)} to ${hourName((items[0].dataIndex + 1) % 24)}`,
                    label: (item) => `${item.raw} ${item.raw === 1 ? "time" : "times"}`
                }
            }
        },
        scales: {
            x: { grid: { display: false }, ticks: { autoSkip: false, maxRotation: 0 } },
            // Whole numbers only: someone can't move 1.5 times
            y: { beginAtZero: true, ticks: { precision: 0 } }
        }
    }
});

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

    // New numbers for the chart. The hour we are in is dark
    const thisHour = new Date().getHours();
    const bars = hourChart.data.datasets[0];
    bars.data = stats.motionByHour;
    bars.backgroundColor = stats.motionByHour.map((count, hour) => (hour === thisHour ? NAVY : BLUE));
    hourChart.update();
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

        showLight(room, stats);
        showMotion(room, stats);
    } catch (error) {
        setMessage(roomMessage, "Cannot reach the server.");
    }
}

updateRoom();
setInterval(updateRoom, 2000);
