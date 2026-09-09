"use client";

import { useState } from "react";
import { Star, Send, CheckCircle, MessageSquare } from "lucide-react";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";
import { feedbackService, apiErrorMessage } from "@/services/api";

/**
 * A product-feedback form (optional 1–5 rating + message). Reused on the public
 * landing page (anonymous, with an optional email) and in Settings (attributed
 * to the signed-in account by the JWT).
 */
export function FeedbackSection({
    source,
    className,
}: {
    source: "landing" | "settings" | "app";
    className?: string;
}) {
    const [rating, setRating] = useState(0);
    const [hover, setHover] = useState(0);
    const [message, setMessage] = useState("");
    const [email, setEmail] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [done, setDone] = useState(false);

    const submit = async () => {
        if (!message.trim()) {
            toast.error("Please write a little feedback first.");
            return;
        }
        setSubmitting(true);
        try {
            await feedbackService.submit({
                message: message.trim(),
                rating: rating || undefined,
                email: source === "landing" && email.trim() ? email.trim() : undefined,
                source,
            });
            setDone(true);
        } catch (err: any) {
            toast.error(apiErrorMessage(err, "Couldn't send your feedback."));
        } finally {
            setSubmitting(false);
        }
    };

    if (done) {
        return (
            <div className={cn("card-elevated rounded-2xl p-6 text-center", className)}>
                <div className="w-12 h-12 rounded-2xl bg-success/10 flex items-center justify-center mx-auto mb-3">
                    <CheckCircle className="w-6 h-6 text-success" />
                </div>
                <h3 className="font-semibold">Thank you!</h3>
                <p className="text-sm text-muted mt-1">Your feedback helps us make the product better.</p>
            </div>
        );
    }

    return (
        <div className={cn("card-elevated rounded-2xl p-6", className)}>
            <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-lg bg-primary/10">
                    <MessageSquare className="w-4 h-4 text-primary" />
                </div>
                <div>
                    <h3 className="font-semibold">Share your feedback</h3>
                    <p className="text-xs text-muted mt-0.5">Tell us what&apos;s working and what we can improve.</p>
                </div>
            </div>

            <div className="flex items-center gap-1 mb-3" role="radiogroup" aria-label="Rating">
                {[1, 2, 3, 4, 5].map((n) => (
                    <button
                        key={n}
                        type="button"
                        aria-label={`${n} star${n > 1 ? "s" : ""}`}
                        aria-pressed={rating === n}
                        onMouseEnter={() => setHover(n)}
                        onMouseLeave={() => setHover(0)}
                        onClick={() => setRating(n === rating ? 0 : n)}
                        className="p-0.5 rounded transition-transform hover:scale-110"
                    >
                        <Star className={cn("w-6 h-6", (hover || rating) >= n ? "fill-warning text-warning" : "text-muted")} />
                    </button>
                ))}
            </div>

            <textarea
                rows={4}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="What did you like? What would make this better?"
                className="input-field resize-none"
            />

            {source === "landing" && (
                <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Email (optional — if you'd like a reply)"
                    className="input-field mt-3"
                />
            )}

            <div className="flex justify-end mt-3">
                <button
                    onClick={submit}
                    disabled={submitting}
                    className="btn-primary inline-flex items-center gap-2 text-sm disabled:opacity-50"
                >
                    <Send className="w-4 h-4" /> {submitting ? "Sending…" : "Send feedback"}
                </button>
            </div>
        </div>
    );
}
