import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CompanyTrackerTable, type CompanyMatch } from "@/components/dashboard/CompanyTrackerTable";

const match = (overrides: Partial<CompanyMatch> = {}): CompanyMatch => ({
    company: "Acme Corp",
    role: "Data Scientist",
    jd_id: "jd-1",
    alignment_score: 82.4,
    ats_score: 61,
    roles_tracked: 3,
    ...overrides,
});

describe("CompanyTrackerTable", () => {
    it("explains what to do when nothing has been analyzed", () => {
        render(<CompanyTrackerTable matches={[]} />);

        expect(screen.getByText(/No analyzed roles yet/)).toBeInTheDocument();
        expect(screen.queryByRole("table")).toBeNull();
    });

    it("renders one row per company with its best-matching role", () => {
        render(<CompanyTrackerTable matches={[match(), match({ company: "Globex", jd_id: "jd-2" })]} />);

        const rows = within(screen.getByRole("table")).getAllByRole("row");
        // One header row plus one row per company.
        expect(rows).toHaveLength(3);
        expect(screen.getByText("Acme Corp")).toBeInTheDocument();
        expect(screen.getByText("Globex")).toBeInTheDocument();
    });

    it("shows rounded alignment and ATS scores and the roles tracked", () => {
        render(<CompanyTrackerTable matches={[match()]} />);

        expect(screen.getByText("82%")).toBeInTheDocument();
        expect(screen.getByText("61%")).toBeInTheDocument();
        expect(screen.getByText("3")).toBeInTheDocument();
    });

    it("tones each score by the shared thresholds", () => {
        render(<CompanyTrackerTable matches={[match({ alignment_score: 80, ats_score: 30 })]} />);

        expect(screen.getByText("80%")).toHaveClass("text-success");
        expect(screen.getByText("30%")).toHaveClass("text-error");
    });

    it("links to company insights using the backend-compatible slug", () => {
        render(<CompanyTrackerTable matches={[match({ company: "AT&T Inc." })]} />);

        expect(screen.getByRole("link", { name: /insights/i })).toHaveAttribute(
            "href",
            "/company/at-t-inc"
        );
    });
});
