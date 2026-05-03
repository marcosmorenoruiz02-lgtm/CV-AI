import { useState } from "react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Sparkles, Loader2, Briefcase, Copy, Check, AlertCircle, Lock } from "lucide-react";
import { toast } from "sonner";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import TierUsageCard from "./TierUsageCard";

const FREE_MONTHLY_LIMIT = 4;

export default function AnalysisTab({ goToHistory }) {
    const { user, checkAuth } = useAuth();
    const [jobTitle, setJobTitle] = useState("");
    const [jobDescription, setJobDescription] = useState("");
    const [loading, setLoading] = useState(false);
    const [upgrading, setUpgrading] = useState(false);
    const [report, setReport] = useState("");
    const [copied, setCopied] = useState(false);

    const profileComplete =
        !!user && (user.headline || (user.skills || []).length || (user.experience || []).length);

    const tier = (user?.tier || "FREE").toUpperCase();
    const used = Number(user?.monthly_analyses_count || 0);
    const limitReached = tier === "FREE" && used >= FREE_MONTHLY_LIMIT;

    const onUpgrade = async () => {
        setUpgrading(true);
        try {
            const { data } = await api.post("/payments/checkout/session", {
                origin_url: window.location.origin,
                package_id: "cvboost_pro_monthly",
            });
            if (data?.url) {
                window.location.href = data.url;
            } else {
                throw new Error("No checkout URL returned");
            }
        } catch (err) {
            toast.error(err.response?.data?.detail || "No se pudo iniciar el pago");
            setUpgrading(false);
        }
    };

    const onGenerate = async () => {
        if (!jobDescription.trim()) {
            toast.error("Pega una oferta para analizar");
            return;
        }
        if (limitReached) {
            toast.error(
                "Has agotado tus 4 análisis gratuitos de este mes. Suscríbete a Pro para continuar."
            );
            return;
        }
        setLoading(true);
        setReport("");
        try {
            const { data } = await api.post("/analyses", {
                job_title: jobTitle,
                job_description: jobDescription,
            });
            setReport(data.report_markdown);
            toast.success("Estrategia lista");
            checkAuth();
        } catch (err) {
            if (err.response?.status === 403) {
                checkAuth();
            }
            toast.error(err.response?.data?.detail || "No se pudo generar la estrategia");
        } finally {
            setLoading(false);
        }
    };

    const copyReport = async () => {
        await navigator.clipboard.writeText(report);
        setCopied(true);
        setTimeout(() => setCopied(false), 1800);
    };

    return (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12" data-testid="analysis-tab">
            <div className="lg:col-span-5">
                <div className="glass-panel p-6">
                    <h2 className="mb-1 text-xl font-semibold text-slate-900">Nueva estrategia</h2>
                    <p className="mb-5 text-sm text-slate-500">
                        Pega la oferta y deja que el headhunter trabaje por ti.
                    </p>

                    <TierUsageCard
                        user={user}
                        onUpgrade={onUpgrade}
                        upgrading={upgrading}
                    />

                    {!profileComplete && (
                        <div className="mb-4 flex items-start gap-2 rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                            <span>
                                Completa tu perfil o sube un CV para que el análisis sea preciso.
                            </span>
                        </div>
                    )}

                    <div className="mb-4">
                        <label className="mb-1.5 block text-sm font-medium text-slate-700">
                            Puesto (opcional)
                        </label>
                        <div className="relative">
                            <Briefcase className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                            <input
                                data-testid="job-title-input"
                                className="input-soft !pl-9"
                                placeholder="Senior Product Designer @ Atlas"
                                value={jobTitle}
                                onChange={(e) => setJobTitle(e.target.value)}
                            />
                        </div>
                    </div>

                    <div className="mb-5">
                        <label className="mb-1.5 block text-sm font-medium text-slate-700">
                            Descripción de la oferta
                        </label>
                        <textarea
                            data-testid="job-description-textarea"
                            className="textarea-soft"
                            placeholder="Pega aquí la descripción completa del puesto..."
                            value={jobDescription}
                            onChange={(e) => setJobDescription(e.target.value)}
                        />
                    </div>

                    <motion.button
                        data-testid="generate-strategy-btn"
                        onClick={onGenerate}
                        disabled={loading || limitReached}
                        whileHover={{ scale: loading || limitReached ? 1 : 1.01 }}
                        whileTap={{ scale: loading || limitReached ? 1 : 0.99 }}
                        className="btn-primary w-full !py-3.5 text-base disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {loading ? (
                            <>
                                <Loader2 className="h-5 w-5 animate-spin" />
                                <span>Generando estrategia</span>
                                <span className="inline-flex items-center">
                                    <span className="dot-bouncing" />
                                    <span className="dot-bouncing" />
                                    <span className="dot-bouncing" />
                                </span>
                            </>
                        ) : limitReached ? (
                            <>
                                <Lock className="h-5 w-5" />
                                Límite mensual alcanzado
                            </>
                        ) : (
                            <>
                                <Sparkles className="h-5 w-5" />
                                Optimizar mi CV para esta oferta
                            </>
                        )}
                    </motion.button>

                    <p className="mt-3 text-center text-xs text-slate-400">
                        Los análisis se guardan automáticamente en tu{" "}
                        <button
                            onClick={goToHistory}
                            className="underline-offset-2 hover:underline"
                        >
                            historial
                        </button>
                        .
                    </p>
                </div>
            </div>

            <div className="lg:col-span-7">
                <div className="glass-panel min-h-[400px] p-6" data-testid="markdown-output-panel">
                    {!report && !loading && (
                        <EmptyReport />
                    )}
                    {loading && <LoadingReport />}
                    {report && (
                        <>
                            <div className="mb-4 flex items-center justify-between">
                                <span className="badge-success">
                                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                                    Informe listo
                                </span>
                                <button
                                    onClick={copyReport}
                                    data-testid="copy-report-btn"
                                    className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white/70 px-3 py-1 text-xs text-slate-600 hover:bg-white"
                                >
                                    {copied ? (
                                        <>
                                            <Check className="h-3.5 w-3.5 text-emerald-500" />
                                            Copiado
                                        </>
                                    ) : (
                                        <>
                                            <Copy className="h-3.5 w-3.5" />
                                            Copiar
                                        </>
                                    )}
                                </button>
                            </div>
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ duration: 0.4 }}
                                className="markdown-report"
                            >
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>{report}</ReactMarkdown>
                            </motion.div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}

