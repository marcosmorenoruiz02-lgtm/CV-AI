import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function AuthCallback() {
    const navigate = useNavigate();
    const { setUser } = useAuth();
    const hasProcessed = useRef(false);

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
                const { data } = await api.post("/auth/session", { session_id });
                setUser(data.user);
                navigate("/dashboard", { replace: true, state: { user: data.user } });
            } catch (err) {
                console.error("Auth failed", err);
                navigate("/", { replace: true });
            }
        };
        run();
    }, [navigate, setUser]);

    return (
        <div className="flex min-h-screen items-center justify-center">
            <div className="glass-panel flex flex-col items-center gap-3 px-10 py-8">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-blue-500" />
                <p className="text-slate-600">Validando tu sesión...</p>
            </div>
        </div>
    );
}
