import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { LogOut, User2, Sparkles, History as HistoryIcon, Target } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import ProfileTab from "../components/ProfileTab";
import AnalysisTab from "../components/AnalysisTab";
import HistoryTab from "../components/HistoryTab";

const TABS = [
    { id: "analysis", label: "Análisis", icon: Sparkles },
    { id: "profile", label: "Perfil", icon: User2 },
    { id: "history", label: "Historial", icon: HistoryIcon },
];

export default function Dashboard() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const initial = location.state?.tab || "analysis";
    const [activeTab, setActiveTab] = useState(initial);

    const handleLogout = async () => {
        await logout();
        navigate("/", { replace: true });
    };

    if (!user) return null;

    return (
        <div className="min-h-screen" data-testid="dashboard-page">
            <header className="glass-header">
                <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
                    <Link to="/dashboard" className="flex items-center gap-2">
                        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#3B82F6] text-white shadow-lg shadow-blue-500/30">
                            <Target className="h-5 w-5" strokeWidth={2} />
                        </div>
                        <span className="font-[Outfit] text-lg font-semibold text-slate-900">
                            Estrategia de Asalto
                        </span>
                    </Link>

                    <div className="flex items-center gap-3">
                        <div
                            className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white/70 px-3 py-1.5 backdrop-blur-sm sm:flex"
                            data-testid="user-chip"
                        >
                            {user.picture ? (
                                <img
                                    src={user.picture}
                                    alt={user.name}
                                    className="h-6 w-6 rounded-full"
                                />
                            ) : (
                                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-200 text-xs font-semibold text-slate-600">
                                    {user.name?.[0] || "U"}
                                </div>
                            )}
                            <span className="text-sm font-medium text-slate-700">{user.name}</span>
                        </div>
                        <button
                            data-testid="logout-btn"
                            onClick={handleLogout}
                            className="btn-ghost !py-2 !px-4"
                            title="Cerrar sesión"
                        >
                            <LogOut className="h-4 w-4" />
                            <span className="hidden sm:inline">Salir</span>
                        </button>
                    </div>
                </div>
            </header>

            <main className="mx-auto max-w-6xl px-6 py-10">
                {/* Tabs */}
                <div className="mb-8 flex flex-wrap items-center gap-2" data-testid="tabs-bar">
                    {TABS.map((t) => {
                        const active = activeTab === t.id;
                        const Icon = t.icon;
                        return (
                            <button
                                key={t.id}
                                data-testid={`tab-${t.id}`}
                                onClick={() => setActiveTab(t.id)}
                                className="relative inline-flex items-center gap-2 rounded-2xl px-4 py-2 text-sm font-medium transition-colors"
                            >
                                {active && (
                                    <motion.span
                                        layoutId="tab-indicator"
                                        className="absolute inset-0 rounded-2xl bg-white shadow-sm ring-1 ring-slate-100"
                                        transition={{ type: "spring", stiffness: 380, damping: 30 }}
                                    />
                                )}
                                <span
                                    className={`relative z-10 flex items-center gap-2 ${active ? "text-blue-600" : "text-slate-500 hover:text-slate-800"}`}
                                >
                                    <Icon className="h-4 w-4" />
                                    {t.label}
                                </span>
                            </button>
                        );
                    })}
                </div>

                <AnimatePresence mode="wait">
                    <motion.div
                        key={activeTab}
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -8 }}
                        transition={{ duration: 0.25 }}
                    >
                        {activeTab === "analysis" && (
                            <AnalysisTab goToHistory={() => setActiveTab("history")} />
                        )}
                        {activeTab === "profile" && <ProfileTab />}
                        {activeTab === "history" && <HistoryTab />}
                    </motion.div>
                </AnimatePresence>
            </main>
        </div>
    );
}
