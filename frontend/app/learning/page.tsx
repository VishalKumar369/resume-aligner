"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { useSearchParams } from "next/navigation";
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

// useSearchParams must sit under a Suspense boundary for the production build.
export default function LearningPage() {
    return (
        <Suspense fallback={<div className="max-w-3xl mx-auto"><Skeleton className="h-8 w-56" /></div>}>
            <LearningContent />
        </Suspense>
    );
}

function LearningContent() {
    const { data, loading, error, reload } = useApi<any>(() => learningService.getRoadmap());
    // Optional skill to focus, deep-linked from the skill-gap / company pages.
    const targetSkill = (useSearchParams().get("skill") || "").trim().toLowerCase();
    const [expandedIndex, setExpandedIndex] = useState<number | null>(0);
    const [completed, setCompleted] = useState<Set<number>>(new Set());
    // A brief attention flash on arrival, not a persistent selection.
    const [flash, setFlash] = useState(false);
    const highlightRef = useRef<HTMLDivElement>(null);

    // Expand the module that teaches the focused skill.
    useEffect(() => {
        if (!targetSkill || !data?.modules?.length) return;
        const idx = data.modules.findIndex((m: any) =>
            (m.skills || []).some((s: string) => s.toLowerCase() === targetSkill)
        );
        if (idx >= 0) setExpandedIndex(idx);
    }, [targetSkill, data]);

    // Scroll to the focused skill and flash it for a couple of seconds.
    useEffect(() => {
        if (!targetSkill || !data) return;
        const inModule = (data.modules || []).some((m: any) =>
            (m.skills || []).some((s: string) => s.toLowerCase() === targetSkill)
        );
        const inPartial = (data.partial_skills || []).some(
            (p: any) => (p.skill || "").toLowerCase() === targetSkill
        );
        if (!inModule && !inPartial) return;

        setFlash(true);
        const scroll = setTimeout(
            () => highlightRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }),
            250
        );
        const clear = setTimeout(() => setFlash(false), 2600);
        return () => { clearTimeout(scroll); clearTimeout(clear); };
    }, [targetSkill, expandedIndex, data]);

    const isTarget = (skill: string) => flash && !!targetSkill && skill.toLowerCase() === targetSkill;

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
    const partials: any[] = data?.partial_skills || [];

    const targetModuleIndex = targetSkill
        ? modules.findIndex((m: any) => (m.skills || []).some((s: string) => s.toLowerCase() === targetSkill))
        : -1;
    const targetPartialIndex = targetSkill && targetModuleIndex < 0
        ? partials.findIndex((p: any) => (p.skill || "").toLowerCase() === targetSkill)
        : -1;

    if (!modules.length && !partials.length) {
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

            {modules.length > 0 && (
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
            )}

            <div className="space-y-3">
                {modules.map((module, i) => {
                    const isOpen = expandedIndex === i;
                    const isDone = completed.has(i);
                    // Each resource carries the skill it documents, so a skill chip
                    // can link straight to its official docs.
                    const docsBySkill = new Map<string, any>(
                        (module.resources || []).map((r: any) => [r.skill, r])
                    );

                    return (
                        <motion.div
                            key={`${module.module}-${i}`}
                            ref={i === targetModuleIndex ? highlightRef : undefined}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.05 }}
                            className={cn(
                                "card-elevated rounded-2xl overflow-hidden transition-shadow duration-500",
                                flash && i === targetModuleIndex && "ring-2 ring-primary"
                            )}
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
                                        <p className="text-xs text-muted mb-2">
                                            Skills in this module
                                            {docsBySkill.size > 0 && <span className="text-muted"> · tap one to open its docs</span>}
                                        </p>
                                        <div className="flex flex-wrap gap-2">
                                            {module.skills.map((skill: string) => {
                                                const doc = docsBySkill.get(skill);
                                                const chip = cn(
                                                    "px-2.5 py-1 rounded-lg border text-xs inline-flex items-center gap-1",
                                                    priorityColor[module.priority] || priorityColor.P3,
                                                    isTarget(skill) && "ring-2 ring-primary font-semibold"
                                                );
                                                return doc ? (
                                                    <a
                                                        key={skill}
                                                        href={doc.url}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        title={`Open ${doc.title}`}
                                                        className={cn(chip, "hover:opacity-80 transition-opacity")}
                                                    >
                                                        {skill}
                                                        <ExternalLink className="w-3 h-3 opacity-70" />
                                                    </a>
                                                ) : (
                                                    <span key={skill} className={chip}>{skill}</span>
                                                );
                                            })}
                                        </div>
                                    </div>

                                    {module.resources?.length > 0 && (
                                        <div>
                                            <p className="text-xs text-muted mb-2">Learn more</p>
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

            {partials.length > 0 && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="card-elevated rounded-2xl p-5"
                >
                    <h3 className="text-sm font-semibold text-warning">Partially covered</h3>
                    <p className="text-xs text-muted mt-0.5 mb-3">
                        Skills you partly cover — worth reinforcing before they become gaps.
                    </p>
                    <div className="space-y-1">
                        {partials.map((p, idx) => (
                            <div
                                key={p.skill}
                                ref={idx === targetPartialIndex ? highlightRef : undefined}
                                className={cn(
                                    "flex items-center justify-between gap-3 py-2 border-b border-border/40 last:border-0 rounded-lg transition-shadow duration-500",
                                    flash && idx === targetPartialIndex && "ring-2 ring-primary px-2 -mx-2"
                                )}
                            >
                                <div className="min-w-0">
                                    <span className={cn("text-sm font-medium", isTarget(p.skill) && "text-primary")}>{p.skill}</span>
                                    {p.covered_by && (
                                        <span className="text-xs text-muted"> · you have {p.covered_by}</span>
                                    )}
                                </div>
                                <div className="flex items-center gap-3 flex-shrink-0">
                                    <span className="text-xs text-muted">
                                        {p.jd_count} role{p.jd_count === 1 ? "" : "s"}
                                    </span>
                                    {p.resource && (
                                        <a
                                            href={p.resource.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            title={`Open ${p.resource.title}`}
                                            className="text-xs text-primary hover:underline inline-flex items-center gap-1"
                                        >
                                            Docs <ExternalLink className="w-3 h-3" />
                                        </a>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </motion.div>
            )}
        </div>
    );
}
