"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { User, Bell, Download, Loader2, Trash2, AlertTriangle } from "lucide-react";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/ui/Sidebar";
import { TopNavbar } from "@/components/ui/TopNavbar";
import { ErrorState, Skeleton } from "@/components/ui/States";
import { useApi } from "@/hooks/useApi";
import { userService, apiErrorMessage, type MeResponse } from "@/services/api";
import { useAuthStore } from "@/store/authStore";

export default function SettingsPage() {
    const router = useRouter();
    const { data, loading, error, reload } = useApi<MeResponse>(() => userService.getMe());

    return (
        <div className="flex h-screen bg-background overflow-hidden">
            <Sidebar />
            <div className="flex-1 flex flex-col overflow-hidden">
                <TopNavbar title="Settings" />
                <main className="flex-1 overflow-y-auto p-6">
                    <div className="max-w-2xl mx-auto space-y-6">
                        <div>
                            <h1 className="text-2xl font-bold">Settings</h1>
                            <p className="text-sm text-muted mt-1">Manage your account preferences</p>
                        </div>

                        {loading && <SettingsSkeleton />}
                        {error && !loading && <ErrorState message={error} onRetry={reload} />}
                        {data && !loading && (
                            <>
                                <ProfileSection profile={data.profile} />
                                <NotificationsSection notifications={data.notifications} />
                                <DataPrivacySection onDeleted={() => router.replace("/auth/login")} />
                            </>
                        )}
                    </div>
                </main>
            </div>
        </div>
    );
}

function SettingsSkeleton() {
    return (
        <div className="space-y-6">
            {[0, 1, 2].map((i) => (
                <div key={i} className="card-elevated rounded-2xl p-6 space-y-4">
                    <Skeleton className="h-6 w-40" />
                    <Skeleton className="h-10 w-full" />
                    <Skeleton className="h-10 w-full" />
                </div>
            ))}
        </div>
    );
}

function SectionCard({
    icon: Icon,
    title,
    children,
    delay = 0,
}: {
    icon: typeof User;
    title: string;
    children: React.ReactNode;
    delay?: number;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay }}
            className="card-elevated rounded-2xl p-6"
        >
            <div className="flex items-center gap-3 mb-5">
                <div className="p-2 bg-surface-2 rounded-lg">
                    <Icon className="w-4 h-4 text-muted" />
                </div>
                <h3 className="font-semibold">{title}</h3>
            </div>
            {children}
        </motion.div>
    );
}

// -------------------------------------------------------------------- profile

function ProfileSection({ profile }: { profile: MeResponse["profile"] }) {
    const updateUser = useAuthStore((s) => s.updateUser);
    const [fullName, setFullName] = useState(profile.full_name ?? "");
    const [targetRole, setTargetRole] = useState(profile.target_role ?? "");
    const [saving, setSaving] = useState(false);

    const dirty =
        fullName.trim() !== (profile.full_name ?? "").trim() ||
        targetRole.trim() !== (profile.target_role ?? "").trim();

    const handleSave = async () => {
        setSaving(true);
        try {
            const res = await userService.updateProfile({
                full_name: fullName.trim(),
                target_role: targetRole.trim(),
            });
            // Keep the navbar/greeting in sync with the saved name.
            updateUser({ name: res.data.full_name || profile.email, targetRole: res.data.target_role });
            toast.success("Profile updated");
        } catch (err) {
            toast.error(apiErrorMessage(err, "Could not update profile"));
        } finally {
            setSaving(false);
        }
    };

    return (
        <SectionCard icon={User} title="Profile" delay={0}>
            <div className="space-y-4">
                <div>
                    <label className="block text-xs font-medium text-muted mb-2">Full Name</label>
                    <input
                        type="text"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        placeholder="Your name"
                        className="input-field"
                    />
                </div>
                <div>
                    <label className="block text-xs font-medium text-muted mb-2">Email</label>
                    <input
                        type="email"
                        value={profile.email}
                        readOnly
                        disabled
                        className="input-field opacity-60 cursor-not-allowed"
                    />
                    <p className="text-[11px] text-muted mt-1.5">
                        Email is tied to your login and can't be changed here.
                    </p>
                </div>
                <div>
                    <label className="block text-xs font-medium text-muted mb-2">Target Role</label>
                    <input
                        type="text"
                        value={targetRole}
                        onChange={(e) => setTargetRole(e.target.value)}
                        placeholder="e.g. Senior Backend Engineer"
                        className="input-field"
                    />
                </div>
                <div className="flex justify-end pt-1">
                    <button
                        onClick={handleSave}
                        disabled={!dirty || saving}
                        className="btn-primary px-6 py-2 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                        Save Profile
                    </button>
                </div>
            </div>
        </SectionCard>
    );
}

// -------------------------------------------------------------- notifications

const NOTIFICATION_FIELDS: {
    key: keyof MeResponse["notifications"];
    label: string;
    hint: string;
}[] = [
    {
        key: "email_alerts_on_new_matches",
        label: "Email Alerts on New Matches",
        hint: "Get notified when a new resume-to-JD match is generated.",
    },
    {
        key: "weekly_career_readiness_report",
        label: "Weekly Career Readiness Report",
        hint: "A weekly summary of your readiness score and skill gaps.",
    },
];

