import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "react-hot-toast";
import { RouteGuard } from "@/components/auth/RouteGuard";

const platformName = process.env.NEXT_PUBLIC_PLATFORM_NAME || "Resume JD Aligner";

export const metadata: Metadata = {
    title: {
        default: platformName,
        template: `%s | ${platformName}`,
    },
    description:
        "AI-powered resume analysis and ATS optimization. Score your resume against any job description and generate tailored, company-specific resume versions.",
    keywords: ["resume", "ATS", "job description", "AI", "career", "optimization"],
    authors: [{ name: "Resume JD Aligner" }],
    openGraph: {
        title: platformName,
        description: "AI-powered resume analysis and optimization platform",
        type: "website",
    },
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    // Set the theme class before first paint so there is no flash of the wrong
    // theme. Reads the saved choice, else the OS preference; defaults to dark.
    const themeScript = `(function(){try{var t=localStorage.getItem('theme');if(t!=='light'&&t!=='dark'){t=window.matchMedia('(prefers-color-scheme: light)').matches?'light':'dark';}var d=document.documentElement;d.classList.remove('light','dark');d.classList.add(t);}catch(e){}})();`;

    return (
        <html lang="en" suppressHydrationWarning>
            <head>
                <script dangerouslySetInnerHTML={{ __html: themeScript }} />
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
                <link
                    href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap"
                    rel="stylesheet"
                />
            </head>
            <body className="bg-background text-foreground antialiased">
                <RouteGuard>{children}</RouteGuard>
                <Toaster
                    position="bottom-right"
                    toastOptions={{
                        style: {
                            background: "rgb(var(--card))",
                            color: "rgb(var(--foreground))",
                            border: "1px solid rgb(var(--border))",
                            borderRadius: "12px",
                            fontSize: "14px",
                        },
                    }}
                />
            </body>
        </html>
    );
}
