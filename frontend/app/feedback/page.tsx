"use client";

import { Sidebar } from "@/components/ui/Sidebar";
import { TopNavbar } from "@/components/ui/TopNavbar";
import { FeedbackSection } from "@/components/ui/FeedbackSection";

export default function FeedbackPage() {
    return (
        <div className="flex h-screen bg-background overflow-hidden">
            <Sidebar />
            <div className="flex-1 flex flex-col overflow-hidden">
                <TopNavbar title="Feedback" />
                <main className="flex-1 overflow-y-auto p-6">
                    <div className="max-w-8xl mx-auto space-y-6">
                        <div>
                            <h1 className="text-2xl font-bold">Feedback</h1>
                            <p className="text-sm text-muted mt-1">
                                Tell us what&apos;s working and what we can improve.
                            </p>
                        </div>
                        <FeedbackSection source="app" />
                    </div>
                </main>
            </div>
        </div>
    );
}
