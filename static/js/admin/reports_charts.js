// The two charts on the Reports page. Colours, the font and dollars() come from static/js/charts.js
// salesBars and categories come from the page (templates/admin/reports.html)

// Sales per day or per month. Each bar is { label: "5", title: "Nov 05", sales: 120.5 }:
// label is under the bar, title is in the tooltip
const salesCanvas = document.getElementById("sales-chart");
if (salesCanvas) {
    // The best bar is dark, like today's bar on the dashboard
    const best = Math.max(...salesBars.map((bar) => bar.sales));

    new Chart(salesCanvas, {
        type: "bar",
        data: {
            labels: salesBars.map((bar) => bar.label),
            datasets: [{
                label: "Sales before tax",
                data: salesBars.map((bar) => bar.sales),
                backgroundColor: salesBars.map((bar) => (bar.sales > 0 && bar.sales === best ? NAVY : BLUE)),
                borderRadius: 4,
                // So one or two bars don't fill the whole card
                maxBarThickness: 56
            }]
        },
        options: {
            plugins: {
                // Only one set of bars, so no legend
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        // "Nov 05" at the top of the tooltip, instead of the short label under the bar
                        title: (items) => salesBars[items[0].dataIndex].title,
                        label: (item) => dollars(item.raw, true)
                    }
                }
            },
            scales: {
                // Show every label. Most days have an empty one, so they don't crowd (see sales_chart() in models/report.py)
                x: { grid: { display: false }, ticks: { autoSkip: false, maxRotation: 0 } },
                // Whole dollars only, so a quiet week doesn't show "$0, $0, $1, $1"
                y: { beginAtZero: true, ticks: { precision: 0, callback: (value) => dollars(value, false) } }
            }
        }
    });
}

// Sales by category, as a doughnut. Each category is { categoryName: "Drink", sales: 80.5, units: 12 }
const categoryCanvas = document.getElementById("category-chart");
if (categoryCanvas) {
    new Chart(categoryCanvas, {
        type: "doughnut",
        data: {
            labels: categories.map((category) => category.categoryName),
            datasets: [{
                data: categories.map((category) => category.sales),
                backgroundColor: categories.map((category, i) => SLICE_COLOURS[i % SLICE_COLOURS.length]),
                // A white gap between the slices
                borderColor: "#fff",
                borderWidth: 2
            }]
        },
        options: {
            // How big the hole in the middle is
            cutout: "60%",
            plugins: {
                legend: { position: "right", labels: { boxWidth: 12 } },
                tooltip: { callbacks: { label: (item) => ` ${item.label}: ${dollars(item.raw, true)}` } }
            }
        }
    });
}
