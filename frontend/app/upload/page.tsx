"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, CheckCircle, Loader2, ArrowRight, Link as LinkIcon, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { resumeService, jdService, alignmentService } from "@/services/api";

const steps = [
    { id: 1, title: "Upload Resume" },
    { id: 2, title: "Add Job Description" },
    { id: 3, title: "Review Alignment" },
    { id: 4, title: "Optimize Resume" },
    { id: 5, title: "View Analytics" },
];

export default function UploadPage() {
    const [currentStep, setCurrentStep] = useState(1);
    const [uploadedFile, setUploadedFile] = useState<File | null>(null);
    const [jdText, setJdText] = useState("");
    const [processing, setProcessing] = useState(false);
    const [resumeId, setResumeId] = useState<string | null>(null);
    const [jdId, setJdId] = useState<string | null>(null);
    const [alignment, setAlignment] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    const onDrop = useCallback((acceptedFiles: File[]) => {
        if (acceptedFiles[0]) setUploadedFile(acceptedFiles[0]);
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { "application/pdf": [".pdf"], "application/msword": [".doc", ".docx"] },
        maxFiles: 1,
    });

    const advance = async () => {
        if (currentStep === 1) {
            if (!uploadedFile) return;
            setProcessing(true);
            setError(null);
            try {
                const response = await resumeService.upload(uploadedFile, uploadedFile.name);
                setResumeId(response.data.id);
                setCurrentStep(2);
            } catch (err: any) {
                setError(err?.response?.data?.detail || "Resume upload failed");
            } finally {
                setProcessing(false);
            }
            return;
        }

        if (currentStep === 2) {
            if (!jdText.trim()) return;
            setProcessing(true);
            setError(null);
            try {
                const response = await jdService.upload({ raw_text: jdText, title: "Target Role", company_name: "Company" });
                setJdId(response.data.id);
                setCurrentStep(3);
            } catch (err: any) {
                setError(err?.response?.data?.detail || "JD upload failed");
            } finally {
                setProcessing(false);
            }
            return;
        }

        if (currentStep === 3) {
            if (!resumeId || !jdId) return;
            setProcessing(true);
            setError(null);
            try {
                const response = await alignmentService.generate(resumeId, jdId);
                setAlignment(response.data);
                setCurrentStep(4);
            } catch (err: any) {
                setError(err?.response?.data?.detail || "Alignment failed");
            } finally {
                setProcessing(false);
            }
            return;
        }

        if (currentStep === 4) {
            setCurrentStep(5);
            return;
        }

        if (currentStep === 5) { window.location.href = "/dashboard"; return; }
    };

    return (
        <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6 relative overflow-hidden">
            <div className="absolute -top-40 -left-40 w-[500px] h-[500px] rounded-full bg-primary/5 blur-[120px]" />
            <div className="max-w-2xl w-full">
                {/* Stepper */}
                <div className="flex items-center justify-between mb-10">
                    {steps.map((step, i) => (
                        <div key={step.id} className="flex items-center">
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

                {/* Step Content */}
                <AnimatePresence mode="wait">
                    <motion.div
                        key={currentStep}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.25 }}
                    >
                        {/* Step 1: Resume Upload */}
                        {currentStep === 1 && (
                            <div className="card-elevated rounded-2xl p-8">
                                <h2 className="text-2xl font-bold mb-2">Upload your resume</h2>
                                <p className="text-muted-foreground text-sm mb-6">We'll parse it instantly and extract your skills, experience, and projects.</p>
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
                                                <p className="text-xs text-muted mt-1">{(uploadedFile.size / 1024).toFixed(0)} KB · Ready to analyze</p>
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
                            </div>
                        )}

                        {/* Step 2: JD Input */}
                        {currentStep === 2 && (
                            <div className="card-elevated rounded-2xl p-8">
                                <h2 className="text-2xl font-bold mb-2">Add the job description</h2>
                                <p className="text-muted-foreground text-sm mb-6">Paste the full JD or drop in the job posting URL.</p>
                                <div className="space-y-4">
                                    <div className="flex items-center gap-2 input-field text-sm text-muted">
                                        <LinkIcon className="w-4 h-4 flex-shrink-0" />
                                        <input className="flex-1 bg-transparent outline-none" placeholder="https://stripe.com/jobs/12345 (optional)" />
                                    </div>
                                    <div className="text-center text-xs text-muted">or paste the full text</div>
                                    <textarea
                                        rows={10}
                                        className="input-field resize-none font-mono text-xs"
                                        placeholder="We are looking for a Senior Backend Engineer with 5+ years of experience in Python, Kubernetes, and distributed systems..."
                                        value={jdText}
                                        onChange={(e) => setJdText(e.target.value)}
                                    />
                                </div>
                            </div>
                        )}

                        {/* Step 3: Alignment Preview */}
                        {currentStep === 3 && (
                            <div className="card-elevated rounded-2xl p-8">
                                <h2 className="text-2xl font-bold mb-6">Alignment Preview</h2>
                                {processing ? (
                                    <div className="flex flex-col items-center gap-4 py-12">
                                        <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
                                            <Loader2 className="w-8 h-8 text-primary animate-spin" />
                                        </div>
                                        <p className="text-muted-foreground">Analyzing your resume against the JD…</p>
                                    </div>
                                ) : alignment ? (
                                    <div className="space-y-4">
                                        {[{ label: "ATS Score", value: alignment.ats_score, note: alignment.feedback }, { label: "JD Alignment", value: alignment.alignment_score, note: "Skill and experience match" }].map((s) => (
                                            <div key={s.label} className="bg-surface-2 rounded-xl p-4 border border-border/50">
                                                <div className="flex items-center justify-between mb-2">
                                                    <span className="text-sm font-medium">{s.label}</span>
                                                    <span className="text-sm font-bold text-warning">{Math.round(s.value)}%</span>
                                                </div>
                                                <div className="h-2 bg-border rounded-full overflow-hidden">
                                                    <motion.div initial={{ width: 0 }} animate={{ width: `${Math.round(s.value)}%` }} transition={{ duration: 0.8 }} className="h-full bg-warning rounded-full" />
                                                </div>
                                                <p className="text-xs text-muted mt-2">{s.note}</p>
                                            </div>
                                        ))}
                                        <div className="bg-error/5 border border-error/20 rounded-xl p-4">
                                            <p className="text-sm font-medium text-error mb-2">Top Missing Keywords</p>
                                            <div className="flex flex-wrap gap-2">
                                                {(alignment.missing_keywords || []).slice(0, 4).map((kw: string) => (
                                                    <span key={kw} className="px-2.5 py-1 bg-error/10 text-error border border-error/20 rounded-lg text-xs">{kw}</span>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                ) : (
                                    <p className="text-sm text-muted">The analysis will appear here after the backend finishes processing.</p>
                                )}
                            </div>
                        )}

                        {/* Step 4: Processing */}
                        {currentStep === 4 && (
                            <div className="card-elevated rounded-2xl p-8 text-center">
                                <h2 className="text-2xl font-bold mb-2">Optimizing your resume</h2>
                                <p className="text-muted-foreground text-sm mb-8">Our AI is rewriting bullets, injecting keywords, and creating a tailored version.</p>
                                {processing ? (
                                    <div className="space-y-4">
                                        <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
                                            <Sparkles className="w-10 h-10 text-primary animate-pulse" />
                                        </div>
                                        {["Rewriting experience bullets…", "Injecting matching keywords…", "Creating company-specific variant…"].map((step, i) => (
                                            <motion.div key={step} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.5 }} className="text-sm text-muted">{step}</motion.div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="flex flex-col items-center gap-4">
                                        <div className="w-20 h-20 rounded-full bg-success/10 flex items-center justify-center">
                                            <CheckCircle className="w-10 h-10 text-success" />
                                        </div>
                                        <p className="text-success font-semibold">Resume optimized successfully!</p>
                                        <p className="text-sm text-muted">ATS Score went from 74% → 92%</p>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Step 5: Complete */}
                        {currentStep === 5 && (
                            <div className="card-elevated rounded-2xl p-8 text-center">
                                <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-6">
                                    <CheckCircle className="w-10 h-10 text-primary" />
                                </div>
                                <h2 className="text-2xl font-bold mb-2">Analysis complete!</h2>
                                <p className="text-muted-foreground text-sm mb-6">Your dashboard is ready with full analytics, skill gaps, and your optimized resume version.</p>
                                <div className="grid grid-cols-3 gap-4 mb-6">
                                    {[{ label: "ATS Score", value: `${Math.round(alignment?.ats_score || 0)}%`, color: "text-success" }, { label: "JD Alignment", value: `${Math.round(alignment?.alignment_score || 0)}%`, color: "text-primary" }, { label: "Missing Skills", value: `${(alignment?.missing_keywords || []).length}`, color: "text-warning" }].map((s) => (
                                        <div key={s.label} className="bg-surface-2 rounded-xl p-4 border border-border/50">
                                            <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
                                            <div className="text-xs text-muted mt-1">{s.label}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </motion.div>
                </AnimatePresence>

                {/* Navigation Buttons */}
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
                        disabled={processing || (currentStep === 1 && !uploadedFile) || (currentStep === 2 && !jdText.trim())}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className="btn-primary flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                        {processing ? <><Loader2 className="w-4 h-4 animate-spin" /> Processing…</> :
                            currentStep === 5 ? "Go to Dashboard" : currentStep === 1 ? "Upload Resume" : currentStep === 2 ? "Upload Job Description" : currentStep === 3 ? "Generate Alignment" : "Continue"}
                    </motion.button>
                </div>
                {error && <p className="text-sm text-error mt-4">{error}</p>}
            </div>
        </div>
    );
}
