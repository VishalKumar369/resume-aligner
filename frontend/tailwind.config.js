/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: [
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            // Colours resolve to CSS variables (space-separated RGB channels), so
            // opacity modifiers still work and the light/dark themes swap the
            // variables rather than the class names. See app/globals.css.
            colors: {
                background: "rgb(var(--background) / <alpha-value>)",
                foreground: "rgb(var(--foreground) / <alpha-value>)",
                card: "rgb(var(--card) / <alpha-value>)",
                border: "rgb(var(--border) / <alpha-value>)",
                primary: {
                    DEFAULT: "rgb(var(--primary) / <alpha-value>)",
                    hover: "rgb(var(--primary-hover) / <alpha-value>)",
                    foreground: "rgb(var(--primary-foreground) / <alpha-value>)",
                },
                accent: "rgb(var(--accent) / <alpha-value>)",
                muted: {
                    DEFAULT: "rgb(var(--muted) / <alpha-value>)",
                    foreground: "rgb(var(--muted-foreground) / <alpha-value>)",
                },
                success: "rgb(var(--success) / <alpha-value>)",
                warning: "rgb(var(--warning) / <alpha-value>)",
                error: "rgb(var(--error) / <alpha-value>)",
                surface: "rgb(var(--surface) / <alpha-value>)",
                "surface-2": "rgb(var(--surface-2) / <alpha-value>)",
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
                float: "float 6s ease-in-out infinite",
                gradient: "gradient 8s ease infinite",
                "spin-slow": "spin 20s linear infinite",
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
                float: {
                    "0%,100%": { transform: "translateY(0)" },
                    "50%": { transform: "translateY(-14px)" },
                },
                gradient: {
                    "0%,100%": { backgroundPosition: "0% 50%" },
                    "50%": { backgroundPosition: "100% 50%" },
                },
            },
        },
    },
    plugins: [],
};
