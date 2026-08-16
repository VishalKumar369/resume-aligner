import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
    CardSkeleton,
    EmptyState,
    ErrorState,
    PriorityBadge,
    ScorePill,
    Skeleton,
    StatSkeletonRow,
} from "@/components/ui/States";

describe("Skeletons", () => {
    it("renders a pulsing block with the requested size", () => {
        const { container } = render(<Skeleton className="h-10" />);

        expect(container.firstChild).toHaveClass("animate-pulse", "h-10");
    });

    it("applies a custom card height", () => {
        const { container } = render(<CardSkeleton height="h-64" />);

        expect(container.firstChild).toHaveClass("h-64");
    });

    it("renders four placeholder stats by default and honours an override", () => {
        const { container, rerender } = render(<StatSkeletonRow />);
        expect(container.querySelectorAll(".animate-pulse")).toHaveLength(4);

        rerender(<StatSkeletonRow count={2} />);
        expect(container.querySelectorAll(".animate-pulse")).toHaveLength(2);
    });
});

describe("ErrorState", () => {
    it("shows the failure reason", () => {
        render(<ErrorState message="Cannot reach the server." />);

        expect(screen.getByText("Cannot reach the server.")).toBeInTheDocument();
        expect(screen.getByText(/Couldn't load this/)).toBeInTheDocument();
    });

    it("hides the retry button when there is nothing to retry with", () => {
        render(<ErrorState message="Cannot reach the server." />);

        expect(screen.queryByRole("button", { name: /try again/i })).toBeNull();
    });

    it("calls onRetry when the user retries", async () => {
        const onRetry = vi.fn();
        render(<ErrorState message="Failed" onRetry={onRetry} />);

        await userEvent.click(screen.getByRole("button", { name: /try again/i }));

        expect(onRetry).toHaveBeenCalledTimes(1);
    });
});

describe("EmptyState", () => {
    it("points at the upload flow by default", () => {
        render(<EmptyState title="Nothing yet" description="Analyze a resume to see scores." />);

        expect(screen.getByRole("heading", { name: "Nothing yet" })).toBeInTheDocument();
        expect(screen.getByText("Analyze a resume to see scores.")).toBeInTheDocument();

        const cta = screen.getByRole("link", { name: "Analyze a resume" });
        expect(cta).toHaveAttribute("href", "/upload");
    });

    it("accepts a custom call to action", () => {
        render(
            <EmptyState
                title="No roles"
                description="Add a job description."
                actionLabel="Add a JD"
                actionHref="/upload?tab=jd"
            />
        );

        expect(screen.getByRole("link", { name: "Add a JD" })).toHaveAttribute("href", "/upload?tab=jd");
    });
});

describe("ScorePill", () => {
    it.each([
        [91, "text-success"],
        [80, "text-success"],
        [79, "text-warning"],
        [60, "text-warning"],
        [59, "text-error"],
    ])("tones %s as %s", (score, tone) => {
        render(<ScorePill score={score} />);

        expect(screen.getByText(`${Math.round(score)}%`)).toHaveClass(tone);
    });

    it("rounds the score it displays", () => {
        render(<ScorePill score={64.7} />);

        expect(screen.getByText("65%")).toBeInTheDocument();
    });
});

describe("PriorityBadge", () => {
    it.each([
        ["P1", "Critical", "text-error"],
        ["P2", "Important", "text-warning"],
        ["P3", "Bonus", "text-primary"],
    ])("renders %s as %s", (priority, label, tone) => {
        render(<PriorityBadge priority={priority} />);

        expect(screen.getByText(label)).toHaveClass(tone);
    });

    it("falls back to the raw value and the P3 tone for an unknown priority", () => {
        render(<PriorityBadge priority="P9" />);

        expect(screen.getByText("P9")).toHaveClass("text-primary");
    });
});
