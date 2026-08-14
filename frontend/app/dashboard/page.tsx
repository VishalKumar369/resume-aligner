"use client";

import { motion } from "framer-motion";
import { Target, Zap, BrainCircuit, BarChart2, Info } from "lucide-react";
import { StatCard } from "@/components/ui/StatCard";
import { CareerRadarChart } from "@/components/dashboard/CareerRadarChart";
import { SkillHeatmap, HeatmapSkill } from "@/components/dashboard/SkillHeatmap";
import { CompanyTrackerTable } from "@/components/dashboard/CompanyTrackerTable";
import { EmptyState, ErrorState, StatSkeletonRow, Skeleton } from "@/components/ui/States";
import { useApi } from "@/hooks/useApi";
import { alignmentService, dashboardService } from "@/services/api";

const priorityColor: Record<string, string> = {
    high: "border-l-error",
    medium: "border-l-warning",
    low: "border-l-primary",
};

const priorityText: Record<string, string> = {
    high: "text-error",
    medium: "text-warning",
    low: "text-primary",
};

export default function DashboardPage() {
    const { data: summary, loading, error, reload } = useApi<any>(() => dashboardService.getSummary());

    // The radar needs the per-component breakdown, which lives on the alignment
    // detail rather than the summary.
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
            <div className="space-y-6 max-w-7xl mx-auto">
                <Skeleton className="h-8 w-64" />
                <StatSkeletonRow />
                <div className="grid lg:grid-cols-3 gap-6">
                    <Skeleton className="h-80 rounded-2xl lg:col-span-1" />
                    <Skeleton className="h-80 rounded-2xl lg:col-span-2" />
                </div>
            </div>
        );
    }

    if (error) return <div className="max-w-7xl mx-auto"><ErrorState message={error} onRetry={reload} /></div>;

    if (!summary?.has_data) {
        return (
            <div className="max-w-3xl mx-auto pt-10">
                <EmptyState
                    title="No analysis yet"
                    description="Upload a resume and a job description, and this dashboard will fill with your real scores, skill gaps, and company matches."
                />
            </div>
        );
    }

    const probability = summary.interview_probability || {};
    const heatmap = buildHeatmap(summary, latestDetail);
    const radarAxes = Object.entries(latestDetail?.breakdown || {}).map(([name, score]: any) => ({
        skill: name.replace(/_match$/, "").replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase()),
        score: Number(score),
    }));

    return (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6 max-w-7xl mx-auto">
            <div>
                <h1 className="text-2xl font-bold text-white">Career Intelligence Dashboard</h1>
                <p className="text-sm text-muted mt-1">
                    {summary.totals.resumes} resume{summary.totals.resumes === 1 ? "" : "s"} ·{" "}
                    {summary.totals.target_roles} target role{summary.totals.target_roles === 1 ? "" : "s"} ·{" "}
                    {summary.totals.optimized_versions} optimized version{summary.totals.optimized_versions === 1 ? "" : "s"}
                </p>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard title="Best ATS Score" value={summary.best_ats_score} icon={Target} scoreType
                    subtitle={`avg ${Math.round(summary.avg_ats_score)}%`} delay={0} />
                <StatCard title="Best JD Alignment" value={summary.best_alignment_score} icon={Zap} scoreType
                    subtitle={`avg ${Math.round(summary.avg_alignment_score)}%`} delay={0.05} />
                <StatCard title="Career Readiness" value={summary.career_readiness_index} icon={BrainCircuit} scoreType
                    subtitle="across all target roles" delay={0.1} />
                <StatCard title="Interview Signal" value={probability.band || "—"} icon={BarChart2}
                    subtitle={probability.score ? `score ${Math.round(probability.score)}` : undefined} delay={0.15} />
            </div>

            {probability.caveat && (
                <div className="flex items-start gap-2 text-xs text-muted">
                    <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                    <span><strong className="text-muted-foreground">Interview signal:</strong> {probability.basis}. {probability.caveat}</span>
                </div>
            )}

            <div className="grid lg:grid-cols-3 gap-6">
                <div className="lg:col-span-1">
                    <CareerRadarChart axes={radarAxes} />
                </div>

                <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.25 }}
                    className="lg:col-span-2 card-elevated rounded-2xl p-6"
                >
                    <h3 className="text-sm font-semibold text-white mb-4">Recommended Improvements</h3>
                    {summary.recommended_improvements?.length ? (
                        <div className="space-y-3">
                            {summary.recommended_improvements.map((item: any, i: number) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: 0.3 + i * 0.06 }}
                                    className={`border-l-2 pl-4 py-2 ${priorityColor[item.priority] || "border-l-primary"}`}
                                >
                                    <p className="text-sm text-muted-foreground leading-relaxed">{item.text}</p>
                                    <span className={`text-xs mt-1 inline-block font-medium capitalize ${priorityText[item.priority] || "text-primary"}`}>
                                        {item.priority} priority
                                    </span>
                                </motion.div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-sm text-muted">Nothing to flag — your resume covers what your target roles ask for.</p>
                    )}
                </motion.div>
            </div>

            <SkillHeatmap skills={heatmap} />
            <CompanyTrackerTable matches={summary.top_company_matches || []} />

            {summary.recent_activity?.length > 0 && (
                <div className="card-elevated rounded-2xl p-6">
                    <h3 className="text-sm font-semibold text-white mb-4">Recent Activity</h3>
                    <div className="space-y-2">
                        {summary.recent_activity.map((event: any, i: number) => (
                            <div key={i} className="flex items-center justify-between text-xs py-1.5 border-b border-border/40 last:border-0">
                                <span className="text-muted-foreground">{event.action}</span>
                                <span className="text-muted truncate max-w-[45%]">{event.target}</span>
                                <span className="text-muted">{event.date}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </motion.div>
    );
}

/**
 * Merge the latest run's matched/partial lists with the cross-role gap ranking,
 * so a skill demanded by several roles shows as critical rather than a plain gap.
 */
function buildHeatmap(summary: any, detail: any): HeatmapSkill[] {
    const tiles: HeatmapSkill[] = [];
    const seen = new Set<string>();

    const push = (name: string, status: HeatmapSkill["status"], detailText?: string) => {
        const key = name.toLowerCase();
        if (!name || seen.has(key)) return;
        seen.add(key);
        tiles.push({ name, status, detail: detailText });
    };

    (detail?.matched_skills || []).forEach((s: string) => push(s, "strong", `${s}: matched`));
    (detail?.partial_skills || []).forEach((p: any) =>
        push(p.skill, "partial", `${p.skill}: partially covered by ${p.covered_by}`)
    );
    (summary?.skill_gap_detail || []).forEach((gap: any) =>
        push(
            gap.skill,
            gap.priority === "P1" ? "critical" : "gap",
            `${gap.skill}: wanted by ${gap.jd_count} role${gap.jd_count === 1 ? "" : "s"}`
        )
    );

    return tiles;
}
