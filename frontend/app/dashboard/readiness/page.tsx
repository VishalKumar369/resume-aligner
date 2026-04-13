"use client";

import { motion } from "framer-motion";
import { CareerRadarChart } from "@/components/dashboard/CareerRadarChart";
import { StatCard } from "@/components/ui/StatCard";
import { Target, TrendingUp, Brain } from "lucide-react";

export default function ReadinessPage() {
    return (
        <div className="max-w-6xl mx-auto space-y-6">
            <div>
                <h1 className="text-2xl font-bold">Career Readiness</h1>
                <p className="text-sm text-muted mt-1">Skill readiness across all target roles and companies</p>
            </div>
            <div className="grid grid-cols-3 gap-4">
                <StatCard title="Overall Readiness" value={78} icon={Target} scoreType trend={5} />
                <StatCard title="Market Alignment" value={72} icon={TrendingUp} scoreType trend={3} />
                <StatCard title="Interview Probability" value="High" icon={Brain} subtitle="Based on latest analysis" />
            </div>
            <div className="grid lg:grid-cols-2 gap-6">
                <CareerRadarChart />
                <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="card-elevated rounded-2xl p-6">
                    <h3 className="text-sm font-semibold mb-4">Readiness by Domain</h3>
                    {[
                        { domain: "Backend Engineering", score: 82 },
                        { domain: "Frontend Development", score: 65 },
                        { domain: "System Design", score: 70 },
                        { domain: "Cloud / DevOps", score: 55 },
                        { domain: "Testing & Quality", score: 74 },
                        { domain: "Data / ML", score: 48 },
                    ].map((item) => (
                        <div key={item.domain} className="mb-4">
                            <div className="flex justify-between text-sm mb-1.5">
                                <span className="text-muted-foreground">{item.domain}</span>
                                <span className={`font-medium ${item.score >= 75 ? "text-success" : item.score >= 55 ? "text-warning" : "text-error"}`}>{item.score}%</span>
                            </div>
                            <div className="h-2 bg-border rounded-full overflow-hidden">
                                <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${item.score}%` }}
                                    transition={{ duration: 0.7, delay: 0.1 }}
                                    className={`h-full rounded-full ${item.score >= 75 ? "bg-success" : item.score >= 55 ? "bg-warning" : "bg-error"}`}
                                />
                            </div>
                        </div>
                    ))}
                </motion.div>
            </div>
        </div>
    );
}
