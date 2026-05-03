import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { CheckCircle2, Loader2, XCircle, ArrowRight } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

const MAX_POLL_ATTEMPTS = 10;
const POLL_INTERVAL_MS = 2000;

export default function PaymentSuccess() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { checkAuth } = useAuth();
    const sessionId = searchParams.get("session_id");

    const [status, setStatus] = useState("checking"); // checking | paid | expired | failed
    const [attempts, setAttempts] = useState(0);

    useEffect(() => {
        if (!sessionId) {
            setStatus("failed");
            return;
        }

        let cancelled = false;
        let attempt = 0;

        const poll = async () => {
            try {
                const { data } = await api.get(`/payments/checkout/status/${sessionId}`);
                if (cancelled) return;

                if (data.payment_status === "paid") {
                    setStatus("paid");
                    // Refresh user so tier=PRO is reflected everywhere
                    await checkAuth();
                    return;
                }
                if (data.status === "expired") {
                    setStatus("expired");
                    return;
                }
                attempt += 1;
                setAttempts(attempt);
                if (attempt >= MAX_POLL_ATTEMPTS) {
                    setStatus("timeout");
                    return;
                }
                setTimeout(poll, POLL_INTERVAL_MS);
            } catch (err) {
                if (cancelled) return;
                setStatus("failed");
            }
        };

        poll();
        return () => {
            cancelled = true;
        };
    }, [sessionId, checkAuth]);

    return (
        <div
            className="flex min-h-screen items-center justify-center px-6"
            data-testid="payment-success-page"
        >
            <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-panel w-full max-w-md p-8 text-center"
            >
                {status === "checking" && (
                    <>
                        <Loader2 className="mx-auto mb-4 h-10 w-10 animate-spin text-indigo-500" />
                        <h1 className="mb-2 text-xl font-semibold text-slate-900 dark:text-slate-100">
                            Confirmando tu pago…
                        </h1>
                        <p className="text-sm text-slate-500 dark:text-slate-400">
                            Intento {attempts + 1} de {MAX_POLL_ATTEMPTS}. Esto tarda solo unos
                            segundos.
                        </p>
                    </>
                )}

                {status === "paid" && (
                    <>
                        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300">
                            <CheckCircle2 className="h-7 w-7" />
                        </div>
                        <h1 className="mb-2 text-2xl font-semibold text-slate-900 dark:text-slate-100">
                            ¡Bienvenido a Pro!
                        </h1>
                        <p className="mb-6 text-sm text-slate-600 dark:text-slate-400">
                            Tu pago se ha procesado correctamente. Disfruta análisis ilimitados con
                            GPT-5.2 durante los próximos 30 días.
                        </p>
                        <button
                            data-testid="success-go-dashboard"
                            onClick={() => navigate("/dashboard", { replace: true })}
                            className="btn-primary w-full"
                        >
                            Ir al panel
                            <ArrowRight className="h-4 w-4" />
                        </button>
                    </>
                )}

                {(status === "expired" || status === "failed" || status === "timeout") && (
                    <>
                        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300">
                            <XCircle className="h-7 w-7" />
                        </div>
                        <h1 className="mb-2 text-xl font-semibold text-slate-900 dark:text-slate-100">
                            {status === "expired"
                                ? "La sesión de pago ha expirado"
                                : status === "timeout"
                                  ? "Confirmación lenta"
                                  : "No se pudo verificar el pago"}
                        </h1>
                        <p className="mb-6 text-sm text-slate-600 dark:text-slate-400">
                            {status === "timeout"
                                ? "Tu pago puede tardar unos minutos en confirmarse. Revisa el panel pronto o escribe a soporte."
                                : "Si ya pagaste pero no se refleja, contacta con soporte."}
                        </p>
                        <Link
                            to="/dashboard"
                            className="btn-ghost w-full"
                            data-testid="success-go-dashboard"
                        >
                            Volver al panel
                        </Link>
                    </>
                )}
            </motion.div>
        </div>
    );
}
