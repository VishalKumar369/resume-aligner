import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "@/app/dashboard/page";
import { alignmentService } from "@/services/api";

vi.mock("@/services/api", () => ({
    alignmentService: { getAll: vi.fn(), getById: vi.fn() },
    // AnalysisTrackerTable builds insight links with this.
    companySlug: (n: string) => (n || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, ""),
    apiErrorMessage: (e: any) => e?.message ?? "error",
}));

const analyses = [
    {
        id: "a-1", resume_id: "r-1", jd_id: "jd-1",
        alignment_score: 82, ats_score: 61,
        company: "Acme Corp", role: "Data Scientist", resume_label: "Main Resume",
        created_at: "2026-08-02T00:00:00Z",
    },
    {
        id: "a-2", resume_id: "r-1", jd_id: "jd-2",
        alignment_score: 70, ats_score: 55,
        company: "Globex", role: "ML Engineer", resume_label: "Main Resume",
        created_at: "2026-08-01T00:00:00Z",
    },
];

const detailFor: Record<string, any> = {
    "a-1": {
        id: "a-1", skill_match_score: 88, experience_match_score: 63,
        breakdown: { skill_match: 88, seniority_match: 63 },
        matched_skills: ["Python"], partial_skills: [],
        missing_skills: [{ skill: "Kafka", importance: "preferred", priority: "P3" }],
        improvement_suggestions: ["Add a metric to your top bullet."], ats_warnings: [],
        extraction_health: { resume_ok: true },
    },
    "a-2": {
        id: "a-2", skill_match_score: 74, experience_match_score: 50,
        breakdown: { skill_match: 74, seniority_match: 50 },
        matched_skills: [], partial_skills: [],
        missing_skills: [{ skill: "PyTorch", importance: "mandatory", priority: "P1" }],
        improvement_suggestions: [], ats_warnings: [],
        extraction_health: { resume_ok: true },
    },
};

describe("DashboardPage — per-analysis view", () => {
    beforeEach(() => {
        vi.mocked(alignmentService.getAll).mockResolvedValue({ data: analyses } as any);
        vi.mocked(alignmentService.getById).mockImplementation(
            (id: string) => Promise.resolve({ data: detailFor[id] }) as any
        );
    });

    it("shows the empty state when there are no analyses", async () => {
        vi.mocked(alignmentService.getAll).mockResolvedValue({ data: [] } as any);
        render(<DashboardPage />);

        expect(await screen.findByText("No analysis yet")).toBeInTheDocument();
    });

    it("defaults to the newest analysis", async () => {
        render(<DashboardPage />);

        expect(await screen.findByRole("heading", { name: /Acme Corp/i, level: 2 })).toBeInTheDocument();
        expect(alignmentService.getById).toHaveBeenCalledWith("a-1");

        // Per-run cards are present.
        expect(screen.getByText("JD Alignment")).toBeInTheDocument();
        expect(screen.getByText("Skill Match")).toBeInTheDocument();
        expect(screen.getByText("Experience Match")).toBeInTheDocument();
    });

    it("lists every run in the tracker with a header summary", async () => {
        render(<DashboardPage />);
        await screen.findByRole("heading", { name: /Acme Corp/i, level: 2 });

        expect(screen.getByText(/2 analyses · 1 resume · 2 roles/)).toBeInTheDocument();
        const table = screen.getByRole("table");
        expect(within(table).getAllByRole("button")).toHaveLength(2);
    });

    it("switches the whole view when another run is selected", async () => {
        render(<DashboardPage />);
        await screen.findByRole("heading", { name: /Acme Corp/i, level: 2 });

        await userEvent.click(screen.getByLabelText(/Select analysis for Globex/i));

        await waitFor(() => expect(alignmentService.getById).toHaveBeenCalledWith("a-2"));
        expect(await screen.findByRole("heading", { name: /Globex/i, level: 2 })).toBeInTheDocument();
    });

    it("builds recommendations from the selected run", async () => {
        render(<DashboardPage />);

        expect(await screen.findByText("Add a metric to your top bullet.")).toBeInTheDocument();
        // Missing skill becomes an actionable recommendation.
        expect(screen.getByText(/Add evidence of Kafka/i)).toBeInTheDocument();
    });
});
