"use client";

import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Tooltip } from "recharts";
import { motion } from "framer-motion";

const data = [
    { skill: "Backend", score: 82 },
    { skill: "Frontend", score: 65 },
    { skill: "System Design", score: 70 },
    { skill: "Cloud / DevOps", score: 55 },
    { skill: "Testing", score: 74 },
    { skill: "Data / ML", score: 48 },
];

const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-card border border-border rounded-xl px-3 py-2 text-sm">
                <p className="text-white font-medium">{payload[0].payload.skill}</p>
                <p className="text-primary">{payload[0].value}%</p>
            </div>
        );
    }
    return null;
};

export function CareerRadarChart() {
    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, delay: 0.2 }}
            className="card-elevated rounded-2xl p-6"
        >
            <div className="mb-4">
                <h3 className="text-sm font-semibold text-white">Career Readiness Radar</h3>
                <p className="text-xs text-muted mt-1">Skill readiness vs. industry benchmarks</p>
            </div>
            <ResponsiveContainer width="100%" height={280}>
                <RadarChart data={data} outerRadius="75%">
                    <PolarGrid stroke="#1E1E2E" />
                    <PolarAngleAxis dataKey="skill" tick={{ fill: "#71717A", fontSize: 11 }} />
                    <Radar
                        name="Readiness"
                        dataKey="score"
                        stroke="#6366F1"
                        fill="#6366F1"
                        fillOpacity={0.15}
                        strokeWidth={2}
                    />
                    <Tooltip content={<CustomTooltip />} />
                </RadarChart>
            </ResponsiveContainer>
        </motion.div>
    );
}
