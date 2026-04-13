"use client";

import { SkillHeatmap } from "@/components/dashboard/SkillHeatmap";
import { StatCard } from "@/components/ui/StatCard";
import { motion } from "framer-motion";
import { BarChart3, AlertCircle } from "lucide-react";

const gaps = [
    { skill: "Kubernetes", priority: "P1", demand: 94, jds: 8 },
    { skill: "Terraform", priority: "P1", demand: 88, jds: 6 },
    { skill: "Service Mesh (Istio)", priority: "P2", demand: 72, jds: 4 },
    { skill: "Go (Golang)", priority: "P2", demand: 68, jds: 5 },
    { skill: "TypeScript", priority: "P3", demand: 60, jds: 3 },
];

const priorityStyle = {
    P1: "bg-error/10 text-error border-error/20",
    P2: "bg-warning/10 text-warning border-warning/20",
    P3: "bg-primary/10 text-primary border-primary/20",
};

export default function SkillsPage() {
    return (
        <div className="max-w-6xl mx-auto space-y-6">
            <div>
                <h1 className="text-2xl font-bold">Skill Gap Analysis</h1>
                <p className="text-sm text-muted mt-1">Missing skills ranked by market demand and JD frequency</p>
            </div>
            <div className="grid grid-cols-3 gap-4">
                <StatCard title="Critical Gaps (P1)" value={2} icon={AlertCircle} />
                <StatCard title="Important Gaps (P2)" value={3} icon={BarChart3} />
                <StatCard title="Optional Gaps (P3)" value={4} icon={BarChart3} />
            </div>
            <SkillHeatmap />
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="card-elevated rounded-2xl overflow-hidden">
                <div className="p-5 border-b border-border">
                    <h3 className="text-sm font-semibold">Priority Gap Breakdown</h3>
                </div>
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b border-border text-xs text-muted">
                            <th className="text-left p-4 font-medium">Skill</th>
                            <th className="text-left p-4 font-medium">Priority</th>
                            <th className="text-left p-4 font-medium">Market Demand</th>
                            <th className="text-left p-4 font-medium">JDs Requiring</th>
                        </tr>
                    </thead>
                    <tbody>
                        {gaps.map((gap, i) => (
                            <tr key={gap.skill} className={i % 2 === 0 ? "bg-surface/20" : ""}>
                                <td className="p-4 font-medium text-white">{gap.skill}</td>
                                <td className="p-4">
                                    <span className={`px-2.5 py-1 rounded-full border text-xs font-bold ${priorityStyle[gap.priority as keyof typeof priorityStyle]}`}>
                                        {gap.priority}
                                    </span>
                                </td>
                                <td className="p-4">
                                    <div className="flex items-center gap-3">
                                        <div className="h-2 w-32 bg-border rounded-full overflow-hidden">
                                            <div className="h-full bg-primary rounded-full" style={{ width: `${gap.demand}%` }} />
                                        </div>
                                        <span className="text-xs text-muted">{gap.demand}%</span>
                                    </div>
                                </td>
                                <td className="p-4 text-muted">{gap.jds} of your JDs</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </motion.div>
        </div>
    );
}
