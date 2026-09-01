"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, GraduationCap } from "lucide-react";
import { cn } from "@/lib/utils";
import { learningService, apiErrorMessage } from "@/services/api";

const levelColor: Record<string, string> = {
    beginner: "bg-success/10 text-success border-success/30",
    intermediate: "bg-primary/10 text-primary border-primary/30",
    advanced: "bg-warning/10 text-warning border-warning/30",
    practical: "bg-accent/10 text-accent border-accent/30",
};

interface Level { level: string; label: string; count: number; questions: string[] }

/**
 * Lazily-loaded interview question bank for one skill. Collapsed by default;
 * fetches on first open and shows the questions grouped by difficulty.
 */
export function InterviewPrep({ skill, total }: { skill: string; total: number }) {
    const [open, setOpen] = useState(false);
    const [levels, setLevels] = useState<Level[] | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [activeLevel, setActiveLevel] = useState<string>("beginner");

    const toggle = async () => {
        const next = !open;
        setOpen(next);
        if (next && !levels && !loading) {
            setLoading(true);
            setError(null);
            try {
                const res = await learningService.getQuestions(skill);
                const loaded: Level[] = res.data?.levels || [];
                setLevels(loaded);
                if (loaded[0]) setActiveLevel(loaded[0].level);
            } catch (err: any) {
                setError(apiErrorMessage(err, "Couldn't load questions"));
            } finally {
                setLoading(false);
            }
        }
    };

    const active = levels?.find((l) => l.level === activeLevel);

    return (
        <div className="rounded-xl border border-border/60 bg-surface-2/40 overflow-hidden">
            <button
                onClick={toggle}
                aria-expanded={open}
                className="w-full flex items-center justify-between gap-3 p-3 text-left hover:bg-surface/50 transition-colors"
            >
                <span className="inline-flex items-center gap-2 text-sm font-medium min-w-0">
                    <GraduationCap className="w-4 h-4 text-primary flex-shrink-0" />
                    <span className="truncate">{skill}</span>
                    <span className="text-xs text-muted hidden sm:inline">interview prep</span>
                </span>
                <span className="inline-flex items-center gap-2 flex-shrink-0">
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
                        {total} Qs
                    </span>
                    <ChevronDown className={cn("w-4 h-4 text-muted transition-transform", open && "rotate-180")} />
                </span>
            </button>

            <AnimatePresence initial={false}>
                {open && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                    >
                        <div className="p-3 pt-0">
                            {loading && <p className="text-xs text-muted py-3">Loading questions…</p>}
                            {error && <p className="text-xs text-error py-3">{error}</p>}

                            {levels && (
                                <>
                                    <div className="flex flex-wrap gap-1.5 my-3">
                                        {levels.map((l) => (
                                            <button
                                                key={l.level}
                                                onClick={() => setActiveLevel(l.level)}
                                                aria-pressed={activeLevel === l.level}
                                                className={cn(
                                                    "px-2.5 py-1 rounded-lg border text-xs font-medium transition-colors",
                                                    activeLevel === l.level
                                                        ? levelColor[l.level] || "border-primary text-primary"
                                                        : "border-border text-muted hover:text-foreground"
                                                )}
                                            >
                                                {l.label} <span className="opacity-60">{l.count}</span>
                                            </button>
                                        ))}
                                    </div>

                                    {active && (
                                        <ol className="space-y-1.5 list-decimal list-inside marker:text-muted">
                                            {active.questions.map((q, i) => (
                                                <li key={i} className="text-sm text-muted-foreground leading-relaxed pl-1">
                                                    {q}
                                                </li>
                                            ))}
                                        </ol>
                                    )}
                                </>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
