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

    it("links Insights to the company page, scoped to this analysis", () => {
        render(
            <AnalysisTrackerTable
                analyses={[row({ company: "AT&T Inc.", jd_id: "jd-1", resume_id: "r-1", id: "a-1" })]}
                activeId={null}
                onSelect={noop}
            />
        );

        expect(screen.getByRole("link", { name: /insights/i })).toHaveAttribute(
            "href",
            "/company/at-t-inc?jd=jd-1&resume=r-1&alignment=a-1"
        );
    });

    it("always shows Insights, routing by JD id when the company is unknown", () => {
        render(
            <AnalysisTrackerTable
                analyses={[row({ company: null, jd_id: "jd-9", resume_id: "r-1", id: "a-9" })]}
                activeId={null}
                onSelect={noop}
            />
        );

        // The button is never removed; with no company it falls back to the JD id
        // so the URL stays valid and the page shows the JD-scoped view.
        expect(screen.getByRole("link", { name: /insights/i })).toHaveAttribute(
            "href",
            "/company/jd-9?jd=jd-9&resume=r-1&alignment=a-9"
        );
    });

    it("does not select the row when the insights link is clicked", async () => {
        const onSelect = vi.fn();
        render(<AnalysisTrackerTable analyses={[row()]} activeId={null} onSelect={onSelect} />);

        await userEvent.click(screen.getByRole("link", { name: /insights/i }));

        expect(onSelect).not.toHaveBeenCalled();
    });

    describe("pagination", () => {
        const many = (n: number) =>
            Array.from({ length: n }, (_, i) => row({ id: `a-${i}`, jd_id: `jd-${i}`, role: `Role ${i}` }));

        it("shows only ten rows per page with a range summary", () => {
            render(<AnalysisTrackerTable analyses={many(12)} activeId={null} onSelect={noop} />);

            const bodyRows = within(screen.getByRole("table")).getAllByRole("button");
            expect(bodyRows).toHaveLength(10);
            expect(screen.getByText("Showing 1–10 of 12")).toBeInTheDocument();
            expect(screen.getByText("Page 1 of 2")).toBeInTheDocument();
        });

        it("shows the remaining rows on the next page", async () => {
            render(<AnalysisTrackerTable analyses={many(12)} activeId={null} onSelect={noop} />);

            await userEvent.click(screen.getByRole("button", { name: /next page/i }));

            expect(within(screen.getByRole("table")).getAllByRole("button")).toHaveLength(2);
            expect(screen.getByText("Showing 11–12 of 12")).toBeInTheDocument();
            expect(screen.getByText("Role 11")).toBeInTheDocument();
        });

        it("disables prev on the first page and next on the last", async () => {
            render(<AnalysisTrackerTable analyses={many(12)} activeId={null} onSelect={noop} />);

            expect(screen.getByRole("button", { name: /previous page/i })).toBeDisabled();

            await userEvent.click(screen.getByRole("button", { name: /next page/i }));
            expect(screen.getByRole("button", { name: /next page/i })).toBeDisabled();
        });

        it("shows no pagination controls for ten or fewer runs", () => {
            render(<AnalysisTrackerTable analyses={many(10)} activeId={null} onSelect={noop} />);

            expect(screen.queryByText(/Showing/)).toBeNull();
            expect(screen.queryByRole("button", { name: /next page/i })).toBeNull();
        });
    });
});
