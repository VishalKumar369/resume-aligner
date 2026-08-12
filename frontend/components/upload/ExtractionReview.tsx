"use client";

import { AlertTriangle, Briefcase, GraduationCap, Mail, Phone, MapPin, RotateCcw } from "lucide-react";

/**
 * Shows what the parser actually got out of the uploaded file.
 *
 * Without this the user has no way to tell a good parse from a bad one until
 * three steps later, when a broken extraction shows up as a low match score.
 */
export function ExtractionReview({
    resume,
    onReplace,
}: {
    resume: any;
    onReplace: () => void;
}) {
    const data = resume?.structured_data || {};
    const meta = resume?.extraction_meta || {};
    const personal = data.personal_info || {};
    const skills = data.skills || {};
    const categories: Record<string, string[]> = skills.categories || {};
    const experience: any[] = data.experience || [];
    const education: any[] = data.education || [];
    const projects: any[] = data.projects || [];

    const warnings: string[] = meta.warnings || [];
    const confidence = typeof meta.confidence === "number" ? meta.confidence : null;
    const lowConfidence = confidence !== null && confidence < 0.6;

    return (
        <div className="mt-6 space-y-4">
            <div className="flex items-center justify-between">
                <div>
                    <p className="text-sm font-semibold text-success">Parsed successfully</p>
                    <p className="text-xs text-muted mt-0.5">
                        {[
                            meta.method && `via ${String(meta.method).replace(/_/g, " ")}`,
                            meta.page_count && `${meta.page_count} page${meta.page_count > 1 ? "s" : ""}`,
                            meta.word_count && `${meta.word_count} words`,
                            confidence !== null && `confidence ${confidence.toFixed(2)}`,
                        ]
                            .filter(Boolean)
                            .join(" · ")}
                    </p>
                </div>
                <button onClick={onReplace} className="btn-ghost text-xs inline-flex items-center gap-1.5">
                    <RotateCcw className="w-3.5 h-3.5" /> Replace file
                </button>
            </div>

            {(warnings.length > 0 || lowConfidence) && (
                <div className="bg-warning/5 border border-warning/20 rounded-xl p-3 flex gap-2.5">
                    <AlertTriangle className="w-4 h-4 text-warning flex-shrink-0 mt-0.5" />
                    <div className="text-xs text-warning-foreground">
                        <p className="font-medium text-warning mb-1">Extraction may be incomplete</p>
                        {lowConfidence && <p className="text-muted">Low confidence — check the details below carefully.</p>}
                        {warnings.map((w) => (
                            <p key={w} className="text-muted">{w.replace(/_/g, " ")}</p>
                        ))}
                    </div>
                </div>
            )}

            {resume?.duplicate_of_existing && (
                <div className="bg-primary/5 border border-primary/20 rounded-xl p-3 text-xs text-muted">
                    You&apos;ve uploaded this exact file before — reusing the existing analysis.
                </div>
            )}

            <div className="bg-surface-2 rounded-xl p-4 border border-border/50 space-y-4">
                <div>
                    <p className="font-semibold">{personal.name || <span className="text-error">Name not found</span>}</p>
                    {personal.title && <p className="text-xs text-muted mt-0.5">{personal.title}</p>}
                    <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-muted">
                        {personal.email && <span className="inline-flex items-center gap-1"><Mail className="w-3 h-3" />{personal.email}</span>}
                        {personal.phone && <span className="inline-flex items-center gap-1"><Phone className="w-3 h-3" />{personal.phone}</span>}
                        {personal.location && <span className="inline-flex items-center gap-1"><MapPin className="w-3 h-3" />{personal.location}</span>}
                    </div>
                </div>

                <div className="grid grid-cols-3 gap-3 text-center">
                    {[
                        { label: "Experience", value: `${data.total_experience_years ?? 0} yrs` },
                        { label: "Roles", value: experience.length },
                        { label: "Projects", value: projects.length },
                    ].map((stat) => (
                        <div key={stat.label} className="bg-background/40 rounded-lg py-2">
                            <div className="text-sm font-bold">{stat.value}</div>
                            <div className="text-[11px] text-muted">{stat.label}</div>
                        </div>
                    ))}
                </div>

                {Object.keys(categories).length > 0 && (
                    <div className="space-y-1.5">
                        {Object.entries(categories).map(([name, items]) => (
                            <div key={name} className="text-xs">
                                <span className="text-muted">{name}: </span>
                                <span>{items.join(", ")}</span>
                            </div>
                        ))}
                    </div>
                )}

                {experience.length > 0 && (
                    <div className="space-y-2">
                        {experience.slice(0, 3).map((entry, i) => (
                            <div key={i} className="flex gap-2 text-xs">
                                <Briefcase className="w-3.5 h-3.5 text-muted flex-shrink-0 mt-0.5" />
                                <div>
                                    <p className="font-medium">{entry.role || "Role not found"}</p>
                                    <p className="text-muted">
                                        {[entry.company, entry.start_date && `${entry.start_date} → ${entry.end_date || "?"}`]
                                            .filter(Boolean)
                                            .join(" · ")}
                                        {entry.is_internship && " · internship"}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {education.length > 0 && (
                    <div className="flex gap-2 text-xs">
                        <GraduationCap className="w-3.5 h-3.5 text-muted flex-shrink-0 mt-0.5" />
                        <div>
                            <p className="font-medium">{education[0].degree || "Degree not found"}</p>
                            <p className="text-muted">
                                {[education[0].institution, education[0].end_year].filter(Boolean).join(" · ")}
                            </p>
                        </div>
                    </div>
                )}
            </div>

            <p className="text-xs text-muted text-center">
                Something wrong? Replace the file before continuing — everything downstream builds on this.
            </p>
        </div>
    );
}
