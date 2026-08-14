import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface AuthUser {
    id: string;
    name: string;
    email: string;
    targetRole?: string | null;
}

interface AuthState {
    user: AuthUser | null;
    token: string | null;
    setUser: (user: AuthUser, token: string) => void;
    /** Patch fields on the current user (e.g. after a profile save) without touching the token. */
    updateUser: (patch: Partial<AuthUser>) => void;
    clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            user: null,
            token: null,
            setUser: (user, token) => set({ user, token }),
            updateUser: (patch) =>
                set((state) =>
                    state.user ? { user: { ...state.user, ...patch } } : state
                ),
            clearAuth: () => set({ user: null, token: null }),
        }),
        {
            name: "auth-storage",
        }
    )
);
