"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { CheckCircle, Circle, ExternalLink, Clock, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";

const roadmap = [
    {
        week: "Week 1–2", module: "Containerization Foundations", priority: "high",
        skills: ["Docker basics", "Docker Compose", "Image optimization"],
        resources: [{ title: "Docker Deep Dive", url: "#" }, { title: "Play with Docker", url: "#" }],
        completed: false,
    },
    {
        week: "Week 3–5", module: "Kubernetes Orchestration", priority: "high",
        skills: ["Pods & Deployments", "Services & Ingress", "Helm Charts"],
        resources: [{ title: "Kubernetes Official Docs", url: "#" }, { title: "KodeKloud K8s Course", url: "#" }],
        completed: false,
    },
    {
        week: "Week 6–7", module: "Infrastructure as Code", priority: "medium",
        skills: ["Terraform basics", "AWS Provider", "State management"],
        resources: [{ title: "HashiCorp Learn", url: "#" }],
        completed: false,
    },
    {
        week: "Week 8–9", module: "CI/CD Pipelines", priority: "medium",
        skills: ["GitHub Actions", "ArgoCD", "Build optimization"],
        resources: [{ title: "GitHub Actions docs", url: "#" }],
        completed: true,
    },
];

const priorityColor = { high: "border-error text-error bg-error/10", medium: "border-warning text-warning bg-warning/10", low: "border-primary text-primary bg-primary/10" };

export default function LearningPage() {
    const [expandedIndex, setExpandedIndex] = useState<number | null>(0);
    const [completedSet, setCompletedSet] = useState<Set<number>>(new Set(roadmap.map((r, i) => r.completed ? i : -1).filter(i => i >= 0)));

    const toggleComplete = (i: number) => {
        setCompletedSet((prev) => {
            const next = new Set(prev);
            next.has(i) ? next.delete(i) : next.add(i);
            return next;
        });
    };

    return (
        <div className="max-w-3xl mx-auto space-y-6">
            <div>
                <h1 className="text-2xl font-bold">Learning Roadmap</h1>
                <p className="text-sm text-muted mt-1">Personalized based on your skill gaps across all target JDs</p>
            </div>

            {/* Progress Bar */}
            <div className="card-elevated rounded-2xl p-5">
                <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-medium">Overall Progress</span>
                    <span className="text-sm font-bold text-primary">{completedSet.size}/{roadmap.length} modules</span>
                </div>
                <div className="h-2.5 bg-border rounded-full overflow-hidden">
                    <motion.div
                        animate={{ width: `${(completedSet.size / roadmap.length) * 100}%` }}
                        transition={{ duration: 0.5 }}
                        className="h-full bg-gradient-to-r from-primary to-accent rounded-full"
                    />
                </div>
            </div>

            {/* Timeline */}
            <div className="relative">
                <div className="absolute left-6 top-8 bottom-0 w-px bg-border" />
                <div className="space-y-4">
                    {roadmap.map((item, i) => (
                        <motion.div key={i} initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.06 }}>
                            <div className="flex gap-4">
                                {/* Timeline node */}
                                <button
                                    onClick={() => toggleComplete(i)}
                                    className="relative z-10 mt-4 flex-shrink-0 w-12 h-12 rounded-full bg-card border-2 border-border flex items-center justify-center hover:border-primary transition-colors"
                                >
                                    {completedSet.has(i)
                                        ? <CheckCircle className="w-6 h-6 text-success" />
                                        : <Circle className="w-6 h-6 text-muted" />}
                                </button>

                                {/* Card */}
                                <div className="flex-1 card-elevated rounded-2xl overflow-hidden">
                                    <div
                                        className="p-4 cursor-pointer flex items-center justify-between"
                                        onClick={() => setExpandedIndex(expandedIndex === i ? null : i)}
                                    >
                                        <div>
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium", priorityColor[item.priority as keyof typeof priorityColor])}>
                                                    {item.priority} priority
                                                </span>
                                                <div className="flex items-center gap-1 text-xs text-muted">
                                                    <Clock className="w-3 h-3" /> {item.week}
                                                </div>
                                            </div>
                                            <h3 className={cn("font-semibold", completedSet.has(i) ? "line-through text-muted" : "text-white")}>
                                                {item.module}
                                            </h3>
                                        </div>
                                        {expandedIndex === i ? <ChevronUp className="w-4 h-4 text-muted" /> : <ChevronDown className="w-4 h-4 text-muted" />}
                                    </div>

                                    {expandedIndex === i && (
                                        <motion.div
                                            initial={{ height: 0, opacity: 0 }}
                                            animate={{ height: "auto", opacity: 1 }}
                                            exit={{ height: 0, opacity: 0 }}
                                            className="px-4 pb-4 border-t border-border pt-4"
                                        >
                                            <p className="text-xs text-muted font-medium mb-2 uppercase tracking-wider">Topics Covered</p>
                                            <div className="flex flex-wrap gap-2 mb-4">
                                                {item.skills.map((s) => (
                                                    <span key={s} className="text-xs bg-surface-2 border border-border rounded-lg px-2.5 py-1 text-muted-foreground">{s}</span>
                                                ))}
                                            </div>
                                            <p className="text-xs text-muted font-medium mb-2 uppercase tracking-wider">Resources</p>
                                            <div className="space-y-2">
                                                {item.resources.map((r) => (
                                                    <a key={r.title} href={r.url} className="flex items-center gap-2 text-sm text-primary hover:underline">
                                                        <ExternalLink className="w-3.5 h-3.5" /> {r.title}
                                                    </a>
                                                ))}
                                            </div>
                                        </motion.div>
                                    )}
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>
        </div>
    );
}
