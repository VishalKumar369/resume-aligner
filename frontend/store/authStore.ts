import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
    user: { id: string; name: string; email: string } | null;
    token: string | null;
    setUser: (user: AuthState["user"], token: string) => void;
    clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            user: null,
            token: null,
            setUser: (user, token) => set({ user, token }),
            clearAuth: () => set({ user: null, token: null }),
        }),
        {
            name: "auth-storage",
        }
    )
);
