"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useInView, useScroll, useSpring } from "framer-motion";
import {
    ArrowRight, CheckCircle, Zap, Target, BarChart3, Brain, Rocket, Shield, Star,
    ChevronRight, FileText, TrendingUp, Award,
} from "lucide-react";
import Link from "next/link";
import { ThemeToggle } from "@/components/ui/ThemeToggle";

const PLATFORM_NAME = process.env.NEXT_PUBLIC_PLATFORM_NAME || "Resume JD Aligner";

const features = [
    { icon: Target, title: "ATS Score Analysis", description: "A real-time ATS compatibility score with a breakdown of keyword density, formatting, and section completeness.", color: "text-primary", bg: "bg-primary/10" },
    { icon: Brain, title: "Semantic Alignment", description: "Vector matching that understands the true meaning behind your skills and the job's requirements — not just keyword overlap.", color: "text-accent", bg: "bg-accent/10" },
    { icon: Zap, title: "Resume Optimization", description: "Rewrites bullet points and injects missing keywords to match each company's language — without ever fabricating experience.", color: "text-warning", bg: "bg-warning/10" },
    { icon: BarChart3, title: "Skill Gap Detection", description: "Pinpoints exactly which skills you're missing for a role, prioritized by market demand and job criticality.", color: "text-success", bg: "bg-success/10" },
    { icon: TrendingUp, title: "Learning Roadmap", description: "Auto-generated, time-bound learning paths with curated resources to close your gaps in the shortest time.", color: "text-primary", bg: "bg-primary/10" },
    { icon: Award, title: "Interview Readiness", description: "An interview probability signal and company-specific prep, so you know where you stand before you apply.", color: "text-accent", bg: "bg-accent/10" },
];

const comparisonData = [
    { feature: "ATS Score Analysis", us: true, resumeio: false, zety: false, kickresume: false },
    { feature: "Semantic JD Alignment", us: true, resumeio: false, zety: false, kickresume: false },
    { feature: "Company-Specific Variants", us: true, resumeio: false, zety: false, kickresume: false },
    { feature: "AI Bullet Rewriting", us: true, resumeio: true, zety: true, kickresume: false },
    { feature: "Skill Gap Detection", us: true, resumeio: false, zety: false, kickresume: false },
    { feature: "Learning Roadmap", us: true, resumeio: false, zety: false, kickresume: false },
    { feature: "Interview Probability Score", us: true, resumeio: false, zety: false, kickresume: false },
    { feature: "Version History & Compare", us: true, resumeio: true, zety: false, kickresume: false },
];

const steps = [
    { number: "01", title: "Upload Your Resume", description: "Drop your PDF or DOCX. We parse it instantly and show you what we read." },
    { number: "02", title: "Add a Job Description", description: "Paste the posting. We extract the role, company, and requirements." },
    { number: "03", title: "Get Your Score", description: "See your ATS score, alignment %, and skill gaps in seconds." },
    { number: "04", title: "Optimize & Apply", description: "Download a tailored resume version and apply with confidence." },
];

const metrics = [
    { value: "3x", label: "Higher Interview Rate" },
    { value: "94%", label: "ATS Pass Rate" },
    { value: "60s", label: "Time to Score", prefix: "<" },
    { value: "50+", label: "Company Profiles" },
];

const faqs = [
    { q: "Is it really free?", a: "Yes. The core analysis — ATS scoring, JD alignment, and skill-gap detection — is free, with no credit card required." },
    { q: "Does it work with any job description?", a: "Paste any posting. We parse the role, company, requirements, and responsibilities, then score your resume against them." },
    { q: "Will it invent experience I don't have?", a: "Never. Rewrites are fact-guarded: we rephrase what's already in your resume, and block anything that would add claims you can't back up." },
    { q: "What files can I upload?", a: "PDF and DOCX up to 5MB. We show you exactly what we parsed before scoring, so you can catch a bad extraction early." },
    { q: "Is my data private?", a: "Your resume and job descriptions are scoped to your account and used only to generate your own analysis." },
];