function NotificationsSection({ notifications }: { notifications: MeResponse["notifications"] }) {
    const [state, setState] = useState(notifications);
    const [pending, setPending] = useState<keyof MeResponse["notifications"] | null>(null);

    const toggle = async (key: keyof MeResponse["notifications"]) => {
        const next = !state[key];
        setState((s) => ({ ...s, [key]: next })); // optimistic
        setPending(key);
        try {
            await userService.updateNotifications({ [key]: next });
        } catch (err) {
            setState((s) => ({ ...s, [key]: !next })); // revert on failure
            toast.error(apiErrorMessage(err, "Could not update notifications"));
        } finally {
            setPending(null);
        }
    };

    return (
        <SectionCard icon={Bell} title="Notifications" delay={0.08}>
            <div className="space-y-5">
                {NOTIFICATION_FIELDS.map((field) => (
                    <div key={field.key} className="flex items-start justify-between gap-4">
                        <div>
                            <p className="text-sm font-medium">{field.label}</p>
                            <p className="text-xs text-muted mt-0.5">{field.hint}</p>
                        </div>
                        <button
                            role="switch"
                            aria-checked={state[field.key]}
                            aria-label={field.label}
                            disabled={pending === field.key}
                            onClick={() => toggle(field.key)}
                            className={`w-11 h-6 rounded-full relative transition-colors flex-shrink-0 disabled:opacity-60 ${
                                state[field.key] ? "bg-primary" : "bg-surface-2"
                            }`}
                        >
                            <span
                                className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${
                                    state[field.key] ? "right-1" : "left-1"
                                }`}
                            />
                        </button>
                    </div>
                ))}
            </div>
        </SectionCard>
    );
}

// ------------------------------------------------------------- data & privacy

function DataPrivacySection({ onDeleted }: { onDeleted: () => void }) {
    const clearAuth = useAuthStore((s) => s.clearAuth);
    const [exporting, setExporting] = useState(false);
    const [showDelete, setShowDelete] = useState(false);

    const handleExport = async () => {
        setExporting(true);
        try {
            const res = await userService.exportData();
            const url = URL.createObjectURL(new Blob([res.data], { type: "application/json" }));
            const a = document.createElement("a");
            a.href = url;
            a.download = "resume-jd-aligner-export.json";
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
            toast.success("Your data export has downloaded");
        } catch (err) {
            toast.error(apiErrorMessage(err, "Could not export your data"));
        } finally {
            setExporting(false);
        }
    };

    return (
        <>
            <SectionCard icon={Download} title="Data & Privacy" delay={0.16}>
                <div className="flex flex-wrap gap-3">
                    <button
                        onClick={handleExport}
                        disabled={exporting}
                        className="btn-ghost border border-border rounded-xl text-sm px-4 py-2 flex items-center gap-2 disabled:opacity-50"
                    >
                        {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                        Export All Data
                    </button>
                    <button
                        onClick={() => setShowDelete(true)}
                        className="text-error hover:bg-error/10 border border-error/20 text-sm px-4 py-2 rounded-xl transition-colors flex items-center gap-2"
                    >
                        <Trash2 className="w-4 h-4" />
                        Delete Account
                    </button>
                </div>
            </SectionCard>

            {showDelete && (
                <DeleteAccountModal
                    onClose={() => setShowDelete(false)}
                    onConfirmed={() => {
                        clearAuth();
                        onDeleted();
                    }}
                />
            )}
        </>
    );
}

function DeleteAccountModal({
    onClose,
    onConfirmed,
}: {
    onClose: () => void;
    onConfirmed: () => void;
}) {
    const [password, setPassword] = useState("");
    const [submitting, setSubmitting] = useState(false);

    // Close on Escape for expected modal behaviour.
    useEffect(() => {
        const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [onClose]);

    const handleDelete = async () => {
        if (!password) return;
        setSubmitting(true);
        try {
            await userService.deleteAccount(password);
            toast.success("Account deleted");
            onConfirmed();
        } catch (err) {
            toast.error(apiErrorMessage(err, "Could not delete account"));
            setSubmitting(false);
        }
    };

    return (
        <div
            className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={onClose}
        >
            <motion.div
                initial={{ opacity: 0, scale: 0.96, y: 8 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                onClick={(e) => e.stopPropagation()}
                className="w-full max-w-md card-elevated rounded-2xl p-6"
            >
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-error/10 rounded-lg">
                        <AlertTriangle className="w-5 h-5 text-error" />
                    </div>
                    <h3 className="font-semibold text-lg">Delete account</h3>
                </div>
                <p className="text-sm text-muted mb-4">
                    This deactivates your account and removes access to your resumes, job
                    descriptions, and analyses. Enter your password to confirm.
                </p>
                <input
                    type="password"
                    autoFocus
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleDelete()}
                    placeholder="Current password"
                    className="input-field mb-5"
                />
                <div className="flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        disabled={submitting}
                        className="btn-ghost border border-border rounded-xl text-sm px-4 py-2 disabled:opacity-50"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleDelete}
                        disabled={!password || submitting}
                        className="bg-error text-foreground text-sm px-4 py-2 rounded-xl transition-colors hover:bg-error/90 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                        Delete Account
                    </button>
                </div>
            </motion.div>
        </div>
    );
}
