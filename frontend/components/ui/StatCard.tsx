"use client";

import { motion } from "framer-motion";
import { cn, getScoreColor, getScoreBg, formatScore } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface StatCardProps {
    title: string;
    value: string | number;
    subtitle?: string;
    trend?: number;
    icon?: React.ElementType;
    scoreType?: boolean;
    delay?: number;
    className?: string;
}

export function StatCard({ title, value, subtitle, trend, icon: Icon, scoreType, delay = 0, className }: StatCardProps) {
    const numVal = typeof value === "number" ? value : parseFloat(String(value));
    const scoreClass = scoreType ? getScoreColor(numVal) : "text-foreground";
    const scoreBg = scoreType ? getScoreBg(numVal) : "";

    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay }}
            whileHover={{ y: -2, transition: { duration: 0.15 } }}
            className={cn("card-elevated rounded-xl p-4 group", className)}
        >
            <div className="stat-label">
                {Icon && <Icon className="w-3 h-3 opacity-80" />}
                {title}
            </div>
            <div className={cn("stat-value mt-2.5", scoreClass)}>
                {scoreType ? formatScore(numVal) : value}
            </div>
            <div className="flex items-center gap-2 mt-2">
                {trend !== undefined && (
                    <div className={cn(
                        "stat-badge",
                        trend > 0 ? "bg-success/10 text-success" : trend < 0 ? "bg-error/10 text-error" : "bg-muted/10 text-muted"
                    )}>
                        {trend > 0 ? <TrendingUp className="w-3 h-3" /> : trend < 0 ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                        {Math.abs(trend)}%
                    </div>
                )}
                {subtitle && <span className="text-[11px] text-muted">{subtitle}</span>}
            </div>
        </motion.div>
    );
}

export function SkeletonCard({ className }: { className?: string }) {
    return (
        <div className={cn("card-elevated rounded-xl p-4 animate-pulse", className)}>
            <div className="h-3 bg-surface-2 rounded w-2/3 mb-4" />
            <div className="h-7 bg-surface-2 rounded w-1/2 mb-3" />
            <div className="h-3 bg-surface-2 rounded w-1/3" />
        </div>
    );
}
