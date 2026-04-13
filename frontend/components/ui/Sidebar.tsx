"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutDashboard, Upload, BookOpen, Building2, Settings,
    FileText, ChevronLeft, ChevronRight, Target, BarChart3, FolderKanban
} from "lucide-react";
import { cn } from "@/lib/utils";

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
    { href: "/learning", icon: BookOpen, label: "Learning Roadmap" },
    { href: "/company/google", icon: Building2, label: "Company Intel" },
    { href: "/settings", icon: Settings, label: "Settings" },
];

export function Sidebar() {
    const [collapsed, setCollapsed] = useState(false);
    const pathname = usePathname();

    return (
        <motion.aside
            initial={false}
            animate={{ width: collapsed ? 68 : 240 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="relative flex flex-col h-full bg-card border-r border-border overflow-hidden flex-shrink-0"
        >
            {/* Logo */}
            <div className="h-16 flex items-center px-4 border-b border-border flex-shrink-0">
                <Link href="/dashboard" className="flex items-center gap-3 overflow-hidden">
                    <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center flex-shrink-0">
                        <FileText className="w-4 h-4 text-white" />
                    </div>
                    <AnimatePresence>
                        {!collapsed && (
                            <motion.span
                                initial={{ opacity: 0, width: 0 }}
                                animate={{ opacity: 1, width: "auto" }}
                                exit={{ opacity: 0, width: 0 }}
                                transition={{ duration: 0.2 }}
                                className="font-bold text-sm whitespace-nowrap overflow-hidden"
                            >
                                {PLATFORM_NAME}
                            </motion.span>
                        )}
                    </AnimatePresence>
                </Link>
            </div>

            {/* Nav */}
            <nav className="flex-1 p-3 space-y-1 overflow-y-auto overflow-x-hidden">
                {navItems.map((item) => {
                    if ("isGroup" in item && item.isGroup) {
                        return (
                            <div key={item.label} className="pt-3">
                                <AnimatePresence>
                                    {!collapsed && (
                                        <motion.div
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            exit={{ opacity: 0 }}
                                            className="px-3 pb-1"
                                        >
                                            <span className="text-xs font-semibold text-muted uppercase tracking-wider">
                                                {item.label}
                                            </span>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                                <div className="space-y-1">
                                    {item.children?.map((child) => (
                                        <NavLink key={child.href} item={child} collapsed={collapsed} pathname={pathname} />
                                    ))}
                                </div>
                            </div>
                        );
                    }
                    return <NavLink key={item.href} item={item as NavItem} collapsed={collapsed} pathname={pathname} />;
                })}
            </nav>

            {/* Collapse toggle */}
            <div className="p-3 border-t border-border">
                <button
                    onClick={() => setCollapsed(!collapsed)}
                    className={cn(
                        "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-muted hover:text-white hover:bg-surface-2 transition-all duration-200",
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
    );
}

interface NavItem { href: string; icon: React.ElementType; label: string }

function NavLink({ item, collapsed, pathname }: { item: NavItem; collapsed: boolean; pathname: string }) {
    const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
    return (
        <Link href={item.href}>
            <div
                className={cn(
                    "flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200 cursor-pointer group",
                    isActive
                        ? "bg-primary/15 text-primary border border-primary/20"
                        : "text-muted hover:text-white hover:bg-surface-2",
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
