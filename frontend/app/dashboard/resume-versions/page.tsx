"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Download, GitBranch, FileText } from "lucide-react";
import { cn, getScoreColor, formatScore } from "@/lib/utils";
import { useApi } from "@/hooks/useApi";
import { apiErrorMessage, resumeService } from "@/services/api";
import { EmptyState, ErrorState, Skeleton } from "@/components/ui/States";

export default function ResumeVersionsPage() {
    const { data: resumes, loading: loadingResumes, error: resumeError, reload } =
        useApi<any[]>(() => resumeService.getAll());

    const resumeId = resumes?.[0]?.id;
    const { data: versions, loading: loadingVersions, error: versionError } = useApi<any[]>(
        () => resumeService.getVersions(resumeId!),
        [resumeId],
        { skip: !resumeId }
    );

    const [downloadError, setDownloadError] = useState<string | null>(null);
    const [expanded, setExpanded] = useState<string | null>(null);

    const download = async (versionId: string, filename: string, format: "docx" | "pdf") => {
        setDownloadError(null);
        try {
            const response = await resumeService.download(versionId, format);
            const url = URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement("a");
            link.href = url;
            link.download = `${filename.replace(/\.docx$/, "")}.${format}`;
            link.click();
            URL.revokeObjectURL(url);
        } catch (err: any) {
            setDownloadError(apiErrorMessage(err, "Download failed"));
        }
    };

    if (loadingResumes || loadingVersions) {
        return (
            <div className="max-w-5xl mx-auto space-y-6">
                <Skeleton className="h-8 w-56" />
                {[0, 1, 2].map((i) => <Skeleton key={i} className="h-28 rounded-2xl" />)}
            </div>
        );
    }

    const error = resumeError || versionError;
    if (error) return <div className="max-w-5xl mx-auto"><ErrorState message={error} onRetry={reload} /></div>;

    if (!versions?.length) {
        return (
            <div className="max-w-3xl mx-auto pt-10">
                <EmptyState
                    title="No tailored versions yet"
                    description="Run the optimizer against a job description and each tailored resume will appear here with its scores and downloads."
                    actionLabel="Optimize a resume"
                />
            </div>
        );
    }

    return (
        <div className="max-w-5xl mx-auto space-y-6">
            <div>
                <h1 className="text-xl font-semibold tracking-tight">Resume Versions</h1>
                <p className="text-[13px] text-muted mt-1">
                    Tailored variants of {resumes?.[0]?.label || resumes?.[0]?.filename}
                </p>
            </div>

            {downloadError && (
                <div className="bg-error/5 border border-error/20 rounded-xl p-3 text-sm text-error">{downloadError}</div>
            )}

            <div className="space-y-3">
                {versions.map((version, i) => {
                    const atsDelta = (version.ats_score ?? 0) - (version.baseline_ats_score ?? 0);
                    const alignDelta = (version.alignment_score ?? 0) - (version.baseline_alignment_score ?? 0);
                    const isOpen = expanded === version.id;

                    return (
                        <motion.div
                            key={version.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.05 }}
                            className="card-elevated rounded-2xl p-5"
                        >
                            <div className="flex items-start justify-between gap-4 flex-wrap">
                                <div className="flex items-start gap-3 min-w-0">
                                    <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                                        <GitBranch className="w-4 h-4 text-primary" />
                                    </div>
                                    <div className="min-w-0">
                                        <p className="font-medium truncate">{version.label || `Version ${version.version_number}`}</p>
                                        <p className="text-xs text-muted mt-0.5 inline-flex items-center gap-1.5">
                                            <FileText className="w-3 h-3" />
                                            {version.filename} · {new Date(version.created_at).toLocaleDateString()}
                                        </p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-5">
                                    <ScoreDelta label="ATS" score={version.ats_score ?? 0} delta={atsDelta} />
                                    <ScoreDelta label="Alignment" score={version.alignment_score ?? 0} delta={alignDelta} />
                                    <div className="flex gap-2">
                                        <button onClick={() => download(version.id, version.filename, "docx")}
                                            className="btn-ghost text-xs inline-flex items-center gap-1.5">
                                            <Download className="w-3.5 h-3.5" /> docx
                                        </button>
                                        <button onClick={() => download(version.id, version.filename, "pdf")}
                                            className="btn-ghost text-xs inline-flex items-center gap-1.5">
                                            <Download className="w-3.5 h-3.5" /> pdf
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {version.changes_applied?.length > 0 && (
                                <div className="mt-4 pt-3 border-t border-border/50">
                                    <button
                                        onClick={() => setExpanded(isOpen ? null : version.id)}
                                        className="text-xs text-primary hover:underline"
                                    >
                                        {isOpen ? "Hide" : "Show"} {version.changes_applied.length} change
                                        {version.changes_applied.length === 1 ? "" : "s"}
                                    </button>

                                    {isOpen && (
                                        <div className="mt-3 space-y-2">
                                            {version.changes_applied.map((change: any, index: number) => (
                                                <div key={index} className="text-xs border-l-2 border-border pl-3 py-1">
                                                    <p className="text-muted-foreground">{change.description}</p>
                                                    {change.before && (
                                                        <div className="mt-1.5 space-y-1 text-[11px]">
                                                            <p className="text-error/70 line-through">{change.before}</p>
                                                            <p className="text-success">{change.after}</p>
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
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

function ScoreDelta({ label, score, delta }: { label: string; score: number; delta: number }) {
    return (
        <div className="text-center">
            <div className={cn("text-lg font-bold", getScoreColor(score))}>{formatScore(score)}</div>
            <div className="text-[11px] text-muted">
                {label}
                {delta > 0 && <span className="text-success"> +{delta.toFixed(1)}</span>}
            </div>
        </div>
    );
}
