"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { useSearchParams } from "next/navigation";
import {
    Check, ExternalLink, Clock, ChevronDown, Layers, Target, GraduationCap,
    Container, Cloud, Server, Wrench, Database, Layout, Code, Radio, BarChart3, Brain,
    Network, Building2, BookOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useApi } from "@/hooks/useApi";
import { learningService } from "@/services/api";
import { EmptyState, ErrorState, PriorityBadge, Skeleton } from "@/components/ui/States";
import { InterviewPrep } from "@/components/learning/InterviewPrep";

const priorityColor: Record<string, string> = {
    P1: "border-error text-error bg-error/10",
    P2: "border-warning text-warning bg-warning/10",
    P3: "border-primary text-primary bg-primary/10",
};

const nodeColor: Record<string, string> = {
    P1: "border-error/40 text-error bg-error/10",
    P2: "border-warning/40 text-warning bg-warning/10",
    P3: "border-primary/40 text-primary bg-primary/10",
};

const categoryIcon: Record<string, React.ElementType> = {
    containers: Container, cloud: Cloud, infrastructure: Server, devops: Wrench,
    database: Database, "web-framework": Server, frontend: Layout, language: Code,
    messaging: Radio, data: BarChart3, "ai-ml": Brain, api: Network,
    architecture: Building2, tooling: Wrench, discipline: Target, other: BookOpen,
};

// useSearchParams must sit under a Suspense boundary for the production build.
export default function LearningPage() {
    return (
        <Suspense fallback={<div className="max-w-5xl mx-auto"><Skeleton className="h-8 w-56" /></div>}>
            <LearningContent />
        </Suspense>
    );
}

