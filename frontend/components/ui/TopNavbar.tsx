"use client";

import { Bell, Search, User, Plus } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";

const PLATFORM_NAME = process.env.NEXT_PUBLIC_PLATFORM_NAME || "Resume JD Aligner";

export function TopNavbar({ title }: { title?: string }) {
    return (
        <header className="h-16 flex items-center justify-between px-6 border-b border-border bg-card/80 backdrop-blur-sm sticky top-0 z-40">
            <div className="flex items-center gap-4">
                {title && (
                    <h1 className="text-lg font-semibold text-white">{title}</h1>
                )}
            </div>

            {/* Search */}
            <div className="hidden md:flex items-center gap-2 bg-surface border border-border rounded-xl px-3 py-2 w-64 text-sm text-muted">
                <Search className="w-4 h-4 flex-shrink-0" />
                <span>Search resumes, companies…</span>
                <kbd className="ml-auto text-xs bg-surface-2 text-muted px-1.5 py-0.5 rounded border border-border">⌘K</kbd>
            </div>

            <div className="flex items-center gap-3">
                <Link href="/upload">
                    <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className="btn-primary flex items-center gap-2 text-sm py-2"
                    >
                        <Plus className="w-4 h-4" />
                        New Analysis
                    </motion.button>
                </Link>

                <button className="relative p-2 rounded-lg text-muted hover:text-white hover:bg-surface-2 transition-colors">
                    <Bell className="w-5 h-5" />
                    <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-primary" />
                </button>

                <button className="flex items-center gap-2 p-1.5 rounded-xl hover:bg-surface-2 transition-colors">
                    <div className="w-8 h-8 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center">
                        <User className="w-4 h-4 text-primary" />
                    </div>
                </button>
            </div>
        </header>
    );
}
