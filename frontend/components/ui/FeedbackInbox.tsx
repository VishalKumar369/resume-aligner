"use client";

import { useEffect, useState } from "react";
import { Inbox, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import { feedbackService } from "@/services/api";
import { Skeleton } from "@/components/ui/States";

interface FeedbackRow {
    id: string;
    rating?: number | null;
    message: string;
    created_at: string;
    owner_id?: string | null;
    email?: string | null;
    source?: string | null;
}

/**
 * The admin feedback inbox. Fetches every submission; if the account isn't an
 * admin the endpoint 403s and this renders nothing at all — so it's safe to drop
 * on the shared /feedback page for everyone.
 */
export function FeedbackInbox() {
    const [rows, setRows] = useState<FeedbackRow[] | null>(null);
    const [allowed, setAllowed] = useState(true);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let alive = true;
        feedbackService
            .list()
            .then((res) => alive && setRows(res.data))
            .catch((err) => {
                if (!alive) return;
                if (err?.response?.status === 403) setAllowed(false);
                else setRows([]);
            })
            .finally(() => alive && setLoading(false));
        return () => {
            alive = false;
        };
    }, []);

    // Non-admins: show nothing.
    if (!allowed) return null;

    return (
        <div className="card-elevated rounded-2xl p-6">
            <div className="flex items-center gap-3 mb-1">
                <div className="p-2 rounded-lg bg-primary/10">
                    <Inbox className="w-4 h-4 text-primary" />
                </div>
                <div>
                    <h3 className="font-semibold">All feedback</h3>
                    <p className="text-xs text-muted mt-0.5">Everything users have submitted · admin only</p>
                </div>
            </div>

            {loading ? (
                <div className="space-y-2 mt-4">
                    {[0, 1, 2].map((i) => <Skeleton key={i} className="h-12 rounded-lg" />)}
                </div>
            ) : rows && rows.length > 0 ? (
                <div className="divide-y divide-border mt-2">
                    {rows.map((row) => (
                        <div key={row.id} className="py-3 flex items-start gap-3">
                            <div className="flex items-center gap-0.5 flex-shrink-0 w-[70px]">
                                {row.rating
                                    ? Array.from({ length: 5 }).map((_, i) => (
                                        <Star
                                            key={i}
                                            className={cn("w-3 h-3", i < row.rating! ? "fill-warning text-warning" : "text-muted/40")}
                                        />
                                    ))
                                    : <span className="text-xs text-muted">—</span>}
                            </div>
                            <div className="min-w-0 flex-1">
                                <p className="text-sm whitespace-pre-wrap break-words">{row.message}</p>
                                <p className="text-[11px] text-muted mt-1">
                                    {(row.source || "—")} ·{" "}
                                    {row.email || (row.owner_id ? "account" : "anonymous")} ·{" "}
                                    {new Date(row.created_at).toLocaleString()}
                                </p>
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <p className="text-sm text-muted mt-4">No feedback yet.</p>
            )}
        </div>
    );
}
