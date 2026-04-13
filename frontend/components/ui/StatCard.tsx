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
    const scoreClass = scoreType ? getScoreColor(numVal) : "text-white";
    const scoreBg = scoreType ? getScoreBg(numVal) : "";

    return (
        <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay }}
            whileHover={{ y: -2, transition: { duration: 0.15 } }}
            className={cn("card-elevated rounded-2xl p-5 group", className)}
        >
            <div className="flex items-start justify-between mb-4">
                <span className="text-sm text-muted font-medium">{title}</span>
                {Icon && (
                    <div className="p-2 rounded-lg bg-surface-2 group-hover:bg-primary/10 transition-colors">
                        <Icon className="w-4 h-4 text-muted group-hover:text-primary transition-colors" />
                    </div>
                )}
            </div>
            <div className={cn("text-3xl font-bold mb-1", scoreClass)}>
                {scoreType ? formatScore(numVal) : value}
            </div>
            <div className="flex items-center gap-2">
                {trend !== undefined && (
                    <div className={cn(
                        "flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full",
                        trend > 0 ? "bg-success/10 text-success" : trend < 0 ? "bg-error/10 text-error" : "bg-muted/10 text-muted"
                    )}>
                        {trend > 0 ? <TrendingUp className="w-3 h-3" /> : trend < 0 ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                        {Math.abs(trend)}%
                    </div>
                )}
                {subtitle && <span className="text-xs text-muted">{subtitle}</span>}
            </div>
        </motion.div>
    );
}

export function SkeletonCard({ className }: { className?: string }) {
    return (
        <div className={cn("card-elevated rounded-2xl p-5 animate-pulse", className)}>
            <div className="h-4 bg-surface-2 rounded w-2/3 mb-4" />
            <div className="h-8 bg-surface-2 rounded w-1/2 mb-3" />
            <div className="h-3 bg-surface-2 rounded w-1/3" />
        </div>
    );
}
