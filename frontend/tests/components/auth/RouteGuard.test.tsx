import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RouteGuard } from "@/components/auth/RouteGuard";
import { useAuthStore } from "@/store/authStore";
import { routerMock, setPathname } from "../../mocks/router";

const signIn = () =>
    useAuthStore.setState({
        token: "jwt-123",
        user: { id: "u-1", name: "Ada", email: "ada@example.com" },
    });

const renderGuard = () =>
    render(
        <RouteGuard>
            <p>protected content</p>
        </RouteGuard>
    );

describe("RouteGuard", () => {
    it("redirects a signed-out visitor away from a private page", async () => {
        setPathname("/dashboard");

        renderGuard();

        await waitFor(() => expect(routerMock.replace).toHaveBeenCalledWith("/auth/login"));
        expect(screen.queryByText("protected content")).toBeNull();
    });

    it("renders a private page for a signed-in user", async () => {
        setPathname("/dashboard");
        signIn();

        renderGuard();

        expect(await screen.findByText("protected content")).toBeInTheDocument();
        expect(routerMock.replace).not.toHaveBeenCalled();
    });

    it("lets a signed-out visitor see public pages", async () => {
        setPathname("/auth/login");

        renderGuard();

        expect(await screen.findByText("protected content")).toBeInTheDocument();
        expect(routerMock.replace).not.toHaveBeenCalled();
    });

    it("keeps the landing page open to everyone", async () => {
        setPathname("/");
        signIn();

        renderGuard();

        expect(await screen.findByText("protected content")).toBeInTheDocument();
        expect(routerMock.replace).not.toHaveBeenCalled();
    });

    it("sends a signed-in user away from login and signup", async () => {
        setPathname("/auth/signup");
        signIn();

        renderGuard();

        await waitFor(() => expect(routerMock.replace).toHaveBeenCalledWith("/dashboard"));
    });

    it("guards nested private paths too", async () => {
        setPathname("/dashboard/skills");

        renderGuard();

        await waitFor(() => expect(routerMock.replace).toHaveBeenCalledWith("/auth/login"));
    });

    it("ignores a query string when deciding whether a path is public", async () => {
        setPathname("/auth/login?next=/dashboard");

        renderGuard();

        expect(await screen.findByText("protected content")).toBeInTheDocument();
        expect(routerMock.replace).not.toHaveBeenCalled();
    });
});