function LearningContent() {
    const { data, loading, error, reload } = useApi<any>(() => learningService.getRoadmap());
    const targetSkill = (useSearchParams().get("skill") || "").trim().toLowerCase();
    const [expandedIndex, setExpandedIndex] = useState<number | null>(0);
    const [completed, setCompleted] = useState<Set<number>>(new Set());
    const [filter, setFilter] = useState<string>("all");
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

    // Scroll to and flash the focused skill; reset any filter so it is visible.
    useEffect(() => {
        if (!targetSkill || !data) return;
        const inModule = (data.modules || []).some((m: any) =>
            (m.skills || []).some((s: string) => s.toLowerCase() === targetSkill)
        );
        const inPartial = (data.partial_skills || []).some(
            (p: any) => (p.skill || "").toLowerCase() === targetSkill
        );
        if (!inModule && !inPartial) return;

        setFilter("all");
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
            <div className="max-w-5xl mx-auto space-y-4">
                <Skeleton className="h-9 w-64" />
                <Skeleton className="h-10 w-full rounded-xl" />
                {[0, 1, 2].map((i) => <Skeleton key={i} className="h-20 rounded-2xl" />)}
            </div>
        );
    }

    if (error) return <div className="max-w-5xl mx-auto"><ErrorState message={error} onRetry={reload} /></div>;

    const modules: any[] = data?.modules || [];
    const partials: any[] = data?.partial_skills || [];
    const questionBanks: Record<string, any> = data?.question_banks || {};

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

    const skillsCount = data?.skills_covered?.length
        || modules.reduce((acc: number, m: any) => acc + (m.skills?.length || 0), 0);
    const questionsCount = Object.values(questionBanks).reduce((acc: number, b: any) => acc + (b?.total || 0), 0);
    const pct = modules.length ? Math.round((completed.size / modules.length) * 100) : 0;
    const countBy = (p: string) => modules.filter((m) => m.priority === p).length;

    const tabs = [
        { key: "all", label: "All", count: modules.length },
        ...(countBy("P1") ? [{ key: "P1", label: "Critical", count: countBy("P1") }] : []),
        ...(countBy("P2") ? [{ key: "P2", label: "Important", count: countBy("P2") }] : []),
        ...(countBy("P3") ? [{ key: "P3", label: "Bonus", count: countBy("P3") }] : []),
        { key: "done", label: "Completed", count: completed.size },
        ...(partials.length ? [{ key: "partial", label: "Partially covered", count: partials.length }] : []),
    ];

    const indexed = modules.map((module: any, i: number) => ({ module, i }));
    const filteredModules = indexed.filter(({ module, i }) => {
        if (filter === "P1" || filter === "P2" || filter === "P3") return module.priority === filter;
        if (filter === "done") return completed.has(i);
        if (filter === "partial") return false;
        return true;
    });
    const showPartials = (filter === "all" || filter === "partial") && partials.length > 0;

    return (
        <div className="max-w-8xl mx-auto space-y-4">
            {/* Header + inline stats + progress */}
            <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="min-w-0">
                    <h1 className="text-2xl font-bold">Learning Roadmap</h1>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5 text-xs text-muted">
                        <span className="inline-flex items-center gap-1"><Layers className="w-3.5 h-3.5" /> {modules.length} modules</span>
                        <span className="inline-flex items-center gap-1"><Clock className="w-3.5 h-3.5" /> {data.total_duration}</span>
                        <span className="inline-flex items-center gap-1"><Target className="w-3.5 h-3.5" /> {skillsCount} skills</span>
                        {questionsCount > 0 && (
                            <span className="inline-flex items-center gap-1"><GraduationCap className="w-3.5 h-3.5" /> {questionsCount} practice Qs</span>
                        )}
                    </div>
                </div>
                {modules.length > 0 && (
                    <div className="text-right flex-shrink-0">
                        <div className="text-2xl font-bold gradient-text leading-none">{pct}%</div>
                        <div className="text-xs text-muted mt-1">{completed.size}/{modules.length} done</div>
                    </div>
                )}
            </div>

            {modules.length > 0 && (
                <div className="h-1.5 bg-border rounded-full overflow-hidden">
                    <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.6, ease: "easeOut" }}
                        className="h-full rounded-full bg-gradient-to-r from-primary to-accent" />
                </div>
            )}

            {/* Filter tabs */}
            {modules.length > 0 && (
                <div className="flex flex-wrap gap-2">
                    {tabs.map((t) => {
                        const on = filter === t.key;
                        return (
                            <button
                                key={t.key}
                                onClick={() => setFilter(t.key)}
                                aria-pressed={on}
                                className={cn(
                                    "px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors inline-flex items-center gap-1.5",
                                    on
                                        ? "bg-primary text-primary-foreground border-primary"
                                        : "border-border text-muted hover:text-foreground hover:bg-surface-2"
                                )}
                            >
                                {t.label}
                                <span className={cn("px-1.5 rounded-full text-[10px] font-semibold",
                                    on ? "bg-white/20" : "bg-surface-2 text-muted")}>
                                    {t.count}
                                </span>
                            </button>
                        );
                    })}
                </div>
            )}

            {/* Modules (filtered) */}
            {filter !== "partial" && (
                filteredModules.length > 0 ? (
                    <div>
                        <div className="space-y-3">
                            {filteredModules.map(({ module, i }) => (
                                <ModuleItem
                                    key={`${module.module}-${i}`}
                                    module={module}
                                    index={i}
                                    isOpen={expandedIndex === i}
                                    isDone={completed.has(i)}
                                    isTargetModule={i === targetModuleIndex}
                                    flash={flash}
                                    highlightRef={highlightRef}
                                    questionBanks={questionBanks}
                                    isTarget={isTarget}
                                    onToggleExpand={() => setExpandedIndex(expandedIndex === i ? null : i)}
                                    onToggleComplete={() => toggleComplete(i)}
                                />
                            ))}
                        </div>
                    </div>
                ) : (
                    <p className="text-sm text-muted text-center py-8">Nothing in this view.</p>
                )
            )}

            {/* Partials */}
            {showPartials && (
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                    className="card-elevated rounded-2xl p-5">
                    <h3 className="text-sm font-semibold text-warning inline-flex items-center gap-2">
                        <Wrench className="w-4 h-4" /> Partially covered
                    </h3>
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
                                    {p.covered_by && <span className="text-xs text-muted"> · you have {p.covered_by}</span>}
                                </div>
                                <div className="flex items-center gap-3 flex-shrink-0">
                                    <span className="text-xs text-muted">{p.jd_count} role{p.jd_count === 1 ? "" : "s"}</span>
                                    {p.resource && (
                                        <a href={p.resource.url} target="_blank" rel="noopener noreferrer"
                                            title={`Open ${p.resource.title}`}
                                            className="text-xs text-primary hover:underline inline-flex items-center gap-1">
                                            Docs <ExternalLink className="w-3 h-3" />
                                        </a>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>

                    {partials.some((p) => questionBanks[p.skill]) && (
                        <div className="mt-4 pt-3 border-t border-border/50 space-y-2">
                            <p className="text-[11px] uppercase tracking-wider text-muted font-semibold">Interview preparation</p>
                            {partials.filter((p) => questionBanks[p.skill]).map((p) => (
                                <InterviewPrep key={p.skill} skill={p.skill} total={questionBanks[p.skill].total} />
                            ))}
                        </div>
                    )}
                </motion.div>
            )}
        </div>
    );
}

