import { create } from "zustand";

interface DashboardAnalytics {
    atsScore: number;
    alignmentScore: number;
    careerReadiness: number;
    interviewProbability: string;
    skillGaps: { skill: string; priority: string }[];
    recentAlignments: { company: string; score: number }[];
}

interface DashboardState {
    analytics: DashboardAnalytics | null;
    loading: boolean;
    setAnalytics: (data: DashboardAnalytics) => void;
    setLoading: (l: boolean) => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
    analytics: null,
    loading: false,
    setAnalytics: (analytics) => set({ analytics }),
    setLoading: (loading) => set({ loading }),
}));
