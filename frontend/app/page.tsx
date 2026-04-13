"use client";

import { motion } from "framer-motion";
import { ArrowRight, CheckCircle, Zap, Target, BarChart3, Brain, Rocket, Shield, Star, ChevronRight, FileText, TrendingUp, Award } from "lucide-react";
import Link from "next/link";

const PLATFORM_NAME = process.env.NEXT_PUBLIC_PLATFORM_NAME || "Resume JD Aligner";

const features = [
    {
        icon: Target,
        title: "ATS Score Analysis",
        description: "Get a real-time ATS compatibility score with detailed breakdown of keyword density, formatting, and section completeness.",
        color: "text-primary",
        bg: "bg-primary/10",
    },
    {
        icon: Brain,
        title: "Semantic Alignment",
        description: "AI-powered vector matching that understands the true semantic meaning behind your skills and the job requirements.",
        color: "text-accent",
        bg: "bg-accent/10",
    },
    {
        icon: Zap,
        title: "Resume Optimization",
        description: "Automatically rewrite bullet points and inject missing keywords to match each company's language—without fabricating experience.",
        color: "text-warning",
        bg: "bg-warning/10",
    },
    {
        icon: BarChart3,
        title: "Skill Gap Detection",
        description: "Pinpoint exactly which skills you're missing for any role, prioritized by market demand and job criticality.",
        color: "text-success",
        bg: "bg-success/10",
    },
    {
        icon: TrendingUp,
        title: "Learning Roadmap",
        description: "Auto-generated, time-bound learning paths with curated resources to close your skill gaps in the shortest time.",
        color: "text-cyan-400",
        bg: "bg-cyan-400/10",
    },
    {
        icon: Award,
        title: "Interview Readiness",
        description: "Predict your interview probability score and get company-specific preparation tips before you apply.",
        color: "text-rose-400",
        bg: "bg-rose-400/10",
    },
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
    { number: "01", title: "Upload Your Resume", description: "Drop your PDF or Docx. We parse it instantly." },
    { number: "02", title: "Add a Job Description", description: "Paste the JD or link to the job posting." },
    { number: "03", title: "Get Your Score", description: "See your ATS score, alignment %, and skill gaps in seconds." },
    { number: "04", title: "Optimize & Apply", description: "Download a tailored resume version. Apply with confidence." },
];

const metrics = [
    { value: "3x", label: "Higher Interview Rate" },
    { value: "94%", label: "ATS Pass Rate" },
    { value: "< 60s", label: "Time to Score" },
    { value: "50+", label: "Company Profiles" },
];

