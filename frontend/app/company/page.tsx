"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { Building2, ArrowRight, Briefcase, AlertTriangle, Clock } from "lucide-react";
import { EmptyState, ErrorState, ScorePill, Skeleton } from "@/components/ui/States";
import { useApi } from "@/hooks/useApi";
import { companyService } from "@/services/api";

interface CompanyCard {
    company_id: string;
    company: string;
    named?: boolean;
    jd_id?: string | null;
    resume_id?: string | null;
    alignment_id?: string | null;
    jd_count: number;
    roles: string[];
    demanded_skills: string[];
    your_best_alignment: number | null;
    your_average_alignment: number | null;
    gap_count: number;
    last_activity: string | null;
}

/** Named companies open their aggregate page; a nameless posting opens its
 * analysis directly (there is no company to aggregate). */
function cardHref(c: CompanyCard): string {
    if (c.named !== false) return `/company/${c.company_id}`;
    const params = new URLSearchParams({ jd: c.jd_id || c.company_id });
    if (c.resume_id) params.set("resume", c.resume_id);
    if (c.alignment_id) params.set("alignment", c.alignment_id);
    return `/company/${c.jd_id || c.company_id}?${params.toString()}`;
}

export default function CompanyIndexPage() {
    const { data: companies, loading, error, reload } = useApi<CompanyCard[]>(
        () => companyService.getAll()
    );

    if (loading) {
        return (
            <div className="max-w-6xl mx-auto space-y-6">
                <Skeleton className="h-8 w-64" />
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-52 rounded-2xl" />)}
                </div>
            </div>
        );
    }

    if (error) return <div className="max-w-6xl mx-auto"><ErrorState message={error} onRetry={reload} /></div>;

    if (!companies?.length) {
        return (
            <div className="max-w-3xl mx-auto pt-10">
                <EmptyState
                    title="No companies yet"
                    description="Company intelligence is built from the job descriptions you analyze. Add a posting with a company name and it'll show up here with how you match."
                    actionLabel="Analyze a job description"
                />
            </div>
        );
    }

    return (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-7xl mx-auto space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-foreground">Company Intelligence</h1>
                <p className="text-sm text-muted mt-1">
                    {companies.length} compan{companies.length === 1 ? "y" : "ies"} from your analyzed postings
                </p>
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {companies.map((c, i) => (
                    <motion.div
                        key={c.company_id}
                        initial={{ opacity: 0, y: 16 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: Math.min(i * 0.04, 0.3) }}
                    >
                        <Link
                            href={cardHref(c)}
                            className="group block h-full card-elevated rounded-2xl p-5 hover:border-primary/40 transition-colors"
                        >
                            <div className="flex items-start justify-between gap-3 mb-4">
                                <div className="flex items-center gap-3 min-w-0">
                                    <div className="w-11 h-11 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                                        <Building2 className="w-5 h-5 text-primary" />
                                    </div>
                                    <div className="min-w-0">
                                        <p className="font-semibold text-foreground truncate">{c.company}</p>
                                        <p className="text-xs text-muted mt-0.5 inline-flex items-center gap-1">
                                            <Briefcase className="w-3 h-3" />
                                            {c.named === false
                                                ? "Single posting"
                                                : `${c.jd_count} role${c.jd_count === 1 ? "" : "s"}`}
                                        </p>
                                    </div>
                                </div>
                                {c.your_best_alignment !== null && <ScorePill score={c.your_best_alignment} />}
                            </div>

                            {c.roles.length > 0 && (
                                <p className="text-xs text-muted mb-3 line-clamp-2">
                                    {c.roles.slice(0, 3).join(" · ")}
                                    {c.roles.length > 3 && ` +${c.roles.length - 3} more`}
                                </p>
                            )}

                            {c.demanded_skills.length > 0 && (
                                <div className="flex flex-wrap gap-1.5 mb-4">
                                    {c.demanded_skills.slice(0, 4).map((skill) => (
                                        <span key={skill} className="px-2 py-0.5 bg-surface-2 border border-border rounded-md text-[11px] text-muted">
                                            {skill}
                                        </span>
                                    ))}
                                </div>
                            )}

                            <div className="flex items-center justify-between pt-3 border-t border-border/50 text-xs">
                                <div className="flex items-center gap-3 text-muted">
                                    {c.gap_count > 0 && (
                                        <span className="inline-flex items-center gap-1">
                                            <AlertTriangle className="w-3 h-3 text-warning" />
                                            {c.gap_count} gap{c.gap_count === 1 ? "" : "s"}
                                        </span>
                                    )}
                                    {c.last_activity && (
                                        <span className="inline-flex items-center gap-1">
                                            <Clock className="w-3 h-3" />
                                            {new Date(c.last_activity).toLocaleDateString()}
                                        </span>
                                    )}
                                </div>
                                <span className="inline-flex items-center gap-1 text-primary opacity-0 group-hover:opacity-100 transition-opacity">
                                    View <ArrowRight className="w-3 h-3" />
                                </span>
                            </div>
                        </Link>
                    </motion.div>
                ))}
            </div>
        </motion.div>
    );
}
