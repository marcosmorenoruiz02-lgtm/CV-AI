import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { XCircle, ArrowLeft } from "lucide-react";

export default function PaymentCancel() {
    return (
        <div
            className="flex min-h-screen items-center justify-center px-6"
            data-testid="payment-cancel-page"
        >
            <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-panel w-full max-w-md p-8 text-center"
            >
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                    <XCircle className="h-7 w-7" />
                </div>
                <h1 className="mb-2 text-xl font-semibold text-slate-900 dark:text-slate-100">
                    Pago cancelado
                </h1>
                <p className="mb-6 text-sm text-slate-600 dark:text-slate-400">
                    No se ha realizado ningún cargo. Puedes volver al panel y reintentar cuando
                    quieras.
                </p>
                <Link to="/dashboard" className="btn-primary w-full">
                    <ArrowLeft className="h-4 w-4" />
                    Volver al panel
                </Link>
            </motion.div>
        </div>
    );
}
