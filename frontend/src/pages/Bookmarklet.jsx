import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
    ArrowLeft,
    Bookmark,
    CheckCircle2,
    Copy,
    Download,
    Keyboard,
    MousePointer2,
    Puzzle,
    Sparkles,
    Zap,
} from "lucide-react";
import ThemeToggle from "../components/ThemeToggle";

// Bookmarklet fallback (kept for users who can't install extensions, e.g. corporate Chromebooks).
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

export default function Install() {
    const [copied, setCopied] = useState(false);

    const bookmarkletCode = useMemo(() => {
        const origin =
            typeof window !== "undefined" ? window.location.origin : "https://cvboost.app";
        const compact = BOOKMARKLET_SOURCE.replace(/\s+/g, " ").replace(/\s*([{};,()=])\s*/g, "$1");
        const withOrigin = compact.replace(/ORIGIN/g, JSON.stringify(origin));
        return `javascript:${withOrigin}`;
    }, []);

    const copyBookmarklet = async () => {
        await navigator.clipboard.writeText(bookmarkletCode);
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
                    <Link
                        to="/"
                        className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white"
                        data-testid="back-link"
                    >
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
                        <Zap className="h-4 w-4" /> Atajo oficial
                    </span>
                    <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-900 dark:text-slate-100 sm:text-4xl">
                        Instala CVBoost en tu navegador
                    </h1>
                    <p className="mt-3 max-w-xl text-slate-600 dark:text-slate-300">
                        Analiza cualquier oferta de empleo con un solo click. Sin copiar y pegar, sin
                        salir de la página.
                    </p>

                    {/* Chrome extension card (primary) */}
                    <section className="glass-panel mt-8 p-6" data-testid="extension-card">
                        <div className="mb-4 flex items-start gap-4">
                            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-blue-500 text-white shadow-lg shadow-blue-500/30">
                                <Puzzle className="h-6 w-6" strokeWidth={1.6} />
                            </div>
                            <div>
                                <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
                                    Extensión de Chrome
                                </h2>
                                <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                                    Recomendada. Icono propio en el navegador y atajo de teclado.
                                </p>
                            </div>
                        </div>

                        <ul className="mb-5 space-y-2 text-sm text-slate-700 dark:text-slate-300">
                            <li className="flex items-start gap-2">
                                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                                <span>Compatible con LinkedIn, Indeed, InfoJobs, Glassdoor y Welcome to the Jungle.</span>
                            </li>
                            <li className="flex items-start gap-2">
                                <Keyboard className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                                <span>
                                    Atajo: <strong>Ctrl + Shift + B</strong> (Mac: <strong>Cmd + Shift + B</strong>).
                                </span>
                            </li>
                            <li className="flex items-start gap-2">
                                <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                                <span>
                                    Tu CV no se sube automáticamente. Solo pasa el texto de la oferta a CVBoost.
                                </span>
                            </li>
                        </ul>

                        <a
                            href="/cvboost-extension.zip"
                            download="cvboost-extension.zip"
                            data-testid="download-extension-btn"
                            className="btn-primary"
                        >
                            <Download className="h-4 w-4" /> Descargar extensión (.zip)
                        </a>

                        <details className="mt-5 rounded-2xl border border-slate-100 bg-white/60 p-4 text-sm dark:border-slate-800 dark:bg-slate-900/60">
                            <summary className="cursor-pointer font-medium text-slate-800 dark:text-slate-100">
                                Cómo instalarla (1 minuto)
                            </summary>
                            <ol className="mt-3 space-y-3 text-slate-700 dark:text-slate-300">
                                {[
                                    "Descomprime el zip que acabas de bajar en una carpeta cualquiera.",
                                    "Abre Chrome y ve a chrome://extensions",
                                    "Activa el interruptor 'Modo desarrollador' (arriba a la derecha).",
                                    "Pulsa 'Cargar descomprimida' y selecciona la carpeta del zip.",
                                    "Verás el icono de CVBoost en la barra. Fija el icono y listo.",
                                ].map((step, i) => (
                                    <li key={i} className="flex gap-3">
                                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-semibold text-blue-600 dark:bg-blue-500/20 dark:text-blue-300">
                                            {i + 1}
                                        </span>
                                        <span>{step}</span>
                                    </li>
                                ))}
                            </ol>
                            <p className="mt-3 rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-500/10 dark:text-amber-300">
                                Cuando publiquemos en Chrome Web Store podrás instalarla con 1 click.
                                Mientras tanto, este modo manual funciona perfecto.
                            </p>
                        </details>
                    </section>

                    {/* Bookmarklet fallback */}
                    <section className="glass-panel mt-6 p-6" data-testid="bookmarklet-card">
                        <div className="mb-4 flex items-start gap-4">
                            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                                <Bookmark className="h-6 w-6" strokeWidth={1.6} />
                            </div>
                            <div>
                                <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
                                    Marcador de un click
                                </h2>
                                <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                                    Para Firefox, Safari u ordenadores donde no puedes instalar extensiones.
                                </p>
                            </div>
                        </div>

                        <div className="mb-4 flex flex-wrap items-center gap-3">
                            <a
                                href={bookmarkletCode}
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

                        <details className="rounded-2xl border border-slate-100 bg-white/60 p-4 text-sm dark:border-slate-800 dark:bg-slate-900/60">
                            <summary className="cursor-pointer font-medium text-slate-800 dark:text-slate-100">
                                ¿No te deja arrastrar? Pega el código manualmente
                            </summary>
                            <div className="mt-3">
                                <div className="mb-2 flex items-center justify-end">
                                    <button
                                        onClick={copyBookmarklet}
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
                                <pre className="max-h-40 overflow-auto rounded-xl bg-slate-50 p-3 text-[11px] leading-relaxed text-slate-700 dark:bg-slate-950/60 dark:text-slate-300">
                                    {bookmarkletCode}
                                </pre>
                                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                                    Crea un marcador nuevo y pega esto en el campo URL. Ponle de nombre
                                    "Analizar con CVBoost".
                                </p>
                            </div>
                        </details>
                    </section>
                </motion.div>
            </main>
        </div>
    );
}
