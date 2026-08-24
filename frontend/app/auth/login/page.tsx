"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FileText, Eye, EyeOff, ArrowRight } from "lucide-react";
import { authService, userService } from "@/services/api";
import { useAuthStore } from "@/store/authStore";

const PLATFORM_NAME = process.env.NEXT_PUBLIC_PLATFORM_NAME || "Resume JD Aligner";

export default function LoginPage() {
    const router = useRouter();
    const { setUser } = useAuthStore();
    const [showPassword, setShowPassword] = useState(false);
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setIsLoading(true);
        const cleanEmail = email.trim().toLowerCase();
        try {
            const res = await authService.login({
                username: cleanEmail,
                password: password
            });
            const token = res.data.access_token;

            // Seed the store with the token so the next request is authenticated,
            // then hydrate the real profile from /me (login only returns a token).
            setUser({ id: "", name: "", email: cleanEmail }, token);
            try {
                const me = await userService.getMe();
                setUser(
                    {
                        id: me.data.account.id,
                        name: me.data.profile.full_name || cleanEmail,
                        email: me.data.profile.email,
                        targetRole: me.data.profile.target_role,
                    },
                    token
                );
            } catch {
                // Profile hydration is best-effort; the token alone is enough to proceed.
            }

            // Redirect to dashboard on success
            router.push("/dashboard");
        } catch (err: any) {
            setError(err.response?.data?.detail || "Invalid email or password");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-background flex items-center justify-center p-6 relative overflow-hidden">
            {/* BG glows */}
            <div className="absolute -top-40 -left-40 w-[500px] h-[500px] rounded-full bg-primary/5 blur-[100px]" />
            <div className="absolute -bottom-40 -right-40 w-[400px] h-[400px] rounded-full bg-accent/5 blur-[80px]" />

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
                className="w-full max-w-md"
            >
                <div className="text-center mb-8">
                    <Link href="/" className="inline-flex items-center gap-2 mb-8">
                        <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center">
                            <FileText className="w-5 h-5 text-foreground" />
                        </div>
                        <span className="font-bold text-lg">{PLATFORM_NAME}</span>
                    </Link>
                    <h1 className="text-3xl font-bold mb-2">Welcome back</h1>
                    <p className="text-muted-foreground">Sign in to your account to continue</p>
                </div>

                <div className="card-elevated rounded-2xl p-8">
                    {error && <div className="text-red-500 text-sm mb-4 text-center">{error}</div>}
                    <form className="space-y-4" onSubmit={handleSubmit}>
                        <div>
                            <label className="block text-sm font-medium text-muted-foreground mb-2">Email address</label>
                            <input
                                type="email"
                                placeholder="you@example.com"
                                className="input-field"
                                required
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-muted-foreground mb-2">Password</label>
                            <div className="relative">
                                <input
                                    type={showPassword ? "text" : "password"}
                                    placeholder="••••••••"
                                    className="input-field pr-12"
                                    required
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-4 top-1/2 -translate-y-1/2 text-muted hover:text-foreground transition-colors"
                                >
                                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </button>
                            </div>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                            <label className="flex items-center gap-2 text-muted-foreground cursor-pointer">
                                <input type="checkbox" className="rounded" />
                                Remember me
                            </label>
                            <a href="#" className="text-primary hover:underline">Forgot password?</a>
                        </div>
                        <motion.button
                            type="submit"
                            disabled={isLoading}
                            whileHover={{ scale: 1.01 }}
                            whileTap={{ scale: 0.99 }}
                            className="btn-primary w-full flex items-center justify-center gap-2 py-3 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isLoading ? "Signing in..." : "Sign in"}
                            <ArrowRight className="w-4 h-4" />
                        </motion.button>
                    </form>

                    <div className="relative my-6">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-border" />
                        </div>
                        <div className="relative flex justify-center text-xs text-muted">
                            <span className="bg-card px-3">or continue with</span>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        {["Google", "GitHub"].map((provider) => (
                            <button key={provider} className="btn-ghost border border-border py-2.5 rounded-xl text-sm flex items-center justify-center gap-2">
                                {provider}
                            </button>
                        ))}
                    </div>
                </div>

                <p className="text-center text-sm text-muted-foreground mt-6">
                    Don't have an account?{" "}
                    <Link href="/auth/signup" className="text-primary hover:underline">Sign up free</Link>
                </p>
            </motion.div>
        </div>
    );
}
