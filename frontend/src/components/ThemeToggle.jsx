import { motion } from "framer-motion";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "../context/ThemeContext";

export default function ThemeToggle() {
    const { theme, toggle } = useTheme();
    const isDark = theme === "dark";
    return (
        <button
            data-testid="theme-toggle"
            onClick={toggle}
            aria-label={isDark ? "Cambiar a tema claro" : "Cambiar a tema oscuro"}
            title={isDark ? "Tema claro" : "Tema oscuro"}
            className="relative inline-flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white/70 text-slate-600 backdrop-blur-md transition-all hover:bg-white dark:border-slate-700 dark:bg-slate-800/70 dark:text-slate-300 dark:hover:bg-slate-800"
        >
            <motion.span
                key={theme}
                initial={{ rotate: -90, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                exit={{ rotate: 90, opacity: 0 }}
                transition={{ duration: 0.25 }}
                className="absolute inset-0 flex items-center justify-center"
            >
                {isDark ? <Sun className="h-4 w-4" strokeWidth={1.8} /> : <Moon className="h-4 w-4" strokeWidth={1.8} />}
            </motion.span>
        </button>
    );
}
