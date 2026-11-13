// Category and producer boxes: suggest known names as you type, closest first
document.querySelectorAll("[data-combo]").forEach((combo) => {
    const input = combo.querySelector("input");
    const menu = combo.querySelector("[data-combo-menu]");
    const toggle = combo.querySelector("[data-combo-toggle]");
    const names = JSON.parse(input.dataset.options);
    const SHOW = 8;
    let shown = [];
    let active = -1;

    // Lower is better: exact, starts with, a word starts with, anywhere. -1 means no match
    function rank(name, query) {
        const lower = name.toLowerCase();
        if (lower === query) return 0;
        if (lower.startsWith(query)) return 1;
        if (lower.split(/\s+/).some((word) => word.startsWith(query))) return 2;
        if (lower.includes(query)) return 3;
        return -1;
    }

    // Put the chosen name in the box and close the list
    function choose(name) {
        input.value = name;
        menu.hidden = true;
        input.setAttribute("aria-expanded", "false");
    }

    // showAll is true when the dropdown button was pressed: the whole list, not just the closest matches
    function render(showAll) {
        const query = input.value.trim().toLowerCase();
        let matches = names
            .map((name) => ({ name, score: query && !showAll ? rank(name.toLowerCase(), query) : 0 }))
            .filter((match) => match.score >= 0)
            .sort((a, b) => a.score - b.score || a.name.localeCompare(b.name));
        if (!showAll) matches = matches.slice(0, SHOW);
        shown = matches.map((match) => match.name);
        active = -1;
        menu.replaceChildren();

        shown.forEach((name) => {
            const item = document.createElement("button");
            item.type = "button";
            item.className = "dropdown-item";
            item.setAttribute("role", "option");
            item.textContent = name;
            // mousedown (not click) so the box doesn't lose focus before the choice is made
            item.addEventListener("mousedown", (event) => {
                event.preventDefault();
                choose(name);
            });
            menu.appendChild(item);
        });

        const typed = input.value.trim();
        const exact = names.some((name) => name.toLowerCase() === typed.toLowerCase());
        if (!showAll && typed && !exact) {
            const note = document.createElement("div");
            note.className = "dropdown-item-text small text-secondary";
            note.textContent = `New: "${typed}" will be added`;
            menu.appendChild(note);
        }

        menu.hidden = menu.children.length === 0;
        input.setAttribute("aria-expanded", String(!menu.hidden));
    }

    // Mark one suggestion for the arrow keys
    function highlight(index) {
        const items = menu.querySelectorAll("[role='option']");
        items.forEach((item, i) => item.classList.toggle("active", i === index));
        if (items[index]) items[index].scrollIntoView({ block: "nearest" });
        active = index;
    }

    // Keep the focus in the box when the button is pressed, so the list doesn't close first
    toggle.addEventListener("mousedown", (event) => event.preventDefault());
    toggle.addEventListener("click", () => {
        if (!menu.hidden) {
            menu.hidden = true;
            return;
        }
        input.focus();
        render(true);
    });

    input.addEventListener("input", () => render(false));
    input.addEventListener("focus", () => render(false));
    input.addEventListener("blur", () => { menu.hidden = true; });
    input.addEventListener("keydown", (event) => {
        if (menu.hidden) return;
        if (event.key === "ArrowDown") {
            event.preventDefault();
            highlight(Math.min(active + 1, shown.length - 1));
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            highlight(Math.max(active - 1, 0));
        } else if (event.key === "Enter" && active >= 0) {
            event.preventDefault();
            choose(shown[active]);
        } else if (event.key === "Escape") {
            menu.hidden = true;
        }
    });
});
