"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

const skills = [
    { name: "Python", level: 5, status: "strong" },
    { name: "FastAPI", level: 4, status: "strong" },
    { name: "Docker", level: 3, status: "medium" },
    { name: "Kubernetes", level: 1, status: "missing" },
    { name: "Terraform", level: 1, status: "missing" },
    { name: "Redis", level: 2, status: "gap" },
    { name: "CI/CD", level: 2, status: "gap" },
    { name: "AWS", level: 3, status: "medium" },
    { name: "PostgreSQL", level: 4, status: "strong" },
    { name: "React", level: 3, status: "medium" },
    { name: "TypeScript", level: 2, status: "gap" },
    { name: "GraphQL", level: 1, status: "missing" },
];

const colorMap: Record<string, string> = {
    strong: "bg-success/70 border-success/20 text-success",
    medium: "bg-warning/60 border-warning/20 text-warning",
    gap: "bg-orange-500/40 border-orange-500/20 text-orange-400",
    missing: "bg-error/50 border-error/20 text-error",
};

const legendItems = [
    { status: "strong", label: "Strong Match" },
    { status: "medium", label: "Partial Match" },
    { status: "gap", label: "Skill Gap" },
    { status: "missing", label: "Missing" },
];

export function SkillHeatmap() {
    return (
        <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="card-elevated rounded-2xl p-6"
        >
            <div className="flex items-center justify-between mb-4">
                <div>
                    <h3 className="text-sm font-semibold text-white">Skill Heatmap</h3>
                    <p className="text-xs text-muted mt-1">Your skills vs. target JD requirements</p>
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
            <div className="flex flex-wrap gap-2">
                {skills.map((skill, i) => (
                    <motion.div
                        key={skill.name}
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: i * 0.04 }}
                        whileHover={{ scale: 1.08, transition: { duration: 0.1 } }}
                        className={cn(
                            "px-3 py-1.5 rounded-lg border text-xs font-medium cursor-pointer transition-all",
                            colorMap[skill.status]
                        )}
                        title={`${skill.name}: Level ${skill.level}/5`}
                    >
                        {skill.name}
                    </motion.div>
                ))}
            </div>
        </motion.div>
    );
}
