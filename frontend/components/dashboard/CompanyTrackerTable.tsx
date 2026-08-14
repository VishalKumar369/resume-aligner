"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { cn, getScoreColor, formatScore } from "@/lib/utils";
import { companySlug } from "@/services/api";

export interface CompanyMatch {
    company: string;
    role: string;
    jd_id: string;
    alignment_score: number;
    ats_score: number;
    roles_tracked: number;
    analyzed_at?: string | null;
}

function ScorePill({ score }: { score: number }) {
    return (
        <div className={cn("inline-flex items-center gap-1.5 text-sm font-bold", getScoreColor(score))}>
            <div className={cn("w-2 h-2 rounded-full", score >= 75 ? "bg-success" : score >= 50 ? "bg-warning" : "bg-error")} />
            {formatScore(score)}
        </div>
    );
}

/** One row per company, showing its best-matching role. */
export function CompanyTrackerTable({ matches }: { matches: CompanyMatch[] }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="card-elevated rounded-2xl overflow-hidden"
        >
            <div className="p-5 border-b border-border">
                <h3 className="text-sm font-semibold text-white">Company Tracker</h3>
                <p className="text-xs text-muted mt-0.5">Your best match per company</p>
            </div>

            {matches.length === 0 ? (
                <p className="text-xs text-muted p-6 text-center">
                    No analyzed roles yet. Add a job description to start tracking.
                </p>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="text-left text-xs text-muted border-b border-border">
                                <th className="p-4 font-medium">Company</th>
                                <th className="p-4 font-medium">Best-matching role</th>
                                <th className="p-4 font-medium">Alignment</th>
                                <th className="p-4 font-medium">ATS</th>
                                <th className="p-4 font-medium">Roles</th>
                                <th className="p-4 font-medium" />
                            </tr>
                        </thead>
                        <tbody>
                            {matches.map((row) => (
                                <tr key={row.jd_id} className="border-b border-border/50 last:border-0 hover:bg-surface/40 transition-colors">
                                    <td className="p-4 font-medium">{row.company}</td>
                                    <td className="p-4 text-muted">{row.role}</td>
                                    <td className="p-4"><ScorePill score={row.alignment_score} /></td>
                                    <td className="p-4"><ScorePill score={row.ats_score} /></td>
                                    <td className="p-4 text-muted text-xs">{row.roles_tracked}</td>
                                    <td className="p-4 text-right">
                                        <Link
                                            href={`/company/${companySlug(row.company)}`}
                                            className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                                        >
                                            Insights <ExternalLink className="w-3 h-3" />
                                        </Link>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </motion.div>
    );
}
