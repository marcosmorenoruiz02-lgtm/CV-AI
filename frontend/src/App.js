import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider, useTheme } from "./context/ThemeContext";
import Landing from "./pages/Landing";
import Dashboard from "./pages/Dashboard";
import AuthCallback from "./pages/AuthCallback";
import ProtectedRoute from "./components/ProtectedRoute";

function AppRouter() {
    const location = useLocation();
    // Synchronous detection of OAuth callback fragment - prevents race conditions.
    if (location.hash?.includes("session_id=")) {
        return <AuthCallback />;
    }
    return (
        <Routes>
            <Route path="/" element={<Landing />} />
            <Route
                path="/dashboard"
                element={
                    <ProtectedRoute>
                        <Dashboard />
                    </ProtectedRoute>
                }
            />
            <Route path="*" element={<Landing />} />
        </Routes>
    );
}

function ToasterWithTheme() {
    const { theme } = useTheme();
    return <Toaster position="top-right" richColors closeButton theme={theme} />;
}

function App() {
    return (
        <div className="App">
            <ThemeProvider>
                <BrowserRouter>
                    <AuthProvider>
                        <AppRouter />
                        <ToasterWithTheme />
                    </AuthProvider>
                </BrowserRouter>
            </ThemeProvider>
        </div>
    );
}

export default App;
