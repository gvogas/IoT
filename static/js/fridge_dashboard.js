const fridgesDiv = document.getElementById("fridges");
const message = document.getElementById("message");
const fanState = document.getElementById("fan-state");
const fanMessage = document.getElementById("fan-message");
const fanOff = document.getElementById("fan-off");
const fanImage = document.getElementById("fan-image");

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
function makeCard(fridge) {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
        <h3></h3>
        <p>Temperature: <span class="big" id="temp-${fridge.id}">--</span> °C</p>
        <p>Humidity: <span id="hum-${fridge.id}">--</span> %</p>
        <p>Threshold: <span id="threshold-${fridge.id}">--</span> °C</p>
        <form id="form-${fridge.id}">
            <label>New threshold:</label>
            <input type="number" step="0.5" name="threshold" required>
            <button type="submit">Save</button>
        </form>
    `;
    // textContent shows the name as plain text, so it can't turn into HTML
    card.querySelector("h3").textContent = fridge.name;
    fridgesDiv.appendChild(card);

    // Save a new threshold
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
            if (!document.getElementById(`temp-${fridge.id}`)) {
                makeCard(fridge);
            }
            document.getElementById(`temp-${fridge.id}`).textContent = fridge.temperature ?? "--";
            document.getElementById(`hum-${fridge.id}`).textContent = fridge.humidity ?? "--";
            document.getElementById(`threshold-${fridge.id}`).textContent = fridge.threshold;

        }
    } catch (error) {
        message.textContent = "Cannot reach the server.";
        message.style.color = "red";
    }
}

function setFanState(state) {
    fanState.textContent = state;

    if (state === "ON") {
        fanImage.src = fanImage.dataset.onSrc;
        fanImage.alt = "Fan is on";
    } else if (state === "OFF") {
        fanImage.src = fanImage.dataset.offSrc;
        fanImage.alt = "Fan is off";
    } else {
        // UNKNOWN: pick whichever default you prefer
        fanImage.src = fanImage.dataset.offSrc;
        fanImage.alt = "Fan status unknown";
    }
}

update();
updateFan();
setInterval(updateFan, 2000);
setInterval(update, 2000);  // refresh every 2 seconds