/** Counts up to the numeric part of a metric when it scrolls into view. */
function CountUp({ value, prefix = "" }: { value: string; prefix?: string }) {
    const ref = useRef<HTMLSpanElement>(null);
    const inView = useInView(ref, { once: true, margin: "-60px" });
    // Parse once. Keep only primitives — an array in the effect deps would make
    // it re-run (and restart the animation) on every render, never settling.
    const parsed = value.match(/^(\d+)(\D*)$/);
    const numeric = parsed !== null;
    const target = parsed ? parseInt(parsed[1], 10) : 0;
    const suffix = parsed ? parsed[2] : "";
    const [n, setN] = useState(0);

    useEffect(() => {
        if (!inView || !numeric) return;
        const duration = 1200;
        const start = performance.now();
        let raf = 0;
        const tick = (now: number) => {
            const p = Math.min(1, (now - start) / duration);
            const eased = 1 - Math.pow(1 - p, 3);
            setN(Math.round(eased * target));
            if (p < 1) raf = requestAnimationFrame(tick);
        };
        raf = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(raf);
    }, [inView, numeric, target]);

    return (
        <span ref={ref}>
            {prefix}
            {numeric ? `${n}${suffix}` : value}
        </span>
    );
}

const fadeUp = {
    hidden: { opacity: 0, y: 24 },
    show: { opacity: 1, y: 0 },
};

