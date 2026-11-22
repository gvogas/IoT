// Shared settings for every Chart.js chart (chartjs.org). Load it after Chart.js and before the page's chart code

// The colours from theme.css, so the charts match the rest of the app
const styles = getComputedStyle(document.documentElement);
function themeColour(name) {
    return styles.getPropertyValue(name).trim();
}
const BLUE = themeColour("--arctic-blue");
const NAVY = themeColour("--arctic-navy");
const MIST = themeColour("--arctic-mist");
const SLATE = themeColour("--arctic-slate");
const MUTED = themeColour("--muted");
const LINE = themeColour("--line");
const DANGER = themeColour("--danger");
const DANGER_TINT = themeColour("--danger-tint");
const SUCCESS = themeColour("--success");
const WARNING = themeColour("--warning");

// For charts with one colour per slice, like sales by category. They repeat after the last one
const SLICE_COLOURS = [BLUE, NAVY, MIST, SUCCESS, WARNING, SLATE, DANGER];

// Every chart: the page's font, muted text and light grid lines
Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
Chart.defaults.color = MUTED;
Chart.defaults.borderColor = LINE;
// Fill the height of the chart's box (set in components.css) instead of keeping a fixed shape
Chart.defaults.maintainAspectRatio = false;
// The tooltip jumps straight to the mouse instead of sliding there, so it keeps up when the mouse moves fast
Chart.defaults.plugins.tooltip.animation.duration = 0;
Chart.defaults.transitions.active.animation.duration = 0;

// "$1,234.50", or "$1,234" without the cents
function dollars(amount, cents) {
    const digits = cents ? 2 : 0;
    return "$" + amount.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
