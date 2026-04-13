import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "react-hot-toast";

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
    return (
        <html lang="en" className="dark">
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
                <link
                    href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap"
                    rel="stylesheet"
                />
            </head>
            <body className="bg-background text-white antialiased">
                {children}
                <Toaster
                    position="bottom-right"
                    toastOptions={{
                        style: {
                            background: "#111118",
                            color: "#FAFAFA",
                            border: "1px solid #1E1E2E",
                            borderRadius: "12px",
                            fontSize: "14px",
                        },
                    }}
                />
            </body>
        </html>
    );
}