export default function LandingPage() {
    return (
        <div className="min-h-screen bg-background text-white overflow-x-hidden">
            {/* Navbar */}
            <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-border/50">
                <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                            <FileText className="w-4 h-4 text-white" />
                        </div>
                        <span className="font-bold text-white">{PLATFORM_NAME}</span>
                    </div>
                    <div className="hidden md:flex items-center gap-8 text-sm text-muted-foreground">
                        <a href="#features" className="hover:text-white transition-colors">Features</a>
                        <a href="#how-it-works" className="hover:text-white transition-colors">How it works</a>
                        <a href="#compare" className="hover:text-white transition-colors">Compare</a>
                    </div>
                    <div className="flex items-center gap-3">
                        <Link href="/auth/login" className="btn-ghost text-sm">Sign in</Link>
                        <Link href="/auth/signup" className="btn-primary text-sm">Get started free</Link>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="relative min-h-screen flex items-center justify-center pt-16 overflow-hidden">
                {/* Animated gradient background */}
                <div className="absolute inset-0 overflow-hidden pointer-events-none">
                    <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-primary/5 blur-[120px] animate-pulse-slow" />
                    <div className="absolute -bottom-40 -right-40 w-[500px] h-[500px] rounded-full bg-accent/5 blur-[100px] animate-pulse-slow" style={{ animationDelay: "1s" }} />
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full bg-primary/3 blur-[150px]" />
                    {/* Grid */}
                    <div className="absolute inset-0 bg-[linear-gradient(rgba(99,102,241,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.03)_1px,transparent_1px)] bg-[size:60px_60px]" />
                </div>

                <div className="relative max-w-5xl mx-auto px-6 text-center">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6 }}
                    >
                        <div className="inline-flex items-center gap-2 bg-primary/10 border border-primary/20 rounded-full px-4 py-1.5 text-sm text-primary mb-8">
                            <Zap className="w-3.5 h-3.5" />
                            <span>AI-powered resume intelligence</span>
                        </div>

                        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 leading-tight">
                            Your resume,{" "}
                            <span className="gradient-text">perfectly aligned</span>
                            {" "}to every job
                        </h1>

                        <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
                            Stop guessing why you're not getting callbacks. Get your ATS score, skill gap analysis, and an AI-optimized resume tailored to each company — in under 60 seconds.
                        </p>

                        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
                            <Link href="/auth/signup">
                                <motion.button
                                    whileHover={{ scale: 1.03 }}
                                    whileTap={{ scale: 0.98 }}
                                    className="btn-primary flex items-center gap-2 text-base px-8 py-3 glow-primary"
                                >
                                    Analyze my resume free
                                    <ArrowRight className="w-4 h-4" />
                                </motion.button>
                            </Link>
                            <Link href="#how-it-works" className="flex items-center gap-2 text-muted-foreground hover:text-white transition-colors text-sm">
                                See how it works <ChevronRight className="w-4 h-4" />
                            </Link>
                        </div>

                        {/* Trust bar */}
                        <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-muted">
                            {["No credit card required", "Free forever plan", "GDPR compliant", "Instant analysis"].map((item) => (
                                <div key={item} className="flex items-center gap-1.5">
                                    <CheckCircle className="w-3.5 h-3.5 text-success" />
                                    <span>{item}</span>
                                </div>
                            ))}
                        </div>
                    </motion.div>

                    {/* Hero Dashboard Preview */}
                    <motion.div
                        initial={{ opacity: 0, y: 60 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.8, delay: 0.3 }}
                        className="mt-20 relative"
                    >
                        <div className="card-elevated rounded-2xl overflow-hidden p-6 glow-primary">
                            <div className="flex items-center gap-2 mb-4 pb-4 border-b border-border">
                                <div className="flex gap-1.5">
                                    <div className="w-3 h-3 rounded-full bg-error/60" />
                                    <div className="w-3 h-3 rounded-full bg-warning/60" />
                                    <div className="w-3 h-3 rounded-full bg-success/60" />
                                </div>
                                <div className="flex-1 h-5 bg-surface-2 rounded-md w-48 mx-auto" />
                            </div>
                            <div className="grid grid-cols-4 gap-4 mb-6">
                                {[
                                    { label: "ATS Score", value: "92%", color: "text-success" },
                                    { label: "JD Alignment", value: "85%", color: "text-primary" },
                                    { label: "Readiness", value: "78%", color: "text-warning" },
                                    { label: "Interview Prob.", value: "High", color: "text-accent" },
                                ].map((stat) => (
                                    <div key={stat.label} className="bg-surface-2 rounded-xl p-4 text-left border border-border/50">
                                        <div className={`text-2xl font-bold ${stat.color} mb-1`}>{stat.value}</div>
                                        <div className="text-xs text-muted">{stat.label}</div>
                                    </div>
                                ))}
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-surface-2 rounded-xl p-4 border border-border/50 h-32">
                                    <div className="text-xs text-muted mb-3">Skill Gap Heatmap</div>
                                    <div className="grid grid-cols-5 gap-1">
                                        {[...Array(15)].map((_, i) => (
                                            <div key={i} className={`h-5 rounded-sm ${i < 5 ? 'bg-success/60' : i < 10 ? 'bg-warning/40' : 'bg-error/40'}`} />
                                        ))}
                                    </div>
                                </div>
                                <div className="bg-surface-2 rounded-xl p-4 border border-border/50 h-32">
                                    <div className="text-xs text-muted mb-2">Missing Skills</div>
                                    {["Kubernetes", "Terraform", "System Design"].map((s) => (
                                        <div key={s} className="text-xs bg-error/10 text-error border border-error/20 rounded-md px-2 py-1 mb-1 inline-block mr-1">{s}</div>
                                    ))}
                                </div>
                            </div>
                        </div>
                        <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 w-[90%] h-8 bg-primary/10 blur-2xl rounded-full" />
                    </motion.div>
                </div>
            </section>

            {/* Metrics Bar */}
            <section className="py-16 border-y border-border/50">
                <div className="max-w-5xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
                    {metrics.map((m, i) => (
                        <motion.div
                            key={m.label}
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.1 }}
                            viewport={{ once: true }}
                        >
                            <div className="text-4xl font-bold gradient-text mb-2">{m.value}</div>
                            <div className="text-sm text-muted">{m.label}</div>
                        </motion.div>
                    ))}
                </div>
            </section>

            {/* Features Section */}
            <section id="features" className="py-24 max-w-7xl mx-auto px-6">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="text-center mb-16"
                >
                    <div className="inline-flex items-center gap-2 bg-surface border border-border rounded-full px-4 py-1.5 text-sm text-muted mb-4">
                        <Star className="w-3.5 h-3.5 text-warning" />
                        <span>Everything you need to land the job</span>
                    </div>
                    <h2 className="text-4xl md:text-5xl font-bold mb-4">Not just another resume builder</h2>
                    <p className="text-muted-foreground max-w-xl mx-auto">
                        We're an intelligence platform — the gap between you applying and you getting the interview.
                    </p>
                </motion.div>

                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {features.map((feature, i) => (
                        <motion.div
                            key={feature.title}
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.08 }}
                            viewport={{ once: true }}
                            whileHover={{ y: -4, transition: { duration: 0.2 } }}
                            className="card-elevated rounded-2xl p-6 group cursor-default"
                        >
                            <div className={`inline-flex p-3 rounded-xl ${feature.bg} mb-4`}>
                                <feature.icon className={`w-5 h-5 ${feature.color}`} />
                            </div>
                            <h3 className="font-semibold text-white mb-2">{feature.title}</h3>
                            <p className="text-sm text-muted-foreground leading-relaxed">{feature.description}</p>
                        </motion.div>
                    ))}
                </div>
            </section>

            {/* How It Works */}
            <section id="how-it-works" className="py-24 bg-surface/30 border-y border-border/50">
                <div className="max-w-5xl mx-auto px-6">
                    <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center mb-16">
                        <h2 className="text-4xl font-bold mb-4">From upload to offer — in minutes</h2>
                        <p className="text-muted-foreground">Four simple steps to a recruiter-grade resume.</p>
                    </motion.div>
                    <div className="grid md:grid-cols-4 gap-6 relative">
                        <div className="absolute top-8 left-0 right-0 h-px bg-gradient-to-r from-transparent via-border to-transparent hidden md:block" />
                        {steps.map((step, i) => (
                            <motion.div
                                key={step.number}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.1 }}
                                viewport={{ once: true }}
                                className="text-center relative"
                            >
                                <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-4 relative z-10">
                                    <span className="text-xl font-bold text-primary">{step.number}</span>
                                </div>
                                <h3 className="font-semibold mb-2">{step.title}</h3>
                                <p className="text-sm text-muted-foreground">{step.description}</p>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Comparison Table */}
            <section id="compare" className="py-24 max-w-5xl mx-auto px-6">
                <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center mb-16">
                    <h2 className="text-4xl font-bold mb-4">Built differently. For results.</h2>
                    <p className="text-muted-foreground">See how we compare to traditional resume builders.</p>
                </motion.div>
                <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="card-elevated rounded-2xl overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-border">
                                    <th className="text-left p-4 font-medium text-muted-foreground">Feature</th>
                                    <th className="p-4 font-semibold text-primary">{PLATFORM_NAME}</th>
                                    <th className="p-4 font-medium text-muted-foreground">Resume.io</th>
                                    <th className="p-4 font-medium text-muted-foreground">Zety</th>
                                    <th className="p-4 font-medium text-muted-foreground">Kickresume</th>
                                </tr>
                            </thead>
                            <tbody>
                                {comparisonData.map((row, i) => (
                                    <tr key={row.feature} className={i % 2 === 0 ? "bg-surface/20" : ""}>
                                        <td className="p-4 text-muted-foreground">{row.feature}</td>
                                        <td className="p-4 text-center"><CheckCircle className="w-5 h-5 text-success mx-auto" /></td>
                                        <td className="p-4 text-center">{row.resumeio ? <CheckCircle className="w-5 h-5 text-success mx-auto" /> : <span className="text-border text-lg font-light">—</span>}</td>
                                        <td className="p-4 text-center">{row.zety ? <CheckCircle className="w-5 h-5 text-success mx-auto" /> : <span className="text-border text-lg font-light">—</span>}</td>
                                        <td className="p-4 text-center">{row.kickresume ? <CheckCircle className="w-5 h-5 text-success mx-auto" /> : <span className="text-border text-lg font-light">—</span>}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </motion.div>
            </section>

            {/* CTA Section */}
            <section className="py-24 relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-accent/10" />
                <div className="absolute inset-0 bg-[linear-gradient(rgba(99,102,241,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.05)_1px,transparent_1px)] bg-[size:40px_40px]" />
                <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="relative max-w-3xl mx-auto px-6 text-center">
                    <div className="inline-flex p-4 rounded-2xl bg-primary/10 border border-primary/20 mb-6">
                        <Rocket className="w-8 h-8 text-primary" />
                    </div>
                    <h2 className="text-4xl md:text-5xl font-bold mb-6">Start landing more interviews today</h2>
                    <p className="text-xl text-muted-foreground mb-10">
                        Join thousands of candidates who use {PLATFORM_NAME} to apply smarter and get shortlisted faster.
                    </p>
                    <Link href="/auth/signup">
                        <motion.button
                            whileHover={{ scale: 1.03 }}
                            whileTap={{ scale: 0.98 }}
                            className="btn-primary flex items-center gap-2 text-lg px-10 py-4 mx-auto glow-primary"
                        >
                            Get started for free
                            <ArrowRight className="w-5 h-5" />
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
                            <FileText className="w-3 h-3 text-white" />
                        </div>
                        <span className="font-semibold text-sm">{PLATFORM_NAME}</span>
                    </div>
                    <p className="text-sm text-muted">© 2025 {PLATFORM_NAME}. All rights reserved.</p>
                    <div className="flex items-center gap-6 text-sm text-muted">
                        <a href="#" className="hover:text-white transition-colors">Privacy</a>
                        <a href="#" className="hover:text-white transition-colors">Terms</a>
                        <a href="#" className="hover:text-white transition-colors">Contact</a>
                    </div>
                </div>
            </footer>
        </div>
    );
}
