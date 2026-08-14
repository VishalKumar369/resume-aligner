"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useDropzone } from "react-dropzone";
import { useRouter } from "next/navigation";
import {
    Upload, FileText, CheckCircle, Loader2, Link as LinkIcon, Sparkles,
    ShieldCheck, Download, AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { resumeService, jdService, alignmentService, dashboardService, apiErrorMessage } from "@/services/api";
import { ExtractionReview } from "@/components/upload/ExtractionReview";
import { PriorityBadge } from "@/components/ui/States";

const steps = [
    { id: 1, title: "Upload Resume" },
    { id: 2, title: "Add Job Description" },
    { id: 3, title: "Review Alignment" },
    { id: 4, title: "Optimize Resume" },
    { id: 5, title: "View Analytics" },
];

export default function UploadPage() {
    const router = useRouter();
    const [currentStep, setCurrentStep] = useState(1);
    const [uploadedFile, setUploadedFile] = useState<File | null>(null);
    const [jdText, setJdText] = useState("");
    const [jdUrl, setJdUrl] = useState("");
    const [processing, setProcessing] = useState(false);
    const [resume, setResume] = useState<any>(null);
    const [jdId, setJdId] = useState<string | null>(null);
    const [alignment, setAlignment] = useState<any>(null);
    const [optimization, setOptimization] = useState<any>(null);
    const [summary, setSummary] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    const onDrop = useCallback((accepted: File[]) => {
        if (accepted[0]) {
            setUploadedFile(accepted[0]);
            setResume(null);
            setError(null);
        }
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            "application/pdf": [".pdf"],
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
        },
        maxFiles: 1,
        maxSize: 5 * 1024 * 1024,
    });

    const run = async (work: () => Promise<void>) => {
        setProcessing(true);
        setError(null);
        try {
            await work();
        } catch (err: any) {
            setError(apiErrorMessage(err));
        } finally {
            setProcessing(false);
        }
    };

    const parseResume = () =>
        run(async () => {
            const { data } = await resumeService.upload(uploadedFile!, uploadedFile!.name);
            setResume(data);
        });

    const advance = async () => {
        if (currentStep === 1) {
            if (!resume) return parseResume();
            setCurrentStep(2);
            return;
        }

        if (currentStep === 2) {
            if (!jdText.trim()) return;
            return run(async () => {
                const { data } = await jdService.upload({
                    raw_text: jdText,
                    title: "",
                    company_name: "",
                    url: jdUrl.trim() || undefined,
                });
                setJdId(data.id);
                const aligned = await alignmentService.generate(resume.id, data.id);
                setAlignment(aligned.data);
                setCurrentStep(3);
            });
        }

        if (currentStep === 3) {
            return run(async () => {
                const { data } = await resumeService.optimize(resume.id, jdId!);
                setOptimization(data);
                setCurrentStep(4);
            });
        }

        if (currentStep === 4) {
            return run(async () => {
                const { data } = await dashboardService.getSummary();
                setSummary(data);
                setCurrentStep(5);
            });
        }

        router.push("/dashboard");
    };

    const download = async (format: "docx" | "pdf") => {
        try {
            const response = await resumeService.download(optimization.version_id, format);
            const url = URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement("a");
            link.href = url;
            link.download = `${optimization.filename.replace(/\.docx$/, "")}.${format}`;
            link.click();
            URL.revokeObjectURL(url);
        } catch (err: any) {
            setError(apiErrorMessage(err, "Download failed"));
        }
    };

    const primaryLabel = () => {
        if (processing) return null;
        if (currentStep === 1) return resume ? "Continue" : "Upload & Parse";
        if (currentStep === 2) return "Analyze Alignment";
        if (currentStep === 3) return "Optimize Resume";
        if (currentStep === 4) return "View Analytics";
        return "Go to Dashboard";
    };

    const primaryDisabled =
        processing ||
        (currentStep === 1 && !uploadedFile) ||
        (currentStep === 2 && !jdText.trim());

    return (
        <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6 relative overflow-hidden">
            <div className="absolute -top-40 -left-40 w-[500px] h-[500px] rounded-full bg-primary/5 blur-[120px]" />
            <div className="max-w-2xl w-full">
                {/* Stepper */}
                <div className="flex items-center justify-between mb-10">
                    {steps.map((step, i) => (
                        <div key={step.id} className="flex items-center flex-1 last:flex-none">
                            <div className="flex flex-col items-center gap-1">
                                <div className={cn(
                                    "w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all duration-300",
                                    currentStep > step.id ? "bg-primary border-primary text-white" :
                                        currentStep === step.id ? "border-primary text-primary bg-primary/10" :
                                            "border-border text-muted bg-transparent"
                                )}>
                                    {currentStep > step.id ? <CheckCircle className="w-4 h-4" /> : step.id}
                                </div>
                                <span className={cn("text-xs whitespace-nowrap hidden sm:block", currentStep === step.id ? "text-white" : "text-muted")}>
                                    {step.title}
                                </span>
                            </div>
                            {i < steps.length - 1 && (
                                <div className={cn("h-px flex-1 mx-2 transition-colors", currentStep > step.id ? "bg-primary" : "bg-border")} />
                            )}
                        </div>
                    ))}
                </div>

                <AnimatePresence mode="wait">
                    <motion.div
                        key={currentStep}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.25 }}
                    >
                        {/* ---------------------------------------------- step 1 */}
                        {currentStep === 1 && (
                            <div className="card-elevated rounded-2xl p-8">
                                <h2 className="text-2xl font-bold mb-2">Upload your resume</h2>
                                <p className="text-muted-foreground text-sm mb-6">
                                    We&apos;ll parse it and show you exactly what we extracted before going further.
                                </p>

                                {!resume && (
                                    <div
                                        {...getRootProps()}
                                        className={cn(
                                            "border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-200",
                                            isDragActive ? "border-primary bg-primary/5" :
                                                uploadedFile ? "border-success bg-success/5" : "border-border hover:border-primary/50 hover:bg-surface/50"
                                        )}
                                    >
                                        <input {...getInputProps()} />
                                        {uploadedFile ? (
                                            <div className="flex flex-col items-center gap-3">
                                                <div className="w-14 h-14 rounded-2xl bg-success/10 flex items-center justify-center">
                                                    <FileText className="w-7 h-7 text-success" />
                                                </div>
                                                <div>
                                                    <p className="font-medium text-success">{uploadedFile.name}</p>
                                                    <p className="text-xs text-muted mt-1">
                                                        {(uploadedFile.size / 1024).toFixed(0)} KB · Ready to parse
                                                    </p>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="flex flex-col items-center gap-3">
                                                <div className="w-14 h-14 rounded-2xl bg-surface-2 flex items-center justify-center">
                                                    <Upload className="w-7 h-7 text-muted" />
                                                </div>
                                                <div>
                                                    <p className="font-medium">{isDragActive ? "Drop it here!" : "Drag & drop your resume"}</p>
                                                    <p className="text-sm text-muted mt-1">PDF or DOCX · max 5MB</p>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {resume && (
                                    <ExtractionReview
                                        resume={resume}
                                        onReplace={() => { setResume(null); setUploadedFile(null); }}
                                    />
                                )}
                            </div>
                        )}

                        {/* ---------------------------------------------- step 2 */}
                        {currentStep === 2 && (
                            <div className="card-elevated rounded-2xl p-8">
                                <h2 className="text-2xl font-bold mb-2">Add the job description</h2>
                                <p className="text-muted-foreground text-sm mb-6">
                                    Paste the full posting. We read the requirements, responsibilities, and seniority from it.
                                </p>
                                <div className="space-y-4">
                                    <textarea
                                        rows={11}
                                        className="input-field resize-none font-mono text-xs"
                                        placeholder={"Senior Backend Engineer\nAcme Technologies - Bengaluru (Hybrid)\n\nRequirements\n- 3+ years building backend services\n- Strong Python and FastAPI\n\nNice to have\n- Kafka\n\nResponsibilities\n- Design and own backend services end to end"}
                                        value={jdText}
                                        onChange={(e) => setJdText(e.target.value)}
                                    />
                                    <div className="flex items-center gap-2 input-field text-sm text-muted">
                                        <LinkIcon className="w-4 h-4 flex-shrink-0" />
                                        <input
                                            className="flex-1 bg-transparent outline-none"
                                            placeholder="Link to the posting (optional — saved for reference, not fetched)"
                                            value={jdUrl}
                                            onChange={(e) => setJdUrl(e.target.value)}
                                        />
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* ---------------------------------------------- step 3 */}
                        {currentStep === 3 && alignment && (
                            <div className="card-elevated rounded-2xl p-8 space-y-4">
                                <h2 className="text-2xl font-bold">Alignment</h2>

                                {alignment.extraction_health && !alignment.extraction_health.resume_ok && (
                                    <div className="bg-error/5 border border-error/20 rounded-xl p-3 flex gap-2.5">
                                        <AlertTriangle className="w-4 h-4 text-error flex-shrink-0 mt-0.5" />
                                        <p className="text-xs text-muted">
                                            Your resume didn&apos;t extract cleanly, so this score reflects a parsing
                                            problem rather than a poor match.
                                        </p>
                                    </div>
                                )}

                                <div className="grid grid-cols-2 gap-4">
                                    {[
                                        { label: "JD Alignment", value: alignment.alignment_score },
                                        { label: "ATS Score", value: alignment.ats_score },
                                    ].map((s) => (
                                        <div key={s.label} className="bg-surface-2 rounded-xl p-4 border border-border/50">
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-sm font-medium">{s.label}</span>
                                                <span className="text-sm font-bold text-primary">{Math.round(s.value)}%</span>
                                            </div>
                                            <div className="h-2 bg-border rounded-full overflow-hidden">
                                                <motion.div initial={{ width: 0 }} animate={{ width: `${Math.round(s.value)}%` }}
                                                    transition={{ duration: 0.8 }} className="h-full bg-primary rounded-full" />
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                {Object.keys(alignment.breakdown || {}).length > 0 && (
                                    <div className="bg-surface-2 rounded-xl p-4 border border-border/50 space-y-2">
                                        <p className="text-xs font-medium text-muted mb-1">How that score was reached</p>
                                        {Object.entries(alignment.breakdown).map(([name, value]: any) => (
                                            <div key={name} className="flex items-center gap-3 text-xs">
                                                <span className="w-40 text-muted capitalize">{name.replace(/_/g, " ")}</span>
                                                <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
                                                    <div className="h-full bg-primary/60 rounded-full" style={{ width: `${Math.round(value)}%` }} />
                                                </div>
                                                <span className="w-10 text-right">{Math.round(value)}%</span>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                <p className="text-sm text-muted">{alignment.feedback}</p>

                                {alignment.matched_skills?.length > 0 && (
                                    <div>
                                        <p className="text-xs font-medium text-success mb-2">Matched</p>
                                        <div className="flex flex-wrap gap-2">
                                            {alignment.matched_skills.map((s: string) => (
                                                <span key={s} className="px-2.5 py-1 bg-success/10 text-success border border-success/20 rounded-lg text-xs">{s}</span>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {alignment.partial_skills?.length > 0 && (
                                    <div>
                                        <p className="text-xs font-medium text-warning mb-2">Partially covered</p>
                                        <div className="flex flex-wrap gap-2">
                                            {alignment.partial_skills.map((p: any) => (
                                                <span key={p.skill} className="px-2.5 py-1 bg-warning/10 text-warning border border-warning/20 rounded-lg text-xs">
                                                    {p.skill} — you have {p.covered_by}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {alignment.missing_skills?.length > 0 && (
                                    <div>
                                        <p className="text-xs font-medium text-error mb-2">Missing</p>
                                        <div className="flex flex-wrap gap-2">
                                            {alignment.missing_skills.map((m: any) => (
                                                <span key={m.skill} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-error/10 text-error border border-error/20 rounded-lg text-xs">
                                                    {m.skill} <PriorityBadge priority={m.priority} />
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* ---------------------------------------------- step 4 */}
                        {currentStep === 4 && optimization && (
                            <div className="card-elevated rounded-2xl p-8 space-y-4">
                                <div className="flex items-start justify-between">
                                    <div>
                                        <h2 className="text-2xl font-bold">Resume optimized</h2>
                                        <p className="text-sm text-muted mt-1">{optimization.label}</p>
                                    </div>
                                    <Sparkles className="w-6 h-6 text-primary" />
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    {[
                                        { label: "ATS Score", before: optimization.baseline_ats_score, after: optimization.ats_score, delta: optimization.ats_delta },
                                        { label: "JD Alignment", before: optimization.baseline_alignment_score, after: optimization.alignment_score, delta: optimization.alignment_delta },
                                    ].map((s) => (
                                        <div key={s.label} className="bg-surface-2 rounded-xl p-4 border border-border/50">
                                            <p className="text-xs text-muted mb-1">{s.label}</p>
                                            <p className="text-lg font-bold">
                                                {Math.round(s.before)}% <span className="text-muted">→</span> {Math.round(s.after)}%
                                            </p>
                                            <p className={cn("text-xs mt-1", s.delta > 0 ? "text-success" : "text-muted")}>
                                                {s.delta > 0 ? `+${s.delta.toFixed(1)} points` : "no change — already at ceiling here"}
                                            </p>
                                        </div>
                                    ))}
                                </div>

                                {optimization.note && (
                                    <div className="bg-warning/5 border border-warning/20 rounded-xl p-3 flex gap-2.5">
                                        <AlertTriangle className="w-4 h-4 text-warning flex-shrink-0 mt-0.5" />
                                        <p className="text-xs text-muted">{optimization.note}</p>
                                    </div>
                                )}

                                {optimization.from_cache && (
                                    <p className="text-[11px] text-muted">
                                        Reused a previous AI result for these bullets — no quota was spent.
                                    </p>
                                )}

                                {optimization.scoring_note && (
                                    <p className="text-[11px] text-muted">{optimization.scoring_note}</p>
                                )}

                                {optimization.changes?.length > 0 && (
                                    <div className="space-y-2">
                                        <p className="text-xs font-medium text-muted">What changed</p>
                                        {optimization.changes.map((change: any, i: number) => (
                                            <div key={i} className="bg-surface-2 rounded-xl p-3 border border-border/50">
                                                <p className="text-xs">{change.description}</p>
                                                {change.before && (
                                                    <div className="mt-2 space-y-1 text-[11px]">
                                                        <p className="text-error/80 line-through">{change.before}</p>
                                                        <p className="text-success">{change.after}</p>
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {optimization.blocked_rewrites?.length > 0 && (
                                    <div className="bg-primary/5 border border-primary/20 rounded-xl p-3">
                                        <p className="text-xs font-medium text-primary mb-2 inline-flex items-center gap-1.5">
                                            <ShieldCheck className="w-3.5 h-3.5" />
                                            {optimization.blocked_rewrites.length} rewrite(s) blocked
                                        </p>
                                        <p className="text-[11px] text-muted mb-2">
                                            These would have added details your resume doesn&apos;t support, so the originals were kept.
                                        </p>
                                        {optimization.blocked_rewrites.map((b: any, i: number) => (
                                            <p key={i} className="text-[11px] text-muted">· {b.reason}</p>
                                        ))}
                                    </div>
                                )}

                                {optimization.suggestions?.length > 0 && (
                                    <div className="space-y-1.5">
                                        <p className="text-xs font-medium text-muted">Suggestions</p>
                                        {optimization.suggestions.map((s: string, i: number) => (
                                            <p key={i} className="text-[11px] text-muted border-l-2 border-border pl-3">{s}</p>
                                        ))}
                                    </div>
                                )}

                                <div className="flex gap-3 pt-2">
                                    <button onClick={() => download("docx")} className="btn-ghost flex items-center gap-2 text-sm">
                                        <Download className="w-4 h-4" /> .docx
                                    </button>
                                    <button onClick={() => download("pdf")} className="btn-ghost flex items-center gap-2 text-sm">
                                        <Download className="w-4 h-4" /> PDF
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* ---------------------------------------------- step 5 */}
                        {currentStep === 5 && (
                            <div className="card-elevated rounded-2xl p-8 text-center">
                                <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-6">
                                    <CheckCircle className="w-10 h-10 text-primary" />
                                </div>
                                <h2 className="text-2xl font-bold mb-2">Analysis complete</h2>
                                <p className="text-muted-foreground text-sm mb-6">
                                    Your dashboard now reflects this run.
                                </p>
                                <div className="grid grid-cols-3 gap-4 mb-2">
                                    {[
                                        { label: "Career Readiness", value: `${Math.round(summary?.career_readiness_index || 0)}%`, color: "text-primary" },
                                        { label: "Interview Signal", value: summary?.interview_probability?.band || "—", color: "text-success" },
                                        { label: "Skill Gaps", value: `${summary?.top_skill_gaps?.length || 0}`, color: "text-warning" },
                                    ].map((s) => (
                                        <div key={s.label} className="bg-surface-2 rounded-xl p-4 border border-border/50">
                                            <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
                                            <div className="text-xs text-muted mt-1">{s.label}</div>
                                        </div>
                                    ))}
                                </div>
                                {summary?.interview_probability?.caveat && (
                                    <p className="text-[11px] text-muted mt-3">{summary.interview_probability.caveat}</p>
                                )}
                            </div>
                        )}
                    </motion.div>
                </AnimatePresence>

                <div className="flex items-center justify-between mt-6">
                    <button
                        onClick={() => setCurrentStep((s) => Math.max(1, s - 1))}
                        disabled={currentStep === 1 || processing}
                        className="btn-ghost disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                        Back
                    </button>
                    <motion.button
                        onClick={advance}
                        disabled={primaryDisabled}
                        whileHover={{ scale: primaryDisabled ? 1 : 1.02 }}
                        whileTap={{ scale: primaryDisabled ? 1 : 0.98 }}
                        className="btn-primary flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                        {processing ? <><Loader2 className="w-4 h-4 animate-spin" /> Working…</> : primaryLabel()}
                    </motion.button>
                </div>

                {error && (
                    <div className="mt-4 bg-error/5 border border-error/20 rounded-xl p-3">
                        <p className="text-sm text-error">{error}</p>
                    </div>
                )}
            </div>
        </div>
    );
}
