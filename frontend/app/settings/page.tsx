"use client";

import { motion } from "framer-motion";
import { User, Bell, Shield, Palette, Download } from "lucide-react";
import { Sidebar } from "@/components/ui/Sidebar";
import { TopNavbar } from "@/components/ui/TopNavbar";

const sections = [
    { icon: User, title: "Profile", fields: [{ label: "Full Name", value: "John Doe", type: "text" }, { label: "Email", value: "john@example.com", type: "email" }, { label: "Target Role", value: "Senior Backend Engineer", type: "text" }] },
    { icon: Bell, title: "Notifications", fields: [{ label: "Email Alerts on New Matches", value: "true", type: "toggle" }, { label: "Weekly Career Readiness Report", value: "true", type: "toggle" }] },
];

export default function SettingsPage() {
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

                        {sections.map((s, i) => (
                            <motion.div key={s.title} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }} className="card-elevated rounded-2xl p-6">
                                <div className="flex items-center gap-3 mb-5">
                                    <div className="p-2 bg-surface-2 rounded-lg">
                                        <s.icon className="w-4 h-4 text-muted" />
                                    </div>
                                    <h3 className="font-semibold">{s.title}</h3>
                                </div>
                                <div className="space-y-4">
                                    {s.fields.map((field) => (
                                        <div key={field.label}>
                                            <label className="block text-xs font-medium text-muted mb-2">{field.label}</label>
                                            {field.type === "toggle" ? (
                                                <div className="flex items-center gap-3">
                                                    <button className="w-11 h-6 bg-primary rounded-full relative transition-colors">
                                                        <span className="absolute top-1 right-1 w-4 h-4 bg-white rounded-full transition-transform" />
                                                    </button>
                                                    <span className="text-xs text-muted">Enabled</span>
                                                </div>
                                            ) : (
                                                <input type={field.type} defaultValue={field.value} className="input-field" />
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </motion.div>
                        ))}

                        <div className="card-elevated rounded-2xl p-6">
                            <div className="flex items-center gap-3 mb-5">
                                <div className="p-2 bg-surface-2 rounded-lg"><Download className="w-4 h-4 text-muted" /></div>
                                <h3 className="font-semibold">Data & Privacy</h3>
                            </div>
                            <div className="flex gap-3">
                                <button className="btn-ghost border border-border rounded-xl text-sm px-4 py-2">Export All Data</button>
                                <button className="text-error hover:bg-error/10 border border-error/20 text-sm px-4 py-2 rounded-xl transition-colors">Delete Account</button>
                            </div>
                        </div>

                        <div className="flex justify-end">
                            <button className="btn-primary px-8 py-2.5">Save Changes</button>
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}
