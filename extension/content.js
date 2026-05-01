// CVBoost extension — content extractor.
// Runs in the page context via chrome.scripting.executeScript.
// Returns the most likely job description text.

(function () {
    const SELECTORS = [
        // LinkedIn
        '.show-more-less-html__markup',
        '.jobs-description__container',
        '.jobs-box__html-content',
        '[data-test="job-details"]',
        // Indeed
        '#jobDescriptionText',
        '[data-testid="jobsearch-JobComponent-description"]',
        // InfoJobs
        '.description',
        '[data-test="job-description"]',
        // Glassdoor
        '.jobDescriptionContent',
        '[data-test="jobDescriptionText"]',
        // Welcome to the Jungle
        '.sc-bdVaJa',
        // Generic
        'main',
        'article',
        '[role="main"]',
    ];

    function pickBestText() {
        for (const sel of SELECTORS) {
            const el = document.querySelector(sel);
            const text = el?.innerText?.trim() || '';
            if (text && text.length > 250) return text;
        }
        return (document.body?.innerText || '').trim();
    }

    const raw = pickBestText().replace(/\s{2,}/g, ' ').trim().slice(0, 12000);
    return {
        text: raw,
        url: location.href,
        title: document.title || '',
    };
})();
