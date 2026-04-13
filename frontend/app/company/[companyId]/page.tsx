"use client";

import { motion } from "framer-motion";
import { Building2, TrendingUp, Users, Star, ExternalLink } from "lucide-react";
import { StatCard } from "@/components/ui/StatCard";

const companyData = {
    name: "Google",
    tagline: "Engineering Excellence · Large Scale Systems",
    alignmentScore: 88,
    atsScore: 92,
    hiringStatus: "Active",
    primaryStack: ["Go", "C++", "Python", "Kubernetes", "GCP"],
    cultureTags: ["High bar", "Data-driven", "Ownership culture", "Large-scale thinking"],
    prepTips: "Focus on system design with high-throughput distributed systems. Google values clarity at scale — quantify everything. Practice Leetcode Hard.",
    openRoles: ["Senior SWE", "Staff Engineer", "SRE", "ML Engineer"],
};

export default function CompanyPage() {
    return (
        <div className="max-w-5xl mx-auto space-y-6">
            <div className="card-elevated rounded-2xl p-6">
                <div className="flex items-center gap-4">
                    <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                        <Building2 className="w-8 h-8 text-primary" />
                    </div>
                    <div>
                        <div className="flex items-center gap-3">
                            <h1 className="text-2xl font-bold">{companyData.name}</h1>
                            <span className="px-2.5 py-1 bg-success/10 text-success border border-success/20 rounded-full text-xs font-medium">
                                {companyData.hiringStatus}
                            </span>
                        </div>
                        <p className="text-sm text-muted mt-1">{companyData.tagline}</p>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard title="Your Alignment" value={88} scoreType delay={0} />
                <StatCard title="ATS Score" value={92} scoreType delay={0.05} />
                <StatCard title="Open Roles" value={4} icon={Users} delay={0.1} />
                <StatCard title="Culture Fit" value="High" icon={Star} subtitle="Based on resume tone" delay={0.15} />
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
                <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="card-elevated rounded-2xl p-6">
                    <h3 className="text-sm font-semibold mb-4">Primary Tech Stack</h3>
                    <div className="flex flex-wrap gap-2">
                        {companyData.primaryStack.map((tech) => (
                            <span key={tech} className="px-3 py-1.5 bg-primary/10 text-primary border border-primary/20 rounded-lg text-sm font-medium">{tech}</span>
                        ))}
                    </div>
                    <h3 className="text-sm font-semibold mb-3 mt-6">Culture Tags</h3>
                    <div className="flex flex-wrap gap-2">
                        {companyData.cultureTags.map((tag) => (
                            <span key={tag} className="px-3 py-1.5 bg-surface-2 text-muted-foreground border border-border rounded-lg text-sm">{tag}</span>
                        ))}
                    </div>
                </motion.div>

                <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="card-elevated rounded-2xl p-6">
                    <h3 className="text-sm font-semibold mb-3">Interview Prep Tips</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed mb-6">{companyData.prepTips}</p>
                    <h3 className="text-sm font-semibold mb-3">Active Openings</h3>
                    <div className="space-y-2">
                        {companyData.openRoles.map((role) => (
                            <div key={role} className="flex items-center justify-between p-3 bg-surface-2 rounded-xl border border-border/50 hover:border-primary/30 transition-colors cursor-pointer">
                                <span className="text-sm font-medium">{role}</span>
                                <ExternalLink className="w-4 h-4 text-muted" />
                            </div>
                        ))}
                    </div>
                </motion.div>
            </div>
        </div>
    );
}
