import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    UploadCloud,
    Loader2,
    Target,
    Sparkles,
    AlertCircle,
    ArrowRight,
    CheckCircle2,
    FileText,
    Zap,
} from "lucide-react";
import axios from "axios";
import ThemeToggle from "../components/ThemeToggle";
import { API } from "../lib/api";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
const startGoogleLogin = () => {
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
};

export default function Landing() {
    const [view, setView] = useState("hero"); // hero | loading | result | error
    const [result, setResult] = useState(null);
    const [error, setError] = useState("");
    const [dragOver, setDragOver] = useState(false);
    const fileRef = useRef(null);

    const onUpload = async (file) => {
        if (!file) return;
        if (!file.name.toLowerCase().endsWith(".pdf")) {
            setError("Solo aceptamos PDF por ahora.");
            setView("error");
            return;
        }
        if (file.size > 8 * 1024 * 1024) {
            setError("Tu PDF supera los 8 MB. Comprímelo y vuelve a subirlo.");
            setView("error");
            return;
        }
        setView("loading");
        setError("");
        const fd = new FormData();
        fd.append("file", file);
        try {
            const { data } = await axios.post(`${API}/quick-analyze`, fd, {
                headers: { "Content-Type": "multipart/form-data" },
                timeout: 90000,
            });
            setResult(data);
            setView("result");
            window.scrollTo({ top: 0, behavior: "smooth" });
        } catch (err) {
            setError(
                err?.response?.data?.detail ||
                    "No pudimos analizar tu CV. Vuelve a intentarlo en unos segundos.",
            );
            setView("error");
        }
    };

    const onDrop = (e) => {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer?.files?.[0];
        if (file) onUpload(file);
    };

    return (
        <div className="relative min-h-screen overflow-hidden" data-testid="landing-page">
            {/* Ambient blobs */}
            <div aria-hidden className="pointer-events-none absolute inset-0">
                <div className="absolute left-[-10%] top-[-10%] h-[480px] w-[480px] rounded-full bg-blue-200/50 blur-3xl dark:bg-blue-500/10" />
                <div className="absolute right-[-5%] top-[20%] h-[420px] w-[420px] rounded-full bg-emerald-200/40 blur-3xl dark:bg-emerald-500/10" />
                <div className="absolute bottom-[-10%] left-[30%] h-[360px] w-[360px] rounded-full bg-sky-200/40 blur-3xl dark:bg-sky-500/10" />
            </div>

            <header className="glass-header">
                <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
                    <div className="flex items-center gap-2">
                        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#3B82F6] text-white shadow-lg shadow-blue-500/30">
                            <Target className="h-5 w-5" strokeWidth={2} />
                        </div>
                        <span className="font-[Outfit] text-lg font-semibold text-slate-900 dark:text-slate-100">
                            Estrategia de Asalto
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <ThemeToggle />
                        <button
                            data-testid="header-login-btn"
                            onClick={startGoogleLogin}
                            className="btn-ghost"
                        >
                            Entrar
                        </button>
                    </div>
                </div>
            </header>

            <main className="relative mx-auto max-w-6xl px-6 pb-24 pt-12 sm:pt-16">
                <AnimatePresence mode="wait">
                    {view === "hero" && (
                        <motion.section
                            key="hero"
                            initial={{ opacity: 0, y: 16 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -16 }}
                            transition={{ duration: 0.35 }}
                            className="grid grid-cols-1 items-center gap-10 lg:grid-cols-12"
                        >
                            <div className="lg:col-span-6">
                                <span className="badge-success" data-testid="hero-badge">
                                    <Zap className="h-4 w-4" /> Análisis gratis · sin registro
                                </span>
                                <h1 className="mt-5 text-4xl font-semibold tracking-tight text-slate-900 dark:text-slate-100 sm:text-5xl lg:text-6xl">
                                    Tu CV no pasa los{" "}
                                    <span className="relative inline-block">
                                        <span className="relative z-10 text-[#3B82F6]">filtros ATS</span>
                                        <span className="absolute bottom-1 left-0 right-0 z-0 h-3 rounded-md bg-blue-100/80 dark:bg-blue-500/20" />
                                    </span>
                                    .
                                </h1>
                                <p className="mt-5 max-w-xl text-lg leading-relaxed text-slate-600 dark:text-slate-300">
                                    Te decimos por qué y cómo arreglarlo en 30 segundos. Sin login, sin
                                    rollos.
                                </p>
                                <div className="mt-6 hidden items-center gap-2 lg:flex">
                                    <ArrowRight className="h-4 w-4 text-blue-500" />
                                    <span className="text-sm text-slate-500 dark:text-slate-400">
                                        Suelta tu CV en el panel de la derecha
                                    </span>
                                </div>
                            </div>

                            <div className="lg:col-span-6">
                                <UploadCard
                                    fileRef={fileRef}
                                    dragOver={dragOver}
                                    setDragOver={setDragOver}
                                    onUpload={onUpload}
                                    onDrop={onDrop}
                                />
                            </div>
                        </motion.section>
                    )}

                    {view === "loading" && (
                        <motion.section
                            key="loading"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="mx-auto flex max-w-2xl flex-col items-center pt-12 text-center"
                            data-testid="loading-section"
                        >
                            <div className="glass-panel w-full p-10">
                                <Loader2 className="mx-auto mb-4 h-10 w-10 animate-spin text-blue-500" />
                                <h2 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
                                    Analizando tu CV...
                                </h2>
                                <p className="mt-2 text-slate-600 dark:text-slate-300">
                                    Mirándolo como lo haría un ATS y un reclutador a la vez.
                                </p>
                                <ProgressLoader />
                            </div>
                        </motion.section>
                    )}

                    {view === "result" && result && (
                        <motion.section
                            key="result"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                            data-testid="result-section"
                        >
                            <ResultPanel
                                result={result}
                                onTryAgain={() => {
                                    setResult(null);
                                    setView("hero");
                                }}
                            />
                        </motion.section>
                    )}

                    {view === "error" && (
                        <motion.section
                            key="error"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="mx-auto max-w-xl pt-16"
                            data-testid="error-section"
                        >
                            <div className="glass-panel flex flex-col items-center p-10 text-center">
                                <AlertCircle className="mb-3 h-10 w-10 text-red-500" />
                                <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
                                    No pudimos analizarlo
                                </h2>
                                <p className="mt-2 text-slate-600 dark:text-slate-300">{error}</p>
                                <button
                                    data-testid="retry-btn"
                                    onClick={() => setView("hero")}
                                    className="btn-primary mt-6"
                                >
                                    Probar de nuevo
                                </button>
                            </div>
                        </motion.section>
                    )}
                </AnimatePresence>

                {/* How it works */}
                {view === "hero" && (
                    <section id="how-it-works" className="mt-24">
                        <h2 className="mb-10 text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100 sm:text-3xl">
                            Cómo funciona.
                        </h2>
                        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
                            {[
                                {
                                    n: "1",
                                    icon: UploadCloud,
                                    title: "Subes tu CV",
                                    desc: "PDF, sin login. Tarda 2 segundos.",
                                },
                                {
                                    n: "2",
                                    icon: Sparkles,
                                    title: "Lo analizamos con IA + ATS",
                                    desc: "Score real, problemas reales, lenguaje cercano.",
                                },
                                {
                                    n: "3",
                                    icon: CheckCircle2,
                                    title: "Te damos mejoras exactas",
                                    desc: "Antes vs después. Listo para copiar y pegar.",
                                },
                            ].map((s) => (
                                <div key={s.n} className="glass-panel p-6">
                                    <div className="mb-3 flex items-center gap-3">
                                        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-50 text-sm font-semibold text-blue-600 dark:bg-blue-500/15 dark:text-blue-300">
                                            {s.n}
                                        </span>
                                        <s.icon className="h-5 w-5 text-blue-500" strokeWidth={1.5} />
                                    </div>
                                    <h3 className="mb-1 text-lg font-semibold text-slate-900 dark:text-slate-100">
                                        {s.title}
                                    </h3>
                                    <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                                        {s.desc}
                                    </p>
                                </div>
                            ))}
                        </div>

                        {/* Fake preview */}
                        <div className="mt-12">
                            <h3 className="mb-3 text-sm font-medium uppercase tracking-wider text-slate-400 dark:text-slate-500">
                                Ejemplo real de output
                            </h3>
                            <FakePreview />
                        </div>

                        <div className="mt-14 flex flex-col items-center gap-3 text-center">
                            <h2 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 sm:text-3xl">
                                Optimiza tu CV ahora.
                            </h2>
                            <button
                                data-testid="cta-bottom-upload-btn"
                                onClick={() => fileRef.current?.click()}
                                className="btn-primary !py-3.5 !px-7 text-base"
                            >
                                <UploadCloud className="h-5 w-5" />
                                Sube tu CV gratis
                            </button>
                            <p className="text-xs text-slate-500 dark:text-slate-400">
                                Sin tarjeta. Sin registro. Tu CV no se almacena en este modo.
                            </p>
                        </div>
                    </section>
                )}
            </main>

            <footer className="border-t border-slate-200/60 py-8 dark:border-slate-800/60">
                <div className="mx-auto max-w-7xl px-6 text-sm text-slate-500 dark:text-slate-400">
                    © {new Date().getFullYear()} Estrategia de Asalto · Hecho para quienes juegan a ganar.
                </div>
            </footer>
        </div>
    );
}

