import { motion } from "framer-motion";
import { Sparkles, Target, FileUp, LineChart, ArrowRight } from "lucide-react";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
const startGoogleLogin = () => {
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
};

const container = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: { staggerChildren: 0.08, delayChildren: 0.1 },
    },
};

const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
};

const features = [
    {
        icon: Target,
        title: "Radiografía del Puesto",
        desc: "Descifra el problema real detrás de cada oferta antes de postularte.",
    },
    {
        icon: LineChart,
        title: "Análisis de Gap",
        desc: "Mapeo de habilidades transferibles para argumentar cada fortaleza.",
    },
    {
        icon: FileUp,
        title: "CV en PDF",
        desc: "Sube tu CV y tu perfil se completa automáticamente con IA.",
    },
    {
        icon: Sparkles,
        title: "Estrategia de Asalto",
        desc: "Un mensaje de LinkedIn persuasivo, listo para enviar al hiring manager.",
    },
];

export default function Landing() {
    return (
        <div className="relative min-h-screen overflow-hidden" data-testid="landing-page">
            {/* Ambient blobs */}
            <div aria-hidden className="pointer-events-none absolute inset-0">
                <div className="absolute left-[-10%] top-[-10%] h-[480px] w-[480px] rounded-full bg-blue-200/50 blur-3xl" />
                <div className="absolute right-[-5%] top-[20%] h-[420px] w-[420px] rounded-full bg-emerald-200/40 blur-3xl" />
                <div className="absolute bottom-[-10%] left-[30%] h-[360px] w-[360px] rounded-full bg-sky-200/40 blur-3xl" />
            </div>

            <header className="glass-header">
                <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
                    <div className="flex items-center gap-2">
                        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#3B82F6] text-white shadow-lg shadow-blue-500/30">
                            <Target className="h-5 w-5" strokeWidth={2} />
                        </div>
                        <span className="font-[Outfit] text-lg font-semibold text-slate-900">
                            Estrategia de Asalto
                        </span>
                    </div>
                    <button
                        data-testid="header-login-btn"
                        onClick={startGoogleLogin}
                        className="btn-ghost"
                    >
                        Entrar
                    </button>
                </div>
            </header>

            <main className="relative mx-auto max-w-7xl px-6 pb-24 pt-16 sm:pt-24">
                <motion.section
                    variants={container}
                    initial="hidden"
                    animate="show"
                    className="grid grid-cols-1 items-center gap-12 lg:grid-cols-12"
                >
                    <div className="lg:col-span-7">
                        <motion.div variants={item} className="mb-5">
                            <span className="badge-success" data-testid="hero-badge">
                                <Sparkles className="h-4 w-4" /> Powered by GPT-5.2
                            </span>
                        </motion.div>

                        <motion.h1
                            variants={item}
                            className="text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl lg:text-6xl"
                        >
                            Convierte cada oferta en una{" "}
                            <span className="relative inline-block">
                                <span className="relative z-10 text-[#3B82F6]">estrategia ganadora</span>
                                <span className="absolute bottom-1 left-0 right-0 z-0 h-3 rounded-md bg-blue-100/80" />
                            </span>
                            .
                        </motion.h1>

                        <motion.p
                            variants={item}
                            className="mt-6 max-w-xl text-lg leading-relaxed text-slate-600"
                        >
                            Un headhunter de élite y experto en ATS trabajando para ti. Sube tu
                            CV, pega la oferta y recibe un informe accionable en segundos.
                        </motion.p>

                        <motion.div variants={item} className="mt-8 flex flex-wrap items-center gap-3">
                            <button
                                data-testid="hero-login-btn"
                                onClick={startGoogleLogin}
                                className="btn-primary group"
                            >
                                <GoogleIcon />
                                Entrar con Google
                                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                            </button>
                            <a
                                href="#features"
                                data-testid="learn-more-link"
                                className="text-sm font-medium text-slate-600 underline-offset-4 hover:text-slate-900 hover:underline"
                            >
                                Ver cómo funciona
                            </a>
                        </motion.div>

                        <motion.div
                            variants={item}
                            className="mt-10 flex items-center gap-5 text-sm text-slate-500"
                        >
                            <div className="flex -space-x-2">
                                {["#3B82F6", "#10B981", "#0EA5E9"].map((c) => (
                                    <span
                                        key={c}
                                        className="inline-block h-7 w-7 rounded-full border-2 border-white"
                                        style={{ background: c }}
                                    />
                                ))}
                            </div>
                            <span>Datos privados. Sin anuncios. Sin ruido.</span>
                        </motion.div>
                    </div>

                    <motion.div variants={item} className="lg:col-span-5">
                        <FloatingReportCard />
                    </motion.div>
                </motion.section>

                <section id="features" className="mt-28">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.5 }}
                        className="mb-10 max-w-2xl"
                    >
                        <h2 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
                            Un informe, cinco bloques accionables.
                        </h2>
                        <p className="mt-3 text-slate-600">
                            Diseñado para quienes no postulan a ciegas.
                        </p>
                    </motion.div>

                    <motion.div
                        variants={container}
                        initial="hidden"
                        whileInView="show"
                        viewport={{ once: true, amount: 0.2 }}
                        className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4"
                    >
                        {features.map((f) => (
                            <motion.div
                                key={f.title}
                                variants={item}
                                whileHover={{ y: -4 }}
                                className="glass-panel p-6"
                                data-testid={`feature-${f.title.toLowerCase().replace(/\s+/g, "-")}`}
                            >
                                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                                    <f.icon className="h-5 w-5" strokeWidth={1.7} />
                                </div>
                                <h3 className="mb-2 text-lg font-semibold text-slate-900">
                                    {f.title}
                                </h3>
                                <p className="text-sm leading-relaxed text-slate-600">{f.desc}</p>
                            </motion.div>
                        ))}
                    </motion.div>
                </section>

                <section className="mt-28">
                    <div className="glass-panel flex flex-col items-center gap-4 p-10 text-center">
                        <h2 className="max-w-2xl text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
                            La diferencia entre postular y ser contratado está en la estrategia.
                        </h2>
                        <p className="max-w-lg text-slate-600">
                            Entra gratis y genera tu primer informe en menos de un minuto.
                        </p>
                        <button
                            data-testid="cta-login-btn"
                            onClick={startGoogleLogin}
                            className="btn-primary mt-2"
                        >
                            <GoogleIcon /> Empezar ahora
                        </button>
                    </div>
                </section>
            </main>

            <footer className="border-t border-slate-200/60 py-8">
                <div className="mx-auto max-w-7xl px-6 text-sm text-slate-500">
                    © {new Date().getFullYear()} Estrategia de Asalto · Hecho para quienes juegan a ganar.
                </div>
            </footer>
        </div>
    );
}

