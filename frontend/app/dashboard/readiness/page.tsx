"use client";

import { motion } from "framer-motion";
import { Brain, Target, TrendingUp } from "lucide-react";
import { CareerRadarChart } from "@/components/dashboard/CareerRadarChart";
import { StatCard } from "@/components/ui/StatCard";
import { EmptyState, ErrorState, Skeleton, StatSkeletonRow } from "@/components/ui/States";
import { useApi } from "@/hooks/useApi";
import { alignmentService, dashboardService } from "@/services/api";

export default function ReadinessPage() {
    const { data: summary, loading, error, reload } = useApi<any>(() => dashboardService.getSummary());

    const { data: latestList } = useApi<any[]>(
        () => alignmentService.getAll({ latest_only: true, limit: 1 }),
        [summary?.totals?.alignments]
    );
    const { data: latestDetail } = useApi<any>(
        () => alignmentService.getById(latestList![0].id),
        [latestList?.[0]?.id],
        { skip: !latestList?.length }
    );

    if (loading) {
        return (
            <div className="max-w-6xl mx-auto space-y-6">
                <Skeleton className="h-8 w-56" />
                <StatSkeletonRow count={3} />
                <Skeleton className="h-80 rounded-2xl" />
            </div>
        );
    }

    if (error) return <div className="max-w-6xl mx-auto"><ErrorState message={error} onRetry={reload} /></div>;

    if (!summary?.has_data) {
        return (
            <div className="max-w-3xl mx-auto pt-10">
                <EmptyState
                    title="No readiness data yet"
                    description="Readiness is averaged across your analyzed roles. Run an analysis to see it."
                />
            </div>
        );
    }

    const probability = summary.interview_probability || {};
    const trend: any[] = summary.readiness_trend || [];
    const radarAxes = Object.entries(latestDetail?.breakdown || {}).map(([name, score]: any) => ({
        skill: name.replace(/_match$/, "").replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase()),
        score: Number(score),
    }));

    return (
        <div className="max-w-6xl mx-auto space-y-6">
            <div>
                <h1 className="text-xl font-semibold tracking-tight">Career Readiness</h1>
                <p className="text-sm text-muted mt-1">
                    Averaged across {summary.totals.target_roles} target role{summary.totals.target_roles === 1 ? "" : "s"}
                </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <StatCard title="Overall Readiness" value={summary.career_readiness_index} icon={Target} scoreType
                    subtitle="0.65 alignment + 0.35 ATS" />
                <StatCard title="Average Alignment" value={summary.avg_alignment_score} icon={TrendingUp} scoreType
                    subtitle={`best ${Math.round(summary.best_alignment_score)}%`} />
                <StatCard title="Interview Signal" value={probability.band || "—"} icon={Brain}
                    subtitle={probability.score ? `score ${Math.round(probability.score)}` : undefined} />
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
                <CareerRadarChart axes={radarAxes} />

                <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="card-elevated rounded-2xl p-6">
                    <h3 className="text-sm font-semibold mb-1">Score History</h3>
                    <p className="text-xs text-muted mb-4">Every analysis you have run, oldest first</p>

                    {trend.length === 0 ? (
                        <p className="text-sm text-muted">No history yet.</p>
                    ) : (
                        <div className="space-y-2">
                            {trend.map((point, i) => (
                                <div key={i} className="flex items-center gap-3 text-xs">
                                    <span className="w-20 text-muted">{point.date}</span>
                                    <div className="flex-1 h-2 bg-border rounded-full overflow-hidden">
                                        <div className="h-full bg-primary rounded-full" style={{ width: `${Math.round(point.alignment_score)}%` }} />
                                    </div>
                                    <span className="w-10 text-right">{Math.round(point.alignment_score)}%</span>
                                    <span className="w-14 text-right text-muted">ATS {Math.round(point.ats_score)}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </motion.div>
            </div>

            {probability.caveat && (
                <p className="text-xs text-muted">
                    <strong className="text-muted-foreground">Interview signal:</strong> {probability.basis}. {probability.caveat}
                </p>
            )}
        </div>
    );
}
