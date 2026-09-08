"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useDropzone, type FileRejection } from "react-dropzone";
import { useRouter } from "next/navigation";
import {
    Upload, FileText, CheckCircle, Loader2, Link as LinkIcon, Sparkles,
    ShieldCheck, Download, AlertTriangle, FileStack, Building2, Briefcase, RotateCcw,
    LayoutTemplate, ListChecks, Check, ArrowUp, ArrowDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { resumeService, jdService, alignmentService, dashboardService, apiErrorMessage } from "@/services/api";
import { ExtractionReview } from "@/components/upload/ExtractionReview";
import { PriorityBadge } from "@/components/ui/States";

const steps = [
    { id: 1, title: "Resume" },
    { id: 2, title: "Job Description" },
    { id: 3, title: "Preview" },
    { id: 4, title: "Optimize" },
    { id: 5, title: "Analytics" },
];

// The reorderable/hideable body sections, and how to tell one is present.
const SECTION_DEFS: { key: string; label: string; has: (d: any) => boolean }[] = [
    { key: "summary", label: "Summary", has: (d) => !!(d.summary || "").trim?.() },
    { key: "skills", label: "Skills", has: (d) => !!(Object.keys(d.skills?.categories || {}).length || d.skills?.hard_skills?.length) },
    { key: "experience", label: "Experience", has: (d) => !!d.experience?.length },
    { key: "projects", label: "Projects", has: (d) => !!d.projects?.length },
    { key: "education", label: "Education", has: (d) => !!d.education?.length },
    { key: "certifications", label: "Certifications", has: (d) => !!d.certifications?.length },
    { key: "achievements", label: "Achievements", has: (d) => !!d.achievements?.length },
];

export default function UploadPage() {
    const router = useRouter();
    const [currentStep, setCurrentStep] = useState(1);
    const [uploadedFile, setUploadedFile] = useState<File | null>(null);
    const [jdText, setJdText] = useState("");
    const [jdUrl, setJdUrl] = useState("");
    // The parsed JD, plus the role/company the user can verify before analyzing.
    const [jd, setJd] = useState<any>(null);
    const [jdRole, setJdRole] = useState("");
    const [jdCompany, setJdCompany] = useState("");
    // Most resumes should stay to one page, so single is the default. The user
    // can switch to multi when they have enough relevant content to justify it.
    const [pagePreference, setPagePreference] = useState<"single" | "multi">("single");
    // Layout & section controls for step 3. "original" keeps the uploaded .docx.
    const [layout, setLayout] = useState<string>("original");
    const [sections, setSections] = useState<{ key: string; label: string; on: boolean }[]>([]);
    const [processing, setProcessing] = useState(false);
    const [resume, setResume] = useState<any>(null);
    const [jdId, setJdId] = useState<string | null>(null);
    const [alignment, setAlignment] = useState<any>(null);
    const [optimization, setOptimization] = useState<any>(null);
    const [summary, setSummary] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);
    // Lets the "Paste JD" prompt jump focus straight to the paste box below it.
    const jdTextareaRef = useRef<HTMLTextAreaElement>(null);

    // Only a .docx upload can be preserved as-is; a PDF must be rebuilt.
    const isDocx = (resume?.filename || uploadedFile?.name || "").toLowerCase().endsWith(".docx");

    // Seed the section list (present sections only) and the default layout once
    // the resume is parsed.
    useEffect(() => {
        if (!resume) return;
        const data = resume.structured_data || {};
        setSections(
            SECTION_DEFS.filter((s) => s.has(data)).map((s) => ({ key: s.key, label: s.label, on: true }))
        );
        setLayout(isDocx ? "original" : "professional");
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [resume]);

    const moveSection = (index: number, delta: number) =>
        setSections((prev) => {
            const target = index + delta;
            if (target < 0 || target >= prev.length) return prev;
            const next = [...prev];
            [next[index], next[target]] = [next[target], next[index]];
            return next;
        });

    const toggleSection = (index: number) =>
        setSections((prev) => prev.map((s, i) => (i === index ? { ...s, on: !s.on } : s)));

    const layoutOptions = [
        ...(isDocx
            ? [{ id: "original", name: "Keep my format", desc: "Your design — colours, fonts, and links kept; only wording is optimized." }]
            : []),
        { id: "professional", name: "Professional", desc: "Clean, ruled headings, right-aligned dates." },
        { id: "modern", name: "Modern", desc: "Navy accent on the name and headings." },
        { id: "compact", name: "Compact", desc: "Tighter spacing to fit more in." },
        { id: "minimal", name: "Minimal", desc: "Airy and understated, no rules." },
    ];

    // react-dropzone hands rejected files to the second argument instead of
    // onDrop's accepted list, so an image or a .txt would otherwise vanish
    // silently. Turn the rejection code into a message that names the fix.
    const onDrop = useCallback((accepted: File[], rejections: FileRejection[]) => {
        if (accepted[0]) {
            setUploadedFile(accepted[0]);
            setResume(null);
            setError(null);
            return;
        }

        const rejection = rejections[0];
        if (!rejection) return;

        const code = rejection.errors[0]?.code;
        if (code === "file-invalid-type") {
            const ext = rejection.file.name.split(".").pop()?.toLowerCase();
            setError(
                `We can't read ${ext ? `.${ext}` : "that"} files. Upload your resume as a PDF or DOCX — images and scanned files can't be parsed.`
            );
        } else if (code === "file-too-large") {
            setError(
                `"${rejection.file.name}" is over the 5MB limit. Try compressing it or exporting a fresh PDF.`
            );
        } else if (code === "too-many-files") {
            setError("Please upload one resume at a time.");
        } else {
            setError(rejection.errors[0]?.message || "That file couldn't be accepted.");
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
            // First click parses the posting and shows the role/company to verify.
            if (!jd) {
                if (!jdText.trim()) return;
                return run(async () => {
                    const { data } = await jdService.upload({
                        raw_text: jdText,
                        title: "",
                        company_name: "",
                        url: jdUrl.trim() || undefined,
                    });
                    setJd(data);
                    setJdId(data.id);
                    // A placeholder title means the parser found nothing usable.
                    setJdRole(data.title && data.title !== "Untitled role" ? data.title : "");
                    setJdCompany(data.company_name || "");
                });
            }

            // Second click saves any corrections, then runs the alignment.
            return run(async () => {
                const patch: { title?: string; company_name?: string } = {};
                if (jdRole.trim() && jdRole.trim() !== jd.title) patch.title = jdRole.trim();
                if (jdCompany.trim() !== (jd.company_name || "")) patch.company_name = jdCompany.trim();
                if (Object.keys(patch).length) await jdService.update(jd.id, patch);

                const aligned = await alignmentService.generate(resume.id, jd.id);
                setAlignment(aligned.data);
                setCurrentStep(3);
            });
        }

        if (currentStep === 3) {
            return run(async () => {
                // Section order/exclusion only applies when rebuilding (not "original").
                const enabledSections =
                    layout === "original" ? undefined : sections.filter((s) => s.on).map((s) => s.key);
                const { data } = await resumeService.optimize(resume.id, jdId!, {
                    pagePreference,
                    layout,
                    sections: enabledSections,
                });
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
        if (currentStep === 2) return jd ? "Analyze Alignment" : "Parse Job Description";
        if (currentStep === 3) return "Optimize Resume";
        if (currentStep === 4) return "View Analytics";
        return "Go to Dashboard";
    };

    const primaryDisabled =
        processing ||
        (currentStep === 1 && !uploadedFile) ||
        (currentStep === 2 && !jd && !jdText.trim());

    return (
        <div className="max-w-8xl mx-auto p-4 sm:p-6">
            <div className="mb-6">
                <h1 className="text-2xl font-bold">New analysis</h1>
                <p className="text-sm text-muted mt-1">
                    Upload your resume and the job description to begin alignment analysis.
                </p>
            </div>

            {/* Stepper */}
            <div className="flex items-center justify-between mb-8">
                    {steps.map((step, i) => (
                        <div key={step.id} className="flex items-center flex-1 last:flex-none">
                            <div className="flex flex-col items-center gap-1">
                                <div className={cn(
                                    "w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all duration-300",
                                    currentStep > step.id ? "bg-primary border-primary text-primary-foreground" :
                                        currentStep === step.id ? "border-primary text-primary bg-primary/10" :
                                            "border-border text-muted bg-transparent"
                                )}>
                                    {currentStep > step.id ? <CheckCircle className="w-4 h-4" /> : step.id}
                                </div>
                                <span className={cn("text-xs whitespace-nowrap hidden sm:block", currentStep === step.id ? "text-foreground" : "text-muted")}>
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
                            <div className="card-elevated rounded-2xl p-6 sm:p-8">
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
                        {currentStep === 2 && (!jd ? (
                            <div className="space-y-6">
                                <div>
                                    <h2 className="text-lg font-semibold">Add the job description</h2>
                                    <p className="text-muted-foreground text-sm mt-1">
                                        Paste the full posting. We read the role, company, requirements, and responsibilities from it.
                                    </p>
                                </div>

                                <div className="grid md:grid-cols-2 gap-6">
                                    {/* The resume already parsed in step 1. */}
                                    <div className="flex flex-col">
                                        <p className="text-sm font-medium text-muted mb-2">Resume uploaded</p>
                                        <div className="card-elevated rounded-2xl p-4 flex flex-1 items-center gap-3">
                                            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                                                <FileText className="w-5 h-5 text-primary" />
                                            </div>
                                            <div className="min-w-0">
                                                <p className="font-medium truncate">{resume?.filename || uploadedFile?.name || "Your resume"}</p>
                                                <p className="text-xs text-success mt-0.5 inline-flex items-center gap-1">
                                                    <CheckCircle className="w-3 h-3" /> Uploaded
                                                    {uploadedFile ? ` · ${(uploadedFile.size / 1024).toFixed(0)} KB` : ""}
                                                </p>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Prompt — the working paste box sits directly below. */}
                                    <div className="flex flex-col">
                                        <p className="text-sm font-medium text-muted mb-2">Job description</p>
                                        <button
                                            type="button"
                                            onClick={() => jdTextareaRef.current?.focus()}
                                            className="w-full flex-1 flex flex-col items-center justify-center card-elevated rounded-2xl border-2 border-dashed border-border p-8 text-center hover:border-primary/50 transition-colors"
                                        >
                                            <div className="w-12 h-12 rounded-xl bg-surface-2 flex items-center justify-center mx-auto mb-3">
                                                <Upload className="w-6 h-6 text-muted" />
                                            </div>
                                            <p className="font-medium">Paste the posting below</p>
                                            <p className="text-xs text-muted mt-1">We extract skills, requirements &amp; keywords automatically</p>
                                            <span className="btn-primary inline-flex items-center gap-2 text-sm mt-4">
                                                <LinkIcon className="w-4 h-4" /> Paste JD
                                            </span>
                                        </button>
                                    </div>
                                </div>

                                <div className="card-elevated rounded-2xl p-5">
                                    <p className="text-sm font-medium mb-3">Or paste job description text</p>
                                    <textarea
                                        ref={jdTextareaRef}
                                        rows={9}
                                        className="input-field resize-none font-mono text-xs"
                                        placeholder={"Paste the full job description here — we'll extract skills, requirements, and keywords automatically..."}
                                        value={jdText}
                                        onChange={(e) => setJdText(e.target.value)}
                                    />
                                    <div className="flex items-center gap-2 input-field text-sm text-muted mt-3">
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
                        ) : (
                            <div className="card-elevated rounded-2xl p-6 sm:p-8">
                                <h2 className="text-lg font-semibold mb-2">Verify the role &amp; company</h2>
                                <p className="text-muted-foreground text-sm mb-6">
                                    We pulled these from the posting. Fix anything the parser got wrong — they label this analysis across your dashboard and company intelligence.
                                </p>

                                <div className="space-y-4">
                                        <div className="bg-surface-2 rounded-xl p-4 border border-border/50 space-y-4">
                                            <div className="flex items-center justify-between">
                                                <p className="text-sm font-semibold text-success">Parsed — please verify</p>
                                                <button
                                                    onClick={() => { setJd(null); setJdId(null); }}
                                                    className="btn-ghost text-xs inline-flex items-center gap-1.5"
                                                >
                                                    <RotateCcw className="w-3.5 h-3.5" /> Re-paste
                                                </button>
                                            </div>

                                            <div className="grid sm:grid-cols-2 gap-3">
                                                <label className="block">
                                                    <span className="text-xs text-muted mb-1 flex items-center gap-1">
                                                        <Briefcase className="w-3 h-3" /> Role / title
                                                    </span>
                                                    <input
                                                        className="input-field text-sm"
                                                        placeholder="e.g. Senior Backend Engineer"
                                                        value={jdRole}
                                                        onChange={(e) => setJdRole(e.target.value)}
                                                    />
                                                </label>
                                                <label className="block">
                                                    <span className="text-xs text-muted mb-1 flex items-center gap-1">
                                                        <Building2 className="w-3 h-3" /> Company
                                                    </span>
                                                    <input
                                                        className="input-field text-sm"
                                                        placeholder="e.g. Acme Technologies"
                                                        value={jdCompany}
                                                        onChange={(e) => setJdCompany(e.target.value)}
                                                    />
                                                </label>
                                            </div>

                                            {(!jdRole.trim() || !jdCompany.trim()) && (
                                                <p className="text-xs text-warning flex items-start gap-1.5">
                                                    <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                                                    <span>
                                                        The parser couldn&apos;t find{" "}
                                                        {[!jdRole.trim() && "a role", !jdCompany.trim() && "a company"].filter(Boolean).join(" or ")}.
                                                        {" "}Add {!jdRole.trim() && !jdCompany.trim() ? "them" : "it"} so this analysis isn&apos;t
                                                        labelled &quot;Untitled&quot;.
                                                    </span>
                                                </p>
                                            )}

                                            <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted pt-2 border-t border-border/40">
                                                {jd.structured_data?.seniority && <span className="capitalize">{jd.structured_data.seniority}</span>}
                                                {jd.structured_data?.location && <span>{jd.structured_data.location}</span>}
                                                {jd.structured_data?.work_mode && <span className="capitalize">{jd.structured_data.work_mode}</span>}
                                                <span>{jd.structured_data?.requirements?.mandatory_skills?.length || 0} required skills</span>
                                                <span>{jd.structured_data?.responsibilities?.length || 0} responsibilities</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )
                        )}

                        {/* ---------------------------------------------- step 3 */}
                        {currentStep === 3 && alignment && (
                            <div className="card-elevated rounded-2xl p-6 sm:p-8 space-y-4">
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

                                {/* Length preference — drives the optimizer's condensing. */}
                                <div className="pt-2 border-t border-border/50">
                                    <p className="text-xs font-medium text-muted mb-2 inline-flex items-center gap-1.5">
                                        <FileStack className="w-3.5 h-3.5" /> Optimized resume length
                                    </p>
                                    <div className="grid grid-cols-2 gap-3">
                                        {[
                                            {
                                                value: "single" as const,
                                                title: "Single page",
                                                detail: "Trims lower-impact bullets to fit one page. Keeps your skills and the most job-relevant content — ATS score is preserved.",
                                            },
                                            {
                                                value: "multi" as const,
                                                title: "Multiple pages",
                                                detail: "Keeps everything. Lets the resume run to two or more pages if the content needs it.",
                                            },
                                        ].map((option) => {
                                            const active = pagePreference === option.value;
                                            return (
                                                <button
                                                    key={option.value}
                                                    type="button"
                                                    onClick={() => setPagePreference(option.value)}
                                                    aria-pressed={active}
                                                    className={cn(
                                                        "text-left rounded-xl border p-3 transition-colors",
                                                        active
                                                            ? "border-primary bg-primary/10"
                                                            : "border-border bg-surface-2 hover:border-primary/40"
                                                    )}
                                                >
                                                    <span className={cn("text-sm font-semibold", active ? "text-primary" : "text-foreground")}>
                                                        {option.title}
                                                    </span>
                                                    <span className="block text-[11px] text-muted mt-1 leading-snug">
                                                        {option.detail}
                                                    </span>
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>

                                {/* Layout — keep the uploaded design or rebuild in a template. */}
                                <div className="pt-2 border-t border-border/50">
                                    <p className="text-xs font-medium text-muted mb-2 inline-flex items-center gap-1.5">
                                        <LayoutTemplate className="w-3.5 h-3.5" /> Resume layout
                                    </p>
                                    {!isDocx && (
                                        <p className="text-[11px] text-muted mb-2 leading-snug">
                                            Your upload is a PDF, so it&apos;s rebuilt in the template you pick.
                                            Upload a <span className="font-medium text-foreground">.docx</span> to keep your exact design.
                                        </p>
                                    )}
                                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                        {layoutOptions.map((option) => {
                                            const active = layout === option.id;
                                            return (
                                                <button
                                                    key={option.id}
                                                    type="button"
                                                    onClick={() => setLayout(option.id)}
                                                    aria-pressed={active}
                                                    className={cn(
                                                        "text-left rounded-xl border p-3 transition-colors",
                                                        active
                                                            ? "border-primary bg-primary/10"
                                                            : "border-border bg-surface-2 hover:border-primary/40"
                                                    )}
                                                >
                                                    <span className={cn("text-sm font-semibold", active ? "text-primary" : "text-foreground")}>
                                                        {option.name}
                                                    </span>
                                                    <span className="block text-[11px] text-muted mt-1 leading-snug">
                                                        {option.desc}
                                                    </span>
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>

                                {/* Sections — reorder / hide (only when rebuilding). */}
                                {layout !== "original" && sections.length > 0 && (
                                    <div className="pt-2 border-t border-border/50">
                                        <p className="text-xs font-medium text-muted mb-2 inline-flex items-center gap-1.5">
                                            <ListChecks className="w-3.5 h-3.5" /> Sections — reorder or hide
                                        </p>
                                        <div className="space-y-1.5">
                                            {sections.map((section, i) => (
                                                <div key={section.key} className="flex items-center gap-2 rounded-lg border border-border bg-surface-2 px-3 py-2">
                                                    <button
                                                        type="button"
                                                        onClick={() => toggleSection(i)}
                                                        aria-pressed={section.on}
                                                        aria-label={`${section.on ? "Hide" : "Show"} ${section.label}`}
                                                        className={cn(
                                                            "w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 transition-colors",
                                                            section.on ? "bg-primary border-primary text-primary-foreground" : "border-border text-transparent"
                                                        )}
                                                    >
                                                        <Check className="w-3 h-3" />
                                                    </button>
                                                    <span className={cn("text-sm flex-1", section.on ? "text-foreground" : "text-muted line-through")}>
                                                        {section.label}
                                                    </span>
                                                    <button
                                                        type="button"
                                                        onClick={() => moveSection(i, -1)}
                                                        disabled={i === 0}
                                                        aria-label={`Move ${section.label} up`}
                                                        className="p-1 rounded text-muted hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed"
                                                    >
                                                        <ArrowUp className="w-3.5 h-3.5" />
                                                    </button>
                                                    <button
                                                        type="button"
                                                        onClick={() => moveSection(i, 1)}
                                                        disabled={i === sections.length - 1}
                                                        aria-label={`Move ${section.label} down`}
                                                        className="p-1 rounded text-muted hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed"
                                                    >
                                                        <ArrowDown className="w-3.5 h-3.5" />
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* ---------------------------------------------- step 4 */}
                        {currentStep === 4 && optimization && (
                            <div className="card-elevated rounded-2xl p-6 sm:p-8 space-y-4">
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

                                {optimization.length_note && (
                                    <div className={cn(
                                        "border rounded-xl p-3 flex gap-2.5",
                                        optimization.single_page_fit === false
                                            ? "bg-warning/5 border-warning/20"
                                            : "bg-primary/5 border-primary/20"
                                    )}>
                                        <FileStack className={cn(
                                            "w-4 h-4 flex-shrink-0 mt-0.5",
                                            optimization.single_page_fit === false ? "text-warning" : "text-primary"
                                        )} />
                                        <p className="text-xs text-muted">{optimization.length_note}</p>
                                    </div>
                                )}

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
                            <div className="card-elevated rounded-2xl p-6 sm:p-8 text-center">
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
    );
}
