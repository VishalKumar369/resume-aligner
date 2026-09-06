"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useSearchParams } from "next/navigation";
import {
    Plus, Pin, PinOff, Pencil, Trash2, Check, CalendarDays, X, Target, NotebookPen,
    Search, ListChecks, CircleCheck, Clock, AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useApi } from "@/hooks/useApi";
import { apiErrorMessage, noteService, NoteInput } from "@/services/api";
import { ErrorState, Skeleton } from "@/components/ui/States";

interface Note {
    id: string;
    title: string;
    content: string;
    category: string;
    color: string;
    target_date: string | null;
    is_pinned: boolean;
    is_completed: boolean;
    created_at: string;
}

const COLORS = ["primary", "accent", "success", "warning", "error"] as const;
const CATEGORY_SUGGESTIONS = [
    "Goal", "Journal", "Idea", "Task", "Reminder",
    "High priority", "Medium priority", "Low priority",
];

const accentBar: Record<string, string> = {
    primary: "border-l-primary", accent: "border-l-accent", success: "border-l-success",
    warning: "border-l-warning", error: "border-l-error",
};
const dot: Record<string, string> = {
    primary: "bg-primary", accent: "bg-accent", success: "bg-success",
    warning: "bg-warning", error: "bg-error",
};

const emptyForm = { title: "", content: "", category: "Goal", color: "primary", target_date: "" };

// useSearchParams must sit under a Suspense boundary for the production build.
export default function NotesPage() {
    return (
        <Suspense fallback={<div className="max-w-5xl mx-auto"><Skeleton className="h-9 w-56" /></div>}>
            <NotesContent />
        </Suspense>
    );
}