function ModuleItem({
    module, index, isOpen, isDone, isTargetModule, flash, highlightRef, questionBanks, isTarget,
    onToggleExpand, onToggleComplete,
}: {
    module: any; index: number; isOpen: boolean; isDone: boolean; isTargetModule: boolean;
    flash: boolean; highlightRef: React.RefObject<HTMLDivElement>; questionBanks: Record<string, any>;
    isTarget: (skill: string) => boolean; onToggleExpand: () => void; onToggleComplete: () => void;
}) {
    const Icon = categoryIcon[module.category] || BookOpen;
    const docsBySkill = new Map<string, any>((module.resources || []).map((r: any) => [r.skill, r]));
    const prepSkills = module.skills.filter((s: string) => questionBanks[s]);

    return (
        <motion.div
            ref={isTargetModule ? highlightRef : undefined}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(index * 0.04, 0.3) }}
            className={cn(
                "card-elevated rounded-2xl overflow-hidden transition-shadow duration-500",
                flash && isTargetModule && "ring-2 ring-primary"
            )}
        >
            <div className="w-full p-4 flex items-center gap-3">
                {/* Category node doubles as the completion toggle. */}
                <button
                    onClick={onToggleComplete}
                    aria-label={isDone ? `Mark ${module.module} not done` : `Mark ${module.module} done`}
                    aria-pressed={isDone}
                    className={cn(
                        "w-9 h-9 rounded-xl border-2 flex items-center justify-center transition-all flex-shrink-0",
                        isDone ? "border-success bg-success/15 text-success"
                            : cn(nodeColor[module.priority] || nodeColor.P3, "hover:scale-105")
                    )}
                >
                    {isDone ? <Check className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                </button>

                <button onClick={onToggleExpand} aria-expanded={isOpen}
                    className="flex-1 min-w-0 flex items-center gap-3 text-left">
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                            <span className={cn("font-semibold", isDone && "line-through text-muted")}>{module.module}</span>
                            <PriorityBadge priority={module.priority} />
                        </div>
                        <div className="flex items-center gap-2 flex-wrap mt-1.5 text-xs text-muted">
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-surface-2 border border-border/60">
                                <Clock className="w-3 h-3" /> {module.week}
                            </span>
                            <span>{module.skills.length} skill{module.skills.length === 1 ? "" : "s"}</span>
                            <span>· wanted by {module.jd_demand} role{module.jd_demand === 1 ? "" : "s"}</span>
                            {prepSkills.length > 0 && (
                                <span className="inline-flex items-center gap-1 text-primary"><GraduationCap className="w-3 h-3" /> prep</span>
                            )}
                        </div>
                    </div>
                    <ChevronDown className={cn("w-4 h-4 text-muted flex-shrink-0 transition-transform", isOpen && "rotate-180")} />
                </button>
            </div>

            {isOpen && (
                <div className="px-4 pb-5 space-y-4 border-t border-border/50 pt-4">
                        <div>
                            <p className="text-[11px] uppercase tracking-wider text-muted font-semibold mb-2">
                                Skills to learn
                                {docsBySkill.size > 0 && <span className="normal-case font-normal tracking-normal"> · tap to open docs</span>}
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
                                        <a key={skill} href={doc.url} target="_blank" rel="noopener noreferrer"
                                            title={`Open ${doc.title}`} className={cn(chip, "hover:opacity-80 transition-opacity")}>
                                            {skill}<ExternalLink className="w-3 h-3 opacity-70" />
                                        </a>
                                    ) : (
                                        <span key={skill} className={chip}>{skill}</span>
                                    );
                                })}
                            </div>
                        </div>

                        {module.resources?.length > 0 && (
                            <div>
                                <p className="text-[11px] uppercase tracking-wider text-muted font-semibold mb-2">Documentation</p>
                                <div className="grid sm:grid-cols-2 gap-1.5">
                                    {module.resources.map((resource: any) => (
                                        <a key={resource.url} href={resource.url} target="_blank" rel="noopener noreferrer"
                                            className="flex items-center gap-2 text-xs text-primary hover:underline">
                                            <BookOpen className="w-3 h-3 flex-shrink-0" />{resource.title}
                                        </a>
                                    ))}
                                </div>
                            </div>
                        )}

                        {prepSkills.length > 0 && (
                            <div>
                                <p className="text-[11px] uppercase tracking-wider text-muted font-semibold mb-2">Interview preparation</p>
                                <div className="space-y-2">
                                    {prepSkills.map((s: string) => (
                                        <InterviewPrep key={s} skill={s} total={questionBanks[s].total} />
                                    ))}
                                </div>
                            </div>
                        )}
                </div>
            )}
        </motion.div>
    );
}
