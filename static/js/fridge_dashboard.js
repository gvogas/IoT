const fridgesDiv = document.getElementById("fridges");
const message = document.getElementById("message");
const alertsDiv = document.getElementById("alerts");
const fanState = document.getElementById("fan-state");
const fanMessage = document.getElementById("fan-message");
const fanOff = document.getElementById("fan-off");
const fanImage = document.getElementById("fan-image");



const TEMP_MIN = -5;    
const TEMP_MAX = 25;    
const HUM_MIN = 0;
const HUM_MAX = 100;

const cards = {};

async function updateFan() {
    if (fanOff.disabled) return;
    try {
        const response = await fetch("/api/fan", { cache: "no-store" });
        const result = await response.json();
        if (!fanOff.disabled) {
            setFanState(response.ok ? result.state : "UNKNOWN");
        }
    } catch (error) {
        if (!fanOff.disabled) setFanState("UNKNOWN")
    }
}

fanOff.addEventListener("click", async () => {
    fanOff.disabled = true;
    fanMessage.textContent = "";
    try {
        const response = await fetch("/api/fan/off", { method: "POST" });
        const result = await response.json();
        setFanState(response.ok ? result.state : "UNKNOWN");
        fanMessage.textContent = result.error || result.success;
    } catch (error) {
        setFanState("UNKNOWN");
        fanMessage.textContent = "Unable to reach the server. Fan off is not confirmed.";
    } finally {
        fanOff.disabled = false;
    }
});

// Make one card for each fridge (only the first time)
async function updateAlerts() {
    try {
        const response = await fetch("/api/alerts", { cache: "no-store" });
        const alerts = await response.json();
        if (!response.ok) return;
 
        alertsDiv.replaceChildren();
        for (const alert of alerts) {
            const p = document.createElement("p");
            if (alert.status === "sent") {
                p.textContent = `${alert.name} temperature high. Email sent to ${alert.email} at ${alert.time}.`;
                p.style.color = "darkorange";
            } else {
                p.textContent = `${alert.name} temperature high. Failed to send email to ${alert.email}.`;
                p.style.color = "red";
            }
            alertsDiv.appendChild(p);
        }
    } catch (error) {
        // keep showing the current alerts if the server can't be reached
    }
}
 
 
// For the needle
function fraction(value, min, max) {
    return (Math.min(Math.max(value, min), max) - min) / (max - min);
}
 
// Make one card for each fridge (only the first time)
function makeCard(fridge) {
    const template = document.getElementById("fridge-template");
    const card = template.content.firstElementChild.cloneNode(true);
 
    card.querySelector(".fridge-name").textContent = fridge.name;
    fridgesDiv.appendChild(card);
    cards[fridge.id] = card;
 
    const form = card.querySelector("form");
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        try {
            const response = await fetch(`/api/fridges/${fridge.id}/threshold`, {
                method: "POST",
                body: new FormData(form)
            });
            const result = await response.json();
            message.textContent = `${fridge.name}: ${result.error || result.success}`;
            message.style.color = result.error ? "red" : "green";
            if (response.ok) {
                form.reset();
                update();
            }
        } catch (error) {
            message.textContent = "Unable to save the threshold. Please try again.";
            message.style.color = "red";
        }
    });
}

// Get the latest readings from the server and show them
async function update() {
    try {
        const response = await fetch("/api/fridges");
        const fridges = await response.json();
        if (!response.ok) {
            message.textContent = fridges.error;
            message.style.color = "red";
            return;
        }
 
        for (const fridge of fridges) {
            if (!cards[fridge.id]) makeCard(fridge);
            const card = cards[fridge.id];
 
            card.querySelector(".temp").textContent = fridge.temperature ?? "--";
            card.querySelector(".hum").textContent = fridge.humidity ?? "--";
            card.querySelector(".threshold").textContent = fridge.threshold;
 
            // Thermometer: fill level, threshold marker, red when too warm
            const thermo = card.querySelector(".thermo");
            const temp = parseFloat(fridge.temperature);
            const threshold = parseFloat(fridge.threshold);
 
            if (!Number.isNaN(threshold)) {
                thermo.style.setProperty("--threshold-level", fraction(threshold, TEMP_MIN, TEMP_MAX));
            }
            if (!Number.isNaN(temp)) {
                thermo.style.setProperty("--level", fraction(temp, TEMP_MIN, TEMP_MAX));
                card.classList.toggle("hot", !Number.isNaN(threshold) && temp > threshold);
            }
 
            // Humidity needle
            const hum = parseFloat(fridge.humidity);
            if (!Number.isNaN(hum)) {
                card.querySelector(".dial").style
                    .setProperty("--level", fraction(hum, HUM_MIN, HUM_MAX));
            }
        }
    } catch (error) {
        message.textContent = "Cannot reach the server.";
        message.style.color = "red";
    }
}

update();
updateFan();
updateAlerts();
setInterval(updateFan, 2000);
setInterval(update, 2000);  // refresh every 2 seconds
setInterval(updateAlerts, 2000);