import { beforeEach, describe, expect, it } from "vitest";

import { useAuthStore, type AuthUser } from "@/store/authStore";

const user: AuthUser = {
    id: "u-1",
    name: "Ada Lovelace",
    email: "ada@example.com",
    targetRole: "Data Scientist",
};

describe("useAuthStore", () => {
    beforeEach(() => {
        useAuthStore.setState({ user: null, token: null });
    });

    it("starts signed out", () => {
        expect(useAuthStore.getState().user).toBeNull();
        expect(useAuthStore.getState().token).toBeNull();
    });

    it("stores the user and token together on sign-in", () => {
        useAuthStore.getState().setUser(user, "jwt-123");

        expect(useAuthStore.getState().user).toEqual(user);
        expect(useAuthStore.getState().token).toBe("jwt-123");
    });

    it("patches user fields without touching the token", () => {
        useAuthStore.getState().setUser(user, "jwt-123");
        useAuthStore.getState().updateUser({ name: "Ada L.", targetRole: "ML Engineer" });

        const state = useAuthStore.getState();
        expect(state.user).toEqual({ ...user, name: "Ada L.", targetRole: "ML Engineer" });
        expect(state.token).toBe("jwt-123");
    });

    it("ignores a patch when nobody is signed in", () => {
        useAuthStore.getState().updateUser({ name: "Nobody" });

        expect(useAuthStore.getState().user).toBeNull();
    });

    it("clears both user and token on sign-out", () => {
        useAuthStore.getState().setUser(user, "jwt-123");
        useAuthStore.getState().clearAuth();

        expect(useAuthStore.getState().user).toBeNull();
        expect(useAuthStore.getState().token).toBeNull();
    });

    it("persists the session so a reload keeps the user signed in", () => {
        useAuthStore.getState().setUser(user, "jwt-123");

        const persisted = JSON.parse(localStorage.getItem("auth-storage") || "{}");
        expect(persisted.state.token).toBe("jwt-123");
        expect(persisted.state.user.email).toBe("ada@example.com");
    });
});