function GoogleIcon() {
    return (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" className="h-5 w-5" aria-hidden="true">
            <path
                fill="#FFC107"
                d="M43.6 20.5H42V20H24v8h11.3c-1.6 4.7-6.1 8-11.3 8-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.1 8 3l5.7-5.7C34.1 6 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.2-.1-2.3-.4-3.5z"
            />
            <path
                fill="#FF3D00"
                d="M6.3 14.7l6.6 4.8C14.6 16 18.9 13 24 13c3.1 0 5.8 1.1 8 3l5.7-5.7C34.1 6 29.3 4 24 4 16.3 4 9.7 8.4 6.3 14.7z"
            />
            <path
                fill="#4CAF50"
                d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2c-2 1.4-4.5 2.4-7.2 2.4-5.2 0-9.6-3.3-11.2-7.9l-6.5 5C9.5 39.5 16.1 44 24 44z"
            />
            <path
                fill="#1976D2"
                d="M43.6 20.5H42V20H24v8h11.3c-.8 2.3-2.2 4.2-4.1 5.6l6.2 5.2c-.4.4 6.6-4.8 6.6-14.8 0-1.2-.1-2.3-.4-3.5z"
            />
        </svg>
    );
}

function FloatingReportCard() {
    return (
        <motion.div
            animate={{ y: [0, -8, 0] }}
            transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
            className="glass-panel relative overflow-hidden p-6"
        >
            <div className="mb-4 flex items-center justify-between">
                <span className="badge-success">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                    Informe generado
                </span>
                <span className="text-xs text-slate-400">hace 3s</span>
            </div>
            <h4 className="mb-4 font-[Outfit] text-lg font-semibold text-slate-900">
                Senior Product Designer @ Atlas
            </h4>
            <div className="space-y-3 text-sm">
                <SkeletonLine label="Radiografía del Puesto" width="92%" />
                <SkeletonLine label="Análisis de Gap" width="78%" />
                <SkeletonLine label="Optimización ATS" width="85%" delay={0.4} />
                <SkeletonLine label="Insider Advice" width="70%" delay={0.6} />
            </div>
            <div className="mt-5 rounded-xl border-l-4 border-blue-300 bg-blue-50/60 px-4 py-3 text-xs italic text-slate-600">
                "Hola Ana, vi que Atlas está escalando el equipo de producto..."
            </div>
        </motion.div>
    );
}

function SkeletonLine({ label, width, delay = 0 }) {
    return (
        <div>
            <div className="mb-1 text-[11px] font-medium uppercase tracking-wider text-slate-400">
                {label}
            </div>
            <motion.div
                initial={{ width: 0 }}
                animate={{ width }}
                transition={{ duration: 1.2, delay, ease: "easeOut" }}
                className="h-2 rounded-full bg-gradient-to-r from-blue-400 to-emerald-400"
            />
        </div>
    );
}
