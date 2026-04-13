"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronRight, ExternalLink, Download } from "lucide-react";
import { cn, getScoreColor, formatScore } from "@/lib/utils";

const companies = [
    {
        id: "1", company: "Google", role: "Senior Backend Engineer",
        alignmentScore: 88, atsScore: 92, version: "v1.2",
        missingSkills: ["Go", "Kubernetes"], status: "applied",
    },
    {
        id: "2", company: "Stripe", role: "Platform Engineer",
        alignmentScore: 74, atsScore: 81, version: "v1.0",
        missingSkills: ["Ruby", "Service Mesh"], status: "draft",
    },
    {
        id: "3", company: "Figma", role: "Full Stack Engineer",
        alignmentScore: 61, atsScore: 70, version: "v1.1",
        missingSkills: ["WebGL", "C++", "WASM"], status: "in-review",
    },
    {
        id: "4", company: "Notion", role: "Backend Developer",
        alignmentScore: 90, atsScore: 95, version: "v2.0",
        missingSkills: [], status: "interview",
    },
];

const statusConfig: Record<string, { label: string; className: string }> = {
    draft: { label: "Draft", className: "bg-muted/10 text-muted border-muted/20" },
    applied: { label: "Applied", className: "bg-primary/10 text-primary border-primary/20" },
    "in-review": { label: "In Review", className: "bg-warning/10 text-warning border-warning/20" },
    interview: { label: "Interview", className: "bg-success/10 text-success border-success/20" },
};

function ScorePill({ score }: { score: number }) {
    return (
        <div className={cn("inline-flex items-center gap-1.5 text-sm font-bold", getScoreColor(score))}>
            <div className={cn("w-2 h-2 rounded-full", score >= 75 ? "bg-success" : score >= 50 ? "bg-warning" : "bg-error")} />
            {formatScore(score)}
        </div>
    );
}

export function CompanyTrackerTable() {
    const [expandedRow, setExpandedRow] = useState<string | null>(null);

    return (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="card-elevated rounded-2xl overflow-hidden">
            <div className="p-5 border-b border-border flex items-center justify-between">
                <div>
                    <h3 className="text-sm font-semibold text-white">Company Resume Tracker</h3>
                    <p className="text-xs text-muted mt-0.5">Tailored resumes per company and role</p>
                </div>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b border-border text-xs text-muted">
                            <th className="text-left p-4 font-medium">Company / Role</th>
                            <th className="text-left p-4 font-medium">Alignment</th>
                            <th className="text-left p-4 font-medium">ATS Score</th>
                            <th className="text-left p-4 font-medium">Version</th>
                            <th className="text-left p-4 font-medium">Missing Skills</th>
                            <th className="text-left p-4 font-medium">Status</th>
                            <th className="p-4" />
                        </tr>
                    </thead>
                    <tbody>
                        {companies.map((row) => (
                            <>
                                <tr
                                    key={row.id}
                                    onClick={() => setExpandedRow(expandedRow === row.id ? null : row.id)}
                                    className="border-b border-border/50 hover:bg-surface/50 cursor-pointer transition-colors"
                                >
                                    <td className="p-4">
                                        <div className="font-medium text-white">{row.company}</div>
                                        <div className="text-xs text-muted mt-0.5">{row.role}</div>
                                    </td>
                                    <td className="p-4"><ScorePill score={row.alignmentScore} /></td>
                                    <td className="p-4"><ScorePill score={row.atsScore} /></td>
                                    <td className="p-4">
                                        <span className="px-2 py-0.5 bg-surface-2 border border-border rounded text-xs font-mono text-muted">{row.version}</span>
                                    </td>
                                    <td className="p-4">
                                        {row.missingSkills.length === 0
                                            ? <span className="text-xs text-success">All covered ✓</span>
                                            : (
                                                <div className="flex gap-1 flex-wrap">
                                                    {row.missingSkills.slice(0, 2).map((s) => (
                                                        <span key={s} className="px-2 py-0.5 bg-error/10 text-error border border-error/20 rounded text-xs">{s}</span>
                                                    ))}
                                                    {row.missingSkills.length > 2 && (
                                                        <span className="px-2 py-0.5 bg-surface-2 text-muted rounded text-xs">+{row.missingSkills.length - 2}</span>
                                                    )}
                                                </div>
                                            )
                                        }
                                    </td>
                                    <td className="p-4">
                                        <span className={cn("px-2.5 py-1 rounded-full border text-xs font-medium", statusConfig[row.status].className)}>
                                            {statusConfig[row.status].label}
                                        </span>
                                    </td>
                                    <td className="p-4 text-right">
                                        {expandedRow === row.id ? <ChevronDown className="w-4 h-4 text-muted ml-auto" /> : <ChevronRight className="w-4 h-4 text-muted ml-auto" />}
                                    </td>
                                </tr>
                                <AnimatePresence>
                                    {expandedRow === row.id && (
                                        <tr key={`${row.id}-expanded`}>
                                            <td colSpan={7} className="p-0">
                                                <motion.div
                                                    initial={{ opacity: 0, height: 0 }}
                                                    animate={{ opacity: 1, height: "auto" }}
                                                    exit={{ opacity: 0, height: 0 }}
                                                    className="overflow-hidden"
                                                >
                                                    <div className="px-4 py-5 bg-surface/30 border-b border-border flex items-center justify-between gap-4">
                                                        <div>
                                                            <p className="text-xs text-muted mb-1">All missing skills for this role:</p>
                                                            <div className="flex gap-2 flex-wrap">
                                                                {row.missingSkills.map((s) => (
                                                                    <span key={s} className="px-2.5 py-1 bg-error/10 text-error border border-error/20 rounded-lg text-xs">{s}</span>
                                                                ))}
                                                                {row.missingSkills.length === 0 && <span className="text-xs text-success">No skill gaps!</span>}
                                                            </div>
                                                        </div>
                                                        <div className="flex items-center gap-2 flex-shrink-0">
                                                            <button className="btn-ghost text-xs flex items-center gap-1.5 border border-border rounded-lg px-3 py-1.5">
                                                                <ExternalLink className="w-3.5 h-3.5" /> View Resume
                                                            </button>
                                                            <button className="btn-ghost text-xs flex items-center gap-1.5 border border-border rounded-lg px-3 py-1.5">
                                                                <Download className="w-3.5 h-3.5" /> Download PDF
                                                            </button>
                                                        </div>
                                                    </div>
                                                </motion.div>
                                            </td>
                                        </tr>
                                    )}
                                </AnimatePresence>
                            </>
                        ))}
                    </tbody>
                </table>
            </div>
        </motion.div>
    );
}
