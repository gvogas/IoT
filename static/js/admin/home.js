// The fridge cards on the dashboard. Asks /api/fridges every 2 seconds and changes the numbers.
// fridgeStatus(), setStatus(), oneDecimal() and timeAgo() come from static/js/fridges/common.js

async function updateFridgeCards() {
    try {
        const response = await fetch("/api/fridges", { cache: "no-store" });
        if (!response.ok) return;
        const fridges = await response.json();

        for (const fridge of fridges) {
            const card = document.querySelector(`[data-fridge-id="${fridge.id}"]`);
            if (!card) continue;
            const status = fridgeStatus(fridge);

            setStatus(card.querySelector(".fridge-status"), status);
            card.classList.toggle("hot", status === "hot");
            card.querySelector(".temp").textContent = oneDecimal(fridge.temperature);
            card.querySelector(".hum").textContent = fridge.humidity === null ? "--" : Math.round(fridge.humidity);
            card.querySelector(".last-reading").textContent = fridge.age === null
                ? "No reading yet"
                : `Last reading ${timeAgo(fridge.age)}`;
        }
    } catch (error) {
        // Keep showing the last numbers if the server can't be reached
    }
}

updateFridgeCards();
setInterval(updateFridgeCards, 2000);
