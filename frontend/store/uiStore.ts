import { create } from "zustand";

interface UiState {
    // Whether the off-canvas navigation drawer is open on small screens.
    mobileNavOpen: boolean;
    openMobileNav: () => void;
    closeMobileNav: () => void;
    toggleMobileNav: () => void;
}

export const useUiStore = create<UiState>((set) => ({
    mobileNavOpen: false,
    openMobileNav: () => set({ mobileNavOpen: true }),
    closeMobileNav: () => set({ mobileNavOpen: false }),
    toggleMobileNav: () => set((state) => ({ mobileNavOpen: !state.mobileNavOpen })),
}));
