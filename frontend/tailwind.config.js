/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: [
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                background: "#0A0A0F",
                card: "#111118",
                border: "#1E1E2E",
                primary: {
                    DEFAULT: "#6366F1",
                    hover: "#4F46E5",
                    foreground: "#FFFFFF",
                },
                accent: "#A78BFA",
                muted: {
                    DEFAULT: "#71717A",
                    foreground: "#A1A1AA",
                },
                success: "#22C55E",
                warning: "#F59E0B",
                error: "#EF4444",
                surface: "#16161F",
                "surface-2": "#1C1C28",
            },
            fontFamily: {
                sans: ["Inter", "system-ui", "sans-serif"],
                mono: ["JetBrains Mono", "monospace"],
            },
            borderRadius: {
                xl: "0.875rem",
                "2xl": "1rem",
                "3xl": "1.5rem",
            },
            boxShadow: {
                card: "0 0 0 1px rgba(255,255,255,0.05), 0 4px 24px rgba(0,0,0,0.4)",
                glow: "0 0 40px rgba(99,102,241,0.15)",
                "glow-sm": "0 0 20px rgba(99,102,241,0.1)",
            },
            animation: {
                "pulse-slow": "pulse 3s ease-in-out infinite",
                shimmer: "shimmer 2s linear infinite",
                "fade-in": "fadeIn 0.3s ease-out",
                "slide-up": "slideUp 0.4s ease-out",
            },
            keyframes: {
                shimmer: {
                    "0%": { backgroundPosition: "-200% 0" },
                    "100%": { backgroundPosition: "200% 0" },
                },
                fadeIn: {
                    "0%": { opacity: "0" },
                    "100%": { opacity: "1" },
                },
                slideUp: {
                    "0%": { opacity: "0", transform: "translateY(10px)" },
                    "100%": { opacity: "1", transform: "translateY(0)" },
                },
            },
        },
    },
    plugins: [],
};
