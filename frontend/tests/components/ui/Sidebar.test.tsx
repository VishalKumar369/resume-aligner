import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Sidebar } from "@/components/ui/Sidebar";
import { useUiStore } from "@/store/uiStore";
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

    it("keeps Company Intel active on any company route, not just the demo one", () => {
        // Arriving from an analysis's Insights link lands on a different slug.
        setPathname("/company/at-t-inc");
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

describe("Sidebar mobile drawer", () => {
    it("is not shown by default", () => {
        render(<Sidebar />);
        expect(screen.queryByRole("button", { name: /close menu/i })).toBeNull();
    });

    it("renders the drawer when the mobile nav is opened", () => {
        useUiStore.setState({ mobileNavOpen: true });
        render(<Sidebar />);

        expect(screen.getByRole("button", { name: /close menu/i })).toBeInTheDocument();
        // The nav is present in both the desktop rail and the open drawer.
        expect(screen.getAllByText("Overview")).toHaveLength(2);
    });

    it("closes on the close button", async () => {
        useUiStore.setState({ mobileNavOpen: true });
        render(<Sidebar />);

        await userEvent.click(screen.getByRole("button", { name: /close menu/i }));

        expect(useUiStore.getState().mobileNavOpen).toBe(false);
    });

    it("closes after tapping a drawer link", async () => {
        useUiStore.setState({ mobileNavOpen: true });
        render(<Sidebar />);

        // Index 1 is the drawer's copy; its links close the drawer on navigate.
        await userEvent.click(screen.getAllByText("Skill Gaps")[1]);

        expect(useUiStore.getState().mobileNavOpen).toBe(false);
    });
});
