"use client";

import { motion } from "framer-motion";
import { Target, Zap, BrainCircuit, BarChart2 } from "lucide-react";
import { StatCard } from "@/components/ui/StatCard";
import { CareerRadarChart } from "@/components/dashboard/CareerRadarChart";
import { SkillHeatmap } from "@/components/dashboard/SkillHeatmap";
import { CompanyTrackerTable } from "@/components/dashboard/CompanyTrackerTable";

const PLATFORM_NAME = process.env.NEXT_PUBLIC_PLATFORM_NAME || "Resume JD Aligner";

const improvements = [
    { text: "Add 'Kubernetes' to your Skills section — appears 6x in your target JDs", priority: "high" },
    { text: "Quantify the impact of your CI/CD work with team size or deployment frequency metrics", priority: "medium" },
    { text: "Rewrite third bullet in 'Tech Corp' to mirror 'distributed systems' language", priority: "medium" },
    { text: "Add a brief 'System Design' project to your Projects section", priority: "low" },
];

const priorityColor = { high: "border-l-error", medium: "border-l-warning", low: "border-l-primary" };

export default function DashboardPage() {
    return (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6 max-w-7xl mx-auto">
            {/* Page header */}
            <div>
                <h1 className="text-2xl font-bold text-white">Career Intelligence Dashboard</h1>
                <p className="text-sm text-muted mt-1">Last analyzed: Today at 4:12 PM · Resume v2.0 vs Google SWE JD</p>
            </div>

            {/* Score Cards Row */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard title="ATS Score" value={92} icon={Target} scoreType trend={4} subtitle="vs last version" delay={0} />
                <StatCard title="JD Alignment" value={85} icon={Zap} scoreType trend={7} subtitle="vs last analysis" delay={0.05} />
                <StatCard title="Career Readiness" value={78} icon={BrainCircuit} scoreType trend={2} subtitle="cross-JD average" delay={0.1} />
                <StatCard title="Interview Probability" value="High" icon={BarChart2} subtitle="Based on 85% alignment" delay={0.15} />
            </div>

            {/* Main Grid */}
            <div className="grid lg:grid-cols-3 gap-6">
                {/* Radar Chart */}
                <div className="lg:col-span-1">
                    <CareerRadarChart />
                </div>

                {/* Improvements Panel */}
                <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.25 }}
                    className="lg:col-span-2 card-elevated rounded-2xl p-6"
                >
                    <h3 className="text-sm font-semibold text-white mb-4">Recommended Improvements</h3>
                    <div className="space-y-3">
                        {improvements.map((item, i) => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: 0.3 + i * 0.06 }}
                                className={`border-l-2 pl-4 py-2 ${priorityColor[item.priority as keyof typeof priorityColor]}`}
                            >
                                <p className="text-sm text-muted-foreground leading-relaxed">{item.text}</p>
                                <span className={`text-xs mt-1 inline-block font-medium capitalize ${item.priority === "high" ? "text-error" : item.priority === "medium" ? "text-warning" : "text-primary"}`}>
                                    {item.priority} priority
                                </span>
                            </motion.div>
                        ))}
                    </div>
                </motion.div>
            </div>

            {/* Skill Heatmap */}
            <SkillHeatmap />

            {/* Company Tracker Table */}
            <CompanyTrackerTable />
        </motion.div>
    );
}
