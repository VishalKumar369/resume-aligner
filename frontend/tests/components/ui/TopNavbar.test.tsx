import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { TopNavbar } from "@/components/ui/TopNavbar";
import { useAuthStore } from "@/store/authStore";
import { useUiStore } from "@/store/uiStore";
import { routerMock } from "../../mocks/router";

const signIn = (name: string, email = "ada@example.com") =>
    useAuthStore.setState({ token: "jwt-123", user: { id: "u-1", name, email } });

describe("TopNavbar", () => {
    it("renders the page title when one is given", () => {
        signIn("Ada Lovelace");
        render(<TopNavbar title="Dashboard" />);

        expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    });

    it("opens the mobile navigation drawer from the hamburger", async () => {
        signIn("Ada Lovelace");
        render(<TopNavbar />);

        expect(useUiStore.getState().mobileNavOpen).toBe(false);
        await userEvent.click(screen.getByRole("button", { name: /open menu/i }));

        expect(useUiStore.getState().mobileNavOpen).toBe(true);
    });

    it("links to a new analysis", () => {
        signIn("Ada Lovelace");
        render(<TopNavbar />);

        expect(screen.getByRole("link", { name: /new analysis/i })).toHaveAttribute("href", "/upload");
    });

    it("builds initials from the first and last name", () => {
        signIn("Ada Lovelace");
        render(<TopNavbar />);

        expect(screen.getByRole("button", { name: "Account menu" })).toHaveTextContent("AL");
    });

    it("uses a single initial for a one-word name", () => {
        signIn("Ada");
        render(<TopNavbar />);

        expect(screen.getByRole("button", { name: "Account menu" })).toHaveTextContent("A");
    });

    it("falls back to the email when there is no name", () => {
        signIn("", "zara@example.com");
        render(<TopNavbar />);

        expect(screen.getByRole("button", { name: "Account menu" })).toHaveTextContent("Z");
    });

    it("falls back to 'U' with no user at all", () => {
        render(<TopNavbar />);

        expect(screen.getByRole("button", { name: "Account menu" })).toHaveTextContent("U");
    });

    it("falls back to 'U' when the name is only whitespace", () => {
        signIn("   ", "");
        render(<TopNavbar />);

        expect(screen.getByRole("button", { name: "Account menu" })).toHaveTextContent("U");
    });

    it("keeps the account menu closed until it is clicked", () => {
        signIn("Ada Lovelace");
        render(<TopNavbar />);

        const trigger = screen.getByRole("button", { name: "Account menu" });
        expect(trigger).toHaveAttribute("aria-expanded", "false");
        expect(screen.queryByRole("menu")).toBeNull();
    });

    it("shows the signed-in identity in the open menu", async () => {
        signIn("Ada Lovelace");
        render(<TopNavbar />);

        await userEvent.click(screen.getByRole("button", { name: "Account menu" }));

        expect(screen.getByRole("menu")).toBeInTheDocument();
        expect(screen.getByText("Ada Lovelace")).toBeInTheDocument();
        expect(screen.getByText("ada@example.com")).toBeInTheDocument();
        expect(screen.getByRole("menuitem", { name: /account settings/i })).toHaveAttribute(
            "href",
            "/settings"
        );
    });

    it("shows a placeholder name when the user has none", async () => {
        signIn("", "zara@example.com");
        render(<TopNavbar />);

        await userEvent.click(screen.getByRole("button", { name: "Account menu" }));

        expect(screen.getByText("Your account")).toBeInTheDocument();
    });

    it("closes the menu on a click outside", async () => {
        signIn("Ada Lovelace");
        render(<TopNavbar />);

        await userEvent.click(screen.getByRole("button", { name: "Account menu" }));
        expect(screen.getByRole("menu")).toBeInTheDocument();

        await userEvent.click(document.body);

        expect(screen.queryByRole("menu")).toBeNull();
    });

    it("clears the session and returns to login on log out", async () => {
        signIn("Ada Lovelace");
        render(<TopNavbar />);

        await userEvent.click(screen.getByRole("button", { name: "Account menu" }));
        await userEvent.click(screen.getByRole("menuitem", { name: /log out/i }));

        expect(useAuthStore.getState().token).toBeNull();
        expect(useAuthStore.getState().user).toBeNull();
        expect(routerMock.replace).toHaveBeenCalledWith("/auth/login");
        expect(screen.queryByRole("menu")).toBeNull();
    });
});
