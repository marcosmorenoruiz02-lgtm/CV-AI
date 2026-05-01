// CVBoost extension — service worker.
// Receives requests from the popup and opens CVBoost with the captured text.

const CVBOOST_ORIGIN = "https://career-assault.preview.emergentagent.com";

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.type === "OPEN_CVBOOST" && typeof msg.text === "string") {
        const url = `${CVBOOST_ORIGIN}/?job_text=${encodeURIComponent(msg.text)}&from=extension`;
        chrome.tabs.create({ url }, () => sendResponse({ ok: true }));
        return true;
    }
});
