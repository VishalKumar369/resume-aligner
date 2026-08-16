import { beforeEach, describe, expect, it } from "vitest";

import { useDashboardStore } from "@/store/dashboardStore";

const analytics = {
    atsScore: 78,
    alignmentScore: 64,
    careerReadiness: 71,
    interviewProbability: "Moderate",
    skillGaps: [{ skill: "Airflow", priority: "P1" }],
    recentAlignments: [{ company: "Acme", score: 64 }],
};

describe("useDashboardStore", () => {
    beforeEach(() => {
        useDashboardStore.setState({ analytics: null, loading: false });
    });

    it("starts empty and not loading", () => {
        expect(useDashboardStore.getState().analytics).toBeNull();
        expect(useDashboardStore.getState().loading).toBe(false);
    });

    it("stores the analytics payload", () => {
        useDashboardStore.getState().setAnalytics(analytics);

        expect(useDashboardStore.getState().analytics).toEqual(analytics);
    });

    it("toggles the loading flag independently of the data", () => {
        useDashboardStore.getState().setAnalytics(analytics);
        useDashboardStore.getState().setLoading(true);

        expect(useDashboardStore.getState().loading).toBe(true);
        expect(useDashboardStore.getState().analytics).toEqual(analytics);
    });
});
