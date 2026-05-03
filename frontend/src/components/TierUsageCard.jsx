import { motion } from "framer-motion";
import { Crown, Zap, AlertTriangle } from "lucide-react";
import { Progress } from "./ui/progress";
import { Badge } from "./ui/badge";

const FREE_DAILY_LIMIT = 3;

/**
 * Compact tier usage widget shown above analysis forms.
 * - PRO → green unlimited chip
 * - FREE → progress bar X/3 + warning + upgrade CTA when exhausted
 */
export default function TierUsageCard({ user, onUpgrade, upgrading = false }) {
    if (!user) return null;
    const tier = (user.tier || "FREE").toUpperCase();
    const used = Number(user.daily_analyses_count || 0);
    const remaining = Math.max(FREE_DAILY_LIMIT - used, 0);
    const pct = Math.min((used / FREE_DAILY_LIMIT) * 100, 100);
    const exhausted = tier === "FREE" && used >= FREE_DAILY_LIMIT;

    if (tier === "PRO") {
        return (
            <div
                data-testid="tier-usage-card-pro"
                className="mb-4 flex items-center justify-between rounded-2xl border border-emerald-200 bg-gradient-to-r from-emerald-50 to-white p-4 shadow-sm dark:border-emerald-900/40 dark:from-emerald-950/30 dark:to-slate-900"
            >
                <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500 text-white shadow-md shadow-emerald-500/30">
                        <Crown className="h-4 w-4" />
                    </div>
                    <div>
                        <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                            Plan PRO activo
                        </p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                            Análisis ilimitados con GPT-5.2
                        </p>
                    </div>
                </div>
                <Badge
                    data-testid="tier-badge-pro"
                    className="bg-emerald-500 text-white hover:bg-emerald-600"
                >
                    PRO
                </Badge>
            </div>
        );
    }

    return (
        <motion.div
            data-testid="tier-usage-card-free"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className={`mb-4 rounded-2xl border p-4 shadow-sm transition-colors ${
                exhausted
                    ? "border-rose-200 bg-rose-50/70 dark:border-rose-900/40 dark:bg-rose-950/30"
                    : "border-slate-200 bg-white/70 dark:border-slate-700 dark:bg-slate-800/60"
            }`}
        >
            <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Badge
                        data-testid="tier-badge-free"
                        variant="secondary"
                        className="bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200"
                    >
                        FREE
                    </Badge>
                    <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                        Créditos diarios
                    </span>
                </div>
                <span
                    data-testid="daily-credits-count"
                    className={`text-sm font-semibold tabular-nums ${
                        exhausted ? "text-rose-600" : "text-slate-900 dark:text-slate-100"
                    }`}
                >
                    {used}/{FREE_DAILY_LIMIT}
                </span>
            </div>

            <Progress
                data-testid="daily-credits-progress"
                value={pct}
                className={`h-2 ${exhausted ? "bg-rose-100" : ""}`}
            />

            {exhausted ? (
                <div
                    data-testid="tier-limit-warning"
                    className="mt-3 flex items-start gap-2 rounded-xl bg-rose-100/60 p-2.5 text-xs text-rose-800 dark:bg-rose-900/30 dark:text-rose-200"
                >
                    <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    <span>
                        Has agotado tus {FREE_DAILY_LIMIT} análisis diarios. Vuelve mañana o sube a
                        Pro para análisis ilimitados + GPT-5.2.
                    </span>
                </div>
            ) : (
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                    Te quedan <strong>{remaining}</strong> análisis hoy. Se reinicia a las 00:00
                    UTC.
                </p>
            )}

            {onUpgrade && (
                <button
                    data-testid="upgrade-pro-inline-btn"
                    onClick={onUpgrade}
                    disabled={upgrading}
                    className="mt-3 inline-flex w-full items-center justify-center gap-1.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-3 py-2 text-sm font-semibold text-white shadow-md shadow-blue-500/20 transition-all hover:shadow-lg hover:shadow-blue-500/30 disabled:opacity-60"
                >
                    <Zap className="h-3.5 w-3.5" />
                    {upgrading ? "Activando…" : "Subir a Pro"}
                </button>
            )}
        </motion.div>
    );
}
