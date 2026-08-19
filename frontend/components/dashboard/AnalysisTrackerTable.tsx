"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { ExternalLink, ChevronLeft, ChevronRight } from "lucide-react";
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

const PAGE_SIZE = 10;

function ScorePill({ score }: { score: number }) {
    return (
        <div className={cn("inline-flex items-center gap-1.5 text-sm font-bold", getScoreColor(score))}>
            <div className={cn("w-2 h-2 rounded-full", score >= 75 ? "bg-success" : score >= 50 ? "bg-warning" : "bg-error")} />
            {formatScore(score)}
        </div>
    );
}

/**
 * Where a row's "Insights" link points. It carries the analysis context (this
 * resume + JD + run) so the company page can show the specific role, the match,
 * and the tailored resume — not just the aggregate company view. The company
 * slug is the path when known; otherwise the JD id keeps the URL valid and the
 * page falls back to the JD-scoped view.
 */
function insightsHref(row: AnalysisRow): string {
    const slug = companySlug(row.company || "") || row.jd_id;
    const params = new URLSearchParams({ jd: row.jd_id, resume: row.resume_id, alignment: row.id });
    return `/company/${slug}?${params.toString()}`;
}

/**
 * Every stored analysis, newest first, ten per page. Selecting a row drives the
 * rest of the dashboard, so the whole row is the click target and the active one
 * is marked.
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
    const pageCount = Math.max(1, Math.ceil(analyses.length / PAGE_SIZE));
    const [page, setPage] = useState(0);

    // Clamp if the list shrank (e.g. after a reload) so the page stays valid.
    useEffect(() => {
        if (page > pageCount - 1) setPage(pageCount - 1);
    }, [page, pageCount]);

    const start = page * PAGE_SIZE;
    const visible = analyses.slice(start, start + PAGE_SIZE);

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
                <>
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
                                {visible.map((row) => {
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
                                                <Link
                                                    href={insightsHref(row)}
                                                    onClick={(e) => e.stopPropagation()}
                                                    className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                                                >
                                                    Insights <ExternalLink className="w-3 h-3" />
                                                </Link>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>

                    {analyses.length > PAGE_SIZE && (
                        <div className="flex items-center justify-between px-5 py-3 border-t border-border text-xs text-muted">
                            <span>
                                Showing {start + 1}–{Math.min(start + PAGE_SIZE, analyses.length)} of {analyses.length}
                            </span>
                            <div className="flex items-center gap-1">
                                <button
                                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                                    disabled={page === 0}
                                    aria-label="Previous page"
                                    className="p-1.5 rounded-lg hover:bg-surface-2 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                                >
                                    <ChevronLeft className="w-4 h-4" />
                                </button>
                                <span className="px-2">Page {page + 1} of {pageCount}</span>
                                <button
                                    onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
                                    disabled={page >= pageCount - 1}
                                    aria-label="Next page"
                                    className="p-1.5 rounded-lg hover:bg-surface-2 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                                >
                                    <ChevronRight className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    )}
                </>
            )}
        </motion.div>
    );
}
