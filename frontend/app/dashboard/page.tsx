"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Target, Zap, Layers, Briefcase, AlertTriangle } from "lucide-react";
import { StatCard } from "@/components/ui/StatCard";
import { CareerRadarChart } from "@/components/dashboard/CareerRadarChart";
import { SkillHeatmap, HeatmapSkill } from "@/components/dashboard/SkillHeatmap";
import { AnalysisTrackerTable, AnalysisRow } from "@/components/dashboard/AnalysisTrackerTable";
import { EmptyState, ErrorState, StatSkeletonRow, Skeleton } from "@/components/ui/States";
import { useApi } from "@/hooks/useApi";
import { alignmentService } from "@/services/api";

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
    // Every stored run, newest first. Each is selectable and drives the section
    // above; the whole dashboard reflects one analysis at a time.
    const { data: analyses, loading, error, reload } = useApi<AnalysisRow[]>(
        () => alignmentService.getAll({ limit: 100 })
    );

    const [selectedId, setSelectedId] = useState<string | null>(null);
    const activeId = selectedId ?? analyses?.[0]?.id ?? null;

    const { data: detail, loading: detailLoading } = useApi<any>(
        () => alignmentService.getById(activeId!),
        [activeId],
        { skip: !activeId }
    );

    const active = useMemo(
        () => analyses?.find((a) => a.id === activeId) || null,
        [analyses, activeId]
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

    if (!analyses?.length) {
        return (
            <div className="max-w-3xl mx-auto pt-10">
                <EmptyState
                    title="No analysis yet"
                    description="Upload a resume and a job description, and this dashboard will fill with your real scores, skill gaps, and company matches."
                />
            </div>
        );
    }

    const uniqueResumes = new Set(analyses.map((a) => a.resume_id)).size;
    const uniqueRoles = new Set(analyses.map((a) => a.jd_id)).size;

    const heatmap = detail ? buildHeatmap(detail) : [];
    const improvements = detail ? buildImprovements(detail) : [];
    const radarAxes = Object.entries(detail?.breakdown || {}).map(([name, score]: any) => ({
        skill: name.replace(/_match$/, "").replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase()),
        score: Number(score),
    }));

    const resumeUnhealthy = detail?.extraction_health && detail.extraction_health.resume_ok === false;
    const analyzedOn = active?.created_at ? new Date(active.created_at).toLocaleDateString() : null;

    return (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6 max-w-7xl mx-auto">
            <div>
                <h1 className="text-2xl font-bold text-white">Career Intelligence Dashboard</h1>
                <p className="text-sm text-muted mt-1">
                    {analyses.length} analys{analyses.length === 1 ? "is" : "es"} ·{" "}
                    {uniqueResumes} resume{uniqueResumes === 1 ? "" : "s"} ·{" "}
                    {uniqueRoles} role{uniqueRoles === 1 ? "" : "s"}
                </p>
            </div>

            {/* Selected-analysis context */}
            <div className="flex flex-wrap items-baseline justify-between gap-2">
                <div>
                    <h2 className="text-lg font-semibold text-white">
                        {active?.company || "Unknown company"}
                        {active?.role ? <span className="text-muted font-normal"> — {active.role}</span> : null}
                    </h2>
                    <p className="text-xs text-muted mt-0.5">
                        {active?.resume_label ? `${active.resume_label}` : "Selected analysis"}
                        {analyzedOn ? ` · analyzed ${analyzedOn}` : ""}
                    </p>
                </div>
            </div>

            {resumeUnhealthy && (
                <div className="bg-error/5 border border-error/20 rounded-xl p-3 flex gap-2.5">
                    <AlertTriangle className="w-4 h-4 text-error flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-muted">
                        This resume didn&apos;t extract cleanly, so these scores reflect a parsing
                        problem rather than a poor match.
                    </p>
                </div>
            )}

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard title="JD Alignment" value={active?.alignment_score ?? 0} icon={Zap} scoreType delay={0} />
                <StatCard title="ATS Score" value={active?.ats_score ?? 0} icon={Target} scoreType delay={0.05} />
                <StatCard title="Skill Match" value={detail?.skill_match_score ?? 0} icon={Layers} scoreType delay={0.1} />
                <StatCard title="Experience Match" value={detail?.experience_match_score ?? 0} icon={Briefcase} scoreType delay={0.15} />
            </div>

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
                    {detailLoading ? (
                        <div className="space-y-3">
                            {[0, 1, 2].map((i) => <Skeleton key={i} className="h-10 rounded-lg" />)}
                        </div>
                    ) : improvements.length ? (
                        <div className="space-y-3">
                            {improvements.map((item, i) => (
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
                        <p className="text-sm text-muted">Nothing to flag — this resume covers what the role asks for.</p>
                    )}
                </motion.div>
            </div>

            <SkillHeatmap skills={heatmap} />

            <AnalysisTrackerTable analyses={analyses} activeId={activeId} onSelect={setSelectedId} />
        </motion.div>
    );
}

/**
 * The selected run's own matched / partial / missing skills, as heatmap tiles.
 * A missing skill flagged P1 shows as critical rather than a plain gap.
 */
function buildHeatmap(detail: any): HeatmapSkill[] {
    const tiles: HeatmapSkill[] = [];
    const seen = new Set<string>();

    const push = (name: string, status: HeatmapSkill["status"], detailText?: string) => {
        const key = (name || "").toLowerCase();
        if (!name || seen.has(key)) return;
        seen.add(key);
        tiles.push({ name, status, detail: detailText });
    };

    (detail?.matched_skills || []).forEach((s: string) => push(s, "strong", `${s}: matched`));
    (detail?.partial_skills || []).forEach((p: any) =>
        push(p.skill, "partial", `${p.skill}: partially covered by ${p.covered_by}`)
    );
    (detail?.missing_skills || []).forEach((m: any) =>
        push(m.skill, m.priority === "P1" ? "critical" : "gap", `${m.skill}: missing (${m.importance || "wanted"})`)
    );

    return tiles;
}

/**
 * Concrete next actions for this run: the model's own suggestions, ATS warnings,
 * and the top missing skills ranked by priority.
 */
function buildImprovements(detail: any): { text: string; priority: string }[] {
    const items: { text: string; priority: string }[] = [];
    const seen = new Set<string>();

    const add = (text: string, priority: string) => {
        const key = text.trim().toLowerCase();
        if (!text.trim() || seen.has(key)) return;
        seen.add(key);
        items.push({ text: text.trim(), priority });
    };

    (detail?.missing_skills || []).slice(0, 3).forEach((m: any) =>
        add(`Add evidence of ${m.skill} — ${m.importance === "mandatory" ? "required" : "preferred"} for this role.`,
            m.priority === "P1" ? "high" : "medium")
    );
    (detail?.improvement_suggestions || []).forEach((s: string) => add(s, "medium"));
    (detail?.ats_warnings || []).forEach((w: string) => add(w, "low"));

    return items.slice(0, 6);
}