function UploadCard({ fileRef, dragOver, setDragOver, onUpload, onDrop }) {
    return (
        <div className="glass-panel p-6">
            <div className="mb-4 flex items-center gap-2">
                <span className="badge-success">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    Tarda menos de 30 segundos
                </span>
            </div>
            <div
                data-testid="hero-dropzone"
                onClick={() => fileRef.current?.click()}
                onDragOver={(e) => {
                    e.preventDefault();
                    setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={onDrop}
                className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-10 text-center transition-all ${
                    dragOver
                        ? "border-blue-400 bg-blue-50/60 dark:border-blue-400 dark:bg-blue-500/10"
                        : "border-slate-300 bg-white/40 hover:border-blue-300 hover:bg-blue-50/40 dark:border-slate-700 dark:bg-slate-900/40 dark:hover:border-blue-500/60 dark:hover:bg-blue-500/5"
                }`}
            >
                <input
                    ref={fileRef}
                    type="file"
                    accept="application/pdf"
                    className="hidden"
                    onChange={(e) => onUpload(e.target.files?.[0])}
                    data-testid="hero-file-input"
                />
                <UploadCloud className="mb-3 h-10 w-10 text-blue-500" strokeWidth={1.4} />
                <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                    Sube tu CV gratis
                </p>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    Arrastra el PDF aquí o haz clic
                </p>
                <span className="mt-5 inline-flex items-center gap-1 rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-600 dark:bg-blue-500/15 dark:text-blue-300">
                    <FileText className="h-3.5 w-3.5" /> Solo PDF · máx. 8 MB
                </span>
            </div>
            <div className="mt-3 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                <span>No guardamos tu CV en este modo</span>
                <button
                    onClick={startGoogleLogin}
                    className="underline-offset-2 hover:underline"
                    data-testid="hero-account-link"
                >
                    ¿Ya tienes cuenta?
                </button>
            </div>
        </div>
    );
}

function ProgressLoader() {
    return (
        <div className="mt-6 space-y-3 text-left">
            {["Leyendo el PDF...", "Extrayendo experiencia y skills...", "Calculando score ATS..."].map((label, i) => (
                <div key={label} className="space-y-1">
                    <div className="text-xs font-medium uppercase tracking-wider text-slate-400 dark:text-slate-500">
                        {label}
                    </div>
                    <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: "92%" }}
                        transition={{ duration: 1.2 + i * 0.4, delay: i * 0.3, ease: "easeOut" }}
                        className="h-2 rounded-full bg-gradient-to-r from-blue-300 to-emerald-300 dark:from-blue-500 dark:to-emerald-500"
                    />
                </div>
            ))}
        </div>
    );
}

function FakePreview() {
    return (
        <div className="glass-panel p-6">
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h4 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                        Score ATS
                    </h4>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                        Ejemplo de informe (no es tu CV)
                    </p>
                </div>
                <ScoreCircle value={62} label="Aceptable" />
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-red-100 bg-red-50/60 p-4 dark:border-red-500/30 dark:bg-red-500/10">
                    <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-red-700 dark:text-red-300">
                        Problemas
                    </div>
                    <ul className="space-y-1.5 text-sm text-slate-700 dark:text-slate-200">
                        <li>• Falta de keywords del puesto</li>
                        <li>• Experiencia poco clara</li>
                        <li>• Verbos sin impacto medible</li>
                    </ul>
                </div>
                <div className="rounded-2xl border border-emerald-100 bg-emerald-50/60 p-4 dark:border-emerald-500/30 dark:bg-emerald-500/10">
                    <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-emerald-700 dark:text-emerald-300">
                        Ejemplo de mejora
                    </div>
                    <p className="text-sm text-slate-500 line-through dark:text-slate-400">
                        Responsable de ventas
                    </p>
                    <p className="mt-1 text-sm font-medium text-slate-900 dark:text-slate-100">
                        Incrementé ventas un 32% en 6 meses lanzando 3 nuevos canales
                    </p>
                </div>
            </div>
        </div>
    );
}

function ResultPanel({ result, onTryAgain }) {
    const score = result.final_score ?? 0;
    const tone = score >= 80 ? "Excelente" : score >= 60 ? "Aceptable" : score >= 40 ? "Mejorable" : "Necesita arreglos";
    return (
        <div className="space-y-6">
            <div className="glass-panel p-6">
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <span className="badge-success">
                            <CheckCircle2 className="h-4 w-4" /> Tu informe está listo
                        </span>
                        <h2 className="mt-3 text-2xl font-semibold text-slate-900 dark:text-slate-100 sm:text-3xl">
                            Score ATS de tu CV
                        </h2>
                        {result.detected_role && (
                            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                                Detectamos perfil: <strong className="text-slate-700 dark:text-slate-200">{result.detected_role}</strong>
                            </p>
                        )}
                    </div>
                    <ScoreCircle value={score} label={tone} large />
                </div>
                {result.summary && (
                    <p className="mt-5 text-slate-700 dark:text-slate-200">{result.summary}</p>
                )}
                <div className="mt-5 grid grid-cols-3 gap-3">
                    <MiniScore label="ATS" value={result.ats_score} />
                    <MiniScore label="Formato" value={result.format_score} />
                    <MiniScore label="Keywords" value={result.keyword_score} />
                </div>
            </div>

            {result.problems?.length > 0 && (
                <div className="glass-panel p-6">
                    <h3 className="mb-3 text-lg font-semibold text-slate-900 dark:text-slate-100">
                        Lo que falla en tu CV
                    </h3>
                    <ul className="space-y-2">
                        {result.problems.map((p, i) => (
                            <li
                                key={i}
                                className="flex gap-3 rounded-xl border border-red-100 bg-red-50/40 px-4 py-3 text-sm text-slate-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-slate-200"
                            >
                                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
                                <span>{p}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {result.top_improvements?.length > 0 && (
                <div className="glass-panel p-6">
                    <h3 className="mb-4 text-lg font-semibold text-slate-900 dark:text-slate-100">
                        Mejoras concretas (antes → después)
                    </h3>
                    <div className="space-y-4">
                        {result.top_improvements.map((imp, i) => (
                            <div
                                key={i}
                                className="rounded-2xl border border-slate-100 bg-white/60 p-4 dark:border-slate-800 dark:bg-slate-900/60"
                            >
                                <div className="mb-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                                    {imp.title}
                                </div>
                                {imp.before && (
                                    <p className="text-sm text-slate-500 line-through dark:text-slate-500">
                                        {imp.before}
                                    </p>
                                )}
                                {imp.after && (
                                    <p className="mt-1 text-sm font-medium text-emerald-700 dark:text-emerald-300">
                                        → {imp.after}
                                    </p>
                                )}
                                {imp.why && (
                                    <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{imp.why}</p>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {result.missing_keywords?.length > 0 && (
                <div className="glass-panel p-6">
                    <h3 className="mb-3 text-lg font-semibold text-slate-900 dark:text-slate-100">
                        Keywords que probablemente te faltan
                    </h3>
                    <div className="flex flex-wrap gap-2">
                        {result.missing_keywords.map((k) => (
                            <span
                                key={k}
                                className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 ring-1 ring-blue-100 dark:bg-blue-500/15 dark:text-blue-300 dark:ring-blue-500/30"
                            >
                                {k}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            <div className="glass-panel flex flex-col items-center gap-3 p-8 text-center">
                <h3 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
                    ¿Quieres cruzar tu CV con una oferta concreta?
                </h3>
                <p className="max-w-md text-sm text-slate-600 dark:text-slate-300">
                    Crea una cuenta gratis y obtén un plan de ataque por cada oferta que te interese.
                </p>
                <div className="mt-2 flex flex-wrap justify-center gap-3">
                    <button
                        data-testid="result-create-account-btn"
                        onClick={startGoogleLogin}
                        className="btn-primary"
                    >
                        Crear cuenta gratis
                        <ArrowRight className="h-4 w-4" />
                    </button>
                    <button
                        data-testid="result-try-again-btn"
                        onClick={onTryAgain}
                        className="btn-ghost"
                    >
                        Analizar otro CV
                    </button>
                </div>
            </div>
        </div>
    );
}

function MiniScore({ label, value }) {
    const v = Number(value || 0);
    return (
        <div className="rounded-2xl border border-slate-100 bg-white/60 p-3 text-center dark:border-slate-800 dark:bg-slate-900/60">
            <div className="text-xs font-medium uppercase tracking-wider text-slate-400 dark:text-slate-500">
                {label}
            </div>
            <div className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-100">{v}</div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${v}%` }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                    className="h-full rounded-full bg-gradient-to-r from-blue-400 to-emerald-400"
                />
            </div>
        </div>
    );
}

function ScoreCircle({ value, label, large = false }) {
    const v = Math.max(0, Math.min(100, Number(value) || 0));
    const size = large ? 110 : 88;
    const stroke = large ? 9 : 7;
    const r = (size - stroke) / 2;
    const c = 2 * Math.PI * r;
    const dash = c * (v / 100);
    const color = v >= 80 ? "#10B981" : v >= 60 ? "#3B82F6" : v >= 40 ? "#F59E0B" : "#EF4444";
    return (
        <div className="flex items-center gap-3" data-testid="score-circle">
            <svg width={size} height={size} className="-rotate-90">
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={r}
                    stroke="currentColor"
                    strokeWidth={stroke}
                    fill="none"
                    className="text-slate-200 dark:text-slate-800"
                />
                <motion.circle
                    cx={size / 2}
                    cy={size / 2}
                    r={r}
                    stroke={color}
                    strokeWidth={stroke}
                    fill="none"
                    strokeLinecap="round"
                    initial={{ strokeDasharray: `0 ${c}` }}
                    animate={{ strokeDasharray: `${dash} ${c}` }}
                    transition={{ duration: 1.0, ease: "easeOut" }}
                />
            </svg>
            <div>
                <div className="text-3xl font-semibold text-slate-900 dark:text-slate-100">{v}</div>
                <div className="text-xs uppercase tracking-wider text-slate-400 dark:text-slate-500">
                    {label}
                </div>
            </div>
        </div>
    );
}
