"use client";

import { Suspense, useState } from "react";
import { motion } from "framer-motion";
import { useParams, useSearchParams } from "next/navigation";
import {
    Building2, ExternalLink, Info, Download, FileText, Target, Zap, Layers, Briefcase, Sparkles,
} from "lucide-react";
import Link from "next/link";
import { StatCard } from "@/components/ui/StatCard";
import { EmptyState, ErrorState, PriorityBadge, Skeleton, StatSkeletonRow } from "@/components/ui/States";
import { useApi } from "@/hooks/useApi";
import { cn, getScoreColor, formatScore } from "@/lib/utils";
import { alignmentService, apiErrorMessage, companyService, jdService, resumeService } from "@/services/api";

// useSearchParams must sit under a Suspense boundary for the production build.
export default function CompanyPage() {
    return (
        <Suspense fallback={<div className="max-w-5xl mx-auto"><Skeleton className="h-24 rounded-2xl" /></div>}>
            <CompanyPageContent />
        </Suspense>
    );
}

function CompanyPageContent() {
    const params = useParams();
    const search = useSearchParams();
    const companyId = String(params?.companyId || "");

    // When arriving from a specific analysis, these scope the page to one role:
    // its posting, the user's match, and the tailored resume they generated.
    const jdId = search.get("jd");
    const resumeId = search.get("resume");
    const alignmentId = search.get("alignment");
    const scoped = Boolean(jdId);

    const { data: insights, loading: insightsLoading, error: insightsError, reload } =
        useApi<any>(() => companyService.getInsights(companyId), [companyId]);

    const { data: jd, loading: jdLoading } = useApi<any>(
        () => jdService.getById(jdId!), [jdId], { skip: !jdId });
    const { data: alignment, loading: alignLoading } = useApi<any>(
        () => alignmentService.getById(alignmentId!), [alignmentId], { skip: !alignmentId });
    const { data: versions } = useApi<any[]>(
        () => resumeService.getVersions(resumeId!), [resumeId], { skip: !resumeId });

    const [downloadError, setDownloadError] = useState<string | null>(null);

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

    const primaryLoading = scoped ? (jdLoading || alignLoading) : insightsLoading;
    if (primaryLoading) {
        return (
            <div className="max-w-5xl mx-auto space-y-6">
                <Skeleton className="h-24 rounded-2xl" />
                <StatSkeletonRow />
                <Skeleton className="h-48 rounded-2xl" />
            </div>
        );
    }

    // Unscoped view with no saved postings for this company: the backend 404s
    // rather than inventing a profile.
    if (!scoped && insightsError) {
        const notFound = insightsError.toLowerCase().includes("no job descriptions");
        return (
            <div className="max-w-3xl mx-auto pt-10">
                {notFound ? (
                    <EmptyState
                        title={`Nothing saved for "${companyId}"`}
                        description="Company insights are built from the job descriptions you upload. Add a posting from this company to see what it asks for and how you match."
                        actionLabel="Add a job description"
                    />
                ) : (
                    <ErrorState message={insightsError} onRetry={reload} />
                )}
            </div>
        );
    }

    const requirements = (jd?.structured_data?.requirements || {}) as any;
    const mandatory: string[] = requirements.mandatory_skills || [];
    const preferred: string[] = requirements.preferred_skills || [];
    const missing: any[] = alignment?.missing_skills || [];
    const matched: string[] = alignment?.matched_skills || [];
    const tailored = (versions || []).filter((v) => v.jd_id === jdId);
    const gaps: any[] = insights?.your_gaps_here || [];

    return (
        <div className="max-w-5xl mx-auto space-y-6">
            {downloadError && (
                <div className="bg-error/5 border border-error/20 rounded-xl p-3 text-sm text-error">{downloadError}</div>
            )}

            {/* ---------------------------------------- analysis spotlight */}
            {scoped && jd && (
                <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                    <div className="card-elevated rounded-2xl p-6">
                        <div className="flex items-start justify-between gap-4 flex-wrap">
                            <div className="flex items-center gap-4 min-w-0">
                                <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                                    <Building2 className="w-7 h-7 text-primary" />
                                </div>
                                <div className="min-w-0">
                                    <h1 className="text-2xl font-bold truncate">{jd.title || "This role"}</h1>
                                    <p className="text-sm text-muted mt-1">
                                        {[jd.company_name, jd.structured_data?.seniority, jd.structured_data?.location, jd.structured_data?.work_mode]
                                            .filter(Boolean).join(" · ") || "Selected analysis"}
                                    </p>
                                </div>
                            </div>
                            {jd.url && (
                                <a href={jd.url} target="_blank" rel="noopener noreferrer"
                                    className="text-xs text-primary hover:underline inline-flex items-center gap-1 flex-shrink-0">
                                    Open posting <ExternalLink className="w-3 h-3" />
                                </a>
                            )}
                        </div>
                    </div>

                    {alignment && (
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                            <StatCard title="JD Alignment" value={alignment.alignment_score ?? 0} icon={Zap} scoreType delay={0} />
                            <StatCard title="ATS Score" value={alignment.ats_score ?? 0} icon={Target} scoreType delay={0.05} />
                            <StatCard title="Skill Match" value={alignment.skill_match_score ?? 0} icon={Layers} scoreType delay={0.1} />
                            <StatCard title="Experience Match" value={alignment.experience_match_score ?? 0} icon={Briefcase} scoreType delay={0.15} />
                        </div>
                    )}

                    <div className="grid lg:grid-cols-2 gap-6">
                        {/* Tailored resume — the whole point of coming here */}
                        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                            className="card-elevated rounded-2xl p-6">
                            <h3 className="text-sm font-semibold mb-3 inline-flex items-center gap-2">
                                <Sparkles className="w-4 h-4 text-primary" /> Your tailored resume
                            </h3>
                            {tailored.length === 0 ? (
                                <div className="text-sm text-muted">
                                    <p className="mb-3">No tailored resume for this role yet.</p>
                                    <Link href="/upload" className="btn-primary inline-flex text-sm">Optimize for this role</Link>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {tailored.map((version) => {
                                        const atsDelta = (version.ats_score ?? 0) - (version.baseline_ats_score ?? 0);
                                        const alignDelta = (version.alignment_score ?? 0) - (version.baseline_alignment_score ?? 0);
                                        return (
                                            <div key={version.id} className="bg-surface-2 rounded-xl p-4 border border-border/50">
                                                <div className="flex items-center gap-2 mb-2">
                                                    <FileText className="w-4 h-4 text-muted flex-shrink-0" />
                                                    <p className="text-sm font-medium truncate">
                                                        {version.label || `Version ${version.version_number}`}
                                                    </p>
                                                </div>
                                                <div className="flex items-center gap-4 text-xs text-muted mb-3">
                                                    <span>ATS <b className={getScoreColor(version.ats_score ?? 0)}>{formatScore(version.ats_score ?? 0)}</b>
                                                        {atsDelta > 0 && <span className="text-success"> +{atsDelta.toFixed(1)}</span>}</span>
                                                    <span>Alignment <b className={getScoreColor(version.alignment_score ?? 0)}>{formatScore(version.alignment_score ?? 0)}</b>
                                                        {alignDelta > 0 && <span className="text-success"> +{alignDelta.toFixed(1)}</span>}</span>
                                                </div>
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
                                        );
                                    })}
                                </div>
                            )}
                        </motion.div>

                        {/* Your gaps for this specific role */}
                        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
                            className="card-elevated rounded-2xl p-6">
                            <h3 className="text-sm font-semibold mb-3">Gaps for this role</h3>
                            {missing.length === 0 ? (
                                <p className="text-sm text-muted">No missing skills — you cover what this posting asks for.</p>
                            ) : (
                                <div className="space-y-2">
                                    {missing.slice(0, 8).map((m) => (
                                        <div key={m.skill} className="flex items-center justify-between text-xs py-1.5 border-b border-border/40 last:border-0">
                                            <span className="font-medium">{m.skill}</span>
                                            <PriorityBadge priority={m.priority} />
                                        </div>
                                    ))}
                                </div>
                            )}
                            {matched.length > 0 && (
                                <div className="mt-4">
                                    <p className="text-xs text-muted mb-2">You already match</p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {matched.slice(0, 12).map((s) => (
                                            <span key={s} className="px-2 py-0.5 bg-success/10 text-success border border-success/20 rounded-md text-[11px]">{s}</span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </motion.div>
                    </div>

                    {(mandatory.length > 0 || preferred.length > 0) && (
                        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
                            className="card-elevated rounded-2xl p-6">
                            <h3 className="text-sm font-semibold mb-3">What this role asks for</h3>
                            <div className="flex flex-wrap gap-2 mb-3">
                                {mandatory.map((skill) => (
                                    <span key={skill} className="px-2.5 py-1 bg-surface-2 border border-border rounded-lg text-xs">{skill}</span>
                                ))}
                            </div>
                            {preferred.length > 0 && (
                                <>
                                    <p className="text-xs text-muted mb-2">Nice to have</p>
                                    <div className="flex flex-wrap gap-2">
                                        {preferred.map((skill) => (
                                            <span key={skill} className="px-2.5 py-1 bg-surface/40 border border-border/50 rounded-lg text-xs text-muted">{skill}</span>
                                        ))}
                                    </div>
                                </>
                            )}
                        </motion.div>
                    )}
                </motion.div>
            )}

            {/* ---------------------------------------- aggregate company view */}
            {insights ? (
                <>
                    {scoped && (
                        <div className="pt-2">
                            <h2 className="text-lg font-semibold text-white">Across {insights.company}</h2>
                            <p className="text-xs text-muted mt-0.5">All roles you&apos;ve saved for this company</p>
                        </div>
                    )}

                    {!scoped && (
                        <div className="card-elevated rounded-2xl p-6">
                            <div className="flex items-center gap-4">
                                <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                                    <Building2 className="w-8 h-8 text-primary" />
                                </div>
                                <div>
                                    <h1 className="text-2xl font-bold">{insights.company}</h1>
                                    <p className="text-sm text-muted mt-1">
                                        {insights.jd_count} saved posting{insights.jd_count === 1 ? "" : "s"}
                                        {insights.locations?.length > 0 && ` · ${insights.locations.join(", ")}`}
                                        {insights.work_modes?.length > 0 && ` · ${insights.work_modes.join(", ")}`}
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}

                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        <StatCard title="Your Best Alignment" value={insights.your_best_alignment ?? 0} scoreType delay={0} />
                        <StatCard title="Your Average" value={insights.your_average_alignment ?? 0} scoreType delay={0.05} />
                        <StatCard title="Roles Saved" value={insights.roles?.length || 0} delay={0.1} />
                        <StatCard title="Gaps Here" value={gaps.length} delay={0.15} />
                    </div>

                    <div className="grid lg:grid-cols-2 gap-6">
                        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="card-elevated rounded-2xl p-6">
                            <h3 className="text-sm font-semibold mb-3">What their postings ask for</h3>
                            <div className="flex flex-wrap gap-2 mb-4">
                                {insights.demanded_skills?.map((skill: string) => (
                                    <span key={skill} className="px-2.5 py-1 bg-surface-2 border border-border rounded-lg text-xs">{skill}</span>
                                ))}
                            </div>
                            {insights.preferred_skills?.length > 0 && (
                                <>
                                    <p className="text-xs text-muted mb-2">Nice to have</p>
                                    <div className="flex flex-wrap gap-2">
                                        {insights.preferred_skills.map((skill: string) => (
                                            <span key={skill} className="px-2.5 py-1 bg-surface/40 border border-border/50 rounded-lg text-xs text-muted">{skill}</span>
                                        ))}
                                    </div>
                                </>
                            )}
                        </motion.div>

                        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="card-elevated rounded-2xl p-6">
                            <h3 className="text-sm font-semibold mb-3">Your gaps for this company</h3>
                            {gaps.length === 0 ? (
                                <p className="text-sm text-muted">No gaps — you cover what these postings ask for.</p>
                            ) : (
                                <div className="space-y-2">
                                    {gaps.map((gap) => (
                                        <div key={gap.skill} className="flex items-center justify-between text-xs py-1.5 border-b border-border/40 last:border-0">
                                            <span className="font-medium">{gap.skill}</span>
                                            <div className="flex items-center gap-2">
                                                <span className="text-muted">{gap.jd_count} role{gap.jd_count === 1 ? "" : "s"}</span>
                                                <PriorityBadge priority={gap.priority} />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </motion.div>
                    </div>

                    <div className="card-elevated rounded-2xl overflow-hidden">
                        <div className="p-5 border-b border-border">
                            <h3 className="text-sm font-semibold">Saved postings</h3>
                        </div>
                        <div className="divide-y divide-border/50">
                            {insights.postings?.map((posting: any) => (
                                <div key={posting.jd_id} className="p-4 flex items-center justify-between gap-4">
                                    <div className="min-w-0">
                                        <p className="text-sm truncate">{posting.title}</p>
                                        <p className="text-xs text-muted mt-0.5">
                                            Added {posting.added_at ? new Date(posting.added_at).toLocaleDateString() : "—"}
                                        </p>
                                    </div>
                                    {posting.url && (
                                        <a href={posting.url} target="_blank" rel="noopener noreferrer"
                                            className="text-xs text-primary hover:underline inline-flex items-center gap-1 flex-shrink-0">
                                            Open <ExternalLink className="w-3 h-3" />
                                        </a>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="flex items-start gap-2 text-xs text-muted">
                        <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                        <span>{insights.source}</span>
                    </div>
                </>
            ) : (
                // Scoped view whose company has no aggregate profile (e.g. the JD
                // carries no company name). The spotlight above is the whole page.
                scoped && (
                    <div className="flex items-start gap-2 text-xs text-muted pt-2">
                        <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                        <span>No company-wide profile for this posting — it has no saved company name.</span>
                    </div>
                )
            )}
        </div>
    );
}
