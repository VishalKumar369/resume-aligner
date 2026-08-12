"use client";

import { AlertTriangle, Inbox, RefreshCw } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
    return <div className={cn("animate-pulse rounded-lg bg-surface-2", className)} />;
}

export function CardSkeleton({ height = "h-32" }: { height?: string }) {
    return <Skeleton className={cn("card-elevated rounded-2xl w-full", height)} />;
}

export function StatSkeletonRow({ count = 4 }: { count?: number }) {
    return (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: count }).map((_, i) => (
                <Skeleton key={i} className="h-28 rounded-2xl" />
            ))}
        </div>
    );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
    return (
        <div className="card-elevated rounded-2xl p-8 text-center">
            <div className="w-12 h-12 rounded-2xl bg-error/10 flex items-center justify-center mx-auto mb-4">
                <AlertTriangle className="w-6 h-6 text-error" />
            </div>
            <p className="text-sm font-medium text-error mb-1">Couldn&apos;t load this</p>
            <p className="text-sm text-muted max-w-md mx-auto">{message}</p>
            {onRetry && (
                <button onClick={onRetry} className="btn-ghost mt-4 inline-flex items-center gap-2 text-sm">
                    <RefreshCw className="w-4 h-4" /> Try again
                </button>
            )}
        </div>
    );
}

/**
 * Shown when the backend reports `has_data: false`. The alternative is a wall
 * of zeros that reads like a broken page rather than an empty one.
 */
export function EmptyState({
    title,
    description,
    actionLabel = "Analyze a resume",
    actionHref = "/upload",
}: {
    title: string;
    description: string;
    actionLabel?: string;
    actionHref?: string;
}) {
    return (
        <div className="card-elevated rounded-2xl p-10 text-center">
            <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                <Inbox className="w-7 h-7 text-primary" />
            </div>
            <h3 className="text-lg font-semibold mb-2">{title}</h3>
            <p className="text-sm text-muted max-w-md mx-auto mb-6">{description}</p>
            <Link href={actionHref} className="btn-primary inline-flex">
                {actionLabel}
            </Link>
        </div>
    );
}

export function ScorePill({ score }: { score: number }) {
    const tone =
        score >= 80 ? "text-success bg-success/10 border-success/20"
        : score >= 60 ? "text-warning bg-warning/10 border-warning/20"
        : "text-error bg-error/10 border-error/20";
    return (
        <span className={cn("px-2.5 py-1 rounded-lg border text-xs font-semibold", tone)}>
            {Math.round(score)}%
        </span>
    );
}

export function PriorityBadge({ priority }: { priority: string }) {
    const label: Record<string, string> = { P1: "Critical", P2: "Important", P3: "Bonus" };
    const tone: Record<string, string> = {
        P1: "text-error bg-error/10 border-error/20",
        P2: "text-warning bg-warning/10 border-warning/20",
        P3: "text-primary bg-primary/10 border-primary/20",
    };
    return (
        <span className={cn("px-2 py-0.5 rounded-md border text-[11px] font-medium", tone[priority] || tone.P3)}>
            {label[priority] || priority}
        </span>
    );
}
