import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export function formatScore(score: number): string {
    return `${Math.round(score)}%`;
}

export function getScoreColor(score: number): string {
    if (score >= 75) return "text-success";
    if (score >= 50) return "text-warning";
    return "text-error";
}

export function getScoreBg(score: number): string {
    if (score >= 75) return "bg-success/10 border-success/20";
    if (score >= 50) return "bg-warning/10 border-warning/20";
    return "bg-error/10 border-error/20";
}

export function getScoreLabel(score: number): string {
    if (score >= 85) return "Excellent";
    if (score >= 70) return "Good";
    if (score >= 50) return "Fair";
    return "Needs Work";
}

export const PLATFORM_NAME =
    process.env.NEXT_PUBLIC_PLATFORM_NAME || "Resume JD Aligner";
