"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { cn } from "@/lib/utils";

export interface HeatmapSkill {
    name: string;
    status: "strong" | "partial" | "gap" | "critical";
    detail?: string;
}

const colorMap: Record<string, string> = {
    strong: "bg-success/20 border-success/30 text-success",
    partial: "bg-warning/20 border-warning/30 text-warning",
    gap: "bg-orange-500/20 border-orange-500/30 text-orange-400",
    critical: "bg-error/20 border-error/30 text-error",
};

const legendItems = [
    { status: "strong", label: "You have it" },
    { status: "partial", label: "Partially covered" },
    { status: "gap", label: "Gap" },
    { status: "critical", label: "Critical gap" },
];

/**
 * Built from the alignment engine's matched / partial / missing lists, so a tile
 * only appears if some job description actually asked for that skill.
 */
export function SkillHeatmap({
    skills,
    linkForSkill,
    className,
}: {
    skills: HeatmapSkill[];
    // When provided, each tile links here (e.g. to the learning roadmap).
    linkForSkill?: (skill: string) => string;
    className?: string;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className={cn("card-elevated rounded-2xl p-6 flex flex-col", className)}
        >
            <div className="flex items-center justify-between mb-4 gap-4 flex-wrap flex-shrink-0">
                <div>
                    <h3 className="text-sm font-semibold text-foreground">Skill Heatmap</h3>
                    <p className="text-xs text-muted mt-1">Your skills against what your target roles ask for</p>
                </div>
                <div className="flex gap-3 flex-wrap justify-end">
                    {legendItems.map((l) => (
                        <div key={l.status} className="flex items-center gap-1.5 text-xs text-muted">
                            <div className={cn("w-2.5 h-2.5 rounded-sm", colorMap[l.status].split(" ")[0])} />
                            {l.label}
                        </div>
                    ))}
                </div>
            </div>

            {skills.length === 0 ? (
                <p className="text-xs text-muted py-6 text-center">
                    Analyze a resume against a job description to populate this.
                </p>
            ) : (
                <div className="flex flex-wrap gap-2 content-start overflow-y-auto flex-1 min-h-0 pr-1">
                    {skills.map((skill, i) => {
                        const tile = (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.8 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: Math.min(i * 0.03, 0.5) }}
                                whileHover={{ scale: 1.06, transition: { duration: 0.1 } }}
                                className={cn(
                                    "px-3 py-1.5 rounded-lg border text-xs font-medium transition-all",
                                    linkForSkill ? "cursor-pointer" : "cursor-default",
                                    colorMap[skill.status]
                                )}
                                title={linkForSkill ? `Plan how to learn ${skill.name}` : (skill.detail || skill.name)}
                            >
                                {skill.name}
                            </motion.div>
                        );
                        const key = `${skill.name}-${skill.status}`;
                        return linkForSkill ? (
                            <Link key={key} href={linkForSkill(skill.name)}>{tile}</Link>
                        ) : (
                            <div key={key}>{tile}</div>
                        );
                    })}
                </div>
            )}
        </motion.div>
    );
}
