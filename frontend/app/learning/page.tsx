"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { CheckCircle, Circle, ExternalLink, Clock, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { useApi } from "@/hooks/useApi";
import { learningService } from "@/services/api";
import { EmptyState, ErrorState, PriorityBadge, Skeleton } from "@/components/ui/States";

const priorityColor: Record<string, string> = {
    P1: "border-error text-error bg-error/10",
    P2: "border-warning text-warning bg-warning/10",
    P3: "border-primary text-primary bg-primary/10",
};

export default function LearningPage() {
    const { data, loading, error, reload } = useApi<any>(() => learningService.getRoadmap());
    const [expandedIndex, setExpandedIndex] = useState<number | null>(0);
    const [completed, setCompleted] = useState<Set<number>>(new Set());

    const toggleComplete = (i: number) =>
        setCompleted((prev) => {
            const next = new Set(prev);
            next.has(i) ? next.delete(i) : next.add(i);
            return next;
        });

    if (loading) {
        return (
            <div className="max-w-3xl mx-auto space-y-6">
                <Skeleton className="h-8 w-56" />
                <Skeleton className="h-24 rounded-2xl" />
                {[0, 1, 2].map((i) => <Skeleton key={i} className="h-20 rounded-2xl" />)}
            </div>
        );
    }

    if (error) return <div className="max-w-3xl mx-auto"><ErrorState message={error} onRetry={reload} /></div>;

    const modules: any[] = data?.modules || [];

    if (!modules.length) {
        return (
            <div className="max-w-3xl mx-auto pt-10">
                <EmptyState
                    title="No learning plan yet"
                    description={data?.note || "Analyze a resume against a few job descriptions and we'll build a plan from the gaps they share."}
                />
            </div>
        );
    }

    return (
        <div className="max-w-3xl mx-auto space-y-6">
            <div>
                <h1 className="text-2xl font-bold">Learning Roadmap</h1>
                <p className="text-sm text-muted mt-1">
                    Built from gaps across {data.jds_considered} target role{data.jds_considered === 1 ? "" : "s"} ·{" "}
                    {data.total_modules} modules · {data.total_duration}
                </p>
            </div>

            <div className="card-elevated rounded-2xl p-5">
                <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-medium">Overall Progress</span>
                    <span className="text-sm font-bold text-primary">{completed.size}/{modules.length} modules</span>
                </div>
                <div className="h-2 bg-border rounded-full overflow-hidden">
                    <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${(completed.size / modules.length) * 100}%` }}
                        transition={{ duration: 0.5 }}
                        className="h-full bg-primary rounded-full"
                    />
                </div>
                <p className="text-xs text-muted mt-2">Progress is tracked in your browser for now.</p>
            </div>

            <div className="space-y-3">
                {modules.map((module, i) => {
                    const isOpen = expandedIndex === i;
                    const isDone = completed.has(i);

                    return (
                        <motion.div
                            key={`${module.module}-${i}`}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.05 }}
                            className="card-elevated rounded-2xl overflow-hidden"
                        >
                            <button
                                onClick={() => setExpandedIndex(isOpen ? null : i)}
                                className="w-full p-5 flex items-center gap-4 text-left hover:bg-surface/40 transition-colors"
                            >
                                <span
                                    role="button"
                                    tabIndex={0}
                                    onClick={(e) => { e.stopPropagation(); toggleComplete(i); }}
                                    onKeyDown={(e) => { if (e.key === "Enter") { e.stopPropagation(); toggleComplete(i); } }}
                                    className="flex-shrink-0"
                                >
                                    {isDone
                                        ? <CheckCircle className="w-5 h-5 text-success" />
                                        : <Circle className="w-5 h-5 text-muted" />}
                                </span>

                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <span className={cn("font-medium", isDone && "line-through text-muted")}>{module.module}</span>
                                        <PriorityBadge priority={module.priority} />
                                    </div>
                                    <p className="text-xs text-muted mt-1 inline-flex items-center gap-2">
                                        <Clock className="w-3 h-3" /> {module.week}
                                        <span>· wanted by {module.jd_demand} role{module.jd_demand === 1 ? "" : "s"}</span>
                                    </p>
                                </div>

                                {isOpen ? <ChevronUp className="w-4 h-4 text-muted" /> : <ChevronDown className="w-4 h-4 text-muted" />}
                            </button>

                            {isOpen && (
                                <div className="px-5 pb-5 space-y-3 border-t border-border/50 pt-4">
                                    <div>
                                        <p className="text-xs text-muted mb-2">Skills in this module</p>
                                        <div className="flex flex-wrap gap-2">
                                            {module.skills.map((skill: string) => (
                                                <span key={skill} className={cn("px-2.5 py-1 rounded-lg border text-xs", priorityColor[module.priority] || priorityColor.P3)}>
                                                    {skill}
                                                </span>
                                            ))}
                                        </div>
                                    </div>

                                    {module.resources?.length > 0 && (
                                        <div>
                                            <p className="text-xs text-muted mb-2">Official documentation</p>
                                            <div className="space-y-1.5">
                                                {module.resources.map((resource: any) => (
                                                    <a
                                                        key={resource.url}
                                                        href={resource.url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="flex items-center gap-2 text-xs text-primary hover:underline"
                                                    >
                                                        <ExternalLink className="w-3 h-3 flex-shrink-0" />
                                                        {resource.title}
                                                    </a>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </motion.div>
                    );
                })}
            </div>
        </div>
    );
}
