"use client";

import { motion } from "framer-motion";
import { useParams } from "next/navigation";
import { Building2, ExternalLink, Info } from "lucide-react";
import { StatCard } from "@/components/ui/StatCard";
import { EmptyState, ErrorState, PriorityBadge, Skeleton, StatSkeletonRow } from "@/components/ui/States";
import { useApi } from "@/hooks/useApi";
import { companyService } from "@/services/api";

export default function CompanyPage() {
    const params = useParams();
    const companyId = String(params?.companyId || "");
    const { data, loading, error, reload } = useApi<any>(
        () => companyService.getInsights(companyId),
        [companyId]
    );

    if (loading) {
        return (
            <div className="max-w-5xl mx-auto space-y-6">
                <Skeleton className="h-24 rounded-2xl" />
                <StatSkeletonRow />
                <Skeleton className="h-48 rounded-2xl" />
            </div>
        );
    }

    // The backend 404s when no saved posting mentions this company, rather than
    // inventing a profile for it.
    if (error) {
        const notFound = error.toLowerCase().includes("no job descriptions");
        return (
            <div className="max-w-3xl mx-auto pt-10">
                {notFound ? (
                    <EmptyState
                        title={`Nothing saved for "${companyId}"`}
                        description="Company insights are built from the job descriptions you upload. Add a posting from this company to see what it asks for and how you match."
                        actionLabel="Add a job description"
                    />
                ) : (
                    <ErrorState message={error} onRetry={reload} />
                )}
            </div>
        );
    }

    const gaps: any[] = data?.your_gaps_here || [];

    return (
        <div className="max-w-5xl mx-auto space-y-6">
            <div className="card-elevated rounded-2xl p-6">
                <div className="flex items-center gap-4">
                    <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                        <Building2 className="w-8 h-8 text-primary" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold">{data.company}</h1>
                        <p className="text-sm text-muted mt-1">
                            {data.jd_count} saved posting{data.jd_count === 1 ? "" : "s"}
                            {data.locations?.length > 0 && ` · ${data.locations.join(", ")}`}
                            {data.work_modes?.length > 0 && ` · ${data.work_modes.join(", ")}`}
                        </p>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard title="Your Best Alignment" value={data.your_best_alignment ?? 0} scoreType delay={0} />
                <StatCard title="Your Average" value={data.your_average_alignment ?? 0} scoreType delay={0.05} />
                <StatCard title="Roles Saved" value={data.roles?.length || 0} delay={0.1} />
                <StatCard title="Gaps Here" value={gaps.length} delay={0.15} />
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
                <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="card-elevated rounded-2xl p-6">
                    <h3 className="text-sm font-semibold mb-3">What their postings ask for</h3>
                    <div className="flex flex-wrap gap-2 mb-4">
                        {data.demanded_skills?.map((skill: string) => (
                            <span key={skill} className="px-2.5 py-1 bg-surface-2 border border-border rounded-lg text-xs">{skill}</span>
                        ))}
                    </div>
                    {data.preferred_skills?.length > 0 && (
                        <>
                            <p className="text-xs text-muted mb-2">Nice to have</p>
                            <div className="flex flex-wrap gap-2">
                                {data.preferred_skills.map((skill: string) => (
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
                    {data.postings?.map((posting: any) => (
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
                <span>{data.source}</span>
            </div>
        </div>
    );
}
