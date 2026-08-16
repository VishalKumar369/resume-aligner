import "@testing-library/jest-dom/vitest";

import React from "react";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

// --------------------------------------------------------------- module mocks

// The App Router hooks throw outside a real Next tree; route through the shared
// mock in tests/mocks/router.ts instead.
vi.mock("next/navigation", async () => {
    const { routerMock, getPathname } = await import("./mocks/router");
    return {
        useRouter: () => routerMock,
        usePathname: () => getPathname(),
        useSearchParams: () => new URLSearchParams(),
        useParams: () => ({}),
        redirect: vi.fn(),
        notFound: vi.fn(),
    };
});

// next/link expects router context for prefetching. A plain anchor keeps the
// part we actually assert on — the href we build — and drops the rest.
vi.mock("next/link", () => ({
    default: React.forwardRef<HTMLAnchorElement, Record<string, unknown>>(
        ({ href, children, prefetch: _prefetch, replace: _replace, scroll: _scroll, ...rest }, ref) =>
            React.createElement(
                "a",
                { href: typeof href === "string" ? href : String(href), ref, ...rest },
                children as React.ReactNode
            )
    ),
}));

vi.mock("framer-motion", async () => await import("./mocks/framerMotion"));

// ----------------------------------------------------------------- jsdom gaps

// jsdom ships none of these; components (and recharts) call them on mount.
if (!window.matchMedia) {
    window.matchMedia = ((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
    })) as unknown as typeof window.matchMedia;
}

class ObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() {
        return [];
    }
}

if (!globalThis.ResizeObserver) {
    globalThis.ResizeObserver = ObserverStub as unknown as typeof ResizeObserver;
}
if (!globalThis.IntersectionObserver) {
    globalThis.IntersectionObserver = ObserverStub as unknown as typeof IntersectionObserver;
}

// ------------------------------------------------------------- per-test reset

beforeEach(async () => {
    const { resetRouter } = await import("./mocks/router");
    const { useAuthStore } = await import("@/store/authStore");

    resetRouter();
    // The auth store persists to localStorage, so state would otherwise leak
    // from one test into the next.
    localStorage.clear();
    useAuthStore.setState({ user: null, token: null });
});

afterEach(() => {
    cleanup();
});
