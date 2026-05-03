import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { FileUp, Loader2, Plus, Save, Trash2, UploadCloud, Check, Crown, Zap } from "lucide-react";
import { toast } from "sonner";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { Badge } from "./ui/badge";
import { Progress } from "./ui/progress";

const emptyExp = { role: "", company: "", period: "", description: "" };
const FREE_DAILY_LIMIT = 3;

export default function ProfileTab() {
    const { user, setUser, checkAuth } = useAuth();
    const [form, setForm] = useState({
        name: "",
        headline: "",
        skills: [],
        experience: [],
    });
    const [skillInput, setSkillInput] = useState("");
    const [saving, setSaving] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [upgrading, setUpgrading] = useState(false);
    const [dragOver, setDragOver] = useState(false);
    const fileRef = useRef(null);

    useEffect(() => {
        if (!user) return;
        setForm({
            name: user.name || "",
            headline: user.headline || "",
            skills: user.skills || [],
            experience: user.experience?.length ? user.experience : [],
        });
    }, [user]);

    const onUpload = async (file) => {
        if (!file) return;
        if (!file.name.toLowerCase().endsWith(".pdf")) {
            toast.error("Solo se aceptan archivos PDF");
            return;
        }
        setUploading(true);
        const fd = new FormData();
        fd.append("file", file);
        try {
            const { data } = await api.post("/profile/upload-cv", fd, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            setUser(data);
            toast.success("CV procesado. Revisa y confirma tu perfil.");
        } catch (err) {
            toast.error(err.response?.data?.detail || "No se pudo procesar el CV");
        } finally {
            setUploading(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer.files?.[0];
        onUpload(file);
    };

    const addSkill = () => {
        const v = skillInput.trim();
        if (!v) return;
        if (form.skills.includes(v)) return;
        setForm((f) => ({ ...f, skills: [...f.skills, v] }));
        setSkillInput("");
    };

    const removeSkill = (s) =>
        setForm((f) => ({ ...f, skills: f.skills.filter((x) => x !== s) }));

    const addExperience = () =>
        setForm((f) => ({ ...f, experience: [...f.experience, { ...emptyExp }] }));

    const updateExperience = (i, key, val) =>
        setForm((f) => {
            const copy = [...f.experience];
            copy[i] = { ...copy[i], [key]: val };
            return { ...f, experience: copy };
        });

    const removeExperience = (i) =>
        setForm((f) => ({ ...f, experience: f.experience.filter((_, idx) => idx !== i) }));

    const save = async () => {
        setSaving(true);
        try {
            const { data } = await api.put("/profile", form);
            setUser(data);
            toast.success("Perfil guardado");
        } catch (err) {
            toast.error("No se pudo guardar el perfil");
        } finally {
            setSaving(false);
        }
    };

    const onUpgrade = async () => {
        setUpgrading(true);
        try {
            await api.post("/billing/upgrade");
            await checkAuth();
            toast.success("¡Bienvenido a Pro! Análisis ilimitados activados.");
        } catch (err) {
            toast.error(err.response?.data?.detail || "No se pudo activar Pro");
        } finally {
            setUpgrading(false);
        }
    };

    const tier = (user?.tier || "FREE").toUpperCase();
    const used = Number(user?.daily_analyses_count || 0);
    const pct = Math.min((used / FREE_DAILY_LIMIT) * 100, 100);
    const isPro = tier === "PRO";

    return (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12" data-testid="profile-tab">
            {/* Upload CV */}
            <div className="lg:col-span-4">
                <div
                    data-testid="upload-cv-dropzone"
                    onDragOver={(e) => {
                        e.preventDefault();
                        setDragOver(true);
                    }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleDrop}
                    onClick={() => fileRef.current?.click()}
                    className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition-all ${
                        dragOver
                            ? "border-blue-400 bg-blue-50/60"
                            : "border-slate-300 bg-white/60 hover:border-blue-300 hover:bg-blue-50/50"
                    }`}
                >
                    <input
                        ref={fileRef}
                        type="file"
                        accept="application/pdf"
                        className="hidden"
                        onChange={(e) => onUpload(e.target.files?.[0])}
                        data-testid="cv-file-input"
                    />
                    {uploading ? (
                        <>
                            <Loader2 className="mb-3 h-8 w-8 animate-spin text-blue-500" />
                            <p className="font-medium text-slate-700">Analizando tu CV...</p>
                            <p className="mt-1 text-xs text-slate-500">
                                GPT-5.2 está extrayendo tus datos
                            </p>
                        </>
                    ) : (
                        <>
                            <UploadCloud className="mb-3 h-8 w-8 text-blue-500" strokeWidth={1.5} />
                            <p className="font-medium text-slate-800">Sube tu CV en PDF</p>
                            <p className="mt-1 text-xs text-slate-500">
                                Arrastra aquí o haz clic para seleccionar
                            </p>
                            <span className="mt-4 inline-flex items-center gap-1 text-xs text-blue-600">
                                <FileUp className="h-3 w-3" /> Autocompleta tu perfil
                            </span>
                        </>
                    )}
                </div>

                <div className="mt-4 rounded-2xl border border-slate-100 bg-white/60 p-4 text-sm text-slate-600">
                    <p className="mb-2 font-medium text-slate-800">¿Cómo funciona?</p>
                    <ul className="space-y-1 text-xs">
                        <li className="flex gap-2">
                            <Check className="mt-0.5 h-3.5 w-3.5 text-emerald-500" /> Extraemos
                            texto del PDF
                        </li>
                        <li className="flex gap-2">
                            <Check className="mt-0.5 h-3.5 w-3.5 text-emerald-500" /> La IA
                            estructura tu titular, skills y experiencia
                        </li>
                        <li className="flex gap-2">
                            <Check className="mt-0.5 h-3.5 w-3.5 text-emerald-500" /> Tú revisas y
                            pulsas Guardar
                        </li>
                    </ul>
                </div>

                {/* Plan / Tier card */}
                <div
                    data-testid="plan-card"
                    className={`mt-4 rounded-2xl border p-5 shadow-sm ${
                        isPro
                            ? "border-emerald-200 bg-gradient-to-br from-emerald-50 to-white dark:border-emerald-900/40 dark:from-emerald-950/30 dark:to-slate-900"
                            : "border-slate-200 bg-white/70 dark:border-slate-700 dark:bg-slate-800/60"
                    }`}
                >
                    <div className="mb-3 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <div
                                className={`flex h-8 w-8 items-center justify-center rounded-xl text-white shadow-sm ${
                                    isPro
                                        ? "bg-emerald-500 shadow-emerald-500/30"
                                        : "bg-slate-400 shadow-slate-400/20"
                                }`}
                            >
                                <Crown className="h-4 w-4" />
                            </div>
                            <div>
                                <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                                    Tu plan
                                </p>
                                <p className="text-xs text-slate-500 dark:text-slate-400">
                                    {isPro ? "Análisis ilimitados" : "3 análisis por día"}
                                </p>
                            </div>
                        </div>
                        {isPro ? (
                            <Badge
                                data-testid="profile-tier-badge"
                                className="bg-emerald-500 text-white hover:bg-emerald-600"
                            >
                                PRO
                            </Badge>
                        ) : (
                            <Badge
                                data-testid="profile-tier-badge"
                                variant="secondary"
                                className="bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200"
                            >
                                FREE
                            </Badge>
                        )}
                    </div>

                    {!isPro && (
                        <>
                            <div className="mb-1 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                                <span>Uso diario</span>
                                <span
                                    data-testid="profile-credits-count"
                                    className="font-semibold tabular-nums text-slate-700 dark:text-slate-200"
                                >
                                    {used}/{FREE_DAILY_LIMIT}
                                </span>
                            </div>
                            <Progress value={pct} className="h-1.5" />
                            <button
                                data-testid="upgrade-pro-btn"
                                onClick={onUpgrade}
                                disabled={upgrading}
                                className="mt-4 inline-flex w-full items-center justify-center gap-1.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-3 py-2.5 text-sm font-semibold text-white shadow-md shadow-blue-500/20 transition-all hover:shadow-lg hover:shadow-blue-500/30 disabled:opacity-60"
                            >
                                {upgrading ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    <Zap className="h-4 w-4" />
                                )}
                                {upgrading ? "Activando…" : "Subir a Pro"}
                            </button>
                            <p className="mt-2 text-center text-[11px] text-slate-400">
                                Incluye GPT-5.2 + análisis ilimitados
                            </p>
                        </>
                    )}

                    {isPro && (
                        <p className="text-xs text-emerald-700 dark:text-emerald-300">
                            Tienes análisis ilimitados con GPT-5.2. Gracias por apoyar CVBoost.
                        </p>
                    )}
                </div>
            </div>

            {/* Form */}
            <div className="glass-panel p-6 lg:col-span-8" data-testid="profile-form">
                <div className="mb-6 flex items-center justify-between">
                    <div>
                        <h2 className="text-xl font-semibold text-slate-900">Perfil profesional</h2>
                        <p className="text-sm text-slate-500">
                            Estos datos se usarán como tu CV en cada análisis.
                        </p>
                    </div>
                    <button
                        data-testid="save-profile-btn"
                        onClick={save}
                        disabled={saving}
                        className="btn-primary !py-2.5 !px-5"
                    >
                        {saving ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            <Save className="h-4 w-4" />
                        )}
                        Guardar
                    </button>
                </div>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div>
                        <label className="mb-1.5 block text-sm font-medium text-slate-700">
                            Nombre
                        </label>
                        <input
                            data-testid="profile-name-input"
                            className="input-soft"
                            value={form.name}
                            onChange={(e) => setForm({ ...form, name: e.target.value })}
                        />
                    </div>
                    <div>
                        <label className="mb-1.5 block text-sm font-medium text-slate-700">
                            Titular profesional
                        </label>
                        <input
                            data-testid="profile-headline-input"
                            placeholder="Senior Product Designer"
                            className="input-soft"
                            value={form.headline}
                            onChange={(e) => setForm({ ...form, headline: e.target.value })}
                        />
                    </div>
                </div>

                {/* Skills */}
                <div className="mt-6">
                    <label className="mb-1.5 block text-sm font-medium text-slate-700">
                        Habilidades
                    </label>
                    <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-slate-200 bg-white/80 p-3">
                        {form.skills.map((s) => (
                            <span
                                key={s}
                                className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-3 py-1 text-sm text-blue-700 ring-1 ring-blue-100"
                                data-testid={`skill-chip-${s}`}
                            >
                                {s}
                                <button
                                    onClick={() => removeSkill(s)}
                                    className="ml-1 text-blue-500 hover:text-blue-700"
                                >
                                    ×
                                </button>
                            </span>
                        ))}
                        <input
                            data-testid="skill-input"
                            value={skillInput}
                            onChange={(e) => setSkillInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === "Enter" || e.key === ",") {
                                    e.preventDefault();
                                    addSkill();
                                }
                            }}
                            placeholder="Añade una habilidad y pulsa Enter"
                            className="min-w-[180px] flex-1 bg-transparent px-2 py-1 text-sm text-slate-800 outline-none placeholder:text-slate-400"
                        />
                    </div>
                </div>

                {/* Experience */}
                <div className="mt-6">
                    <div className="mb-2 flex items-center justify-between">
                        <label className="block text-sm font-medium text-slate-700">
                            Experiencia laboral
                        </label>
                        <button
                            onClick={addExperience}
                            data-testid="add-experience-btn"
                            className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700"
                        >
                            <Plus className="h-4 w-4" /> Añadir
                        </button>
                    </div>
                    <div className="space-y-3">
                        {form.experience.length === 0 && (
                            <div className="rounded-2xl border border-dashed border-slate-200 bg-white/50 p-6 text-center text-sm text-slate-500">
                                Aún no has añadido experiencia. Sube tu CV para autocompletarla.
                            </div>
                        )}
                        {form.experience.map((exp, i) => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, y: 8 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="rounded-2xl border border-slate-100 bg-white/70 p-4"
                                data-testid={`experience-row-${i}`}
                            >
                                <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                                    <input
                                        placeholder="Rol"
                                        className="input-soft !py-2"
                                        value={exp.role}
                                        onChange={(e) => updateExperience(i, "role", e.target.value)}
                                    />
                                    <input
                                        placeholder="Empresa"
                                        className="input-soft !py-2"
                                        value={exp.company}
                                        onChange={(e) =>
                                            updateExperience(i, "company", e.target.value)
                                        }
                                    />
                                    <input
                                        placeholder="2022 — actualidad"
                                        className="input-soft !py-2"
                                        value={exp.period}
                                        onChange={(e) =>
                                            updateExperience(i, "period", e.target.value)
                                        }
                                    />
                                </div>
                                <textarea
                                    placeholder="Logros, responsabilidades, métricas..."
                                    rows={3}
                                    className="input-soft mt-2 resize-y"
                                    value={exp.description}
                                    onChange={(e) =>
                                        updateExperience(i, "description", e.target.value)
                                    }
                                />
                                <div className="mt-2 flex justify-end">
                                    <button
                                        onClick={() => removeExperience(i)}
                                        data-testid={`remove-experience-${i}`}
                                        className="inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs text-slate-500 hover:bg-red-50 hover:text-red-600"
                                    >
                                        <Trash2 className="h-3.5 w-3.5" /> Quitar
                                    </button>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
