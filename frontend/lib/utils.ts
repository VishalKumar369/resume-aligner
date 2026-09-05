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

/** Deep-link to the learning roadmap, focused on one skill. */
export function learningLinkForSkill(skill: string): string {
    return `/learning?skill=${encodeURIComponent(skill)}`;
}

/** Deep-link to the notes planner with the composer pre-filled (e.g. from a gap). */
export function noteComposeLink(params: {
    title?: string;
    content?: string;
    category?: string;
    color?: string;
    target?: string;
}): string {
    const q = new URLSearchParams({ compose: "1" });
    if (params.title) q.set("title", params.title);
    if (params.content) q.set("content", params.content);
    if (params.category) q.set("category", params.category);
    if (params.color) q.set("color", params.color);
    if (params.target) q.set("target", params.target);
    return `/notes?${q.toString()}`;
}