function EmptyReport() {
    return (
        <div className="flex h-full min-h-[360px] flex-col items-center justify-center text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-blue-500">
                <Sparkles className="h-7 w-7" strokeWidth={1.5} />
            </div>
            <h3 className="mb-1 text-lg font-semibold text-slate-900">
                Tu informe aparecerá aquí
            </h3>
            <p className="max-w-sm text-sm text-slate-500">
                Pega una oferta y pulsa "Optimizar mi CV para esta oferta" para recibir un análisis
                estructurado en segundos.
            </p>
        </div>
    );
}

function LoadingReport() {
    return (
        <div className="space-y-4">
            {["Radiografía del Puesto", "Análisis de Gap", "Optimización ATS", "Insider Advice", "Estrategia LinkedIn"].map(
                (label, i) => (
                    <div key={label}>
                        <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                            {label}
                        </div>
                        <div className="space-y-2">
                            <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: "95%" }}
                                transition={{ duration: 1.4, delay: i * 0.15, ease: "easeOut" }}
                                className="h-3 rounded-full bg-gradient-to-r from-blue-200 via-blue-100 to-emerald-100"
                            />
                            <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: "75%" }}
                                transition={{
                                    duration: 1.6,
                                    delay: i * 0.15 + 0.2,
                                    ease: "easeOut",
                                }}
                                className="h-3 rounded-full bg-gradient-to-r from-blue-100 to-emerald-100"
                            />
                        </div>
                    </div>
                )
            )}
        </div>
    );
}
