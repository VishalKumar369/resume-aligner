"use client";

import { motion } from "framer-motion";
import { AlertCircle, BarChart3, Layers } from "lucide-react";
import { StatCard } from "@/components/ui/StatCard";
import { SkillHeatmap, HeatmapSkill } from "@/components/dashboard/SkillHeatmap";
import { EmptyState, ErrorState, PriorityBadge, Skeleton, StatSkeletonRow } from "@/components/ui/States";
import { useApi } from "@/hooks/useApi";
import { dashboardService } from "@/services/api";

export default function SkillsPage() {
    const { data, loading, error, reload } = useApi<any>(() => dashboardService.getSummary());

    if (loading) {
        return (
            <div className="max-w-6xl mx-auto space-y-6">
                <Skeleton className="h-8 w-64" />
                <StatSkeletonRow count={3} />
                <Skeleton className="h-40 rounded-2xl" />
            </div>
        );
    }

    if (error) return <div className="max-w-6xl mx-auto"><ErrorState message={error} onRetry={reload} /></div>;

    const gaps: any[] = data?.skill_gap_detail || [];
    const partial: any[] = data?.partial_skills || [];

    if (!data?.has_data) {
        return (
            <div className="max-w-3xl mx-auto pt-10">
                <EmptyState
                    title="No skill gaps yet"
                    description="Analyze your resume against a job description and the gaps will be ranked here by how many of your target roles ask for them."
                />
            </div>
        );
    }

    const counts = {
        P1: gaps.filter((g) => g.priority === "P1").length,
        P2: gaps.filter((g) => g.priority === "P2").length,
        P3: gaps.filter((g) => g.priority === "P3").length,
    };

    const heatmap: HeatmapSkill[] = [
        ...partial.map((p): HeatmapSkill => ({
            name: p.skill, status: "partial", detail: `partially covered by ${p.covered_by}`,
        })),
        ...gaps.map((g): HeatmapSkill => ({
            name: g.skill,
            status: g.priority === "P1" ? "critical" : "gap",
            detail: `wanted by ${g.jd_count} role${g.jd_count === 1 ? "" : "s"}`,
        })),
    ];

    return (
        <div className="max-w-6xl mx-auto space-y-6">
            <div>
                <h1 className="text-2xl font-bold">Skill Gap Analysis</h1>
                <p className="text-sm text-muted mt-1">
                    Ranked by how many of your target roles ask for each skill, then by priority
                </p>
            </div>

            <div className="grid grid-cols-3 gap-4">
                <StatCard title="Critical Gaps" value={counts.P1} icon={AlertCircle} subtitle="named in a role title or repeated" />
                <StatCard title="Important Gaps" value={counts.P2} icon={BarChart3} subtitle="stated requirements" />
                <StatCard title="Bonus Gaps" value={counts.P3} icon={Layers} subtitle="nice-to-haves" />
            </div>

            <SkillHeatmap skills={heatmap} />

            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="card-elevated rounded-2xl overflow-hidden">
                <div className="p-5 border-b border-border">
                    <h3 className="text-sm font-semibold">Priority Gap Breakdown</h3>
                    <p className="text-xs text-muted mt-0.5">
                        A skill several roles demand outranks a single critical one
                    </p>
                </div>

                {gaps.length === 0 ? (
                    <p className="text-sm text-muted p-6 text-center">
                        No gaps — your resume covers everything your target roles ask for.
                    </p>
                ) : (
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-border text-xs text-muted">
                                <th className="text-left p-4 font-medium">Skill</th>
                                <th className="text-left p-4 font-medium">Priority</th>
                                <th className="text-left p-4 font-medium">Category</th>
                                <th className="text-left p-4 font-medium">Roles requiring it</th>
                                <th className="text-left p-4 font-medium">Type</th>
                            </tr>
                        </thead>
                        <tbody>
                            {gaps.map((gap, i) => (
                                <tr key={gap.skill} className={i % 2 === 0 ? "bg-surface/20" : ""}>
                                    <td className="p-4 font-medium">{gap.skill}</td>
                                    <td className="p-4"><PriorityBadge priority={gap.priority} /></td>
                                    <td className="p-4 text-muted capitalize">{(gap.category || "—").replace(/-/g, " ")}</td>
                                    <td className="p-4 text-muted">{gap.jd_count}</td>
                                    <td className="p-4 text-muted">{gap.mandatory ? "Required" : "Nice to have"}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </motion.div>

            {partial.length > 0 && (
                <div className="card-elevated rounded-2xl p-5">
                    <h3 className="text-sm font-semibold mb-3">Partially covered</h3>
                    <p className="text-xs text-muted mb-3">
                        You have a related tool. Calling out direct exposure would close these.
                    </p>
                    <div className="space-y-2">
                        {partial.map((item) => (
                            <div key={item.skill} className="text-xs text-muted border-l-2 border-warning/40 pl-3 py-1">
                                <span className="text-warning font-medium">{item.skill}</span> — you have {item.covered_by}
                                {item.jd_count > 1 && ` · asked for by ${item.jd_count} roles`}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
