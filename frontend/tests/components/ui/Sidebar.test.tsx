import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Sidebar } from "@/components/ui/Sidebar";
import { setPathname } from "../../mocks/router";

/** The clickable row for a nav label (the styled div inside the link). */
const navRow = (label: string) => screen.getByText(label).closest("a")!.firstElementChild!;

describe("Sidebar", () => {
    it("renders every navigation destination", () => {
        render(<Sidebar />);

        for (const label of [
            "Overview",
            "Upload & Analyze",
            "Career Readiness",
            "Skill Gaps",
            "Resume Versions",
            "Learning Roadmap",
            "Company Intel",
            "Settings",
        ]) {
            expect(screen.getByText(label)).toBeInTheDocument();
        }
    });

    it("groups the analytics pages under a heading", () => {
        render(<Sidebar />);

        expect(screen.getByText("Analytics")).toBeInTheDocument();
        expect(screen.getByText("Skill Gaps").closest("a")).toHaveAttribute("href", "/dashboard/skills");
    });

    it("highlights the current page", () => {
        setPathname("/dashboard");
        render(<Sidebar />);

        expect(navRow("Overview")).toHaveClass("text-primary");
        expect(navRow("Settings")).not.toHaveClass("text-primary");
    });

    it("highlights only the sub-page on a nested analytics route", () => {
        setPathname("/dashboard/skills");
        render(<Sidebar />);

        expect(navRow("Skill Gaps")).toHaveClass("text-primary");
        // "/dashboard" is matched exactly, so Overview must not light up too.
        expect(navRow("Overview")).not.toHaveClass("text-primary");
    });

    it("matches nested routes for non-dashboard sections", () => {
        setPathname("/company/google");
        render(<Sidebar />);

        expect(navRow("Company Intel")).toHaveClass("text-primary");
    });

    it("hides the labels once collapsed", async () => {
        render(<Sidebar />);

        await userEvent.click(screen.getByRole("button", { name: /collapse/i }));

        expect(screen.queryByText("Overview")).toBeNull();
        expect(screen.queryByText("Analytics")).toBeNull();
        // The links themselves stay, just icon-only.
        expect(screen.getAllByRole("link").length).toBeGreaterThan(0);
    });

    it("expands again on a second click", async () => {
        render(<Sidebar />);
        const toggle = screen.getByRole("button", { name: /collapse/i });

        await userEvent.click(toggle);
        await userEvent.click(screen.getByRole("button"));

        expect(screen.getByText("Overview")).toBeInTheDocument();
    });
});
