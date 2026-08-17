"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { cn, getScoreColor, formatScore } from "@/lib/utils";
import { companySlug } from "@/services/api";

export interface AnalysisRow {
    id: string;
    resume_id: string;
    jd_id: string;
    alignment_score: number;
    ats_score: number;
    company?: string | null;
    role?: string | null;
    resume_label?: string | null;
    created_at?: string | null;
}

function ScorePill({ score }: { score: number }) {
    return (
        <div className={cn("inline-flex items-center gap-1.5 text-sm font-bold", getScoreColor(score))}>
            <div className={cn("w-2 h-2 rounded-full", score >= 75 ? "bg-success" : score >= 50 ? "bg-warning" : "bg-error")} />
            {formatScore(score)}
        </div>
    );
}

/** A real, named company we can build a working insights link for. */
function hasCompany(name?: string | null): name is string {
    const trimmed = (name || "").trim();
    return trimmed.length > 0 && trimmed.toLowerCase() !== "unknown company";
}

/**
 * Every stored analysis, newest first. Selecting a row drives the rest of the
 * dashboard, so the whole row is the click target and the active one is marked.
 */
export function AnalysisTrackerTable({
    analyses,
    activeId,
    onSelect,
}: {
    analyses: AnalysisRow[];
    activeId: string | null;
    onSelect: (id: string) => void;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="card-elevated rounded-2xl overflow-hidden"
        >
            <div className="p-5 border-b border-border">
                <h3 className="text-sm font-semibold text-white">Your Analyses</h3>
                <p className="text-xs text-muted mt-0.5">Every run — select one to see it above</p>
            </div>

            {analyses.length === 0 ? (
                <p className="text-xs text-muted p-6 text-center">
                    No analyses yet. Analyze a resume against a job description to start.
                </p>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="text-left text-xs text-muted border-b border-border">
                                <th className="p-4 font-medium">Company</th>
                                <th className="p-4 font-medium">Role</th>
                                <th className="p-4 font-medium">Alignment</th>
                                <th className="p-4 font-medium">ATS</th>
                                <th className="p-4 font-medium">Analyzed</th>
                                <th className="p-4 font-medium" />
                            </tr>
                        </thead>
                        <tbody>
                            {analyses.map((row) => {
                                const active = row.id === activeId;
                                return (
                                    <tr
                                        key={row.id}
                                        onClick={() => onSelect(row.id)}
                                        onKeyDown={(e) => {
                                            if (e.key === "Enter" || e.key === " ") {
                                                e.preventDefault();
                                                onSelect(row.id);
                                            }
                                        }}
                                        role="button"
                                        tabIndex={0}
                                        aria-pressed={active}
                                        aria-label={`Select analysis for ${row.company || "Unknown company"} — ${row.role || "role"}`}
                                        className={cn(
                                            "border-b border-border/50 last:border-0 cursor-pointer transition-colors outline-none",
                                            active
                                                ? "bg-primary/10 hover:bg-primary/15"
                                                : "hover:bg-surface/40 focus-visible:bg-surface/40"
                                        )}
                                    >
                                        <td className="p-4 font-medium">
                                            <span className="inline-flex items-center gap-2">
                                                {active && <span className="w-1.5 h-1.5 rounded-full bg-primary" />}
                                                {row.company || "Unknown company"}
                                            </span>
                                        </td>
                                        <td className="p-4 text-muted">{row.role || "—"}</td>
                                        <td className="p-4"><ScorePill score={row.alignment_score} /></td>
                                        <td className="p-4"><ScorePill score={row.ats_score} /></td>
                                        <td className="p-4 text-muted text-xs">
                                            {row.created_at ? new Date(row.created_at).toLocaleDateString() : "—"}
                                        </td>
                                        <td className="p-4 text-right">
                                            {hasCompany(row.company) && (
                                                <Link
                                                    href={`/company/${companySlug(row.company)}`}
                                                    onClick={(e) => e.stopPropagation()}
                                                    className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                                                >
                                                    Insights <ExternalLink className="w-3 h-3" />
                                                </Link>
                                            )}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </motion.div>
    );
}
