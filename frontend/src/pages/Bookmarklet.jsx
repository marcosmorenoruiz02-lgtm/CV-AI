import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Bookmark, CheckCircle2, Copy, MousePointer2 } from "lucide-react";
import ThemeToggle from "../components/ThemeToggle";

// Bookmarklet source (kept tidy on purpose)
// Reads the page's main content, normalises it, and opens CVBoost with the text pre-loaded.
const BOOKMARKLET_SOURCE = `(function(){
  var doc = document;
  var pickText = function(){
    var sels = ['main','article','[data-test="job-details"]','[data-job-description]','#job-details'];
    for (var i=0;i<sels.length;i++){var el=doc.querySelector(sels[i]);if(el && el.innerText && el.innerText.length>200) return el.innerText;}
    return doc.body ? doc.body.innerText : '';
  };
  var raw = pickText().replace(/\\s{2,}/g,' ').trim().slice(0,12000);
  if (!raw || raw.length < 80){ alert('CVBoost: no encontré texto de oferta en esta página.'); return; }
  var url = ORIGIN + '/?job_text=' + encodeURIComponent(raw) + '&from=bookmarklet';
  window.open(url, '_blank');
})();`;

export default function Bookmarklet() {
    const [copied, setCopied] = useState(false);

    const code = useMemo(() => {
        const origin =
            typeof window !== "undefined" ? window.location.origin : "https://cvboost.app";
        const compact = BOOKMARKLET_SOURCE.replace(/\s+/g, " ").replace(/\s*([{};,()=])\s*/g, "$1");
        const withOrigin = compact.replace(/ORIGIN/g, JSON.stringify(origin));
        return `javascript:${withOrigin}`;
    }, []);

    const copy = async () => {
        await navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="relative min-h-screen overflow-hidden">
            <div aria-hidden className="pointer-events-none absolute inset-0">
                <div className="absolute left-[-10%] top-[-10%] h-[400px] w-[400px] rounded-full bg-blue-200/40 blur-3xl dark:bg-blue-500/10" />
                <div className="absolute right-[-5%] bottom-[10%] h-[360px] w-[360px] rounded-full bg-emerald-200/30 blur-3xl dark:bg-emerald-500/10" />
            </div>

            <header className="glass-header">
                <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
                    <Link to="/" className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white">
                        <ArrowLeft className="h-4 w-4" /> Volver
                    </Link>
                    <ThemeToggle />
                </div>
            </header>

            <main className="relative mx-auto max-w-3xl px-6 py-12">
                <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4 }}
                >
                    <span className="badge-success">
                        <Bookmark className="h-4 w-4" /> Atajo de 1 click
                    </span>
                    <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-100 sm:text-4xl">
                        Importa cualquier oferta con{" "}
                        <span className="text-[#3B82F6]">1 click</span>
                    </h1>
                    <p className="mt-3 max-w-xl text-slate-600 dark:text-slate-300">
                        Arrastra este botón a la barra de marcadores. Cuando estés en una oferta de
                        LinkedIn, Indeed, InfoJobs o cualquier portal, púlsalo y CVBoost se abrirá con
                        la oferta ya cargada.
                    </p>

                    <div className="mt-8 flex flex-wrap items-center gap-4">
                        <a
                            href={code}
                            data-testid="bookmarklet-anchor"
                            onClick={(e) => e.preventDefault()}
                            draggable
                            className="inline-flex items-center gap-2 rounded-2xl border-2 border-blue-500 bg-blue-50 px-5 py-3 font-semibold text-blue-700 shadow-sm transition-all hover:bg-blue-100 dark:border-blue-400 dark:bg-blue-500/15 dark:text-blue-200 dark:hover:bg-blue-500/25"
                            title="Arrástrame a la barra de marcadores"
                        >
                            <MousePointer2 className="h-4 w-4" />
                            Analizar con CVBoost
                        </a>
                        <span className="text-sm text-slate-500 dark:text-slate-400">
                            ← Arrástralo a la barra de marcadores
                        </span>
                    </div>

                    <div className="mt-10 glass-panel p-6">
                        <h2 className="mb-3 text-lg font-semibold text-slate-900 dark:text-slate-100">
                            Cómo se instala (30 segundos)
                        </h2>
                        <ol className="space-y-3 text-sm text-slate-700 dark:text-slate-300">
                            {[
                                "Asegúrate de tener visible la barra de marcadores del navegador (Ctrl/Cmd + Shift + B en Chrome).",
                                "Arrastra el botón azul de arriba a tu barra de marcadores.",
                                "Visita una oferta en LinkedIn, Indeed, InfoJobs o donde sea.",
                                "Pulsa el marcador. CVBoost se abrirá con la oferta ya pegada. Solo te falta subir tu CV.",
                            ].map((step, i) => (
                                <li key={i} className="flex gap-3">
                                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-semibold text-blue-600 dark:bg-blue-500/20 dark:text-blue-300">
                                        {i + 1}
                                    </span>
                                    <span>{step}</span>
                                </li>
                            ))}
                        </ol>
                    </div>

                    <div className="mt-6 glass-panel p-6">
                        <div className="mb-3 flex items-center justify-between">
                            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                                ¿No te deja arrastrar? Copia el código manualmente
                            </h3>
                            <button
                                onClick={copy}
                                data-testid="copy-bookmarklet-btn"
                                className="btn-ghost !py-1.5 !px-3 text-xs"
                            >
                                {copied ? (
                                    <>
                                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> Copiado
                                    </>
                                ) : (
                                    <>
                                        <Copy className="h-3.5 w-3.5" /> Copiar
                                    </>
                                )}
                            </button>
                        </div>
                        <pre className="max-h-48 overflow-auto rounded-xl bg-slate-50 p-3 text-[11px] leading-relaxed text-slate-700 dark:bg-slate-950/60 dark:text-slate-300">
                            {code}
                        </pre>
                        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                            Crea un nuevo marcador a mano y pega esto en el campo URL. El nombre puede
                            ser "Analizar con CVBoost".
                        </p>
                    </div>
                </motion.div>
            </main>
        </div>
    );
}
