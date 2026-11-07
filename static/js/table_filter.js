// Search, filter and sort for the inventory, products and units tables.
// The search box has data-search, each row has data-search-row with its text in data-search,
// and a heading with data-sort sorts its column

const searchBox = document.querySelector("[data-search]");
const rows = [...document.querySelectorAll("[data-search-row]")];

if (searchBox && rows.length) {
    const chips = [...document.querySelectorAll("[data-status-filter]")];
    const categoryBox = document.querySelector("[data-category-filter]");
    const count = document.querySelector("[data-count]");
    const empty = document.querySelector("[data-empty]");
    let status = "all";

    function applyFilters() {
        const words = searchBox.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
        const category = categoryBox ? categoryBox.value : "";
        let shown = 0;
        rows.forEach((row) => {
            row.hidden = !(words.every((word) => row.dataset.search.includes(word))
                && (status === "all" || row.dataset.status === status)
                && (!category || row.dataset.category === category));
            if (!row.hidden) shown++;
        });
        if (count) count.textContent = `Showing ${shown} of ${rows.length}`;
        if (empty) empty.hidden = shown > 0;
    }

    searchBox.addEventListener("input", applyFilters);
    if (categoryBox) categoryBox.addEventListener("change", applyFilters);

    chips.forEach((chip) => {
        // Each button says how many rows it will show
        const value = chip.dataset.statusFilter;
        const number = document.createElement("span");
        number.className = "chip-count";
        number.textContent = value === "all" ? rows.length : rows.filter((row) => row.dataset.status === value).length;
        chip.append(number);

        chip.addEventListener("click", () => {
            status = value;
            chips.forEach((other) => {
                other.classList.toggle("active", other === chip);
                other.setAttribute("aria-pressed", String(other === chip));
            });
            applyFilters();
        });
    });
    applyFilters();
}

// Click a heading to sort by that column, and again to flip the order
document.querySelectorAll("th[data-sort]").forEach((heading) => {
    const body = heading.closest("table").tBodies[0];

    function cellValue(row) {
        const cell = row.cells[heading.cellIndex];
        return cell.dataset.sortValue ?? cell.textContent.trim();
    }

    heading.querySelector("button").addEventListener("click", () => {
        const direction = heading.getAttribute("aria-sort") === "ascending" ? -1 : 1;
        const number = (text) => Number(text.replace(/[^0-9.-]/g, ""));
        const sorted = [...body.rows].sort((a, b) => {
            const [x, y] = [cellValue(a), cellValue(b)];
            return direction * (heading.dataset.sort === "number" ? number(x) - number(y) : x.localeCompare(y, undefined, { numeric: true }));
        });
        body.append(...sorted);

        heading.closest("tr").querySelectorAll("th[data-sort]").forEach((other) => {
            other.removeAttribute("aria-sort");
            other.querySelector("i").className = "bi bi-chevron-expand";
        });
        heading.setAttribute("aria-sort", direction === 1 ? "ascending" : "descending");
        heading.querySelector("i").className = `bi bi-chevron-${direction === 1 ? "up" : "down"}`;
    });
});
