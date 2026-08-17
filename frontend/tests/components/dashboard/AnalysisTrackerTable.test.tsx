import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AnalysisTrackerTable, type AnalysisRow } from "@/components/dashboard/AnalysisTrackerTable";

const row = (overrides: Partial<AnalysisRow> = {}): AnalysisRow => ({
    id: "a-1",
    resume_id: "r-1",
    jd_id: "jd-1",
    alignment_score: 82.4,
    ats_score: 61,
    company: "Acme Corp",
    role: "Data Scientist",
    resume_label: "Main Resume",
    created_at: "2026-08-01T00:00:00Z",
    ...overrides,
});

const noop = () => {};

describe("AnalysisTrackerTable", () => {
    it("prompts to analyze when there are no runs", () => {
        render(<AnalysisTrackerTable analyses={[]} activeId={null} onSelect={noop} />);

        expect(screen.getByText(/No analyses yet/)).toBeInTheDocument();
        expect(screen.queryByRole("table")).toBeNull();
    });

    it("renders one row per analysis, including repeat runs of a pair", () => {
        render(
            <AnalysisTrackerTable
                analyses={[row(), row({ id: "a-2", alignment_score: 70 })]}
                activeId="a-1"
                onSelect={noop}
            />
        );

        const rows = within(screen.getByRole("table")).getAllByRole("button");
        expect(rows).toHaveLength(2);
        expect(screen.getByText("82%")).toBeInTheDocument();
        expect(screen.getByText("70%")).toBeInTheDocument();
    });

    it("marks the active row as pressed", () => {
        render(
            <AnalysisTrackerTable
                analyses={[row({ id: "a-1" }), row({ id: "a-2" })]}
                activeId="a-2"
                onSelect={noop}
            />
        );

        const rows = screen.getAllByRole("button");
        expect(rows[0]).toHaveAttribute("aria-pressed", "false");
        expect(rows[1]).toHaveAttribute("aria-pressed", "true");
    });

    it("selects a run when its row is clicked", async () => {
        const onSelect = vi.fn();
        render(
            <AnalysisTrackerTable
                analyses={[row({ id: "a-1" }), row({ id: "a-2" })]}
                activeId="a-1"
                onSelect={onSelect}
            />
        );

        await userEvent.click(screen.getAllByRole("button")[1]);

        expect(onSelect).toHaveBeenCalledWith("a-2");
    });

    it("selects a run via the keyboard", async () => {
        const onSelect = vi.fn();
        render(<AnalysisTrackerTable analyses={[row({ id: "a-1" })]} activeId={null} onSelect={onSelect} />);

        screen.getByRole("button").focus();
        await userEvent.keyboard("{Enter}");

        expect(onSelect).toHaveBeenCalledWith("a-1");
    });

    it("links to company insights using the backend-compatible slug", () => {
        render(<AnalysisTrackerTable analyses={[row({ company: "AT&T Inc." })]} activeId={null} onSelect={noop} />);

        expect(screen.getByRole("link", { name: /insights/i })).toHaveAttribute("href", "/company/at-t-inc");
    });

    it("hides the insights link when there is no real company", () => {
        render(
            <AnalysisTrackerTable
                analyses={[
                    row({ id: "a-1", company: null }),
                    row({ id: "a-2", company: "Unknown company" }),
                    row({ id: "a-3", company: "   " }),
                ]}
                activeId={null}
                onSelect={noop}
            />
        );

        expect(screen.queryByRole("link", { name: /insights/i })).toBeNull();
        expect(screen.getAllByText("Unknown company").length).toBeGreaterThan(0);
    });

    it("does not select the row when the insights link is clicked", async () => {
        const onSelect = vi.fn();
        render(<AnalysisTrackerTable analyses={[row()]} activeId={null} onSelect={onSelect} />);

        await userEvent.click(screen.getByRole("link", { name: /insights/i }));

        expect(onSelect).not.toHaveBeenCalled();
    });
});
