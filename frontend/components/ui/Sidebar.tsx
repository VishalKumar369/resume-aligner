"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutDashboard, Upload, BookOpen, Building2, Settings,
    FileText, ChevronLeft, ChevronRight, Target, BarChart3, FolderKanban, X, NotebookPen,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useUiStore } from "@/store/uiStore";

const PLATFORM_NAME = process.env.NEXT_PUBLIC_PLATFORM_NAME || "Resume JD Aligner";

const navItems = [
    { href: "/dashboard", icon: LayoutDashboard, label: "Overview" },
    { href: "/upload", icon: Upload, label: "Upload & Analyze" },
    {
        label: "Analytics",
        isGroup: true,
        children: [
            { href: "/dashboard/readiness", icon: Target, label: "Career Readiness" },
            { href: "/dashboard/skills", icon: BarChart3, label: "Skill Gaps" },
            { href: "/dashboard/resume-versions", icon: FolderKanban, label: "Resume Versions" },
        ],
    },
    {
        label: "Targeting",
        isGroup: true,
        children: [
            // `match` keeps Company Intel active on the per-analysis insight
            // pages too (/company/<slug>?jd=...), not just the index.
            { href: "/company", match: "/company", icon: Building2, label: "Company Intel" },
            { href: "/learning", icon: BookOpen, label: "Learning Roadmap" },
        ],
    },
    {
        label: "Personal",
        isGroup: true,
        children: [
            { href: "/notes", icon: NotebookPen, label: "Notes" },
        ],
    },
    {
        label: "Account",
        isGroup: true,
        children: [
            { href: "/settings", icon: Settings, label: "Settings" },
        ],
    },
];

export function Sidebar() {
    const [collapsed, setCollapsed] = useState(false);
    const pathname = usePathname();
    const { mobileNavOpen, closeMobileNav } = useUiStore();

    return (
        <>
            {/* Desktop: static, collapsible rail (hidden on small screens). */}
            <motion.aside
                initial={false}
                animate={{ width: collapsed ? 64 : 220 }}
                transition={{ duration: 0.25, ease: "easeInOut" }}
                className="relative hidden md:flex flex-col h-full bg-card border-r border-border overflow-hidden flex-shrink-0"
            >
                <SidebarLogo collapsed={collapsed} />
                <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto overflow-x-hidden">
                    <SidebarNav collapsed={collapsed} pathname={pathname} />
                </nav>
                <div className="p-2 border-t border-border">
                    <button
                        onClick={() => setCollapsed(!collapsed)}
                        className={cn(
                            "w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-[13px] text-muted-foreground hover:text-foreground hover:bg-surface-2 transition-colors duration-150",
                            collapsed && "justify-center"
                        )}
                    >
                        {collapsed ? <ChevronRight className="w-4 h-4" /> : (
                            <>
                                <ChevronLeft className="w-4 h-4" />
                                <span className="text-sm">Collapse</span>
                            </>
                        )}
                    </button>
                </div>
            </motion.aside>

            {/* Mobile: off-canvas drawer, only mounted while open. */}
            <AnimatePresence>
                {mobileNavOpen && (
                    <div className="md:hidden fixed inset-0 z-[70]">
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={closeMobileNav}
                            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                        />
                        <motion.aside
                            initial={{ x: "-100%" }}
                            animate={{ x: 0 }}
                            exit={{ x: "-100%" }}
                            transition={{ type: "tween", duration: 0.25, ease: "easeInOut" }}
                            className="absolute left-0 top-0 h-full w-[80%] max-w-xs bg-card border-r border-border flex flex-col"
                        >
                            <div className="h-14 flex items-center justify-between px-3 border-b border-border flex-shrink-0">
                                <div className="flex items-center gap-2.5">
                                    <div className="w-7 h-7 rounded-md bg-primary flex items-center justify-center flex-shrink-0">
                                        <FileText className="w-3.5 h-3.5 text-primary-foreground" />
                                    </div>
                                    <span className="font-semibold text-[13px] tracking-tight">{PLATFORM_NAME}</span>
                                </div>
                                <button
                                    onClick={closeMobileNav}
                                    aria-label="Close menu"
                                    className="p-2 rounded-lg text-muted hover:text-foreground hover:bg-surface-2 transition-colors"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                            <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto">
                                <SidebarNav collapsed={false} pathname={pathname} onNavigate={closeMobileNav} />
                            </nav>
                        </motion.aside>
                    </div>
                )}
            </AnimatePresence>
        </>
    );
}

