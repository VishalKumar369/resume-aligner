import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CompanyIndexPage from "@/app/company/page";
import { companyService } from "@/services/api";

vi.mock("@/services/api", () => ({
    companyService: { getAll: vi.fn() },
    apiErrorMessage: (e: any) => e?.message ?? "error",
}));

const companies = [
    {
        company_id: "acme", company: "Acme", jd_count: 2,
        roles: ["Backend Engineer", "Platform Engineer"], demanded_skills: ["Python", "FastAPI"],
        your_best_alignment: 82, your_average_alignment: 70, gap_count: 3,
        last_activity: "2026-08-01T00:00:00Z",
    },
    {
        company_id: "globex", company: "Globex", jd_count: 1,
        roles: ["ML Engineer"], demanded_skills: ["PyTorch"],
        your_best_alignment: 65, your_average_alignment: 65, gap_count: 0, last_activity: null,
    },
];

describe("CompanyIndexPage", () => {
    beforeEach(() => {
        vi.mocked(companyService.getAll).mockResolvedValue({ data: companies } as any);
    });

    it("lists a card per company with a summary count", async () => {
        render(<CompanyIndexPage />);

        expect(await screen.findByText("Acme")).toBeInTheDocument();
        expect(screen.getByText("Globex")).toBeInTheDocument();
        expect(screen.getByText("2 companies from your analyzed postings")).toBeInTheDocument();
    });

    it("links each card to that company's page", async () => {
        render(<CompanyIndexPage />);
        await screen.findByText("Acme");

        expect(screen.getByRole("link", { name: /Acme/i })).toHaveAttribute("href", "/company/acme");
        expect(screen.getByRole("link", { name: /Globex/i })).toHaveAttribute("href", "/company/globex");
    });

    it("shows the best alignment, roles, and demanded skills", async () => {
        render(<CompanyIndexPage />);
        await screen.findByText("Acme");

        expect(screen.getByText("82%")).toBeInTheDocument();
        expect(screen.getByText(/2 roles/)).toBeInTheDocument();
        expect(screen.getByText("Python")).toBeInTheDocument();
        expect(screen.getByText(/3 gaps/)).toBeInTheDocument();
    });

    it("shows an empty state when there are no companies", async () => {
        vi.mocked(companyService.getAll).mockResolvedValue({ data: [] } as any);
        render(<CompanyIndexPage />);

        expect(await screen.findByText("No companies yet")).toBeInTheDocument();
    });

    it("links a nameless posting straight to its analysis", async () => {
        vi.mocked(companyService.getAll).mockResolvedValue({
            data: [{
                company_id: "jd-9", company: "Data Scientist", named: false,
                jd_id: "jd-9", resume_id: "r-1", alignment_id: "al-1",
                jd_count: 1, roles: ["Data Scientist"], demanded_skills: [],
                your_best_alignment: 60, your_average_alignment: 60, gap_count: 0, last_activity: null,
            }],
        } as any);
        render(<CompanyIndexPage />);

        // No aggregate company page exists, so it opens the scoped analysis.
        const link = await screen.findByRole("link", { name: /Data Scientist/i });
        expect(link).toHaveAttribute("href", "/company/jd-9?jd=jd-9&resume=r-1&alignment=al-1");
        expect(screen.getByText("Single posting")).toBeInTheDocument();
    });
});
