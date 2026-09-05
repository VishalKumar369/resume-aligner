import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SkillsPage from "@/app/dashboard/skills/page";
import { dashboardService } from "@/services/api";

vi.mock("@/services/api", () => ({
    dashboardService: { getSummary: vi.fn() },
    apiErrorMessage: (e: any) => e?.message ?? "error",
}));

const summary = {
    has_data: true,
    skill_gap_detail: [
        { skill: "Kafka", priority: "P1", category: "messaging", jd_count: 2, mandatory: true },
        { skill: "Airflow", priority: "P3", category: "data", jd_count: 1, mandatory: false },
    ],
    partial_skills: [{ skill: "Kubernetes", covered_by: "Docker", jd_count: 1 }],
};

describe("SkillsPage — add gap as a goal", () => {
    beforeEach(() => {
        vi.mocked(dashboardService.getSummary).mockResolvedValue({ data: summary } as any);
    });

    it("offers an 'Add goal' link per gap, coloured by priority", async () => {
        render(<SkillsPage />);

        const kafka = await screen.findByTitle("Add Kafka as a personal goal");
        expect(kafka).toHaveAttribute(
            "href",
            "/notes?compose=1&title=Learn+Kafka&category=Goal&color=error"
        );
    });

    it("offers an 'Add goal' link for partially-covered skills", async () => {
        render(<SkillsPage />);

        const k8s = await screen.findByTitle("Add Kubernetes as a personal goal");
        expect(k8s).toHaveAttribute(
            "href",
            "/notes?compose=1&title=Strengthen+Kubernetes&category=Goal&color=warning"
        );
    });
});