function SidebarLogo({ collapsed }: { collapsed: boolean }) {
    return (
        <div className="h-14 flex items-center px-3 border-b border-border flex-shrink-0">
            <Link href="/dashboard" className="flex items-center gap-2.5 overflow-hidden">
                <div className="w-7 h-7 rounded-md bg-primary flex items-center justify-center flex-shrink-0">
                    <FileText className="w-3.5 h-3.5 text-primary-foreground" />
                </div>
                <AnimatePresence>
                    {!collapsed && (
                        <motion.div
                            initial={{ opacity: 0, width: 0 }}
                            animate={{ opacity: 1, width: "auto" }}
                            exit={{ opacity: 0, width: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden whitespace-nowrap leading-tight"
                        >
                            <div className="font-semibold text-[13px] tracking-tight">{PLATFORM_NAME}</div>
                            <div className="text-[10px] text-muted font-mono">process.env.APP_NAME</div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </Link>
        </div>
    );
}

/** The navigation items, shared by the desktop rail and the mobile drawer. */
function SidebarNav({
    collapsed,
    pathname,
    onNavigate,
}: {
    collapsed: boolean;
    pathname: string;
    onNavigate?: () => void;
}) {
    return (
        <>
            {navItems.map((item) => {
                if ("isGroup" in item && item.isGroup) {
                    return (
                        <div key={item.label} className="pt-4">
                            <AnimatePresence>
                                {!collapsed && (
                                    <motion.div
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0 }}
                                        className="px-2.5 pb-1"
                                    >
                                        <span className="section-label">
                                            {item.label}
                                        </span>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                            <div className="space-y-0.5">
                                {item.children?.map((child) => (
                                    <NavLink key={child.href} item={child} collapsed={collapsed} pathname={pathname} onNavigate={onNavigate} />
                                ))}
                            </div>
                        </div>
                    );
                }
                return <NavLink key={item.href} item={item as NavItem} collapsed={collapsed} pathname={pathname} onNavigate={onNavigate} />;
            })}
        </>
    );
}

interface NavItem { href: string; icon: React.ElementType; label: string; match?: string }

function NavLink({
    item,
    collapsed,
    pathname,
    onNavigate,
}: {
    item: NavItem;
    collapsed: boolean;
    pathname: string;
    onNavigate?: () => void;
}) {
    // `match` lets a link stay active across a whole section even when its href
    // points at one page within it (e.g. Company Intel → any /company route).
    const activePrefix = item.match || item.href;
    const isActive = pathname === item.href || (activePrefix !== "/dashboard" && pathname.startsWith(activePrefix));
    return (
        <Link href={item.href} onClick={onNavigate}>
            <div
                className={cn(
                    "flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-[13px] transition-colors duration-150 cursor-pointer group",
                    isActive
                        ? "bg-primary/10 text-primary font-medium"
                        : "text-muted-foreground hover:text-foreground hover:bg-surface-2",
                    collapsed && "justify-center"
                )}
            >
                <item.icon className="w-4 h-4 flex-shrink-0" />
                <AnimatePresence>
                    {!collapsed && (
                        <motion.span
                            initial={{ opacity: 0, width: 0 }}
                            animate={{ opacity: 1, width: "auto" }}
                            exit={{ opacity: 0, width: 0 }}
                            transition={{ duration: 0.2 }}
                            className="text-sm font-medium whitespace-nowrap overflow-hidden"
                        >
                            {item.label}
                        </motion.span>
                    )}
                </AnimatePresence>
            </div>
        </Link>
    );
}