export default function LandingPage() {
    const { scrollYProgress } = useScroll();
    const progress = useSpring(scrollYProgress, { stiffness: 120, damping: 30, mass: 0.3 });
    const [scrolled, setScrolled] = useState(false);

    useEffect(() => {
        const onScroll = () => setScrolled(window.scrollY > 12);
        onScroll();
        window.addEventListener("scroll", onScroll, { passive: true });
        return () => window.removeEventListener("scroll", onScroll);
    }, []);

    return (
        <div className="min-h-screen bg-background text-foreground overflow-x-hidden selection:bg-primary/30">
            {/* Scroll progress */}
            <motion.div
                style={{ scaleX: progress }}
                className="fixed top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-primary via-accent to-primary origin-left z-[60]"
            />

            {/* Navbar */}
            <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled ? "glass border-b border-border/60" : "bg-transparent"}`}>
                <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shadow-glow-sm flex-shrink-0">
                            <FileText className="w-4 h-4 text-primary-foreground" />
                        </div>
                        <span className="font-bold text-sm sm:text-base whitespace-nowrap truncate">{PLATFORM_NAME}</span>
                    </div>
                    <div className="hidden md:flex items-center gap-8 text-sm text-muted-foreground">
                        <a href="#features" className="hover:text-foreground transition-colors">Features</a>
                        <a href="#how-it-works" className="hover:text-foreground transition-colors">How it works</a>
                        <a href="#compare" className="hover:text-foreground transition-colors">Compare</a>
                        <a href="#faq" className="hover:text-foreground transition-colors">FAQ</a>
                    </div>
                    <div className="flex items-center gap-1.5 sm:gap-3 flex-shrink-0">
                        <ThemeToggle />
                        <Link href="/auth/login" className="btn-ghost text-sm hidden sm:inline-flex">Sign in</Link>
                        <Link href="/auth/signup" className="btn-primary text-sm whitespace-nowrap px-3.5 sm:px-5">
                            <span className="sm:hidden">Sign up</span>
                            <span className="hidden sm:inline">Get started free</span>
                        </Link>
                    </div>
                </div>
            </nav>

            {/* Hero */}
            <section className="relative min-h-screen flex items-center justify-center pt-24 pb-20 overflow-hidden">
                <div className="absolute inset-0 aurora" />
                <div className="absolute inset-0 grid-bg mask-fade-b opacity-70" />
                {/* Floating orbs */}
                <motion.div
                    className="absolute -top-32 -left-24 w-[520px] h-[520px] rounded-full bg-primary/20 blur-[120px] pointer-events-none"
                    animate={{ y: [0, 30, 0], x: [0, 20, 0] }}
                    transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
                />
                <motion.div
                    className="absolute -bottom-40 -right-24 w-[460px] h-[460px] rounded-full bg-accent/20 blur-[120px] pointer-events-none"
                    animate={{ y: [0, -26, 0], x: [0, -18, 0] }}
                    transition={{ duration: 14, repeat: Infinity, ease: "easeInOut" }}
                />

                <div className="relative max-w-5xl mx-auto px-6 text-center">
                    <motion.div
                        initial="hidden"
                        animate="show"
                        transition={{ staggerChildren: 0.12 }}
                    >
                        <motion.div variants={fadeUp} transition={{ duration: 0.5 }}
                            className="inline-flex items-center gap-2 bg-primary/10 border border-primary/20 rounded-full px-4 py-1.5 text-sm text-primary mb-8 backdrop-blur-sm">
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-60" />
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary" />
                            </span>
                            AI-powered resume intelligence
                        </motion.div>

                        <motion.h1 variants={fadeUp} transition={{ duration: 0.6 }}
                            className="text-[2.5rem] sm:text-6xl md:text-7xl font-bold tracking-tight mb-6 leading-[1.08] sm:leading-[1.05] text-balance">
                            Your resume, <span className="gradient-text">perfectly aligned</span> to every job
                        </motion.h1>

                        <motion.p variants={fadeUp} transition={{ duration: 0.6 }}
                            className="text-base sm:text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed text-balance">
                            Stop guessing why you&apos;re not getting callbacks. Get your ATS score, skill-gap analysis, and an AI-optimized resume tailored to each company — in under 60 seconds.
                        </motion.p>

                        <motion.div variants={fadeUp} transition={{ duration: 0.6 }}
                            className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-14">
                            <Link href="/auth/signup">
                                <motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.98 }}
                                    className="btn-primary flex items-center gap-2 text-base px-8 py-3 glow-primary group">
                                    Analyze my resume free
                                    <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                                </motion.button>
                            </Link>
                            <a href="#how-it-works" className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors text-sm">
                                See how it works <ChevronRight className="w-4 h-4" />
                            </a>
                        </motion.div>

                        <motion.div variants={fadeUp} transition={{ duration: 0.6 }}
                            className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-muted">
                            {["No credit card required", "Free forever plan", "Private by default", "Instant analysis"].map((item) => (
                                <div key={item} className="flex items-center gap-1.5">
                                    <CheckCircle className="w-3.5 h-3.5 text-success" />
                                    <span>{item}</span>
                                </div>
                            ))}
                        </motion.div>
                    </motion.div>

                    {/* Animated dashboard preview */}
                    <motion.div
                        initial={{ opacity: 0, y: 60, rotateX: 8 }}
                        animate={{ opacity: 1, y: 0, rotateX: 0 }}
                        transition={{ duration: 0.9, delay: 0.4, ease: "easeOut" }}
                        className="mt-20 relative"
                        style={{ perspective: 1000 }}
                    >
                        <div className="card-elevated rounded-2xl overflow-hidden p-5 sm:p-6 card-glow">
                            <div className="flex items-center gap-2 mb-5 pb-4 border-b border-border">
                                <div className="flex gap-1.5">
                                    <div className="w-3 h-3 rounded-full bg-error/60" />
                                    <div className="w-3 h-3 rounded-full bg-warning/60" />
                                    <div className="w-3 h-3 rounded-full bg-success/60" />
                                </div>
                                <div className="flex-1 h-5 bg-surface-2 rounded-md max-w-xs mx-auto" />
                            </div>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4 mb-6">
                                {[
                                    { label: "ATS Score", value: "92%", color: "text-success" },
                                    { label: "JD Alignment", value: "85%", color: "text-primary" },
                                    { label: "Readiness", value: "78%", color: "text-warning" },
                                    { label: "Interview", value: "High", color: "text-accent" },
                                ].map((stat, i) => (
                                    <motion.div key={stat.label}
                                        initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }}
                                        transition={{ delay: 0.5 + i * 0.1 }} viewport={{ once: true }}
                                        className="bg-surface-2 rounded-xl p-4 text-left border border-border/50">
                                        <div className={`text-2xl font-bold ${stat.color} mb-1`}>{stat.value}</div>
                                        <div className="text-xs text-muted">{stat.label}</div>
                                    </motion.div>
                                ))}
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div className="bg-surface-2 rounded-xl p-4 border border-border/50">
                                    <div className="text-xs text-muted mb-3">Alignment breakdown</div>
                                    {[
                                        { l: "Skills", w: "88%", c: "bg-success" },
                                        { l: "Experience", w: "72%", c: "bg-primary" },
                                        { l: "Seniority", w: "64%", c: "bg-warning" },
                                    ].map((bar, i) => (
                                        <div key={bar.l} className="flex items-center gap-2 mb-2 last:mb-0 text-xs">
                                            <span className="w-16 text-muted">{bar.l}</span>
                                            <div className="flex-1 h-2 bg-border rounded-full overflow-hidden">
                                                <motion.div className={`h-full ${bar.c} rounded-full`}
                                                    initial={{ width: 0 }} whileInView={{ width: bar.w }}
                                                    transition={{ duration: 0.9, delay: 0.6 + i * 0.15 }} viewport={{ once: true }} />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                <div className="bg-surface-2 rounded-xl p-4 border border-border/50">
                                    <div className="text-xs text-muted mb-3">Missing skills</div>
                                    <div className="flex flex-wrap gap-1.5">
                                        {["Kubernetes", "Terraform", "System Design", "Kafka"].map((s, i) => (
                                            <motion.span key={s}
                                                initial={{ opacity: 0, scale: 0.8 }} whileInView={{ opacity: 1, scale: 1 }}
                                                transition={{ delay: 0.7 + i * 0.1 }} viewport={{ once: true }}
                                                className="text-xs bg-error/10 text-error border border-error/20 rounded-md px-2 py-1">
                                                {s}
                                            </motion.span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </div>
            </section>

            {/* Metrics */}
            <section className="py-12 sm:py-16 border-y border-border/60 bg-surface/30">
                <div className="max-w-5xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
                    {metrics.map((m, i) => (
                        <motion.div key={m.label} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.1 }} viewport={{ once: true }}>
                            <div className="text-4xl md:text-5xl font-bold gradient-text mb-2">
                                <CountUp value={m.value} prefix={m.prefix} />
                            </div>
                            <div className="text-sm text-muted">{m.label}</div>
                        </motion.div>
                    ))}
                </div>
            </section>

            {/* Features */}
            <section id="features" className="py-16 sm:py-24 max-w-7xl mx-auto px-6">
                <SectionHeading
                    chip={<><Star className="w-3.5 h-3.5 text-warning" /> Everything you need to land the job</>}
                    title="Not just another resume builder"
                    subtitle="An intelligence platform — the gap between you applying and you getting the interview."
                />
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {features.map((feature, i) => (
                        <motion.div key={feature.title}
                            initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.06 }} viewport={{ once: true }}
                            whileHover={{ y: -6 }}
                            className="card-elevated rounded-2xl p-6 group cursor-default hover:border-primary/40 transition-colors">
                            <div className={`inline-flex p-3 rounded-xl ${feature.bg} mb-4 transition-transform group-hover:scale-110 group-hover:-rotate-3`}>
                                <feature.icon className={`w-5 h-5 ${feature.color}`} />
                            </div>
                            <h3 className="font-semibold mb-2">{feature.title}</h3>
                            <p className="text-sm text-muted-foreground leading-relaxed">{feature.description}</p>
                        </motion.div>
                    ))}
                </div>
            </section>

            {/* How it works */}
            <section id="how-it-works" className="py-16 sm:py-24 bg-surface/40 border-y border-border/60 relative overflow-hidden">
                <div className="absolute inset-0 grid-bg opacity-40" />
                <div className="max-w-5xl mx-auto px-6 relative">
                    <SectionHeading title="From upload to offer — in minutes" subtitle="Four simple steps to a recruiter-grade resume." />
                    <div className="grid md:grid-cols-4 gap-6 relative">
                        <div className="absolute top-8 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent hidden md:block" />
                        {steps.map((step, i) => (
                            <motion.div key={step.number}
                                initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.12 }} viewport={{ once: true }}
                                className="text-center relative">
                                <motion.div whileHover={{ scale: 1.08 }}
                                    className="w-16 h-16 rounded-2xl bg-card border border-primary/30 flex items-center justify-center mx-auto mb-4 relative z-10 shadow-glow-sm">
                                    <span className="text-xl font-bold gradient-text">{step.number}</span>
                                </motion.div>
                                <h3 className="font-semibold mb-2">{step.title}</h3>
                                <p className="text-sm text-muted-foreground">{step.description}</p>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Comparison */}
            <section id="compare" className="py-16 sm:py-24 max-w-5xl mx-auto px-6">
                <SectionHeading title="Built differently. For results." subtitle="How we compare to traditional resume builders." />
                <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
                    className="card-elevated rounded-2xl overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-border">
                                    <th className="text-left p-4 font-medium text-muted-foreground">Feature</th>
                                    <th className="p-4 font-semibold text-primary whitespace-nowrap">{PLATFORM_NAME}</th>
                                    <th className="p-4 font-medium text-muted-foreground">Resume.io</th>
                                    <th className="p-4 font-medium text-muted-foreground">Zety</th>
                                    <th className="p-4 font-medium text-muted-foreground">Kickresume</th>
                                </tr>
                            </thead>
                            <tbody>
                                {comparisonData.map((row, i) => (
                                    <tr key={row.feature} className={`border-b border-border/50 last:border-0 ${i % 2 === 0 ? "bg-surface/30" : ""}`}>
                                        <td className="p-4 text-muted-foreground">{row.feature}</td>
                                        <td className="p-4 text-center"><CheckCircle className="w-5 h-5 text-success mx-auto" /></td>
                                        <td className="p-4 text-center">{row.resumeio ? <CheckCircle className="w-5 h-5 text-success mx-auto" /> : <span className="text-muted/40 text-lg">—</span>}</td>
                                        <td className="p-4 text-center">{row.zety ? <CheckCircle className="w-5 h-5 text-success mx-auto" /> : <span className="text-muted/40 text-lg">—</span>}</td>
                                        <td className="p-4 text-center">{row.kickresume ? <CheckCircle className="w-5 h-5 text-success mx-auto" /> : <span className="text-muted/40 text-lg">—</span>}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </motion.div>
            </section>

            {/* FAQ */}
            <section id="faq" className="py-16 sm:py-24 max-w-3xl mx-auto px-6">
                <SectionHeading
                    chip={<><Shield className="w-3.5 h-3.5 text-primary" /> Honest by design</>}
                    title="Questions, answered"
                    subtitle="Everything you need to know before you start."
                />
                <div className="space-y-3">
                    {faqs.map((faq, i) => (
                        <motion.details key={faq.q}
                            initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.05 }} viewport={{ once: true }}
                            className="card-elevated rounded-2xl p-5 group hover:border-primary/30 transition-colors">
                            <summary className="flex items-center justify-between gap-4 cursor-pointer font-medium list-none">
                                {faq.q}
                                <ChevronRight className="w-4 h-4 text-muted flex-shrink-0 transition-transform group-open:rotate-90" />
                            </summary>
                            <p className="text-sm text-muted-foreground mt-3 leading-relaxed">{faq.a}</p>
                        </motion.details>
                    ))}
                </div>
            </section>

            {/* CTA */}
            <section className="py-16 sm:py-24 relative overflow-hidden">
                <div className="absolute inset-0 aurora" />
                <div className="absolute inset-0 grid-bg opacity-40" />
                <motion.div initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
                    className="relative max-w-3xl mx-auto px-6 text-center">
                    <motion.div animate={{ y: [0, -8, 0] }} transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                        className="inline-flex p-4 rounded-2xl bg-primary/10 border border-primary/20 mb-6">
                        <Rocket className="w-8 h-8 text-primary" />
                    </motion.div>
                    <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-6 text-balance">Start landing more interviews today</h2>
                    <p className="text-base sm:text-lg md:text-xl text-muted-foreground mb-10 text-balance">
                        Join candidates who use {PLATFORM_NAME} to apply smarter and get shortlisted faster.
                    </p>
                    <Link href="/auth/signup">
                        <motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.98 }}
                            className="btn-primary flex items-center gap-2 text-lg px-10 py-4 mx-auto glow-primary group">
                            Get started for free
                            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                        </motion.button>
                    </Link>
                    <p className="text-sm text-muted mt-4">No credit card required · Free forever plan · Cancel anytime</p>
                </motion.div>
            </section>

            {/* Footer */}
            <footer className="border-t border-border py-12">
                <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
                    <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-md bg-primary flex items-center justify-center">
                            <FileText className="w-3 h-3 text-primary-foreground" />
                        </div>
                        <span className="font-semibold text-sm">{PLATFORM_NAME}</span>
                    </div>
                    <p className="text-sm text-muted">© 2026 {PLATFORM_NAME}. All rights reserved.</p>
                    <div className="flex items-center gap-6 text-sm text-muted">
                        <a href="#" className="hover:text-foreground transition-colors">Privacy</a>
                        <a href="#" className="hover:text-foreground transition-colors">Terms</a>
                        <a href="#" className="hover:text-foreground transition-colors">Contact</a>
                    </div>
                </div>
            </footer>
        </div>
    );
}

function SectionHeading({ chip, title, subtitle }: { chip?: React.ReactNode; title: string; subtitle: string }) {
    return (
        <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
            className="text-center mb-10 sm:mb-14">
            {chip && (
                <div className="inline-flex items-center gap-2 bg-surface border border-border rounded-full px-4 py-1.5 text-sm text-muted mb-4">
                    {chip}
                </div>
            )}
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-4 text-balance">{title}</h2>
            <p className="text-muted-foreground max-w-xl mx-auto text-balance">{subtitle}</p>
        </motion.div>
    );
}
