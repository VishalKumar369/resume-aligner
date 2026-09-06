"use client";

import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Tooltip } from "recharts";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface Axis { skill: string; score: number }

const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-card border border-border rounded-xl px-3 py-2 text-sm">
                <p className="text-foreground font-medium">{payload[0].payload.skill}</p>
                <p className="text-primary">{Math.round(payload[0].value)}%</p>
            </div>
        );
    }
    return null;
};

/**
 * Each axis is one scoring component from the latest alignment, so the shape
 * shows where the match is actually strong or weak.
 */
export function CareerRadarChart({
    axes,
    className,
    title = "Alignment Breakdown",
    subtitle = "How your latest match scored, component by component",
}: {
    axes: Axis[];
    className?: string;
    title?: string;
    subtitle?: string;
}) {
    const hasEnoughAxes = axes.length >= 3;

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, delay: 0.2 }}
            className={cn("card-elevated rounded-2xl p-6", className)}
        >
            <div className="mb-4">
                <h3 className="text-sm font-semibold text-foreground">{title}</h3>
                <p className="text-xs text-muted mt-1">{subtitle}</p>
            </div>

            {hasEnoughAxes ? (
                <ResponsiveContainer width="100%" height={280}>
                    <RadarChart data={axes} outerRadius="75%">
                        {/* A translucent neutral so the grid reads on both light and dark. */}
                        <PolarGrid stroke="rgba(128,128,150,0.25)" />
                        <PolarAngleAxis dataKey="skill" tick={{ fill: "#8A8A9A", fontSize: 11 }} />
                        <Radar name="Score" dataKey="score" stroke="#6366F1" fill="#6366F1" fillOpacity={0.15} strokeWidth={2} />
                        <Tooltip content={<CustomTooltip />} />
                    </RadarChart>
                </ResponsiveContainer>
            ) : (
                // A radar needs at least three axes to be a shape rather than a line.
                <div className="h-[280px] flex flex-col justify-center gap-3">
                    {axes.map((axis) => (
                        <div key={axis.skill} className="flex items-center gap-3 text-xs">
                            <span className="w-32 text-muted">{axis.skill}</span>
                            <div className="flex-1 h-2 bg-border rounded-full overflow-hidden">
                                <div className="h-full bg-primary rounded-full" style={{ width: `${Math.round(axis.score)}%` }} />
                            </div>
                            <span className="w-10 text-right">{Math.round(axis.score)}%</span>
                        </div>
                    ))}
                    {axes.length === 0 && (
                        <p className="text-xs text-muted text-center">No alignment components to show yet.</p>
                    )}
                </div>
            )}
        </motion.div>
    );
}
