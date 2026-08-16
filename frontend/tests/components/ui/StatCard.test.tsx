import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SkeletonCard, StatCard } from "@/components/ui/StatCard";

describe("StatCard", () => {
    it("renders the title and a plain value as given", () => {
        render(<StatCard title="Resumes analyzed" value={12} />);

        expect(screen.getByText("Resumes analyzed")).toBeInTheDocument();
        expect(screen.getByText("12")).toBeInTheDocument();
    });

    it("formats and colours the value when it is a score", () => {
        render(<StatCard title="ATS score" value={82.4} scoreType />);

        const value = screen.getByText("82%");
        expect(value).toHaveClass("text-success");
    });

    it("colours a failing score as an error", () => {
        render(<StatCard title="ATS score" value={41} scoreType />);

        expect(screen.getByText("41%")).toHaveClass("text-error");
    });

    it("parses a numeric string score", () => {
        render(<StatCard title="ATS score" value="63.6" scoreType />);

        expect(screen.getByText("64%")).toHaveClass("text-warning");
    });

    it("shows a positive trend as a success badge", () => {
        render(<StatCard title="Alignment" value={70} trend={8} />);

        const badge = screen.getByText("8%");
        expect(badge.closest("div")).toHaveClass("text-success");
    });

    it("shows a negative trend as an error badge with the magnitude only", () => {
        render(<StatCard title="Alignment" value={70} trend={-5} />);

        const badge = screen.getByText("5%");
        expect(badge.closest("div")).toHaveClass("text-error");
    });

    it("treats a flat trend as neutral", () => {
        render(<StatCard title="Alignment" value={70} trend={0} />);

        expect(screen.getByText("0%").closest("div")).toHaveClass("text-muted");
    });

    it("omits the trend badge when no trend is supplied", () => {
        render(<StatCard title="Alignment" value={70} subtitle="last 30 days" />);

        expect(screen.getByText("last 30 days")).toBeInTheDocument();
        expect(screen.queryByText(/%$/)).toBeNull();
    });

    it("renders the supplied icon", () => {
        const Icon = () => <svg data-testid="stat-icon" />;
        render(<StatCard title="Alignment" value={70} icon={Icon} />);

        expect(screen.getByTestId("stat-icon")).toBeInTheDocument();
    });

    it("merges an extra class onto the card", () => {
        const { container } = render(<StatCard title="Alignment" value={70} className="col-span-2" />);

        expect(container.firstChild).toHaveClass("col-span-2");
    });
});

describe("SkeletonCard", () => {
    it("renders a pulsing placeholder", () => {
        const { container } = render(<SkeletonCard />);

        expect(container.firstChild).toHaveClass("animate-pulse");
    });
});
