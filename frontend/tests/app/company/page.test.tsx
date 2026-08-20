import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CompanyPage from "@/app/company/[companyId]/page";
import { alignmentService, companyService, jdService, resumeService } from "@/services/api";

// Controllable route params/search for this page (overrides the global setup mock).
let mockParams: Record<string, string> = { companyId: "acme" };
let mockSearch = new URLSearchParams();

vi.mock("next/navigation", () => ({
    useParams: () => mockParams,
    useSearchParams: () => mockSearch,
    useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
    usePathname: () => "/company/acme",
}));

vi.mock("@/services/api", () => ({
    companyService: { getInsights: vi.fn() },
    jdService: { getById: vi.fn() },
    alignmentService: { getById: vi.fn() },
    resumeService: { getVersions: vi.fn(), download: vi.fn() },
    apiErrorMessage: (e: any) => e?.message ?? "error",
}));

const jd = {
    title: "Senior Backend Engineer",
    company_name: "Acme",
    url: "https://jobs.acme.test/be",
    structured_data: {
        seniority: "senior",
        requirements: { mandatory_skills: ["Python", "FastAPI"], preferred_skills: ["Kafka"] },
    },
};

const alignment = {
    alignment_score: 70, ats_score: 60, skill_match_score: 80, experience_match_score: 55,
    missing_skills: [{ skill: "Docker", importance: "mandatory", priority: "P1" }],
    matched_skills: ["Python"],
};

const version = {
    id: "v-1", jd_id: "jd-1", version_number: 1, label: "Tailored for Acme",
    filename: "cv_v1.docx", ats_score: 75, alignment_score: 80,
    baseline_ats_score: 60, baseline_alignment_score: 70,
};

describe("CompanyPage — analysis spotlight", () => {
    beforeEach(() => {
        mockParams = { companyId: "acme" };
        mockSearch = new URLSearchParams("jd=jd-1&resume=r-1&alignment=al-1");

        vi.mocked(jdService.getById).mockResolvedValue({ data: jd } as any);
        vi.mocked(alignmentService.getById).mockResolvedValue({ data: alignment } as any);
        vi.mocked(resumeService.getVersions).mockResolvedValue({ data: [version] } as any);
        vi.mocked(resumeService.download).mockResolvedValue({ data: new Blob(["x"]) } as any);
        // No aggregate company profile in these tests: spotlight-only view.
        vi.mocked(companyService.getInsights).mockRejectedValue({
            response: { data: { detail: "No job descriptions saved for 'acme'." } },
        });

        // jsdom doesn't implement object URLs the blob download uses.
        (URL as any).createObjectURL = vi.fn(() => "blob:mock");
        (URL as any).revokeObjectURL = vi.fn();
    });

    it("shows the role, the match, and what the role asks for", async () => {
        render(<CompanyPage />);

        expect(await screen.findByRole("heading", { name: /Senior Backend Engineer/i })).toBeInTheDocument();
        // Per-run match cards.
        expect(screen.getByText("JD Alignment")).toBeInTheDocument();
        expect(screen.getByText("Skill Match")).toBeInTheDocument();
        // Requirements from the JD.
        expect(screen.getByText("What this role asks for")).toBeInTheDocument();
        expect(screen.getByText("Kafka")).toBeInTheDocument();
    });

    it("surfaces this role's gaps and matched skills", async () => {
        render(<CompanyPage />);

        expect(await screen.findByText("Gaps for this role")).toBeInTheDocument();
        expect(screen.getByText("Docker")).toBeInTheDocument();
    });

    it("offers the tailored resume for download and fetches the blob", async () => {
        render(<CompanyPage />);

        expect(await screen.findByText("Your tailored resume")).toBeInTheDocument();
        expect(screen.getByText("Tailored for Acme")).toBeInTheDocument();

        await userEvent.click(screen.getByRole("button", { name: /docx/i }));
        expect(resumeService.download).toHaveBeenCalledWith("v-1", "docx");

        await userEvent.click(screen.getByRole("button", { name: /pdf/i }));
        expect(resumeService.download).toHaveBeenCalledWith("v-1", "pdf");
    });

    it("prompts to optimize when no tailored resume exists for the role", async () => {
        vi.mocked(resumeService.getVersions).mockResolvedValue({ data: [] } as any);
        render(<CompanyPage />);

        expect(await screen.findByText(/No tailored resume for this role yet/i)).toBeInTheDocument();
        expect(screen.getByRole("link", { name: /Optimize for this role/i })).toHaveAttribute("href", "/upload");
    });

    it("notes when the posting has no company-wide profile", async () => {
        render(<CompanyPage />);

        expect(await screen.findByText(/No company-wide profile for this posting/i)).toBeInTheDocument();
    });

    it("filters out tailored versions from other roles", async () => {
        vi.mocked(resumeService.getVersions).mockResolvedValue({
            data: [version, { ...version, id: "v-2", jd_id: "jd-OTHER", label: "For a different role" }],
        } as any);
        render(<CompanyPage />);

        expect(await screen.findByText("Tailored for Acme")).toBeInTheDocument();
        expect(screen.queryByText("For a different role")).toBeNull();
    });
});

describe("CompanyPage — aggregate view (no analysis scope)", () => {
    beforeEach(() => {
        mockParams = { companyId: "acme" };
        mockSearch = new URLSearchParams();
        vi.mocked(companyService.getInsights).mockResolvedValue({
            data: {
                company: "Acme", jd_count: 2, roles: ["Backend"], locations: [], work_modes: [],
                demanded_skills: ["Python"], preferred_skills: [], your_best_alignment: 70,
                your_average_alignment: 65, your_gaps_here: [], postings: [],
                source: "Derived from the job descriptions you saved for this company.",
            },
        } as any);
    });

    it("still shows the company profile when opened without an analysis", async () => {
        render(<CompanyPage />);

        expect(await screen.findByRole("heading", { name: "Acme" })).toBeInTheDocument();
        expect(screen.getByText("What their postings ask for")).toBeInTheDocument();
        expect(jdService.getById).not.toHaveBeenCalled();
    });
});
