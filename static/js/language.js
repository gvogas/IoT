// Language picker in the menu (English, French, Farsi, Greek, Italian, Dutch,
// Mandarin, Hakka, Arabic, Vietnamese, Hindi). Google Translate does the translating
// Google remembers the chosen language in a cookie called "googtrans", like "/en/fr"
// The pages are written in English, so with no cookie the page stays in English

const LANGUAGES = ["en", "fr", "fa", "el", "it", "nl", "zh-CN", "hak", "ar", "vi", "hi"];

// Farsi and Arabic are written right to left
const RIGHT_TO_LEFT = ["fa", "ar"];

// Read the language from the cookie. No cookie means English
function currentLanguage() {
    const match = document.cookie.match(/(?:^|;\s*)googtrans=\/en\/([\w-]+)/);
    if (match && LANGUAGES.includes(match[1])) return match[1];
    return "en";
}

// Save the language in the cookie. No expiry date, so it goes back to English when the browser is closed
function saveLanguage(language) {
    if (language === "en") {
        // Remove the cookie. Google sometimes saves it on the domain too, so remove both
        const expired = "googtrans=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        document.cookie = expired;
        document.cookie = `${expired}; domain=${location.hostname}`;
    } else {
        document.cookie = `googtrans=/en/${language}; path=/`;
    }
}

// Google calls this once its script has loaded. It translates the page using the cookie
function googleTranslateElementInit() {
    new google.translate.TranslateElement({
        pageLanguage: "en",
        includedLanguages: LANGUAGES.join(","),
        autoDisplay: false
    }, "google_translate_element");
}

const languageSelect = document.getElementById("language-select");
const language = currentLanguage();
languageSelect.value = language;

// Picking a language saves it and reloads the page, so Google can translate it from the start
languageSelect.addEventListener("change", () => {
    saveLanguage(languageSelect.value);
    location.reload();
});

// Only load Google's script when the page needs translating. In English nothing extra is loaded
if (language !== "en") {
    if (RIGHT_TO_LEFT.includes(language)) document.documentElement.dir = "rtl";

    const script = document.createElement("script");
    script.src = "https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit";
    document.body.appendChild(script);
}
