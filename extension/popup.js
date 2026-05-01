// CVBoost popup — captures job text from the active tab and opens CVBoost.

const goBtn = document.getElementById("go");
const statusEl = document.getElementById("status");
const errorEl = document.getElementById("error");

async function captureAndOpen() {
    goBtn.disabled = true;
    errorEl.hidden = true;
    statusEl.textContent = "Leyendo la oferta...";

    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab?.id) throw new Error("No hay pestaña activa.");

        const results = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            files: ["content.js"],
        });

        const data = results?.[0]?.result;
        if (!data || !data.text || data.text.length < 80) {
            throw new Error(
                "No encontré texto de oferta en esta página. Asegúrate de estar en la página de la oferta concreta."
            );
        }

        await chrome.runtime.sendMessage({ type: "OPEN_CVBOOST", text: data.text });
        statusEl.textContent = "¡Listo! Abriendo CVBoost...";
        setTimeout(() => window.close(), 600);
    } catch (e) {
        errorEl.textContent = e?.message || "No pude leer la oferta. Inténtalo en otra página.";
        errorEl.hidden = false;
        goBtn.disabled = false;
        statusEl.textContent = "Lee la oferta abierta en esta pestaña y la analiza con CVBoost.";
    }
}

goBtn.addEventListener("click", captureAndOpen);
