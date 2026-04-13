"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Download, Eye, GitBranch, Plus } from "lucide-react";
import { cn, getScoreColor, formatScore } from "@/lib/utils";

const versions = [
    { id: "v2.0", company: "Notion", role: "Backend Developer", atsScore: 95, alignment: 90, date: "Apr 10, 2025", changes: ["Rewrote 5 bullets", "Added PostgreSQL keyword", "+12 ATS points"] },
    { id: "v1.2", company: "Google", role: "Senior Backend Engineer", atsScore: 88, alignment: 82, date: "Apr 8, 2025", changes: ["Added Go language", "Rewrote scalability section"] },
    { id: "v1.1", company: "Figma", role: "Full Stack Engineer", atsScore: 72, alignment: 65, date: "Apr 5, 2025", changes: ["Added WASM mention", "Frontend skills expanded"] },
    { id: "v1.0", company: "Base", role: "Original Resume", atsScore: 68, alignment: 0, date: "Apr 1, 2025", changes: ["Original upload"] },
];

export default function ResumeVersionsPage() {
    const [selected, setSelected] = useState<string[]>([]);

    const toggleSelect = (id: string) => {
        setSelected((prev) =>
            prev.includes(id) ? prev.filter((s) => s !== id) : prev.length < 2 ? [...prev, id] : [prev[1], id]
        );
    };

    return (
        <div className="max-w-5xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Resume Versions</h1>
                    <p className="text-sm text-muted mt-1">All tailored variants of your resume</p>
                </div>
                <button className="btn-primary flex items-center gap-2 text-sm">
                    <Plus className="w-4 h-4" /> New Variant
                </button>
            </div>

            {selected.length === 2 && (
                <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="bg-primary/10 border border-primary/20 rounded-xl p-4 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm text-primary">
                        <GitBranch className="w-4 h-4" />
                        <span>Comparing <strong>{selected[0]}</strong> vs <strong>{selected[1]}</strong></span>
                    </div>
                    <button className="btn-primary text-xs py-1.5 px-3">View Side-by-Side</button>
                </motion.div>
            )}
            {selected.length < 2 && <p className="text-xs text-muted">Select 2 versions to compare them side by side</p>}

            <div className="space-y-3">
                {versions.map((v, i) => (
                    <motion.div
                        key={v.id}
                        initial={{ opacity: 0, y: 16 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.06 }}
                        onClick={() => toggleSelect(v.id)}
                        className={cn(
                            "card-elevated rounded-2xl p-5 cursor-pointer transition-all duration-200",
                            selected.includes(v.id) ? "border-primary/40 ring-1 ring-primary/30" : "hover:border-border/80"
                        )}
                    >
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                <div className={cn(
                                    "w-5 h-5 rounded-full border-2 transition-colors flex-shrink-0",
                                    selected.includes(v.id) ? "border-primary bg-primary" : "border-border"
                                )} />
                                <div>
                                    <div className="flex items-center gap-2">
                                        <span className="font-mono text-xs bg-surface-2 border border-border px-2 py-0.5 rounded text-muted">{v.id}</span>
                                        <span className="font-semibold text-white">{v.company}</span>
                                        <span className="text-sm text-muted">· {v.role}</span>
                                    </div>
                                    <div className="flex gap-2 mt-2 flex-wrap">
                                        {v.changes.map((c) => (
                                            <span key={c} className="text-xs bg-surface-2 border border-border text-muted-foreground px-2 py-0.5 rounded">{c}</span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-center gap-6 text-right flex-shrink-0">
                                <div>
                                    <div className={cn("text-lg font-bold", getScoreColor(v.atsScore))}>{formatScore(v.atsScore)}</div>
                                    <div className="text-xs text-muted">ATS Score</div>
                                </div>
                                {v.alignment > 0 && (
                                    <div>
                                        <div className={cn("text-lg font-bold", getScoreColor(v.alignment))}>{formatScore(v.alignment)}</div>
                                        <div className="text-xs text-muted">Alignment</div>
                                    </div>
                                )}
                                <div className="text-xs text-muted">{v.date}</div>
                                <div className="flex gap-2">
                                    <button className="p-2 rounded-lg hover:bg-surface-2 text-muted hover:text-white transition-colors" onClick={(e) => e.stopPropagation()}>
                                        <Eye className="w-4 h-4" />
                                    </button>
                                    <button className="p-2 rounded-lg hover:bg-surface-2 text-muted hover:text-white transition-colors" onClick={(e) => e.stopPropagation()}>
                                        <Download className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                ))}
            </div>
        </div>
    );
}
