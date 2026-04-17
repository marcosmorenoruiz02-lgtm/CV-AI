import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
    Trash2,
    History as HistoryIcon,
    ChevronRight,
    ArrowLeft,
    Calendar,
    Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "../lib/api";

const container = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.06 } },
};
const item = {
    hidden: { opacity: 0, y: 12 },
    show: { opacity: 1, y: 0, transition: { duration: 0.35 } },
};

export default function HistoryTab() {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selected, setSelected] = useState(null);

    const load = async () => {
        setLoading(true);
        try {
            const { data } = await api.get("/analyses");
            setItems(data);
        } catch {
            toast.error("No se pudo cargar el historial");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, []);

    const onDelete = async (id, e) => {
        e.stopPropagation();
        if (!window.confirm("¿Eliminar este análisis?")) return;
        try {
            await api.delete(`/analyses/${id}`);
            setItems((x) => x.filter((a) => a.id !== id));
            if (selected?.id === id) setSelected(null);
            toast.success("Eliminado");
        } catch {
            toast.error("No se pudo eliminar");
        }
    };

    if (loading) {
        return (
            <div className="flex min-h-[240px] items-center justify-center" data-testid="history-tab">
                <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
            </div>
        );
    }

    if (selected) {
        return (
            <div className="glass-panel p-6" data-testid="history-detail">
                <button
                    onClick={() => setSelected(null)}
                    data-testid="history-back-btn"
                    className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-slate-500 hover:text-slate-800"
                >
                    <ArrowLeft className="h-4 w-4" /> Volver al historial
                </button>
                <h2 className="mb-1 text-xl font-semibold text-slate-900">{selected.job_title}</h2>
                <div className="mb-5 flex items-center gap-2 text-xs text-slate-500">
                    <Calendar className="h-3.5 w-3.5" />
                    {new Date(selected.created_at).toLocaleString("es-ES", {
                        dateStyle: "long",
                        timeStyle: "short",
                    })}
                </div>
                <details className="mb-6 rounded-2xl border border-slate-100 bg-white/60 p-4 text-sm">
                    <summary className="cursor-pointer font-medium text-slate-700">
                        Ver oferta original
                    </summary>
                    <p className="mt-3 whitespace-pre-wrap text-slate-600">
                        {selected.job_description}
                    </p>
                </details>
                <div className="markdown-report">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {selected.report_markdown}
                    </ReactMarkdown>
                </div>
            </div>
        );
    }

    return (
        <div data-testid="history-tab">
            <div className="mb-6 flex items-center justify-between">
                <div>
                    <h2 className="text-xl font-semibold text-slate-900">Historial de análisis</h2>
                    <p className="text-sm text-slate-500">
                        Todas tus estrategias generadas, siempre al alcance.
                    </p>
                </div>
            </div>

            {items.length === 0 ? (
                <div className="glass-panel flex min-h-[260px] flex-col items-center justify-center p-8 text-center">
                    <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
                        <HistoryIcon className="h-6 w-6" strokeWidth={1.5} />
                    </div>
                    <h3 className="mb-1 text-lg font-semibold text-slate-900">Sin análisis aún</h3>
                    <p className="text-sm text-slate-500">
                        Genera tu primera estrategia desde la pestaña "Análisis".
                    </p>
                </div>
            ) : (
                <motion.div
                    variants={container}
                    initial="hidden"
                    animate="show"
                    className="grid grid-cols-1 gap-3"
                >
                    {items.map((a) => (
                        <motion.button
                            key={a.id}
                            variants={item}
                            whileHover={{ y: -2 }}
                            onClick={() => setSelected(a)}
                            data-testid={`history-item-${a.id}`}
                            className="group flex items-center justify-between rounded-2xl border border-slate-100 bg-white/70 p-5 text-left shadow-sm backdrop-blur-sm transition-all hover:shadow-md"
                        >
                            <div className="min-w-0 flex-1">
                                <h3 className="truncate font-semibold text-slate-900">
                                    {a.job_title || "Análisis sin título"}
                                </h3>
                                <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                                    <Calendar className="h-3.5 w-3.5" />
                                    {new Date(a.created_at).toLocaleString("es-ES", {
                                        dateStyle: "medium",
                                        timeStyle: "short",
                                    })}
                                </div>
                                <p className="mt-2 line-clamp-2 text-sm text-slate-500">
                                    {a.job_description.slice(0, 220)}
                                    {a.job_description.length > 220 ? "..." : ""}
                                </p>
                            </div>
                            <div className="ml-4 flex items-center gap-1">
                                <button
                                    onClick={(e) => onDelete(a.id, e)}
                                    data-testid={`delete-history-${a.id}`}
                                    className="rounded-full p-2 text-slate-400 opacity-0 transition-opacity hover:bg-red-50 hover:text-red-500 group-hover:opacity-100"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </button>
                                <ChevronRight className="h-5 w-5 text-slate-300 transition-transform group-hover:translate-x-0.5" />
                            </div>
                        </motion.button>
                    ))}
                </motion.div>
            )}
        </div>
    );
}