function NotesContent() {
    const { data: notes, loading, error, reload } = useApi<Note[]>(() => noteService.getAll());
    const search$ = useSearchParams();
    const [editing, setEditing] = useState<Note | Record<string, never> | null>(null);
    const [form, setForm] = useState(emptyForm);
    const [saving, setSaving] = useState(false);
    const [actionError, setActionError] = useState<string | null>(null);
    // The composer is portalled to <body>, so guard the portal until mounted.
    const [mounted, setMounted] = useState(false);
    useEffect(() => setMounted(true), []);

    // Open the composer pre-filled when linked from a skill gap ("Add as goal").
    useEffect(() => {
        if (search$.get("compose") !== "1") return;
        setForm({
            title: search$.get("title") || "",
            content: search$.get("content") || "",
            category: search$.get("category") || "Goal",
            color: search$.get("color") || "primary",
            target_date: search$.get("target") || "",
        });
        setEditing({});
        // Only on first load of a compose link.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    const [filter, setFilter] = useState<string>("all");
    const [search, setSearch] = useState("");
    const [hideCompleted, setHideCompleted] = useState(false);

    const list = notes || [];

    const categories = useMemo(
        () => Array.from(new Set(list.map((n) => n.category).filter(Boolean))),
        [list]
    );

    const now = Date.now();
    const summary = useMemo(() => ({
        total: list.length,
        completed: list.filter((n) => n.is_completed).length,
        upcoming: list.filter((n) => n.target_date && !n.is_completed && new Date(n.target_date).getTime() >= now).length,
        overdue: list.filter((n) => n.target_date && !n.is_completed && new Date(n.target_date).getTime() < now).length,
    }), [list, now]);

    const q = search.trim().toLowerCase();
    const visible = list.filter((n) =>
        (filter === "all" || n.category === filter) &&
        (!hideCompleted || !n.is_completed) &&
        (!q || n.title.toLowerCase().includes(q) || (n.content || "").toLowerCase().includes(q))
    );

    const openNew = () => { setForm(emptyForm); setEditing({}); setActionError(null); };
    const openEdit = (note: Note) => {
        setForm({
            title: note.title, content: note.content, category: note.category, color: note.color,
            target_date: note.target_date ? note.target_date.slice(0, 10) : "",
        });
        setEditing(note);
        setActionError(null);
    };
    const close = () => setEditing(null);

    const isEdit = editing && "id" in editing;

    const save = async () => {
        if (!form.title.trim()) { setActionError("Give your note a title."); return; }
        setSaving(true);
        setActionError(null);
        const payload: NoteInput = {
            title: form.title.trim(),
            content: form.content,
            category: form.category.trim() || "Note",
            color: form.color,
            target_date: form.target_date ? new Date(`${form.target_date}T00:00:00`).toISOString() : null,
        };
        try {
            if (isEdit) await noteService.update((editing as Note).id, payload);
            else await noteService.create(payload);
            close();
            reload();
        } catch (err: any) {
            setActionError(apiErrorMessage(err, "Couldn't save the note."));
        } finally {
            setSaving(false);
        }
    };

    const patch = async (note: Note, data: NoteInput) => {
        setActionError(null);
        try {
            await noteService.update(note.id, data);
            reload();
        } catch (err: any) {
            setActionError(apiErrorMessage(err, "Couldn't update the note."));
        }
    };

    const remove = async (note: Note) => {
        setActionError(null);
        try {
            await noteService.remove(note.id);
            reload();
        } catch (err: any) {
            setActionError(apiErrorMessage(err, "Couldn't delete the note."));
        }
    };

    if (loading) {
        return (
            <div className="max-w-5xl mx-auto space-y-6">
                <Skeleton className="h-9 w-56" />
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-40 rounded-2xl" />)}
                </div>
            </div>
        );
    }

    if (error) return <div className="max-w-5xl mx-auto"><ErrorState message={error} onRetry={reload} /></div>;

    return (
        <div className="max-w-5xl mx-auto space-y-5">
            {/* Header */}
            <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                    <h1 className="text-xl font-semibold tracking-tight inline-flex items-center gap-2">
                        <NotebookPen className="w-6 h-6 text-primary" /> Notes
                    </h1>
                    <p className="text-sm text-muted mt-1">
                        Plan your personal targets and jot down your thoughts — private to you.
                    </p>
                </div>
                <button onClick={openNew} className="btn-primary inline-flex items-center gap-2 text-sm">
                    <Plus className="w-4 h-4" /> New note
                </button>
            </div>

            {actionError && (
                <div className="bg-error/5 border border-error/20 rounded-xl p-3 text-sm text-error">{actionError}</div>
            )}

            {list.length === 0 ? (
                <div className="card-elevated rounded-2xl p-10 text-center mt-4">
                    <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                        <NotebookPen className="w-7 h-7 text-primary" />
                    </div>
                    <h3 className="text-lg font-semibold mb-2">No notes yet</h3>
                    <p className="text-sm text-muted max-w-md mx-auto mb-6">
                        Create your first note to plan a goal, track a target, or keep a journal.
                    </p>
                    <button onClick={openNew} className="btn-primary inline-flex items-center gap-2">
                        <Plus className="w-4 h-4" /> Create a note
                    </button>
                </div>
            ) : (
                <>
                    {/* Target summary */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        <SummaryTile icon={ListChecks} label="Total" value={summary.total} tone="primary" />
                        <SummaryTile icon={CircleCheck} label="Completed" value={summary.completed} tone="success" />
                        <SummaryTile icon={Clock} label="Upcoming" value={summary.upcoming} tone="primary" />
                        <SummaryTile icon={AlertTriangle} label="Overdue" value={summary.overdue} tone="error" />
                    </div>

                    {/* Controls: search + hide completed + category filter */}
                    <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                        <div className="flex items-center gap-2 input-field flex-1 py-2">
                            <Search className="w-4 h-4 text-muted flex-shrink-0" />
                            <input
                                className="flex-1 bg-transparent outline-none text-sm"
                                placeholder="Search notes…"
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                            />
                            {search && (
                                <button onClick={() => setSearch("")} aria-label="Clear search" className="text-muted hover:text-foreground">
                                    <X className="w-4 h-4" />
                                </button>
                            )}
                        </div>
                        <button
                            onClick={() => setHideCompleted((v) => !v)}
                            aria-pressed={hideCompleted}
                            className={cn(
                                "px-3 py-2 rounded-xl text-sm font-medium border transition-colors inline-flex items-center gap-2 flex-shrink-0",
                                hideCompleted
                                    ? "bg-primary/10 text-primary border-primary/30"
                                    : "border-border text-muted hover:text-foreground hover:bg-surface-2"
                            )}
                        >
                            <Check className="w-4 h-4" /> Hide completed
                        </button>
                    </div>

                    {categories.length > 1 && (
                        <div className="flex flex-wrap gap-2">
                            {["all", ...categories].map((c) => (
                                <button
                                    key={c}
                                    onClick={() => setFilter(c)}
                                    aria-pressed={filter === c}
                                    className={cn(
                                        "px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors capitalize",
                                        filter === c
                                            ? "bg-primary text-primary-foreground border-primary"
                                            : "border-border text-muted hover:text-foreground hover:bg-surface-2"
                                    )}
                                >
                                    {c === "all" ? "All" : c}
                                </button>
                            ))}
                        </div>
                    )}

                    {/* Grid */}
                    {visible.length > 0 ? (
                        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                            {visible.map((note, i) => (
                                <NoteCard key={note.id} note={note} delay={i}
                                    onEdit={() => openEdit(note)}
                                    onDelete={() => remove(note)}
                                    onTogglePin={() => patch(note, { is_pinned: !note.is_pinned })}
                                    onToggleComplete={() => patch(note, { is_completed: !note.is_completed })}
                                />
                            ))}
                        </div>
                    ) : (
                        <p className="text-sm text-muted text-center py-10">No notes match your filters.</p>
                    )}
                </>
            )}

            {/* Composer modal — portalled to <body> so its overlay covers the
                whole viewport, above the sticky navbar and sidebar. */}
            {mounted && createPortal(
                <AnimatePresence>
                {editing !== null && (
                    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            onClick={close} className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
                        <motion.div
                            initial={{ opacity: 0, y: 16, scale: 0.98 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: 16, scale: 0.98 }}
                            className="relative card-elevated rounded-2xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto"
                        >
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="text-lg font-semibold">{isEdit ? "Edit note" : "New note"}</h2>
                                <button onClick={close} aria-label="Close" className="p-1.5 rounded-lg text-muted hover:text-foreground hover:bg-surface-2">
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <label className="text-xs text-muted mb-1 block">Title</label>
                                    <input className="input-field" placeholder="e.g. Land a backend role by Q1"
                                        value={form.title} autoFocus
                                        onChange={(e) => setForm({ ...form, title: e.target.value })} />
                                </div>
                                <div>
                                    <label className="text-xs text-muted mb-1 block">Details</label>
                                    <textarea rows={5} className="input-field resize-none"
                                        placeholder="What's the plan, the steps, or your reflection?"
                                        value={form.content}
                                        onChange={(e) => setForm({ ...form, content: e.target.value })} />
                                </div>
                                <div className="grid sm:grid-cols-2 gap-4">
                                    <div>
                                        <label className="text-xs text-muted mb-1 block">Category</label>
                                        <input className="input-field" list="note-categories" placeholder="Goal"
                                            value={form.category}
                                            onChange={(e) => setForm({ ...form, category: e.target.value })} />
                                        <datalist id="note-categories">
                                            {CATEGORY_SUGGESTIONS.map((c) => <option key={c} value={c} />)}
                                        </datalist>
                                    </div>
                                    <div>
                                        <label className="text-xs text-muted mb-1 block">Target date (optional)</label>
                                        <input type="date" className="input-field"
                                            value={form.target_date}
                                            onChange={(e) => setForm({ ...form, target_date: e.target.value })} />
                                    </div>
                                </div>
                                <div>
                                    <label className="text-xs text-muted mb-1.5 block">Colour</label>
                                    <div className="flex items-center gap-2">
                                        {COLORS.map((c) => (
                                            <button key={c} onClick={() => setForm({ ...form, color: c })}
                                                aria-label={`Colour ${c}`} aria-pressed={form.color === c}
                                                className={cn("w-7 h-7 rounded-full transition-transform", dot[c],
                                                    form.color === c ? "ring-2 ring-offset-2 ring-offset-card ring-foreground/40 scale-110" : "hover:scale-105")} />
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <div className="flex justify-end gap-2 mt-6">
                                <button onClick={close} className="btn-ghost text-sm">Cancel</button>
                                <button onClick={save} disabled={saving} className="btn-primary text-sm disabled:opacity-50">
                                    {saving ? "Saving…" : isEdit ? "Save changes" : "Create note"}
                                </button>
                            </div>
                        </motion.div>
                    </div>
                )}
                </AnimatePresence>,
                document.body
            )}
        </div>
    );
}

function SummaryTile({ icon: Icon, label, value, tone }: {
    icon: React.ElementType; label: string; value: number; tone: "primary" | "success" | "error";
}) {
    const toneClass = tone === "success" ? "text-success bg-success/10"
        : tone === "error" ? "text-error bg-error/10" : "text-primary bg-primary/10";
    return (
        <div className="card-elevated rounded-2xl p-4 flex items-center gap-3">
            <div className={cn("w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0", toneClass)}>
                <Icon className="w-4 h-4" />
            </div>
            <div>
                <div className="text-xl font-bold leading-none">{value}</div>
                <div className="text-xs text-muted mt-1">{label}</div>
            </div>
        </div>
    );
}

function NoteCard({
    note, delay, onEdit, onDelete, onTogglePin, onToggleComplete,
}: {
    note: Note; delay: number; onEdit: () => void; onDelete: () => void;
    onTogglePin: () => void; onToggleComplete: () => void;
}) {
    const overdue = note.target_date && !note.is_completed && new Date(note.target_date) < new Date();
    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(delay * 0.04, 0.3) }}
            className={cn(
                "card-elevated rounded-2xl p-4 border-l-4 flex flex-col group",
                accentBar[note.color] || accentBar.primary,
                note.is_completed && "opacity-70"
            )}
        >
            <div className="flex items-start justify-between gap-2 mb-2">
                <span className="text-[11px] uppercase tracking-wider text-muted font-semibold">{note.category}</span>
                <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
                    <button onClick={onTogglePin} aria-label={note.is_pinned ? "Unpin" : "Pin"} title={note.is_pinned ? "Unpin" : "Pin"}
                        className={cn("p-1.5 rounded-md hover:bg-surface-2", note.is_pinned ? "text-primary" : "text-muted")}>
                        {note.is_pinned ? <Pin className="w-3.5 h-3.5 fill-current" /> : <PinOff className="w-3.5 h-3.5" />}
                    </button>
                    <button onClick={onEdit} aria-label="Edit" title="Edit" className="p-1.5 rounded-md text-muted hover:text-foreground hover:bg-surface-2">
                        <Pencil className="w-3.5 h-3.5" />
                    </button>
                    <button onClick={onDelete} aria-label="Delete" title="Delete" className="p-1.5 rounded-md text-muted hover:text-error hover:bg-error/10">
                        <Trash2 className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>

            <h3 className={cn("font-semibold leading-snug", note.is_completed && "line-through text-muted")}>{note.title}</h3>
            {note.content && (
                <p className="text-sm text-muted-foreground mt-1.5 whitespace-pre-wrap line-clamp-5">{note.content}</p>
            )}

            <div className="flex items-center justify-between gap-2 mt-4 pt-3 border-t border-border/50">
                {note.target_date ? (
                    <span className={cn("inline-flex items-center gap-1 text-xs", overdue ? "text-error" : "text-muted")}>
                        <Target className="w-3 h-3" />
                        {new Date(note.target_date).toLocaleDateString()}
                        {overdue && " · overdue"}
                    </span>
                ) : (
                    <span className="inline-flex items-center gap-1 text-xs text-muted">
                        <CalendarDays className="w-3 h-3" /> {new Date(note.created_at).toLocaleDateString()}
                    </span>
                )}
                <button onClick={onToggleComplete}
                    className={cn("inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-md border transition-colors",
                        note.is_completed
                            ? "border-success/30 text-success bg-success/10"
                            : "border-border text-muted hover:text-foreground hover:bg-surface-2")}>
                    <Check className="w-3 h-3" /> {note.is_completed ? "Done" : "Mark done"}
                </button>
            </div>
        </motion.div>
    );
}
