"use client";

import { Suspense, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { MailCheck, ArrowRight, Loader2 } from "lucide-react";
import { authService, userService } from "@/services/api";
import { useAuthStore } from "@/store/authStore";

const PLATFORM_NAME = process.env.NEXT_PUBLIC_PLATFORM_NAME || "Resume JD Aligner";

function VerifyContent() {
    const router = useRouter();
    const email = useSearchParams().get("email") || "";
    const { setUser } = useAuthStore();
    const [code, setCode] = useState("");
    const [error, setError] = useState("");
    const [notice, setNotice] = useState("");
    const [loading, setLoading] = useState(false);

    const verify = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setNotice("");
        setLoading(true);
        try {
            const res = await authService.verifyEmail({ email, code: code.trim() });
            const token = res.data.access_token;
            setUser({ id: "", name: "", email }, token);
            try {
                const me = await userService.getMe();
                setUser(
                    {
                        id: me.data.account.id,
                        name: me.data.profile.full_name || email,
                        email: me.data.profile.email,
                        targetRole: me.data.profile.target_role,
                    },
                    token
                );
            } catch {
                // best-effort profile hydration; the token alone is enough.
            }
            router.push("/dashboard");
        } catch (err: any) {
            setError(err?.response?.data?.detail || "Invalid or expired code.");
        } finally {
            setLoading(false);
        }
    };

    const resend = async () => {
        setError("");
        try {
            await authService.resendVerification(email);
            setNotice("A new code is on its way.");
        } catch {
            setError("Couldn't resend the code. Try again in a moment.");
        }
    };

    return (
        <div className="min-h-screen bg-background flex items-center justify-center p-4 sm:p-6 relative overflow-hidden">
            <div className="absolute -top-40 -left-40 w-[500px] h-[500px] rounded-full bg-primary/5 blur-[100px]" />

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
                className="w-full max-w-md"
            >
                <div className="text-center mb-8">
                    <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                        <MailCheck className="w-6 h-6 text-primary" />
                    </div>
                    <h1 className="text-2xl font-bold mb-2">Verify your email</h1>
                    <p className="text-muted-foreground text-sm">
                        {email
                            ? <>We sent a 6-digit code to <span className="text-foreground font-medium">{email}</span>.</>
                            : "Enter the code we emailed you."}
                    </p>
                </div>

                <div className="card-elevated rounded-2xl p-6 sm:p-8">
                    {error && <div className="text-error text-sm mb-4 text-center">{error}</div>}
                    {notice && <div className="text-success text-sm mb-4 text-center">{notice}</div>}

                    <form className="space-y-4" onSubmit={verify}>
                        <div>
                            <label className="block text-sm font-medium text-muted-foreground mb-2">Verification code</label>
                            <input
                                inputMode="numeric"
                                autoComplete="one-time-code"
                                maxLength={6}
                                placeholder="123456"
                                className="input-field text-center text-lg tracking-[0.4em] font-semibold"
                                required
                                value={code}
                                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                            />
                        </div>
                        <motion.button
                            type="submit"
                            disabled={loading || code.length < 6}
                            whileHover={{ scale: loading ? 1 : 1.01 }}
                            whileTap={{ scale: loading ? 1 : 0.99 }}
                            className="btn-primary w-full flex items-center justify-center gap-2 py-3 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <>Verify <ArrowRight className="w-4 h-4" /></>}
                        </motion.button>
                    </form>

                    <p className="text-center text-sm text-muted-foreground mt-6">
                        Didn&apos;t get it?{" "}
                        <button type="button" onClick={resend} className="text-primary hover:underline">Resend code</button>
                    </p>
                </div>

                <p className="text-center text-sm text-muted-foreground mt-6">
                    Wrong email? <Link href="/auth/signup" className="text-primary hover:underline">Sign up again</Link>
                </p>
                <p className="text-center text-xs text-muted mt-4">{PLATFORM_NAME}</p>
            </motion.div>
        </div>
    );
}

export default function VerifyPage() {
    return (
        <Suspense fallback={null}>
            <VerifyContent />
        </Suspense>
    );
}
