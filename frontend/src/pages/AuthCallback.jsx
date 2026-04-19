import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function AuthCallback() {
    const navigate = useNavigate();
    const { setUser } = useAuth();
    const hasProcessed = useRef(false);
    const [status, setStatus] = useState("Validando tu sesión...");

    useEffect(() => {
        if (hasProcessed.current) return;
        hasProcessed.current = true;

        const run = async () => {
            const hash = window.location.hash || "";
            const match = hash.match(/session_id=([^&]+)/);
            if (!match) {
                navigate("/", { replace: true });
                return;
            }
            const session_id = decodeURIComponent(match[1]);
            try {
                setStatus("Validando tu sesión...");
                const { data } = await api.post(
                    "/auth/session",
                    { session_id },
                    { timeout: 45000 },
                );
                setUser(data.user);
                // Clean hash before navigate to avoid re-entering callback.
                window.history.replaceState(null, "", "/dashboard");
                navigate("/dashboard", { replace: true, state: { user: data.user } });
            } catch (err) {
                const msg =
                    err?.response?.data?.detail ||
                    err?.message ||
                    "No pudimos iniciar sesión. Inténtalo de nuevo.";
                console.error("Auth failed:", err);
                toast.error(msg);
                setStatus("No se pudo iniciar sesión");
                setTimeout(() => navigate("/", { replace: true }), 2000);
            }
        };
        run();
    }, [navigate, setUser]);

    return (
        <div className="flex min-h-screen items-center justify-center">
            <div
                className="glass-panel flex flex-col items-center gap-3 px-10 py-8"
                data-testid="auth-callback-panel"
            >
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-blue-500" />
                <p className="text-slate-600">{status}</p>
            </div>
        </div>
    );
}
