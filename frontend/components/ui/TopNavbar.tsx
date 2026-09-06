"use client";

import { useEffect, useRef, useState } from "react";
import { Bell, Search, User, Plus, LogOut, Menu } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useAuthStore } from "@/store/authStore";
import { useUiStore } from "@/store/uiStore";
import { ThemeToggle } from "@/components/ui/ThemeToggle";

const PLATFORM_NAME = process.env.NEXT_PUBLIC_PLATFORM_NAME || "Resume JD Aligner";

/** First letters of the first and last words, e.g. "John Doe" -> "JD". */
function initialsOf(name: string): string {
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) return "U";
    if (parts.length === 1) return parts[0][0]!.toUpperCase();
    return (parts[0][0]! + parts[parts.length - 1][0]!).toUpperCase();
}

export function TopNavbar({ title }: { title?: string }) {
    const router = useRouter();
    const clearAuth = useAuthStore((state) => state.clearAuth);
    const user = useAuthStore((state) => state.user);
    const openMobileNav = useUiStore((state) => state.openMobileNav);
    const [showProfileMenu, setShowProfileMenu] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);

    const displayName = user?.name?.trim() || "Your account";
    const email = user?.email || "";
    const initials = initialsOf(user?.name || email || "U");

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setShowProfileMenu(false);
            }
        };

        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const handleLogout = () => {
        setShowProfileMenu(false);
        clearAuth();
        router.replace("/auth/login");
    };

    return (
        <header className="h-14 flex items-center justify-between gap-2 px-4 sm:px-5 border-b border-border bg-card/80 backdrop-blur-sm sticky top-0 z-40">
            <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                <button
                    onClick={openMobileNav}
                    aria-label="Open menu"
                    className="md:hidden p-2 rounded-lg text-muted hover:text-foreground hover:bg-surface-2 transition-colors flex-shrink-0"
                >
                    <Menu className="w-5 h-5" />
                </button>
                {title && (
                    <h1 className="text-base sm:text-lg font-semibold text-foreground truncate">{title}</h1>
                )}
            </div>

            {/* Search */}
            <div className="hidden md:flex items-center gap-2 bg-surface border border-border rounded-lg px-2.5 py-1.5 w-56 text-xs text-muted">
                <Search className="w-3.5 h-3.5 flex-shrink-0" />
                <span>Search resumes, companies…</span>
                <kbd className="ml-auto text-[10px] bg-surface-2 text-muted px-1.5 py-0.5 rounded border border-border">⌘K</kbd>
            </div>

            <div className="flex items-center gap-1.5 sm:gap-3 flex-shrink-0">
                <Link href="/upload">
                    <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className="btn-primary flex items-center gap-2 text-sm py-2 px-3 sm:px-5"
                    >
                        <Plus className="w-4 h-4" />
                        <span className="hidden sm:inline">New Analysis</span>
                    </motion.button>
                </Link>

                <ThemeToggle />

                <button className="relative p-2 rounded-lg text-muted hover:text-foreground hover:bg-surface-2 transition-colors">
                    <Bell className="w-5 h-5" />
                    <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-primary" />
                </button>

                <div ref={menuRef} className="relative">
                    <button
                        type="button"
                        onClick={() => setShowProfileMenu((prev) => !prev)}
                        aria-haspopup="menu"
                        aria-expanded={showProfileMenu}
                        aria-label="Account menu"
                        className="flex items-center gap-2 p-1.5 rounded-xl hover:bg-surface-2 transition-colors"
                    >
                        <div className="w-8 h-8 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center text-xs font-semibold text-primary">
                            {initials}
                        </div>
                    </button>

                    {showProfileMenu && (
                        <motion.div
                            initial={{ opacity: 0, y: -6, scale: 0.98 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            transition={{ duration: 0.12 }}
                            role="menu"
                            className="absolute right-0 top-full mt-2 w-64 rounded-xl border border-border bg-card shadow-lg z-50 overflow-hidden"
                        >
                            {/* Identity header */}
                            <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
                                <div className="w-10 h-10 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center text-sm font-semibold text-primary flex-shrink-0">
                                    {initials}
                                </div>
                                <div className="min-w-0">
                                    <p className="text-sm font-medium text-foreground truncate">{displayName}</p>
                                    {email && <p className="text-xs text-muted truncate">{email}</p>}
                                </div>
                            </div>

                            <div className="py-1.5">
                                <Link
                                    href="/settings"
                                    onClick={() => setShowProfileMenu(false)}
                                    role="menuitem"
                                    className="flex w-full items-center gap-2.5 px-4 py-2 text-sm text-muted hover:bg-surface-2 hover:text-foreground transition-colors"
                                >
                                    <User className="w-4 h-4" />
                                    Account settings
                                </Link>
                                <button
                                    onClick={handleLogout}
                                    role="menuitem"
                                    className="flex w-full items-center gap-2.5 px-4 py-2 text-sm text-error hover:bg-error/10 transition-colors"
                                >
                                    <LogOut className="w-4 h-4" />
                                    Log out
                                </button>
                            </div>
                        </motion.div>
                    )}
                </div>
            </div>
        </header>
    );
}
