"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FileText, Eye, EyeOff, ArrowRight, Check } from "lucide-react";
import { authService } from "@/services/api";

const PLATFORM_NAME = process.env.NEXT_PUBLIC_PLATFORM_NAME || "Resume JD Aligner";

const benefits = [
    "ATS score for every job you apply to",
    "Company-specific resume variants",
    "Skill gap detection & learning roadmap",
    "Interview probability scoring",
];

export default function SignupPage() {
    const router = useRouter();
    const [showPassword, setShowPassword] = useState(false);
    const [firstName, setFirstName] = useState("");
    const [lastName, setLastName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setIsLoading(true);
        try {
            await authService.signup({
                email,
                password,
                full_name: `${firstName} ${lastName}`.trim()
            });
            router.push("/auth/login");
        } catch (err: any) {
            setError(err.response?.data?.detail || "Something went wrong during signup");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-background flex items-center justify-center p-6 relative overflow-hidden">
            <div className="absolute -top-40 -right-40 w-[500px] h-[500px] rounded-full bg-primary/5 blur-[100px]" />
            <div className="absolute -bottom-40 -left-40 w-[400px] h-[400px] rounded-full bg-accent/5 blur-[80px]" />

            <div className="w-full max-w-4xl grid md:grid-cols-2 gap-12 items-center relative">
                {/* Left side */}
                <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.5 }}>
                    <Link href="/" className="inline-flex items-center gap-2 mb-10">
                        <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center">
                            <FileText className="w-5 h-5 text-white" />
                        </div>
                        <span className="font-bold text-lg">{PLATFORM_NAME}</span>
                    </Link>
                    <h1 className="text-4xl font-bold mb-4">Start landing more interviews</h1>
                    <p className="text-muted-foreground mb-8">
                        Analyze your resume against any job description and get an optimized version ready to submit.
                    </p>
                    <ul className="space-y-3">
                        {benefits.map((b) => (
                            <li key={b} className="flex items-center gap-3 text-sm">
                                <div className="w-5 h-5 rounded-full bg-success/20 flex items-center justify-center flex-shrink-0">
                                    <Check className="w-3 h-3 text-success" />
                                </div>
                                <span className="text-muted-foreground">{b}</span>
                            </li>
                        ))}
                    </ul>
                </motion.div>

                {/* Right side - Form */}
                <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.5, delay: 0.1 }}>
                    <div className="card-elevated rounded-2xl p-8">
                        <h2 className="text-xl font-bold mb-6">Create your free account</h2>
                        {error && <div className="text-red-500 text-sm mb-4">{error}</div>}
                        <form className="space-y-4" onSubmit={handleSubmit}>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="block text-xs font-medium text-muted-foreground mb-2">First name</label>
                                    <input type="text" placeholder="John" className="input-field" required value={firstName} onChange={(e) => setFirstName(e.target.value)} />
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-muted-foreground mb-2">Last name</label>
                                    <input type="text" placeholder="Doe" className="input-field" required value={lastName} onChange={(e) => setLastName(e.target.value)} />
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-muted-foreground mb-2">Work email</label>
                                <input type="email" placeholder="you@example.com" className="input-field" required value={email} onChange={(e) => setEmail(e.target.value)} />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-muted-foreground mb-2">Password</label>
                                <div className="relative">
                                    <input
                                        type={showPassword ? "text" : "password"}
                                        placeholder="At least 8 characters"
                                        className="input-field pr-12"
                                        required
                                        minLength={8}
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-4 top-1/2 -translate-y-1/2 text-muted hover:text-white transition-colors"
                                    >
                                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                    </button>
                                </div>
                            </div>
                            <label className="flex items-start gap-2 text-xs text-muted-foreground cursor-pointer">
                                <input type="checkbox" className="mt-0.5" required />
                                <span>I agree to the <a href="#" className="text-primary hover:underline">Terms of Service</a> and <a href="#" className="text-primary hover:underline">Privacy Policy</a></span>
                            </label>
                            <motion.button
                                type="submit"
                                disabled={isLoading}
                                whileHover={{ scale: 1.01 }}
                                whileTap={{ scale: 0.99 }}
                                className="btn-primary w-full flex items-center justify-center gap-2 py-3 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {isLoading ? "Creating..." : "Create free account"}
                                <ArrowRight className="w-4 h-4" />
                            </motion.button>
                        </form>
                        <p className="text-center text-xs text-muted-foreground mt-4">
                            Already have an account?{" "}
                            <Link href="/auth/login" className="text-primary hover:underline">Sign in</Link>
                        </p>
                    </div>
                </motion.div>
            </div>
        </div>
    );
}
