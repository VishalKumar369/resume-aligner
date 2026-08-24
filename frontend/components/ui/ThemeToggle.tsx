"use client";

import { useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";
import { cn } from "@/lib/utils";

type Theme = "light" | "dark";

/**
 * Day/night switch. The active theme lives as a `light`/`dark` class on <html>
 * (set before paint by the inline script in the root layout), so this only
 * reads that class on mount and flips it, persisting the choice.
 */
export function ThemeToggle({ className }: { className?: string }) {
    // Start from the class the no-flash script already applied; correct it on
    // mount to avoid a hydration mismatch on the icon.
    const [theme, setTheme] = useState<Theme>("dark");
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
        setTheme(document.documentElement.classList.contains("light") ? "light" : "dark");
    }, []);

    const toggle = () => {
        const next: Theme = theme === "dark" ? "light" : "dark";
        const root = document.documentElement;
        root.classList.remove("light", "dark");
        root.classList.add(next);
        try {
            localStorage.setItem("theme", next);
        } catch {
            /* private mode / storage disabled — the toggle still works for the session */
        }
        setTheme(next);
    };

    return (
        <button
            type="button"
            onClick={toggle}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            className={cn(
                "relative p-2 rounded-lg text-muted hover:text-foreground hover:bg-surface-2 transition-colors",
                className
            )}
        >
            {/* Render nothing theme-specific until mounted, so SSR and client agree. */}
            {mounted && theme === "dark" ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>
    );
}
